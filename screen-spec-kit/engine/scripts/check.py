#!/usr/bin/env python3
"""一致性檢查：只列出問題，全部通過時只印一行。

用法：
  python3 scripts/check.py          # 錯誤（✗）與提醒（!）都列
  python3 scripts/check.py --errors # 只列錯誤

檢查項目：
  1. SVG 檔名：每個頁面 ID 恰有一個 SVG
  2. 規格：每頁有標題、錨點、正確 SVG 路徑；「對應流程」連結指向存在的流程段落
  3. 規格畫面文字清單是否與 SVG 一致（不一致時提示 sync 指令）
  4. 網站地圖.md：每個 ID 在各區（project.json › regions）中恰有一個按鈕、所屬區域正確、區域頁數表正確
  5. index.html：網站地圖按鈕唯一且在正確欄位、各欄「共 n 頁」、SVG 路徑、標題；不得殘留已移除的圖庫元素
  6. 流程：PUML／SVG 成對；PUML、規格、index.html 的頁面清單與標題一致；
     多頁流程有 @order 且與 @pages 相符；頁面圖例、樣式區塊與 index.html 流程資料已同步；
     不用 !theme；每個參與者都列在規格「流程圖參與者類別」表；
     流程 SVG 含所有 @pages 頁面 ID（否則視為尚未重新渲染）
  7. 共用選單：SVG 與「網站地圖.md › 共用選單」一致
  8. 用語檢查：依 project.json › term_rules，SVG 畫面不得出現指定用語（例：非賣品不得出現購物車、售價等商品用語）
  9. 網站地圖節點標題：Markdown 與 index.html 是否一致
 10. assets/svg_sources.js（燈箱選取文字用）是否與 SVG 一致
 11. assets/dev_notes.js（燈箱「開發說明」頁籤）是否與規格一致、各頁是否有 AI 補充與 SA 規格區塊；
     各 API 有「API 規格」區塊（介接資訊、傳送欄位、回傳欄位、加解密方式）與 AI 補充，index.html 有 API 模式頁籤
 12. 系統架構圖：architecture/ 的 PUML／SVG 成對、SVG 不比 PUML 舊；規格與 index.html 引用的架構圖檔存在；
     每個頁面 ID 都歸入規格「系統架構 › 業務模組」（「暫不歸入模組」除外）、表內 ID 存在；
     功能架構圖的業務模組與入口層頁面和規格一致；每張架構圖有讀圖說明與圖例（圖例不畫在圖內、
     規格圖例的色碼都用在圖上、圖上方塊的底色都列在圖例）；流程參與者不得使用「統一名稱」表中的舊名稱
 13. assets/inventory.js（首頁「文件內容與完整度」燈箱）是否與目前檔案一致；index.html 有載入該檔與按鈕
 新專案訪談中（規格有「〔待訪談第 n 階段〕」標記）時，該階段才會補的項目只列提醒，例如第 6 階段前頁面未歸入業務模組。
 16. AI 入口檔（AGENTS.md、CLAUDE.md 等，ai_entry.py 產生）與 專案規則.md、規範/README.md 是否存在且一致
 15. 引擎與 plugin（project.json › kit）：示範專案（engine_source）的引擎與 plugin 不同時提醒同步；
     其他專案在 plugin 有新版時提醒可升級（只提醒，不算錯誤）
 14. index.html 網站地圖區塊與專案設定（index_build.py 產生）是否與網站地圖.md、project.json 一致；
     網站地圖每個按鈕有「說明」子項；規格「外部系統」表的需求類別都列在「外部系統需求類別」表
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import nav
from flow_sync import DECL_RE, participant_category, synced_source
import svg_bundle
import dev_notes
import inventory
import index_build
import ai_entry
from interview_status import markers as interview_markers
from _common import (API_RE, ARCH, ARCH_FIGURES, CONFIG, FLOWS, FUNCTIONAL_FIGURE, INDEX_COLUMN, PAGE_RE, flow_palette, arch_label,
                     architecture_spec, expected_region, norm_name, INDEX, REGIONS, ROOT, SITEMAP, flow_list,
                     index_flow_data, index_refs, read, screen_files, screen_name,
                     duplicate_screen_ids, sitemap_buttons, sitemap_menus, sitemap_nodes,
                     spec_sections, svg_texts)

# 區域歸屬（expected_region、INDEX_COLUMN）與用語檢查規則（term_rules）都讀自 project.json
TERM_RULES = CONFIG.get("term_rules", [])
SITEMAP_NAME = SITEMAP.name

NAMES = {k: screen_name(v) for k, v in screen_files().items()}
API_IDS = {s.key for s in spec_sections() if API_RE.match(s.key)}   # 規格「## API 介接」章的 API
errors: list[str] = []
warns: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warns.append(msg)


def check_screens(files: dict[str, Path]) -> None:
    for pid, names in duplicate_screen_ids().items():
        err(f"[SVG] {pid} 有多個檔案：{'、'.join(names)}")


def check_spec(files: dict[str, Path], sections) -> None:
    by_key = {}
    for s in sections:
        by_key.setdefault(s.key, []).append(s)
    anchors = {s.anchor for s in sections}
    for pid, path in files.items():
        found = by_key.get(pid, [])
        if len(found) != 1:
            err(f"[規格] {pid} 頁面段落數量為 {len(found)}（應為 1）")
            continue
        s = found[0]
        if s.anchor != pid.lower():
            err(f"[規格] {pid} 錨點為 {s.anchor}（應為 {pid.lower()}）")
        rel = f"screens/{path.name}"
        if rel not in s.body:
            err(f"[規格] {pid} 的 SVG 畫面原稿路徑不是 {rel}")
        if not s.text_list:
            warn(f"[規格] {pid} 沒有畫面文字清單")
    for s in sections:
        for target in re.findall(r"\]\(#([^)]+)\)", s.body):
            if target not in anchors:
                err(f"[規格] {s.key} 連到不存在的段落 #{target}")
        for path in re.findall(r"`((?:screens|flows|architecture)/[^`]+\.(?:svg|puml))`", s.body):
            if not (ROOT / path).exists():
                err(f"[規格] {s.key} 引用的檔案不存在：{path}")
    for pid in [k for k in by_key if PAGE_RE.match(k)]:
        if pid not in files:
            err(f"[規格] {pid} 有規格段落但沒有 SVG")


def check_text_lists(files, sections) -> None:
    stale = [s.key for s in sections if s.key in files and s.text_list
             and s.text_list != svg_texts(files[s.key])]
    if stale:
        warn(f"[畫面文字] 規格清單與 SVG 不一致：{' '.join(stale)}"
             f" → python3 scripts/sync_screen_text.py {' '.join(stale)}")


def check_sitemap(files) -> None:
    buttons = sitemap_buttons()
    seen: dict[str, list[str]] = {}
    for region, items in buttons.items():
        for pid, _, line in items:
            seen.setdefault(pid, []).append(f"{region} L{line}")
            if expected_region(pid) != region:
                err(f"[{SITEMAP_NAME}] {pid} 列在「{region}」（應在「{expected_region(pid)}」）L{line}")
    for pid, where in seen.items():
        if len(where) > 1:
            err(f"[{SITEMAP_NAME}] {pid} 按鈕重複：{'、'.join(where)}")
    all_ids = set(files) | API_IDS
    for pid in sorted(all_ids - set(seen)):
        err(f"[{SITEMAP_NAME}] {pid} 沒有網站地圖按鈕")
    for pid in sorted(set(seen) - all_ids):
        err(f"[{SITEMAP_NAME}] 按鈕 {pid} 找不到對應的 SVG／流程圖")
    # 「全站區域」表格頁數
    text = read(SITEMAP)
    for region in REGIONS:   # 頁數欄不是純數字（如 API「2 API＋1 頁」）的列不比對
        m = re.search(rf"^\| {re.escape(region)} \|[^|]*\| (\d+) \|", text, re.M)
        actual = len(buttons[region])
        if m and int(m.group(1)) != actual:
            err(f"[{SITEMAP_NAME}] 全站區域表「{region}」寫 {m.group(1)} 張，實際按鈕 {actual} 個")


def check_index(files) -> None:
    html = read(INDEX)
    refs = index_refs(html)
    # 網站地圖欄位範圍
    cols = [(m.start(), m.group(1)) for m in re.finditer(r'class="mapcolumn ([a-z]+)-map"', html)]
    col_end = html.find('<details', html.find('id="sitemap"'))  # 網站地圖區塊之後的下一個折疊區塊
    def column_of(pos: int) -> str | None:
        name = None
        for start, col in cols:
            if pos >= start:
                name = col
        return name if cols and cols[0][0] <= pos < (col_end if col_end > 0 else len(html)) else None
    map_refs = [r for r in refs if r["class"] == "screen-ref"]
    seen: dict[str, int] = {}
    for r in map_refs:
        pid = r["screen-id"]
        seen[pid] = seen.get(pid, 0) + 1
        col = column_of(r["pos"])
        want = INDEX_COLUMN.get(expected_region(pid))
        if col != want:
            err(f"[index.html] 網站地圖 {pid} 位於 {col} 欄（應在 {want}）")
        src = r.get("svg") or r.get("image", "")
        if src and not (ROOT / src).exists():
            err(f"[index.html] {pid} 連到不存在的檔案：{src}")
    for pid, n in seen.items():
        if n > 1:
            err(f"[index.html] 網站地圖 {pid} 按鈕重複 {n} 次")
    for pid in sorted((set(files) | API_IDS) - set(seen)):
        err(f"[index.html] 網站地圖缺少 {pid} 按鈕")
    # 頁面按鈕的 SVG 路徑與標題（原圖庫卡片的檢查，圖庫已移除，改對網站地圖按鈕檢查）
    per_col: dict[str, int] = {}
    for r in map_refs:
        pid = r["screen-id"]
        path = files.get(pid)
        if not path:
            continue
        col = column_of(r["pos"])
        per_col[col] = per_col.get(col, 0) + 1
        if r.get("svg") != f"screens/{path.name}":
            err(f"[index.html] 網站地圖 {pid} 的 SVG 路徑為 {r.get('svg')}（應為 screens/{path.name}）")
        if r.get("title") != f"{pid} {screen_name(path)}":
            warn(f"[index.html] 網站地圖 {pid} 標題「{r.get('title')}」與檔名「{screen_name(path)}」不同")
    # 地圖欄位標題的「共 n 頁」
    for col, n in per_col.items():
        m = re.search(rf'class="mapcolumn {col}-map"><header[^>]*><h3>[^<]*<span class="area-count">共 (\d+) 頁', html)
        if m and int(m.group(1)) != n:
            err(f"[index.html] {col} 地圖欄位寫 {m.group(1)} 頁，實際 {n} 頁")
    if re.search(r'class="(?:[^"]*\s)?(?:preview|tab-panel|galleryfold)(?:\s[^"]*)?"', html):
        err("[index.html] 仍有已移除的頁面示意圖圖庫元素（preview／tab-panel／galleryfold）")


def check_flows(sections) -> None:
    palette = flow_palette()
    flows = {f["key"]: f for f in flow_list()}
    for f in flows.values():
        svg = FLOWS / f"{f['key']}.svg"
        if not svg.exists():
            err(f"[流程] {f['key']}.puml 沒有對應 SVG")
        else:
            svg_text_all = svg.read_text(encoding="utf-8")
            missing = [p for p in f["pages"] if p not in svg_text_all]
            if missing:
                err(f"[流程] {f['key']}.svg 缺少頁面 {','.join(missing)}，SVG 可能過期 → plantuml -tsvg flows/{f['key']}.puml")
    spec = {s.anchor[5:]: s for s in sections if s.anchor.startswith("flow-")}
    for key, f in flows.items():
        s = spec.get(key)
        if not s:
            err(f"[流程] {key} 在規格中沒有 #flow-{key} 段落")
            continue
        m = re.search(r"^- (?:涵蓋)?頁面：(.+)$", s.body, re.M)
        spec_pages = [p for p in re.split(r"[,、\s。]+", m.group(1)) if p] if m else []
        if spec_pages != f["pages"]:
            err(f"[流程] {key} 頁面不一致：規格 {','.join(spec_pages)}｜PUML {','.join(f['pages'])}")
        if s.heading != f["title"]:
            err(f"[流程] {key} 標題不一致：規格「{s.heading}」｜PUML「{f['title']}」")
        flat = [x for step in f["order"] for x in step]
        if len(f["pages"]) > 1 and not flat:
            err(f"[流程] {key} 有多個頁面，但沒有 @order")
        elif flat and sorted(flat) != sorted(f["pages"]):
            err(f"[流程] {key} @order 與 @pages 的頁面不一致：{','.join(flat)}｜{','.join(f['pages'])}")
        if synced_source(f, NAMES, palette) != f["source"]:
            err(f"[流程] {key} 的頁面圖例或樣式過期 → python3 scripts/flow_sync.py（並重新渲染 SVG）")
        if re.search(r"^!theme ", f["source"], re.M):
            err(f"[流程] {key} 不可用 !theme，樣式由 flow_sync.py 產生")
        for kind, name, _alias in DECL_RE.findall(f["source"]):
            if participant_category(kind, name, palette[1]) not in palette[0]:
                err(f"[流程] {key} 的參與者「{name}」未列在規格「系統架構 › 流程圖參與者類別」→ 加進表後執行 flow_sync.py")
    for key in spec:
        if key not in flows:
            err(f"[流程] 規格有 #flow-{key}，但沒有 flows/{key}.puml")
    data = {d["key"]: d for d in index_flow_data()}
    for key, f in flows.items():
        d = data.get(key)
        if not d:
            err(f"[index.html] 流程資料缺少 {key}")
            continue
        if d.get("order", []) != ["|".join(step) for step in f["order"]]:
            err(f"[index.html] 流程 {key} 的 order 與 PUML 不一致 → python3 scripts/flow_sync.py")
        if d.get("pages") != f["pages"] or d.get("title") != f["title"]:
            err(f"[index.html] 流程 {key} 的標題／頁面與 PUML 不一致")
        elif d.get("source", "").strip() != f["source"].strip():
            warn(f"[index.html] 流程 {key} 內嵌的 PlantUML 原始碼與 flows/{key}.puml 不同")
    for key in data:
        if key not in flows:
            err(f"[index.html] 流程資料 {key} 沒有對應 PUML")


def check_nav() -> None:
    problems, _, _ = nav.run([], write=False)
    for p in problems:
        err(f"[選單] {p}")


def check_terms(files) -> None:
    """project.json › term_rules：畫面出現指定用語時提醒；同一行含 allow_pattern（如否定詞）則略過。"""
    for rule in TERM_RULES:
        allow = rule.get("allow_pattern")
        for pid, path in files.items():
            for t in svg_texts(path):
                hit = [w for w in rule["terms"] if w in t]
                if hit and not (allow and re.search(allow, t)):
                    warn(f"[{rule['label']}] {pid} 出現限制用語「{'、'.join(hit)}」：{t[:40]}")


def check_nodes() -> None:
    md = sitemap_nodes()
    html = read(INDEX)
    for region in REGIONS:
        col = INDEX_COLUMN[region]
        m = re.search(rf'class="mapcolumn {col}-map">(.*?)(?=class="mapcolumn |<details )', html, re.S)
        if not m:
            continue
        html_nodes = re.findall(r'<div class="mapnode"><strong>([^<]+)</strong>', m.group(1))
        if md[region] != html_nodes:
            only_md = [n for n in md[region] if n not in html_nodes]
            only_html = [n for n in html_nodes if n not in md[region]]
            if only_md or only_html:
                warn(f"[節點標題] {region}：Markdown 有「{'、'.join(only_md) or '—'}」｜"
                     f"index.html 有「{'、'.join(only_html) or '—'}」")
            else:
                warn(f"[節點標題] {region}：節點順序不同")


def check_bundle() -> None:
    if svg_bundle.is_stale():
        err("[SVG 打包] assets/svg_sources.js 已過期，請執行 python3 scripts/svg_bundle.py")


PENDING_STAGES = set(interview_markers())   # 新專案訪談中尚未完成的階段（沒有標記時為空）


def check_architecture(files) -> None:
    for puml in sorted(ARCH.glob("*.puml")):
        svg = puml.with_suffix(".svg")
        if not svg.exists():
            err(f"[架構圖] {puml.name} 沒有對應 SVG → plantuml -tsvg architecture/{puml.name}")
        elif svg.stat().st_mtime < puml.stat().st_mtime:
            warn(f"[架構圖] {svg.name} 比 PUML 舊，可能未重新渲染 → plantuml -tsvg architecture/{puml.name}")
    for path in sorted(set(re.findall(r'"(architecture/[^"]+\.svg)"', read(INDEX)))):
        if not (ROOT / path).exists():
            err(f"[架構圖] index.html 引用的檔案不存在：{path}")
    arch = architecture_spec()
    for puml in sorted(ARCH.glob("*.puml")):
        name = ARCH_FIGURES.get(puml.stem)
        if not name:
            err(f"[架構圖] {puml.name} 未登記在 project.json › architecture.figures（圖名對照）")
        elif not arch.guides.get(name):
            err(f"[架構圖] 規格「系統架構 › 讀圖說明」缺少「{name}」")
        if not name:
            continue
        src = read(puml).upper()
        if re.search(r"^\s*LEGEND\b", src, re.M):
            err(f"[架構圖] {puml.name} 不可在圖內放 legend，圖例改寫在規格「系統架構 › 圖例」（燈箱右側顯示）")
        legend = arch.legends.get(name, [])
        if not legend:
            err(f"[架構圖] 規格「系統架構 › 圖例」缺少「{name}」")
        listed = {item["fill"].upper() for item in legend}
        for item in legend:
            for color in (item["fill"], item["line"]):
                if color and color.upper().lstrip("#") not in src:
                    err(f"[架構圖] 規格圖例「{name}」的色碼 {color} 未用在 {puml.name}")
        for fill in sorted(set(re.findall(r"(#[0-9A-F]{6});LINE:", src)) - listed):
            err(f"[架構圖] {puml.name} 的方塊底色 {fill} 未列在規格「系統架構 › 圖例」")
    pages = set(files) | API_IDS
    covered = {pid for _, ids in arch.modules for pid in ids}
    uncovered = sorted(pages - covered - arch.excluded)
    if uncovered and 6 in PENDING_STAGES:
        warn(f"[架構] {len(uncovered)} 頁尚未歸入業務模組（訪談第 6 階段未完成）")
        uncovered = []
    for pid in uncovered:
        err(f"[架構] {pid} 未歸入任何業務模組 → 規格「系統架構 › 業務模組」與 architecture/{FUNCTIONAL_FIGURE}.puml")
    for name, ids in arch.modules:
        for pid in sorted(set(ids) - pages):
            err(f"[架構] 業務模組「{name}」列了不存在的頁面 {pid}")
    puml = ARCH / f"{FUNCTIONAL_FIGURE}.puml"
    if FUNCTIONAL_FIGURE and puml.exists():
        boxes = re.findall(r'rectangle "([^"]+)" as ([EM])\d+', read(puml))
        drawn = {}
        entry: set[str] = set()
        for label, kind in boxes:
            name, ids = arch_label(label)
            if kind == "M":
                drawn[name] = set(ids)
            else:
                entry |= set(ids)
        for name, ids in arch.modules:
            got = drawn.pop(norm_name(name), None)
            if got is None:
                err(f"[架構] 功能架構圖缺少業務模組「{name}」")
            elif got != set(ids):
                err(f"[架構] 功能架構圖「{name}」的頁面與規格不同（圖多 {' '.join(sorted(got - set(ids))) or '—'}／圖少 {' '.join(sorted(set(ids) - got)) or '—'}）")
        for name in drawn:
            err(f"[架構] 功能架構圖有規格沒有的業務模組「{name}」")
        if entry != pages:
            err(f"[架構] 功能架構圖入口層頁面與實際不同（圖多 {' '.join(sorted(entry - pages)) or '—'}／圖少 {' '.join(sorted(pages - entry)) or '—'}）")
    for f in flow_list():
        for label in re.findall(r'^(?:participant|actor|database|queue|collections) "([^"]+)"', f["source"], re.M):
            if label in arch.aliases:
                warn(f"[架構] 流程 {f['key']} 參與者「{label}」請改用統一名稱「{arch.aliases[label]}」")


def check_dev_notes(files) -> None:
    if dev_notes.is_stale():
        err("[開發說明] assets/dev_notes.js 已過期，請執行 python3 scripts/dev_notes.py")
    notes = dev_notes.parse()
    for pid in files:
        if not notes.get(pid, {}).get("ai"):
            warn(f"[開發說明] {pid} 缺少「開發說明（AI 補充）」")
        if "sa" not in notes.get(pid, {}):
            warn(f"[SA 規格] {pid} 缺少「SA 規格」區塊（可先放兩層式空白骨架，見 AGENTS.md）")
    for pid in sorted(API_IDS):
        titles = [s["title"] for s in notes.get(pid, {}).get("api", {}).get("sections", [])]
        if not titles:
            err(f"[API 規格] {pid} 缺少「**API 規格**」區塊（介接資訊、傳送欄位、回傳欄位｜…、加解密方式）")
            continue
        for need, ok in (("介接資訊", "介接資訊" in titles), ("傳送欄位", "傳送欄位" in titles),
                         ("回傳欄位｜…", any(x.startswith("回傳欄位") for x in titles)),
                         ("加解密方式", any(x.startswith("加解密") for x in titles))):
            if not ok:
                warn(f"[API 規格] {pid} 缺少小節「{need}」")
        if not notes.get(pid, {}).get("ai"):
            warn(f"[開發說明] {pid} 缺少「開發說明（AI 補充）」")
    html = read(INDEX)
    for needle in ('id="lightbox-tab-api-request"', 'id="lightbox-tab-api-response"', 'id="lightbox-tab-api-crypto"', 'id="lightbox-api-info"'):
        if needle not in html:
            err(f"[API 規格] index.html 燈箱缺少 API 模式元素 {needle}")


def check_index_build() -> None:
    errors, stale = index_build.status()
    for e in errors:
        err("[網站地圖產生] " + e)
    if stale and not errors:
        err("[網站地圖產生] index.html 網站地圖或專案設定未同步，請執行 python3 scripts/index_build.py")
    tables = architecture_spec().tables
    ext, cat = tables.get("外部系統"), tables.get("外部系統需求類別")
    if ext and ext["head"] and "需求類別" in ext["head"]:
        i = ext["head"].index("需求類別")
        known = {r[0] for r in (cat or {}).get("rows", [])}
        for row in ext["rows"]:
            if i < len(row) and row[i] and row[i] not in known:
                err(f"[外部系統] 需求類別「{row[i]}」未列在規格「系統架構 › 外部系統需求類別」表")


def _ver(v: str) -> tuple:
    return tuple(int(x) for x in re.findall(r"\d+", v or "0"))


def check_kit() -> None:
    kit = CONFIG.get("kit") or {}
    if not kit.get("path"):
        return
    path = (ROOT / Path(kit["path"]).expanduser()).resolve()   # 支援 ~ 開頭（例如 ~/NewebDoc/PMSkill）
    manifest = path / ".claude-plugin" / "plugin.json"
    if not manifest.exists():
        warn(f"[引擎] 找不到 plugin：{kit['path']}（project.json › kit.path）")
        return
    import json
    latest = json.loads(manifest.read_text(encoding="utf-8")).get("version", "")
    if kit.get("engine_source"):
        sys.path.insert(0, str(path / "tools"))
        import sync_kit
        diffs = sync_kit.engine_diff(ROOT)
        if diffs:
            warn(f"[引擎] 本專案是引擎來源，{'、'.join(diffs[:5])} 與 plugin 不同 → python3 {kit['path']}/tools/sync_kit.py .")
    elif _ver(latest) > _ver(CONFIG.get("engine_version", "")):
        warn(f"[引擎] plugin 有新版 {latest}（本專案 {CONFIG.get('engine_version', '未標示')}）→ "
             f"python3 {kit['path']}/tools/upgrade_project.py . --dry-run")


def check_ai_entry() -> None:
    if not ai_entry.RULES.exists():
        err("[AI 入口] 找不到 專案規則.md（專案專屬規則檔）")
        return
    if not (ROOT / "規範" / "README.md").exists():
        err("[AI 入口] 找不到 規範/README.md（共用設計規範）")
    bad = ai_entry.stale()
    if bad:
        err(f"[AI 入口] {'、'.join(bad)} 未同步 → python3 scripts/ai_entry.py")


def check_inventory() -> None:
    if inventory.is_stale():
        err("[完整度] assets/inventory.js 已過期，請執行 python3 scripts/inventory.py")
    html = INDEX.read_text(encoding="utf-8")
    for needle, label in (('src="assets/inventory.js"', "載入 assets/inventory.js"),
                          ('id="inventory-open"', "「文件內容與完整度」按鈕"),
                          ('id="inventory-dialog"', "「文件內容與完整度」燈箱")):
        if needle not in html:
            err(f"[完整度] index.html 缺少{label}")


def main() -> int:
    only_errors = "--errors" in sys.argv
    files = screen_files()
    sections = spec_sections()
    check_screens(files)
    check_spec(files, sections)
    check_text_lists(files, sections)
    check_sitemap(files)
    check_index(files)
    check_flows(sections)
    check_nav()
    check_terms(files)
    check_nodes()
    check_bundle()
    check_dev_notes(files)
    check_architecture(files)
    check_inventory()
    check_index_build()
    check_kit()
    check_ai_entry()
    for e in errors:
        print("✗ " + e)
    if not only_errors:
        for w in warns:
            print("! " + w)
    summary = f"{len(files)} 張頁面 SVG、{len(flow_list())} 個流程：錯誤 {len(errors)}、提醒 {len(warns)}"
    print(("OK｜" if not errors else "") + summary)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
