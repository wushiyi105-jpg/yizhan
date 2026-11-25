"""纯函数层:数字、汉字残留、术语一致性、分句。

翻译最容易出的两类错:数字被改(1.5 变 15)、术语各译各的。
这两类都能在本地查出来,不用问模型。
"""

from __future__ import annotations

import re

_NUM = re.compile(r"\d+(?:[.,]\d+)*%?")
_CJK = re.compile(r"[\u4e00-\u9fff]")
_WORD = re.compile(r"[A-Za-z]+")


def numbers(text: str) -> list[str]:
    """数字原样抽出,统一去掉千分位逗号,便于前后比对。"""
    return [n.replace(",", "") for n in _NUM.findall(text or "")]


_DATE = re.compile(r"(\d{1,4})\s*(月|日|号)")


def date_numbers(text: str) -> set[str]:
    """「3 月」「15 日」这类月日数字:目标语言里通常写成 March / 15th,不该强求原样。"""
    return {m.group(1) for m in _DATE.finditer(text or "")}


def missing_numbers(source: str, output: str) -> list[str]:
    """译文里丢掉的数字。翻译丢数字比译错更糟。

    年月日里的月、日豁免——英文写 March 是天经地义,不算丢数字。
    """
    skip = date_numbers(source)
    out = set(numbers(output))
    return [n for n in numbers(source) if n not in out and n not in skip]


def han_count(text: str) -> int:
    return len(_CJK.findall(text or ""))


def han_ratio(text: str) -> float:
    t = re.sub(r"\s", "", text or "")
    return round(han_count(t) / len(t), 3) if t else 0.0


def word_count(text: str) -> int:
    return len(_WORD.findall(text or ""))


def sentences(text: str) -> list[str]:
    out = [s.strip() for s in re.split(r"(?<=[。！？!?.;])\s*", text or "") if s.strip()]
    return out


def term_check(source: str, output: str, terms: list[dict], src: str, dst: str) -> list[str]:
    """术语一致性:原文出现过的术语,译文里必须用约定的译法。"""
    problems = []
    for t in terms:
        if src == "zh" and dst == "en":
            if t["zh"] in source and t["en"] not in output:
                problems.append(f"术语「{t['zh']}」应译为「{t['en']}」,译文里没有")
        elif src == "en" and dst == "zh":
            if t["en"].lower() in source.lower() and t["zh"] not in output:
                problems.append(f"术语「{t['en']}」应译为「{t['zh']}」,译文里没有")
    return problems


def apply_terms(text: str, terms: list[dict], direction: str) -> tuple[str, int]:
    """离线模式下能做的:把术语表里的词换掉。长词优先,避免被短词切断。"""
    n = 0
    pairs = [(t["zh"], t["en"]) for t in terms] if direction == "zh2en" else [(t["en"], t["zh"]) for t in terms]
    for a, b in sorted(pairs, key=lambda p: -len(p[0])):
        if a in text:
            n += text.count(a)
            text = text.replace(a, b)
    return text, n


def glossary_text(terms: list[dict]) -> str:
    return "\n".join(f"{t['zh']} = {t['en']}" + (f"  ({t['note']})" if t.get("note") else "") for t in terms)


# ---------------------------------------------------------------------------
# 工具注册表(ReAct:让模型边译边查术语)
# ---------------------------------------------------------------------------
TOOLS = [
    {"name": "lookup_term", "desc": "按中文或英文查术语表。", "args": {"q": "要查的词"}},
    {"name": "list_terms", "desc": "列出全部术语。", "args": {}},
    {"name": "count_numbers", "desc": "数原文里的数字,校对时用。", "args": {}},
]


def tool_list_text() -> str:
    return "\n".join(f"- {t['name']}({', '.join(t['args']) or '无'}):{t['desc']}" for t in TOOLS)


def execute(name: str, args: dict, terms: list[dict], source: str) -> dict:
    if name == "lookup_term":
        q = str(args.get("q", "")).strip().lower()
        hits = [t for t in terms if q and (q in t["zh"].lower() or q in t["en"].lower())]
        return {"hits": hits}
    if name == "list_terms":
        return {"terms": terms}
    if name == "count_numbers":
        return {"numbers": numbers(source), "count": len(numbers(source))}
    return {"error": f"未知工具: {name}"}


def dump(obj) -> str:
    import json

    return json.dumps(obj, ensure_ascii=False)
