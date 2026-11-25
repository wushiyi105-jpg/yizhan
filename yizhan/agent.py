"""编排:模型翻译主路径 + 离线回退 + 硬校验。

翻译这件事,模型负责「说得像人话」,这里负责「数字没丢、术语没跑」。
check 不过就重试一次,再不过就把问题清单一起交给用户,不假装成功。
"""

from __future__ import annotations

from . import llm, mock, tools

MAX_STEPS = 12
MAX_RETRY = 2

LANG_NAME = {"zh": "中文", "en": "英文", "ja": "日文", "ko": "韩文", "fr": "法文", "de": "德文"}

TRANSLATE_SYSTEM = """你在做翻译。源语言:__SRC__,目标语言:__DST__。
必须遵守的术语表(原文术语 = 指定译法):
__TERMS__

输出 JSON:
{"output":"译文全文","notes":["翻译时做的取舍,一句话一条,最多 3 条"]}

规则:
- 术语表里的词,译文必须使用指定译法,一个都不许换。
- 原文里的数字与单位必须保留;年月日可以按目标语言习惯写(March 2026),但年份要留着。
- 不要解释、不要加译注、不要把 JSON 之外的话写进 output。
- 译文要像目标语言里的人写的,不要逐字硬译。"""

POLISH_SYSTEM = """你在润色一篇已经译好的稿子。目标语言:__DST__。
术语表(必须保持一致):
__TERMS__

输出 JSON:
{"output":"润色后的译文","notes":["改了什么,一句话一条"]}

规则:
- 只改表达,不改事实、不改数字、不改术语。
- 不要为了通顺删掉信息。"""


def _use_model(config: dict | None, force_mock: bool) -> bool:
    if force_mock:
        return False
    return bool({**llm.default_config(), **(config or {})}.get("api_key"))


def _cfg(config: dict | None) -> dict:
    return {**llm.default_config(), **(config or {})}


def _chat(messages, config, max_tokens=1600) -> str:
    return llm.chat(messages, config=_cfg(config), temperature=0.2, max_tokens=max_tokens)


def check(source: str, output: str, src: str, dst: str, terms: list[dict]) -> list[str]:
    """硬校验:数字、术语、语言残留。返回问题清单,空表示通过。"""
    problems = []
    lost = tools.missing_numbers(source, output)
    if lost:
        problems.append("译文丢了原文的数字:" + "、".join(lost[:5]))
    problems += tools.term_check(source, output, terms, src, dst)
    if dst == "en" and tools.han_ratio(output) > 0.15:
        problems.append(f"目标是英文,但译文汉字占比 {tools.han_ratio(output)}")
    if dst == "zh" and not tools.han_count(output):
        problems.append("目标是中文,但译文里没有汉字")
    if not output.strip():
        problems.append("译文为空")
    return problems


def translate(doc: dict, terms: list[dict], config: dict | None = None, force_mock: bool = False) -> dict:
    src, dst, source = doc["src_lang"], doc["dst_lang"], doc["source"]
    if not _use_model(config, force_mock):
        r = mock.translate(source, src, dst, terms)
        r["problems"] = []
        return r

    system = TRANSLATE_SYSTEM.replace("__SRC__", LANG_NAME.get(src, src)).replace(
        "__DST__", LANG_NAME.get(dst, dst)).replace("__TERMS__", tools.glossary_text(terms) or "(无)")
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"原文:\n{source}"},
    ]
    last = {}
    for attempt in range(MAX_RETRY):
        raw = _chat(messages, config, max_tokens=min(8000, max(1600, len(source) * 4)))
        data = llm.extract_json(raw)
        out = str(data.get("output", "")).strip()
        problems = check(source, out, src, dst, terms)
        if not problems:
            return {"mode": "translate", "output": out, "notes": data.get("notes", []),
                    "checks": ["硬校验通过:数字未丢、术语一致"], "offline": False}
        last = {"mode": "translate", "output": out, "notes": data.get("notes", []), "checks": problems,
                "offline": False, "rejected": True}
        messages += [
            {"role": "assistant", "content": raw},
            {"role": "user", "content": "上一版有问题:" + ";".join(problems) + "。请修正后重新输出 JSON。"},
        ]
    return last


def polish(output: str, src: str, dst: str, terms: list[dict], config: dict | None = None,
           force_mock: bool = False) -> dict:
    if not _use_model(config, force_mock):
        return mock.polish(output, src, dst, terms)
    system = POLISH_SYSTEM.replace("__DST__", LANG_NAME.get(dst, dst)).replace(
        "__TERMS__", tools.glossary_text(terms) or "(无)")
    raw = _chat([
        {"role": "system", "content": system},
        {"role": "user", "content": f"待润色的译文:\n{output}"},
    ], config, max_tokens=1400)
    data = llm.extract_json(raw)
    body = str(data.get("output", "")).strip()
    problems = tools.term_check(output, body, terms, dst, "zh" if dst == "en" else "en")
    return {"mode": "polish", "output": body or output, "notes": data.get("notes", []),
            "checks": problems or ["硬校验通过:术语一致"], "rejected": bool(problems), "offline": False}
