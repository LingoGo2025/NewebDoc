"""index.html 的內容區與產生區：抽取、合併（init／upgrade／build_engine 共用）。

index.html 分三種區域：
- 內容區（專案自己維護）：<!-- [slot:名稱] -->…<!-- [/slot:名稱] -->；樣式用 /* [slot:名稱] */…/* [/slot:名稱] */
- 產生區（工具產生）：網站地圖、#project-config、#project-theme（index_build.py）、#sequence-flow-data（flow_sync.py）
- 其餘都是引擎（樣式、燈箱、流程位置、完整度），升級時整份換成新版範本
"""
from __future__ import annotations

import re

SLOTS = ["title", "project-css", "hero", "architecture", "cards", "external-intro", "migration", "regulations", "footer"]

_HTML = r"(<!-- \[slot:{n}\] -->)(.*?)(<!-- \[/slot:{n}\] -->)"
_CSS = r"(/\* \[slot:{n}\] \*/)(.*?)(/\* \[/slot:{n}\] \*/)"
FOLD_NUM_RE = re.compile(r'(<span class="fold-num" aria-hidden="true">)\d+(</span>)')
GENERATED = {
    "sitemap": re.compile(r"(<!-- \[sitemap:begin\][^\n]*-->\n)(.*?)(<!-- \[sitemap:end\] -->)", re.S),
    "project-config": re.compile(r'(<script type="application/json" id="project-config">)(.*?)(</script>)', re.S),
    "project-theme": re.compile(r'(<style id="project-theme">)(.*?)(</style>)', re.S),
    "sequence-flow-data": re.compile(r'(<script type="application/json" id="sequence-flow-data">)(.*?)(</script>)', re.S),
}


def slot_re(name: str) -> re.Pattern:
    pat = _CSS if name == "project-css" else _HTML
    return re.compile(pat.format(n=re.escape(name)), re.S)


def extract(text: str) -> dict[str, str]:
    """內容區與產生區的內容（不含標記）。缺少的區域不列入。"""
    out: dict[str, str] = {}
    for name in SLOTS:
        m = slot_re(name).search(text)
        if m:
            out[name] = m.group(2)
    for name, rx in GENERATED.items():
        m = rx.search(text)
        if m:
            out[name] = m.group(2)
    return out


def fill(template: str, values: dict[str, str]) -> str:
    """把 values 填進 template 的同名區域；values 沒有的區域維持 template 原內容。"""
    for name in SLOTS:
        if name in values:
            template = slot_re(name).sub(lambda m: m.group(1) + values[name] + m.group(3), template, count=1)
    for name, rx in GENERATED.items():
        if name in values:
            template = rx.sub(lambda m: m.group(1) + values[name] + m.group(3), template, count=1)
    return template


def merge(template: str, project: str) -> tuple[str, list[str]]:
    """升級：新版範本（引擎）＋專案 index.html 的內容區與產生區。回傳 (結果, 提醒)。"""
    values = extract(project)
    notes = [f"專案 index.html 沒有內容區「{n}」，沿用範本預設內容" for n in SLOTS if n not in values]
    notes += [f"專案 index.html 沒有產生區「{n}」，請執行對應工具重產" for n in GENERATED if n not in values]
    return renumber(fill(template, values)), notes


def renumber(text: str) -> str:
    """首頁折疊區塊導引數字依序重編（與 index_build.py 相同）。"""
    counter = iter(range(1, 1000))
    return FOLD_NUM_RE.sub(lambda m: f"{m.group(1)}{next(counter)}{m.group(2)}", text)
