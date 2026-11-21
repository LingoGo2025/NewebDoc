#!/usr/bin/env python3
"""index.html 產生：網站地圖區塊與專案設定，由 網站地圖.md 與 project.json 產生。

用法：
  python3 scripts/index_build.py            # 重產網站地圖區塊與專案設定 JSON
  python3 scripts/index_build.py --check    # 只檢查是否已同步（不寫檔）

產生的範圍（不手動編輯）：
  - `<!-- [sitemap:begin] -->`～`<!-- [sitemap:end] -->`：網站地圖各區域、節點與按鈕。
      區域順序與欄位堆疊依 project.json › regions、index.layout；
      節點與按鈕依 網站地圖.md「網站地圖節點」章（「- 地圖說明：」為卡片簡短版，
      按鈕子項「- 說明／類似／管理：」為燈箱說明與相關頁面）；
      頁面按鈕標題取自 screens/ 的 SVG 檔名，API 按鈕連到節點內「- 流程圖：」。
  - `<script type="application/json" id="project-config">`：燈箱腳本用的區域名稱、
      後台區域（流程位置標註區域）與頁面 ID 字首順序（前台 → 後台，決定「管理頁面／結果頁面」方向）。
  - `<style id="project-theme">`：index.html 主色（--teal、--teal-dark、--ink），取自 project.json › theme 的 primary、primary_dark、ink。
  - 首頁折疊區塊的導引數字 `<span class="fold-num">n</span>`：依畫面由上而下重新編號。
內容區 `<!-- [slot:名稱] -->`～`<!-- [/slot:名稱] -->`（標題、頁首、架構圖說明、說明卡、外部系統引言、
移轉計畫、相關法規、頁尾、專案樣式）由專案自行維護，本工具不改；升級引擎時只保留內容區與產生區。
改網站地圖.md 或 project.json 的區域設定後執行本工具，再執行 check.py。
"""
from __future__ import annotations

import html
import json
import re
import sys

from _common import API_RE, CONFIG, INDEX, PAGE_PREFIXES, ROOT, SITEMAP, THEME, read, screen_files, screen_name, sitemap_tree

BEGIN = "<!-- [sitemap:begin] 由 scripts/index_build.py 依網站地圖.md 產生，不手動編輯 -->"
END = "<!-- [sitemap:end] -->"
SITEMAP_RE = re.compile(r"<!-- \[sitemap:begin\][^\n]*-->\n.*?<!-- \[sitemap:end\] -->\n", re.S)
CONFIG_RE = re.compile(r'<script type="application/json" id="project-config">.*?</script>\n', re.S)
THEME_RE = re.compile(r'<style id="project-theme">.*?</style>', re.S)
FLOW_DATA_TAG = '<script type="application/json" id="sequence-flow-data">'
FOLD_NUM_RE = re.compile(r'(<span class="fold-num" aria-hidden="true">)\d+(</span>)')


def attr(value: str) -> str:
    return html.escape(value, quote=True)


def text(value: str) -> str:
    return html.escape(value, quote=False)


def render_sitemap(errors: list[str]) -> str:
    regions = {r.name: r for r in sitemap_tree()}
    by_column = {r["column"]: r for r in CONFIG["regions"]}
    screens = screen_files()

    def button(b, column: str) -> str:
        if API_RE.match(b.id):
            if not b.flow:
                errors.append(f"{SITEMAP.name} 第 {b.line} 行：{b.id} 沒有「- 流程圖：`…`」")
            href, title, label = b.flow, f"{b.id} {b.text}", b.text
        else:
            path = screens.get(b.id)
            if path is None:
                errors.append(f"{SITEMAP.name} 第 {b.line} 行：{b.id} 在 screens/ 找不到 SVG")
                href, title = "", b.id
            else:
                href, title = f"screens/{path.name}", f"{b.id} {screen_name(path)}"
            label = title
        if not b.desc:
            errors.append(f"{SITEMAP.name} 第 {b.line} 行：{b.id} 缺少「  - 說明：」")
        return (f'<a class="screen-ref" href="{attr(href)}" data-lightbox="1" data-image="{attr(href)}" '
                f'data-title="{attr(title)}" data-description="{attr(b.desc)}" data-svg="{attr(href)}" '
                f'data-screen-id="{b.id}" data-page-group="{column}" data-similar="{",".join(b.similar)}" '
                f'data-manage="{",".join(b.manage)}">{text(label)}</a>')

    def article(column: str) -> str:
        cfg = by_column[column]
        region = regions.get(cfg["name"])
        if region is None:
            errors.append(f"{SITEMAP.name} 沒有區域「### {cfg['name']}」（project.json › regions）")
            return ""
        ids = [b.id for nd in region.nodes for b in nd.buttons]
        count = "" if any(API_RE.match(i) for i in ids) else f'<span class="area-count">共 {len(ids)} 頁</span>'
        nodes = "\n".join(
            f'<div class="mapnode"><strong>{text(nd.title)}</strong><p>{text(nd.map_desc)}</p><div class="refs">\n'
            + "".join(button(b, column) + "\n" for b in nd.buttons) + "</div></div>"
            for nd in region.nodes)
        return (f'<article class="mapcolumn {column}-map"><header class="mapcolumn-head"><h3>{text(region.name)}{count}</h3>'
                f'<p class="mapcolumn-subtitle">{text(region.map_desc)}</p></header>\n{nodes}</article>')

    layout = CONFIG.get("index", {}).get("layout") or [[r["column"]] for r in CONFIG["regions"]]
    placed = [c for group in layout for c in group]
    for column in by_column:
        if column not in placed:
            errors.append(f"project.json › index.layout 沒有排入區域 {column}")
    for name in regions:
        if name not in {r["name"] for r in CONFIG["regions"]}:
            errors.append(f"{SITEMAP.name} 的區域「{name}」不在 project.json › regions")
    cols = []
    for group in layout:
        arts = [article(c) for c in group if c in by_column]
        cols.append(arts[0] if len(arts) == 1 else '<div class="map-stack">\n' + "\n".join(arts) + "\n</div>")
    return "\n".join(cols) + "\n"


def project_config() -> str:
    data = {
        "regions": [{"column": r["column"], "name": r["name"], "backend": bool(r.get("backend"))} for r in CONFIG["regions"]],
        "pagePrefixes": PAGE_PREFIXES,
    }
    return ('<script type="application/json" id="project-config">'
            + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "</script>\n")


def build(source: str, errors: list[str]) -> str:
    block = BEGIN + "\n" + render_sitemap(errors) + END + "\n"
    if SITEMAP_RE.search(source):
        source = SITEMAP_RE.sub(lambda _: block, source, count=1)
    else:
        errors.append(f"{INDEX.name} 找不到 {BEGIN.split(' ')[1]} 標記（網站地圖區塊）")
    cfg = project_config()
    if CONFIG_RE.search(source):
        source = CONFIG_RE.sub(lambda _: cfg, source, count=1)
    elif FLOW_DATA_TAG in source:
        source = source.replace(FLOW_DATA_TAG, cfg + FLOW_DATA_TAG, 1)
    else:
        errors.append(f"{INDEX.name} 找不到放專案設定的位置（{FLOW_DATA_TAG}）")
    theme = (f'<style id="project-theme">:root{{--teal:{THEME["primary"]};--teal-dark:{THEME["primary_dark"]};'
             f'--ink:{THEME["ink"]}}}</style>')
    if THEME_RE.search(source):
        source = THEME_RE.sub(lambda _: theme, source, count=1)
    else:
        source = source.replace("</head>", theme + "\n</head>", 1)
    counter = iter(range(1, 1000))
    return FOLD_NUM_RE.sub(lambda m: f"{m.group(1)}{next(counter)}{m.group(2)}", source)


def status() -> tuple[list[str], bool]:
    """(錯誤清單, 是否過期)；供 check.py 使用。"""
    errors: list[str] = []
    source = read(INDEX)
    return errors, build(source, errors) != source


def main() -> int:
    check = "--check" in sys.argv[1:]
    errors: list[str] = []
    source = read(INDEX)
    result = build(source, errors)
    for e in errors:
        print("錯誤｜" + e)
    if errors:
        return 1
    if result == source:
        print(f"OK｜{INDEX.name} 網站地圖與專案設定已同步")
        return 0
    if check:
        print(f"錯誤｜{INDEX.name} 網站地圖或專案設定未同步：請執行 python3 scripts/index_build.py")
        return 1
    INDEX.write_text(result, encoding="utf-8")
    print(f"已更新｜{INDEX.name} 網站地圖與專案設定")
    return 0


if __name__ == "__main__":
    sys.exit(main())
