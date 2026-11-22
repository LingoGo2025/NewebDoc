#!/usr/bin/env python3
"""統計本文件包含哪些資料與各自的完整度，產生 assets/inventory.js，供 index.html「文件內容與完整度」燈箱使用。

數字全部由現有檔案自動計算（規格 Markdown、網站地圖、screens/、flows/、architecture/），
不手動填寫；只計算資料是否存在與標記，不代表內容已審核。
新增資料種類（新的規格章節、圖種、產出檔）時，在 build_data() 登記一列。

用法：
  python3 scripts/inventory.py          # 重新產生 assets/inventory.js
  python3 scripts/inventory.py --check  # 只檢查是否過期（check.py 也會呼叫）
"""
from __future__ import annotations

import json
import re
import sys

import dev_notes
from _common import (API_RE, ARCH, ARCH_FIGURES, CONFIG, FLOWS, PAGE_RE, REGIONS, ROOT, SITEMAP, SPEC, architecture_spec,
                     flow_list, read, screen_files, sitemap_buttons, sitemap_nodes, spec_sections)

OUTPUT = ROOT / "assets" / "inventory.js"
HEADER = "// 由 scripts/inventory.py 產生，請勿手動編輯；任何規格、頁面、流程或架構圖改動後重新執行。\n"
# 各列說明的預設文字可在 project.json › inventory_desc 依列名覆寫（專案專屬的舉例寫在那裡）
DESC_OVERRIDES: dict[str, str] = CONFIG.get("inventory_desc", {})
SA_MARK_RE = re.compile(r"\*\*SA 規格(?:（([^）]*)）)?\*\*")
PENDING_RE = re.compile(r"待確認|預設規則")


def _row(name: str, desc: str, done: int | None, total: int | None, unit: str, note: str,
         status: str | None = None) -> dict:
    """status：complete 完整、partial 部分、todo 待補、optional 選填、tracking 追蹤中。"""
    if status is None:
        status = "complete" if done == total else ("todo" if not done else "partial")
    desc = DESC_OVERRIDES.get(name, desc)
    return {"name": name, "desc": desc, "done": done, "total": total, "unit": unit, "note": note, "status": status}


def _pending_lines(body: str) -> int:
    """段落內含「待確認」的行數（略過 #### 小節標題，例如 SA 骨架的「本頁待確認」）。"""
    return sum(1 for ln in body.split("\n") if "待確認" in ln and not ln.startswith("#### "))


def _latest_date() -> str:
    dates = []
    for path in (SPEC, SITEMAP):
        text = read(path)
        log = text[text.find("## 更新紀錄"):] if "## 更新紀錄" in text else ""
        dates += re.findall(r"^- (\d{4}-\d{2}-\d{2})", log, re.M)
    return max(dates) if dates else ""


def _common_rules(spec: str) -> tuple[int, int, list[str]]:
    """全站共用規則：條目總數、含「待確認／預設規則」的條目數、各類數量說明。"""
    start = spec.find("## 全站共用規則")
    chapter = spec[start:spec.find("\n## ", start + 1)] if start >= 0 else ""
    total = pending = 0
    kinds: dict[str, int] = {}
    section_pending = False
    for line in chapter.split("\n"):
        if line.startswith("#### "):
            section_pending = bool(PENDING_RE.search(line))
            continue
        m = re.match(r"\| ((CF|CB|CE|CAC)-\w+) \|", line)
        if m:
            total += 1
            kinds[m.group(2)] = kinds.get(m.group(2), 0) + 1
            if section_pending or PENDING_RE.search(line):
                pending += 1
    labels = {"CF": "欄位規則", "CB": "表單行為", "CE": "錯誤文案", "CAC": "驗收條件"}
    return total, pending, [f"{labels[k]} {kinds[k]}" for k in labels if k in kinds]


def build_data() -> dict:
    spec = read(SPEC)
    sections = spec_sections(spec)
    pages = [s for s in sections if PAGE_RE.match(s.key)]
    apis = [s for s in sections if API_RE.match(s.key)]
    page_ids = [s.key for s in pages]
    total = len(pages)
    files = screen_files()
    notes = dev_notes.parse()
    buttons = sitemap_buttons()
    region_counts = "、".join(f"{r} {n}" for r in REGIONS
                              if (n := sum(1 for i, _, _ in buttons[r] if PAGE_RE.match(i))))

    # ---- 頁面 ----
    with_svg = sum(1 for p in page_ids if p in files)
    with_text = sum(1 for s in pages if s.body and s.text_list)
    with_ai = sum(1 for p in page_ids if notes.get(p, {}).get("ai"))
    with_designer = [p for p in page_ids if notes.get(p, {}).get("designer")]
    sa_kind: dict[str, list[str]] = {"完成": [], "試做": [], "待補": [], "缺少": []}
    for s in pages:
        m = SA_MARK_RE.search(s.body)
        kind = "缺少" if not m else ("完成" if not m.group(1) else m.group(1))
        sa_kind.setdefault(kind, []).append(s.key)
    sa_filled = sa_kind["完成"] + sa_kind["試做"]
    sa_note = f"完成 {len(sa_kind['完成'])}、試做 {len(sa_kind['試做'])}"
    if sa_kind["試做"]:
        sa_note += f"（{'、'.join(sa_kind['試做'])}）"
    sa_note += f"、空白骨架待補 {len(sa_kind['待補'])}"
    if sa_kind["缺少"]:
        sa_note += f"、缺少區塊 {len(sa_kind['缺少'])}"
    sa_note += "；其餘頁面等功能確認後再補"

    # ---- 流程 ----
    flows = flow_list()
    multi = [f for f in flows if len(f["pages"]) > 1]
    flows_ok = sum(1 for f in flows if (FLOWS / f"{f['key']}.svg").exists() and (len(f["pages"]) < 2 or f["order"]))
    api_svg = sum(1 for s in apis if s.key in files or re.search(r"flows/\w+\.svg", s.body))
    api_status: dict[str, int] = {}
    for s in apis:
        m = re.search(r"規格狀態：([^；。\n]+)", s.body)
        key = m.group(1).strip() if m else "未標示狀態"
        api_status[key] = api_status.get(key, 0) + 1
    api_concept = sum(n for k, n in api_status.items() if k != "正式規格")
    api_spec_has = sum(1 for s in apis if notes.get(s.key, {}).get("api", {}).get("sections"))
    api_spec_done = sum(1 for s in apis
                        if (secs := notes.get(s.key, {}).get("api", {}).get("sections"))
                        and all(sec["blocks"] for sec in secs)
                        and "待確認" not in json.dumps(secs, ensure_ascii=False))

    # ---- 結構 ----
    nodes = sitemap_nodes()
    node_count = sum(len(v) for v in nodes.values())
    btn_ids = [i for r in REGIONS for i, _, _ in buttons[r]]
    unique_pages = sum(1 for p in page_ids if btn_ids.count(p) == 1)
    arch = architecture_spec(spec)
    figures_ok = sum(1 for key, name in ARCH_FIGURES.items()
                     if (ARCH / f"{key}.puml").exists() and (ARCH / f"{key}.svg").exists() and arch.guides.get(name))
    in_module = {i for _, ids in arch.modules for i in ids}
    covered = sum(1 for p in page_ids if p in in_module)
    arch_note = f"業務模組 {len(arch.modules)} 個；頁面歸入模組 {covered}/{total}"
    if arch.excluded:
        arch_note += f"（暫不歸入：{'、'.join(sorted(arch.excluded))}）"
    # 外部系統串接（首頁第 4 區塊）：規格「系統架構 › 外部系統」表，依需求類別分組；完整度只計狀態未標示待確認者
    ext = arch.tables.get("外部系統", {"head": [], "rows": []})
    ext_head = ext.get("head") or []
    ext_cat = ext_head.index("需求類別") if "需求類別" in ext_head else None
    ext_status = ext_head.index("狀態") if "狀態" in ext_head else None
    ext_rows = ext.get("rows", [])
    ext_done = sum(1 for r in ext_rows if ext_status is not None and not PENDING_RE.search(r[ext_status]))
    ext_groups: dict[str, list] = {}
    for r in ext_rows:
        ext_groups.setdefault(r[ext_cat] if ext_cat is not None else "未分類", []).append(r)
    ext_note = "、".join(f"{k} {len(v)}" for k, v in ext_groups.items())
    ext_note += f"；完整度只計狀態未標示待確認者，{len(ext_rows) - ext_done} 個待確認"
    if "營運需求" in ext_groups:
        ext_note += "（營運需求系統 API 待補）"
    # 選填章節（首頁第 5、6 區塊）：章節除「狀態／用途／首頁對應」說明外有其他內容才算已填
    def optional_chapter(key: str) -> tuple[bool, int]:
        sec = next((x for x in sections if x.key == key), None)
        body = [ln for ln in (sec.body.split("\n") if sec else [])
                if ln.strip() and not ln.startswith(("## ", "<a id", "- 狀態：", "- 用途：", "- 首頁對應："))]
        return sec is not None, 1 if body else 0

    def optional_note(exists: bool, filled: int, chapter: str) -> str:
        if filled:
            return "已填寫內容"
        return "目前只標出位置，內容待補（選填，不算缺漏）" if exists else f"規格缺少「{chapter}」章"

    mig_exists, mig_filled = optional_chapter("migration-plan")
    law_exists, law_filled = optional_chapter("regulations")
    rules_total, rules_pending, rule_kinds = _common_rules(spec)

    # ---- 待確認 ----
    from interview_status import review_markers
    review = review_markers()
    open_start = spec.find("## 尚待確認")
    open_block = spec[open_start:spec.find("\n## ", open_start + 1)] if open_start >= 0 else ""
    open_items = len(re.findall(r"^- ", open_block, re.M))
    pages_pending = [s.key for s in pages if _pending_lines(s.body)]

    groups = [
        {"name": "頁面", "rows": [
            _row("頁面示意圖（SVG）", "每頁的畫面原稿，網站地圖按鈕點開即燈箱預覽。",
                 with_svg, total, "頁", region_counts),
            _row("頁面說明與畫面文字", "規格中每頁的用途、欄位、狀態說明，以及依 SVG 順序同步的可見文字清單。",
                 with_text, total, "頁", "畫面文字由 sync_screen_text.py 從 SVG 同步"),
            _row("開發說明（AI 補充）", "AI 依已定案規格整理給開發者的重點，未知內容標示待確認。",
                 with_ai, total, "頁", "燈箱「開發說明」頁籤上半部"),
            _row("開發說明（設計者補充）", "設計者要求補充時才寫入，沒有就留空。",
                 len(with_designer), total, "頁",
                 ("已填寫：" + "、".join(with_designer)) if with_designer else "目前沒有頁面填寫（選填，不算缺漏）",
                 "optional"),
            _row("SA 規格", "給人審閱的摘要與給開發使用的明細（欄位、導向、狀態、錯誤文案、資料寫入、驗收條件）。",
                 len(sa_filled), total, "頁", sa_note),
        ]},
        {"name": "流程", "rows": [
            _row("跨頁流程圖", "PlantUML 原稿與 SVG；多頁流程以頁面順序（@order）串起燈箱的流程位置。",
                 flows_ok, len(flows), "條", f"多頁流程 {len(multi)} 條、單頁流程 {len(flows) - len(multi)} 條"),
            _row("API 流程圖", "對外 API 的流程（一支 API 一個網址）。",
                 api_svg, len(apis), "張",
                 "規格狀態：" + "、".join(f"{k} {n}" for k, n in api_status.items())
                 + ("；正式欄位、驗證與錯誤處理待正式規格" if api_concept else ""),
                 "partial" if api_concept or api_svg < len(apis) else None),
            _row("API 介接規格", "各 API 的介接資訊、傳送欄位、回傳欄位與加解密方式（燈箱 API 模式頁籤）。",
                 api_spec_done, len(apis), "支",
                 f"有規格區塊 {api_spec_has}/{len(apis)} 支；完整度只計各小節都有內容且未標示待確認者"),
        ]},
        {"name": "架構與規則", "rows": [
            _row("網站地圖", f"{len(REGIONS)} 個區域、功能節點與頁面按鈕；每頁恰有一個入口。",
                 unique_pages, total, "頁", f"{len([r for r in REGIONS if nodes[r]])} 個區域、{node_count} 個節點、{len(btn_ids)} 個按鈕"),
            _row("系統架構圖", "系統情境圖、功能架構圖與讀圖說明；文字版在規格「系統架構」章。",
                 figures_ok, len(ARCH_FIGURES), "張", arch_note),
            _row("外部系統串接", "首頁「外部系統串接」區塊：依需求類別（系統需求、營運需求）分組的外部系統；文字版在規格「系統架構 › 外部系統」表。",
                 ext_done, len(ext_rows), "個", ext_note),
            _row("舊系統移轉計畫", "首頁「舊系統移轉計畫」區塊：舊系統移轉到本平台的計畫；文字版在規格「舊系統移轉計畫（選填）」章。",
                 mig_filled, 1, "區", optional_note(mig_exists, mig_filled, "舊系統移轉計畫（選填）"), "optional"),
            _row("相關法規", "首頁「相關法規」區塊：平台適用的相關法規；文字版在規格「相關法規（選填）」章。",
                 law_filled, 1, "區", optional_note(law_exists, law_filled, "相關法規（選填）"), "optional"),
            _row("全站共用規則", "各頁 SA 規格引用的共用欄位、表單行為、錯誤文案與驗收條件。",
                 rules_total - rules_pending, rules_total, "條",
                 "、".join(rule_kinds) + f"；完整度只計未標示待確認的條目，{rules_pending} 條標示待確認或預設規則"),
        ]},
        {"name": "待確認", "rows": [
            *([_row("AI 起稿待審閱", "全自動起稿時 AI 依產業常識推測、尚未和使用者確認的內容（標「AI 起稿」）。",
                    None, None, "處", f"第 {'、'.join(str(i) for i in sorted(review))} 階段共 {sum(len(v) for v in review.values())} 處待審閱",
                    "tracking")] if review else []),
            _row("尚待確認事項", "產品、介接、法規與商業政策尚未定案的項目，不可自行補成規格。",
                 None, None, "項",
                 f"規格「尚待確認」清單 {open_items} 項；{len(pages_pending)}/{total} 頁的說明內含待確認標記",
                 "tracking"),
        ]},
    ]
    return {"updated": _latest_date(), "pages": total, "groups": groups}


def build() -> str:
    body = json.dumps(build_data(), ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return HEADER + "window.DOC_INVENTORY=" + body + ";\n"


def is_stale() -> bool:
    return not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != build()


def main() -> int:
    if "--check" in sys.argv:
        if is_stale():
            print("✗ assets/inventory.js 已過期，請執行 python3 scripts/inventory.py")
            return 1
        print("OK｜assets/inventory.js 與目前檔案一致")
        return 0
    OUTPUT.write_text(build(), encoding="utf-8")
    data = build_data()
    print(f"已更新 {OUTPUT.relative_to(ROOT)}（最後更新 {data['updated']}）")
    for group in data["groups"]:
        for row in group["rows"]:
            ratio = f"{row['done']}/{row['total']} {row['unit']}" if row["total"] else row["status"]
            print(f"  {group['name']}｜{row['name']}：{ratio}｜{row['note']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
