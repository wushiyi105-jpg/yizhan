# 译站 yizhan

[![test](https://github.com/wushiyi105-jpg/yizhan/workflows/test/badge.svg)](https://github.com/wushiyi105-jpg/yizhan/actions)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![codecov](https://codecov.io/gh/wushiyi105-jpg/yizhan/branch/main/graph/badge.svg)](https://codecov.io/gh/wushiyi105-jpg/yizhan)

![示例](assets/demo.gif)

粘贴文本或导入文件,中英日多语言互译,术语表管住"同一个词只能有一种译法"。

我做产品文档翻译时被两件事坑过:数字被悄悄改掉(1,200 变成 1200 还是 12,00 全靠运气),以及同一个术语在全文里译出三种说法。译站把这两件事都做成硬校验——**译文回来后,先在本地比数字、比术语,再谈通顺**。

## 功能特性

- **多语言互译**:中 / 英 / 日 / 韩 / 法 / 德,源语言目标语言都能指定。
- **术语表**:`terms add` 之后,每次翻译都会把术语表塞进系统提示,并在译后逐条核对——原文出现了「待办清单」,译文里就必须有 `to-do list`。
- **数字硬校验**:丢数字直接判不通过;**但年月日豁免**——「3 月」写成 March 不算丢数字,否则模型会被逼着写 "the 3rd month" 这种怪句子。
- **不合格自动重试**:校验不过会把问题清单回灌给模型再译一遍,两次不过就保留上一版,把问题列给你,不假装成功。
- **译文润色**:只改表达,术语与数字仍受同一套校验约束。
- **离线模式**:只做术语替换与排版清理,并明确标注"整句翻译需要模型"——规则引擎硬译出来的东西比不译更糟。
- **双入口**:CLI 批处理,网页粘贴即译。

## 快速开始

```bash
git clone https://github.com/wushiyi105-jpg/yizhan.git
cd yizhan
python -m yizhan terms add 待办清单 "to-do list"
python -m yizhan add doc.txt --src zh --dst en
python -m yizhan translate 1
```

不配 key 自动进离线模式;接模型:

```bash
cp .env.example .env
# 填 LLM_API_KEY,默认 https://api.deepseek.com + deepseek-flash
```

```bash
LLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4 LLM_MODEL=glm-4.6 python -m yizhan translate 1
```

网页:

```bash
python -m yizhan web --port 8767
# http://127.0.0.1:8767
```

Docker 运行(容器内用默认端口 8000):

```bash
docker build -t yizhan .
docker run -p 8000:8000 yizhan
```

## 命令参考

| 命令 | 作用 |
| --- | --- |
| `add <file> [--src zh] [--dst en]` | 导入原文,`-` 从 stdin 读 |
| `docs` | 译稿列表 |
| `show <稿>` | 原文与译文概况 |
| `translate <稿>` | 翻译并入库 |
| `polish <稿>` | 润色已有译文 |
| `terms add <中文> <英文> [--note]` | 加术语 |
| `terms list` | 术语表 |
| `terms rm --id <n>` | 删术语 |
| `stats` / `web` | 统计 / Web UI |

全局开关 `--mock`、`--json`、`--model`、`--base-url`、`--api-key`、`--db`,放在子命令前后都认。

## 🤔 为什么不用通用大模型直接问

通用模型翻译得比很多工具顺,但译站补的是它做不到的三件事:

1. **数字与术语不丢** —— 译文出来后本地逐项核对:原文里的数字、日期、型号有没有少,术语表里的词有没有按约定译;缺了就退回重译,最多两轮。通用模型最常见的错是把「3 个工作日」译成「several days」,还看不出来。
2. **术语表说了算** —— 同一个词在你的行业里怎么译,由本地术语表决定,双向生效(中英互译都按同一套)。通用对话每次译法可能不同,一份说明书里出现三种叫法。
3. **文档与术语在本地** —— 原文、译文、术语表都存在本机,合同和产品文档不上传;调模型时只发当前这一段。
4. **离线能顶一部分** —— 没 key 时用术语表做替换、把长句切成待译分句,并明确说「这一版没有成句翻译」,不假装译完。

## 🎯 适用场景

- **产品文档中英互译**:说明书、帮助中心文章,术语表先定好,译完核对数字和型号,不会把「充电 2 小时」译成「charge for a while」。
- **合同/条款对照**:中英双语合同,数字和日期错一个都麻烦,术语表把「不可抗力」「违约金」固定下来。
- **论文摘要**:一段摘要多语言版本,术语统一,审稿人不会因为译名前后不一致挑刺。

## 🗺 Roadmap

- **翻译记忆库**:同一句话第二次出现直接复用上次译文,保证全文一致。
- **术语冲突检测**:术语表里同一个词有两种译法时提前报错,而不是译完才发现。
- **双语对照导出**:原文与译文逐段并排,方便校对。
- **术语表导入导出**:支持 CSV,团队共用一份。
- **分句质量提示**:长句切分后标出哪些句子结构复杂、建议人工看一眼。

## ❓ FAQ

**API key 从哪来?**
项目不带 key。默认接 DeepSeek(`https://api.deepseek.com`),注册后填 `LLM_API_KEY`;任何 OpenAI 兼容端点都能换。

**数据存在哪,会上传吗?**
原文、译文与术语表在本地 SQLite;调模型时只发当前这一段和术语表里相关的词,不发整份文档。

**没有 key 能不能用?**
能,但只做术语替换与分句,不给成句翻译。它会在输出里直说这一版是半成品,不冒充译文。

**怎么换模型?**
改 `LLM_BASE_URL`、`LLM_MODEL`、`LLM_API_KEY`,或用 `--model` 临时覆盖。

**为什么我的译文被退回重译?**
因为数字或术语没对上。退回的次数和原因都写在输出里,你能看到是哪一项没过,而不是只收到一句「失败了」。

## 工作原理

```mermaid
flowchart TD
    CLI["cli.py<br/>argparse 子命令"] --> AGENT
    WEB["web.py<br/>ThreadingHTTPServer + 单页"] --> AGENT
    AGENT["agent.py<br/>翻译 / 润色 / 重试"] -->|有 key| LLM["llm.py<br/>urllib 直连,截断自动加预算"]
    AGENT -->|无 key 或 --mock| MOCK["mock.py<br/>术语替换 + 待译分句"]
    AGENT --> CHECK["tools.py<br/>数字比对 / 术语核对 / 汉字残留"]
    CHECK --> DB["db.py<br/>terms + docs,threading.Lock"]
```

三处取舍:

1. **数字比对带日期豁免**。`tools.date_numbers` 找出「3 月」「15 日」这类月日数字,从必查集合里剔除;年份仍然必查。第一版没做这个豁免,模型为了保住数字被逼出 "the 3rd month of 2026",比丢数字还难看。
2. **术语是双向核对**。中译英查中文术语是否出现、对应英文是否给出;英译中反过来查。术语表为空时明确提示"无法校验一致性",不留假通过。
3. **重试两次就停**。硬校验失败会把问题回灌并要求重写;两次还不过就停手,把译文和问题一起交出来——继续硬试只会烧 token。

另外 `llm.py` 处理了输出被 `max_tokens` 截断的情况:看到 `finish_reason=length` 就把预算翻倍重试,避免把半截 JSON 当结果解析。这个坑在长译文上踩过一次,记忆深刻。

## 目录结构

```
yizhan/
├── yizhan/
│   ├── __init__.py / __main__.py
│   ├── llm.py     # OpenAI 兼容客户端 + .env 加载 + 截断重试
│   ├── db.py      # terms + docs(线程安全)
│   ├── tools.py   # 数字/汉字/术语/分句
│   ├── mock.py    # 离线术语对齐草稿
│   ├── agent.py   # 翻译与润色 + 硬校验 + 重试
│   ├── cli.py     # 命令行
│   └── web.py     # Web UI
├── data/doc-sample.json
├── tests/test_yizhan.py
├── assets/demo.gif
├── .github/workflows/test.yml
├── pyproject.toml
├── README.md / README.en.md
└── CHANGELOG.md / SECURITY.md / CODE_OF_CONDUCT.md / CONTRIBUTING.md
```

## 作者

shiyi · GitHub [@wushiyi105-jpg](https://github.com/wushiyi105-jpg) · wushiyi105@gmail.com

MIT License,Copyright (c) 2026 wushiyi105-jpg
