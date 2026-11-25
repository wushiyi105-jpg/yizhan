"""离线模式:只做术语替换与排版清理。

真正把一句话译成另一种语言,规则引擎做不到——硬做出来的东西
比不译更糟糕。所以离线时输出「术语已替换 + 待译分句」,并明说是草稿。
"""

from __future__ import annotations

import re

from . import tools


def _tidy(text: str) -> str:
    t = text.replace("\u3000", " ").replace("\t", " ")
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"\s+([，。；：！？、])", r"\1", t)
    lines = [ln.strip() for ln in re.split(r"\n+", t) if ln.strip()]
    return "\n".join(lines)


def translate(source: str, src: str, dst: str, terms: list[dict]) -> dict:
    direction = "zh2en" if src == "zh" else "en2zh"
    draft, n = tools.apply_terms(_tidy(source), terms, direction)
    lines = [f"【离线模式:术语已替换 {n} 处,整句翻译需要模型】", draft.strip(), ""]
    lines.append("待译分句:")
    for i, s in enumerate(tools.sentences(source), 1):
        lines.append(f"  {i}. {s}")
    return {
        "mode": "translate",
        "output": "\n".join(lines),
        "offline": True,
        "checks": ["离线模式:未做整句翻译,输出的是术语对齐草稿"],
        "terms_applied": n,
    }


def polish(output: str, src: str, dst: str, terms: list[dict]) -> dict:
    direction = "zh2en" if dst == "en" else "en2zh"
    body, n = tools.apply_terms(_tidy(output), terms, direction)
    bad = [] if n or not terms else ["术语表为空,无法校验一致性"]
    return {
        "mode": "polish",
        "output": body,
        "offline": True,
        "checks": [f"离线模式:统一术语 {n} 处"] + bad,
    }
