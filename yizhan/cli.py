"""命令行入口:python -m yizhan <命令> [选项]。"""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__, agent, llm, tools
from . import db as dbmod
from .llm import LLMError

MOCK_BANNER = (
    "⚠️  当前为离线模式(未配置 LLM_API_KEY),只做术语替换,不整句翻译。\n"
    "   在 .env 填入 LLM_API_KEY 后,翻译与润色由模型完成。\n"
)

_OPEN: list = []


def _db(args) -> dbmod.Database:
    db = dbmod.Database(getattr(args, "db", None))
    _OPEN.append(db)
    return db


def _close_all() -> None:
    for d in _OPEN:
        d.close()
    _OPEN.clear()


def _read_input(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    with open(path, encoding="utf-8") as f:
        return f.read()


def render_result(r: dict) -> str:
    head = f"🌐 {r['mode']}"
    if r.get("offline"):
        head += "  ·  离线模式"
    lines = [head]
    for c in r.get("checks", []):
        lines.append(f"  · {c}")
    if r.get("rejected"):
        lines.append("  ! 校验没过,上一版已保留,可以手动改")
    lines += ["", r.get("output", "")]
    for n in r.get("notes", []):
        lines.append(f"  - {n}")
    return "\n".join(lines)


def cmd_add(args):
    db = _db(args)
    text = _read_input(args.file)
    if not text.strip():
        print("❌ 原文为空", file=sys.stderr)
        sys.exit(1)
    did = db.add_doc(args.src, args.dst, text)
    print(f"✅ 已导入 [{did}] {args.src} → {args.dst}  {len(text)} 字符")


def cmd_docs(args):
    db = _db(args)
    ds = db.list_docs()
    if args.json:
        print(json.dumps(ds, ensure_ascii=False, indent=2))
        return
    if not ds:
        print("(空)用 yizhan add 导入原文")
        return
    for d in ds:
        print(f"[{d['id']}] {d['src_lang']}→{d['dst_lang']}  {d['chars']} 字符  {d['created_at']}  {d['head']}")


def cmd_show(args):
    db = _db(args)
    d = db.get_doc(args.key)
    if not d:
        print(f"❌ 找不到译稿:{args.key}", file=sys.stderr)
        sys.exit(1)
    print(f"🌐 [{d['id']}] {d['src_lang']}→{d['dst_lang']}  {d['created_at']}")
    print(f"数字 {len(tools.numbers(d['source']))} 处 / 句子 {len(tools.sentences(d['source']))} 条")
    print("\n原文:\n" + d["source"][:400])
    if d["output"]:
        print("\n译文:\n" + d["output"][:400])


def cmd_translate(args):
    db = _db(args)
    d = db.get_doc(args.key)
    if not d:
        print(f"❌ 找不到译稿:{args.key}", file=sys.stderr)
        sys.exit(1)
    terms = db.list_terms()
    r = agent.translate(d, terms, config=llm.config_from_args(args), force_mock=args.mock)
    if r.get("output") and not r.get("rejected"):
        db.update_output(d["id"], r["output"])
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return
    print(render_result(r))
    if r.get("output") and not r.get("rejected"):
        print("\n✅ 译文已入库")


def cmd_polish(args):
    db = _db(args)
    d = db.get_doc(args.key)
    if not d:
        print(f"❌ 找不到译稿:{args.key}", file=sys.stderr)
        sys.exit(1)
    if not d["output"]:
        print("❌ 这篇还没有译文,先 translate", file=sys.stderr)
        sys.exit(1)
    r = agent.polish(d["output"], d["src_lang"], d["dst_lang"], db.list_terms(),
                     config=llm.config_from_args(args), force_mock=args.mock)
    if not r.get("rejected"):
        db.update_output(d["id"], r["output"])
    print(json.dumps(r, ensure_ascii=False, indent=2) if args.json else render_result(r))


def cmd_terms(args):
    db = _db(args)
    if args.action == "add":
        tid = db.add_term(args.zh, args.en, args.note or "")
        print(f"✅ 术语 [{tid}] {args.zh} = {args.en}")
    elif args.action == "list":
        ts = db.list_terms()
        if args.json:
            print(json.dumps(ts, ensure_ascii=False, indent=2))
            return
        if not ts:
            print("(术语表为空)")
        for t in ts:
            note = f"  # {t['note']}" if t["note"] else ""
            print(f"[{t['id']}] {t['zh']} = {t['en']}{note}")
    elif args.action == "rm":
        ok = db.delete_term(args.term_id)
        print("🗑  已删除" if ok else "❌ 没有这条术语")


def cmd_stats(args):
    print(json.dumps(_db(args).stats(), ensure_ascii=False))


def cmd_web(args):
    from . import web

    web.serve(host=args.host, port=args.port, db_path=args.db, force_mock=args.mock)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="yizhan", description="译站 · 翻译助手:多语言互译、术语表、译文润色。")
    p.add_argument("--version", action="version", version=f"yizhan {__version__}")
    p.add_argument("--mock", action="store_true", help="强制离线模式(不调用模型)")
    p.add_argument("--json", action="store_true")
    p.add_argument("--model")
    p.add_argument("--base-url")
    p.add_argument("--api-key")
    p.add_argument("--db")

    sub = p.add_subparsers(dest="command", required=True)

    a = sub.add_parser("add", help="导入原文(文件或 - 读 stdin)")
    a.add_argument("file")
    a.add_argument("--src", default="zh", choices=list(agent.LANG_NAME))
    a.add_argument("--dst", default="en", choices=list(agent.LANG_NAME))
    a.set_defaults(func=cmd_add)

    ls = sub.add_parser("docs", help="列出译稿")
    ls.set_defaults(func=cmd_docs)

    sh = sub.add_parser("show", help="看一篇译稿")
    sh.add_argument("key")
    sh.set_defaults(func=cmd_show)

    tr = sub.add_parser("translate", help="翻译")
    tr.add_argument("key")
    tr.set_defaults(func=cmd_translate)

    po = sub.add_parser("polish", help="润色译文")
    po.add_argument("key")
    po.set_defaults(func=cmd_polish)

    tm = sub.add_parser("terms", help="术语表")
    tm.add_argument("action", choices=["add", "list", "rm"])
    tm.add_argument("zh", nargs="?")
    tm.add_argument("en", nargs="?")
    tm.add_argument("--note")
    tm.add_argument("--id", dest="term_id", type=int)

    def run_terms(args):
        if args.action == "add" and not (args.zh and args.en):
            print("❌ 需要中文与英文两个词:yizhan terms add 术语 translation", file=sys.stderr)
            sys.exit(1)
        if args.action == "rm" and not args.term_id:
            print("❌ 需要 --id", file=sys.stderr)
            sys.exit(1)
        cmd_terms(args)

    tm.set_defaults(func=run_terms)

    st = sub.add_parser("stats", help="统计")
    st.set_defaults(func=cmd_stats)

    wb = sub.add_parser("web", help="启动 Web 界面")
    wb.add_argument("--host", default="127.0.0.1")
    wb.add_argument("--port", type=int, default=8000)
    wb.set_defaults(func=cmd_web)
    return p


GLOBAL_FLAGS = ("--mock", "--json")
GLOBAL_OPTS = ("--model", "--base-url", "--api-key", "--db")


def hoist_globals(argv: list[str]) -> list[str]:
    """把全局开关挪到子命令前,顺手解决「--mock 写在后面报错」的坏体验。"""
    g, rest = [], []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in GLOBAL_FLAGS:
            g.append(a)
            i += 1
        elif a in GLOBAL_OPTS:
            g += [a, argv[i + 1]] if i + 1 < len(argv) else [a]
            i += 2
        elif any(a.startswith(o + "=") for o in GLOBAL_OPTS):
            g.append(a)
            i += 1
        else:
            rest.append(a)
            i += 1
    return g + rest


def main(argv=None):
    args = build_parser().parse_args(hoist_globals(list(sys.argv[1:] if argv is None else argv)))
    if not args.mock and args.command in ("translate", "polish"):
        if not llm.config_from_args(args).get("api_key"):
            print(MOCK_BANNER, file=sys.stderr)
    try:
        args.func(args)
    except LLMError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)
    finally:
        _close_all()


if __name__ == "__main__":
    main()
