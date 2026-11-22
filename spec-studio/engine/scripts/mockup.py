#!/usr/bin/env python3
"""新頁面 SVG 示意圖：依頁面描述（JSON）以元件組合產生初稿。

用法：
  python3 scripts/mockup.py <描述.json>              # 產生 screens/<ID>_<名稱>.svg（檔案已存在時不覆蓋）
  python3 scripts/mockup.py <描述.json> --force      # 覆寫（只用於尚未手動調整過的初稿）
  python3 scripts/mockup.py <描述.json> --out <路徑>  # 輸出到指定檔案（例如暫存目錄預覽）
  python3 scripts/mockup.py --example backend         # 印出描述範例（backend 或 public）

只產生「新頁面的初稿」：產生後的修改一律局部編輯 SVG，不重跑本工具覆蓋（避免蓋掉手動調整）。
配色讀 project.json › theme（各區可在 theme › regions 覆寫），各區版型與固定文字讀 project.json › mockup，
標誌讀 project.json › brand。共用選單依網站地圖.md › 共用選單產生 <g data-nav>（與 nav.py 相同）。

頁面描述欄位：
  id, name, desc            頁面 ID、名稱（檔名與標題）、一句說明（SVG <desc>）
  region                    選填；regions › column，預設依 project.json › regions 判斷
  subtitle                  選填；標題下說明，預設同 desc（backend 版型）
  badge, active             選填；右上區域標籤（預設 mockup 設定）、選單反白項目（預設共用選單表）
  hero                      選填（public）：{"eyebrow","title","lead":[…]}
  stats                     選填：[[標籤, 數值, 註記], …] 一排統計卡
  hero                      前台主視覺另可加 search（搜尋框提示字）、cta（按鈕）、art: false（不畫右側插圖）
  rows                      區塊列：[[區塊, 區塊], [區塊]]；同列並排（最多 3 個），區塊可設 flex 調整寬度比例（例：表單 2、說明 1）
區塊 type：list、steps、table、form、kv、text、notice、actions、section、stats，
  以及 filters（一列查詢條件）、tabs（頁籤）、chart（長條圖）、timeline（處理歷程）、cards（卡片牆）、
  summary（明細頁首：標題＋狀態標籤＋重點欄位＋按鈕）、caption（小字註記）。
  table 可加 actions（標題列按鈕）、row_actions（每列操作連結）、pager（分頁）；狀態欄自動畫成彩色標籤。
  form／filters 的欄位可寫 "名稱*"（必填）或 [標籤, 提示, 型態]／{label, type, help, options}；
  型態 text、select、date、textarea、upload、radio、checkbox，沒寫時依欄位名稱推測。
內容超過預設高度時畫布自動加高，頁尾跟著下移；文字超出寬度會截斷並提醒。
"""
from __future__ import annotations

import dataclasses
import html
import json
import math
import re
import sys
from pathlib import Path

from _common import (BRAND, INDEX_COLUMN, MOCKUP, ROOT, SCREENS, expected_region, region_theme,
                     sitemap_menus)

BACKEND = {"w": 1600, "h": 1080, "x": 280, "cw": 1280, "gap": 18, "vgap": 15, "top": 185, "foot": 30}
PUBLIC = {"w": 1440, "h": 1000, "x": 76, "cw": 1288, "gap": 30, "vgap": 28, "top": 116, "foot": 60}
# 中性色（不隨品牌變）：標籤、欄位框、表頭、分隔線
LABEL, PLACEHOLDER, FIELD_LINE, TABLE_HEAD, ROW_LINE, DIVIDER = "#778981", "#87958e", "#e0e7e1", "#f3f6f2", "#edf0ed", "#e8ede8"
FOOT_LINE, FOOT_TEXT, SUB_TEXT, CELL_FIRST, CELL = "#e2e9e3", "#99a69f", "#71847c", "#405b53", "#61766f"

EXAMPLES = {
    "backend": {
        "id": "B90", "name": "範例管理頁", "desc": "後台頁面範例：統計卡、表格、表單與清單。",
        "stats": [["待處理", "12", "今日"], ["已完成", "48", "本週"]],
        "rows": [
            [{"type": "table", "title": "資料清單", "columns": ["編號", "名稱", "狀態"],
              "rows": [["N-001", "範例資料", "啟用"], ["N-002", "範例資料", "停用"]]}],
            [{"type": "form", "title": "篩選條件", "fields": [["關鍵字", "請輸入"], ["狀態", "全部"]]},
             {"type": "list", "title": "注意事項", "items": ["一般說明", ["重點說明", "補充一行"]]}],
            [{"type": "actions", "buttons": ["取消", {"label": "儲存", "style": "primary"}]}],
        ],
    },
    "public": {
        "id": "A90", "name": "範例前台頁", "desc": "前台頁面範例：主視覺、統計卡與資訊卡。",
        "hero": {"eyebrow": "副標", "title": "主視覺標題", "lead": ["第一行說明文字。", "第二行說明文字。"]},
        "rows": [
            [{"type": "section", "text": "區塊標題"}],
            [{"type": "stats", "items": [["數字說明", "128"], ["數字說明", "92%"], ["數字說明", "3,240"]]}],
            [{"type": "kv", "title": "資訊卡", "items": [["欄位", "內容"], ["欄位", "內容"], ["欄位", "內容"]]}],
            [{"type": "steps", "title": "步驟", "items": ["第一步", "第二步", "第三步"]},
             {"type": "notice", "text": "提醒文字：標「待確認」的內容尚未定案。", "tone": "warn"}],
        ],
    },
}


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def text_width(s: str, size: float) -> float:
    return sum(size if ord(c) > 0x2E80 else size * (0.3 if c == " " else 0.55) for c in str(s))


class Canvas:
    def __init__(self, theme: dict, warnings: list[str]):
        self.t, self.out, self.warn = theme, [], warnings

    def add(self, s: str) -> None:
        self.out.append(s)

    def text(self, x, y, s, size=13, weight=500, fill=None, anchor=None, maxw=None):
        s = str(s)
        if maxw and text_width(s, size) > maxw:
            self.warn.append(f"文字超出寬度已截斷：「{s[:20]}…」")
            while s and text_width(s + "…", size) > maxw:
                s = s[:-1]
            s += "…"
        a = f' text-anchor="{anchor}"' if anchor else ""
        self.add(f'<text x="{x:g}" y="{y:g}" font-size="{size}" font-weight="{weight}" fill="{fill or self.t["text"]}"{a}>{esc(s)}</text>')

    def wrap(self, s: str, size: float, width: float) -> list[str]:
        lines, cur = [], ""
        for ch in str(s):
            if text_width(cur + ch, size) > width and cur:
                lines.append(cur)
                cur = ""
            cur += ch
        return lines + ([cur] if cur else [])

    def card(self, x, y, w, h):
        self.add(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="16" fill="{self.t["surface"]}" '
                 f'stroke="{self.t["border"]}" filter="url(#sh)"/>')

    def card_head(self, x, y, w, title):
        self.text(x + 20, y + 31, title, 17, 800, self.t["heading"], maxw=w - 40)
        self.add(f'<line x1="{x + 20:g}" y1="{y + 48:g}" x2="{x + w - 20:g}" y2="{y + 48:g}" stroke="{DIVIDER}"/>')

    def button(self, x, y, label, primary=False, h=40):
        w = text_width(label, 14) + 40
        if primary:
            self.add(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h}" rx="{h / 2:g}" fill="{self.t["primary"]}"/>')
            self.text(x + w / 2, y + h / 2 + 5, label, 14, 750, "#fff", "middle")
        else:
            self.add(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h}" rx="{h / 2:g}" fill="#f0f4ef"/>')
            self.text(x + w / 2, y + h / 2 + 5, label, 14, 700, self.t["nav_active"], "middle")
        return w


# ---------- 狀態標籤（表格、明細頁首共用） ----------

TONES = {
    "ok": ("#e3f4ea", "#1f7a4d", r"啟用|已核准|核准|成功|已付款|完成|正常|有效|已上傳|已開立|營業中|上線|通過|已結案|已處理|已繳費|在場"),
    "warn": ("#fff2d9", "#9a6200", r"待|審核中|處理中|即將|候補|草稿|未讀|排程|部分"),
    "bad": ("#fde7e7", "#b3261e", r"停用|失敗|退回|駁回|異常|逾期|取消|作廢|離線|錯誤|拒絕|過期|未繳"),
}


def tone_of(value: str) -> tuple[str, str] | None:
    for fill, ink, pattern in TONES.values():
        if re.search(pattern, value):
            return fill, ink
    return None


def is_status_col(header: str) -> bool:
    return bool(re.search(r"狀態|結果|審核|進度", header))


def badge(c: "Canvas", x, y, label, tone=None, size=11) -> float:
    """在 (x, y 為文字基線) 畫狀態膠囊，回傳寬度。"""
    fill, ink = tone or tone_of(label) or ("#eef2ef", "#5a6f68")
    w = text_width(label, size) + 18
    c.add(f'<rect x="{x:g}" y="{y - size - 4:g}" width="{w:g}" height="{size + 10:g}" rx="{(size + 10) / 2:g}" fill="{fill}"/>')
    c.text(x + 9, y, label, size, 700, ink)
    return w


def small_button(c: "Canvas", x, y, label, primary=False) -> float:
    """卡片標題列右側的小按鈕（右對齊：x 為右緣），回傳寬度。"""
    w = text_width(label, 12) + 26
    if primary:
        c.add(f'<rect x="{x - w:g}" y="{y:g}" width="{w:g}" height="30" rx="8" fill="{c.t["primary"]}"/>')
        c.text(x - w / 2, y + 20, label, 12, 750, "#fff", "middle")
    else:
        c.add(f'<rect x="{x - w:g}" y="{y:g}" width="{w:g}" height="30" rx="8" fill="#fff" stroke="{FIELD_LINE}"/>')
        c.text(x - w / 2, y + 20, label, 12, 700, c.t["nav_active"], "middle")
    return w


def head_actions(c: "Canvas", b, x, y, w) -> None:
    rx = x + w - 20
    for i, label in enumerate(reversed(b.get("actions", []))):
        rx -= small_button(c, rx, y + 13, label, primary=(i == 0)) + 8


# ---------- 區塊：height(block, w) 與 draw(c, block, x, y, w, h) ----------

def _items(b):
    return b.get("items", [])


def h_list(b, w): return 80 + len(_items(b)) * 43
def h_steps(b, w): return 80 + len(_items(b)) * 48
def h_table(b, w): return 100 + len(b.get("rows", [])) * 43 + (46 if b.get("pager") else 0)
def _field(f) -> dict:
    """表單欄位：字串、[標籤, 提示, 型態] 或 {label, type, value, help, options}。型態：text、select、date、textarea、upload、radio、checkbox。"""
    if isinstance(f, dict):
        d = dict(f)
    elif isinstance(f, (list, tuple)):
        d = {"label": f[0], "value": f[1] if len(f) > 1 else "", "type": f[2] if len(f) > 2 else ""}
    else:
        d = {"label": f}
    label = str(d.get("label", ""))
    d["required"] = d.get("required") or label.endswith("*")
    d["label"] = label.rstrip("*").strip()
    t = d.get("type") or ""
    if not t:   # 依標籤推測型態
        name = d["label"]
        t = ("textarea" if re.search(r"說明|備註|內容|原因|描述", name) else
             "upload" if re.search(r"檔案|文件|附件|圖片|影本|上傳", name) else
             "date" if re.search(r"日期|期間|起訖|生日|到期", name) else
             "select" if re.search(r"狀態|類型|方案|類別|分類|地區|縣市|場站|停車場|角色|對象|稅別|期別", name) else "text")
    d["type"] = t
    if not d.get("value"):
        d["value"] = {"select": "請選擇", "date": "YYYY-MM-DD", "textarea": "請輸入", "upload": "拖曳檔案到這裡，或點選上傳",
                      "radio": "", "checkbox": ""}.get(t, "請輸入")
    return d


def _form_layout(b, w):
    """回傳 [(field, col, row_y, span)] 與總高度；textarea、upload 佔整列。"""
    cols = max(1, b.get("cols", 2 if w > 500 else 1))
    out, col, y = [], 0, 66
    for f in (_field(x) for x in b.get("fields", [])):
        full = f["type"] in ("textarea", "upload") and cols > 1
        hh = 87 + (54 if f["type"] in ("textarea", "upload") else 0) + (16 if f.get("help") else 0)
        if full and col:
            y += 87; col = 0
        out.append((f, 0 if full else col, y, cols if full else 1, hh))
        if full:
            y += hh; col = 0
        else:
            col += 1
            if col == cols:
                y += max(x[4] for x in out[-cols:]); col = 0
    if col:
        y += 87
    return out, cols, y + 12


def h_form(b, w): return _form_layout(b, w)[2]
def h_kv(b, w): return 66 + math.ceil(len(_items(b)) / max(1, b.get("cols", 3 if w > 900 else 2 if w > 500 else 1))) * 62 + 10
def h_section(b, w): return 34
def h_actions(b, w): return 44


def h_text(b, w):
    lines = sum(len(Canvas({}, []).wrap(p, 14, w - 40)) for p in b.get("paragraphs", []))
    return (66 if b.get("title") else 24) + lines * 24 + 12


def h_notice(b, w):
    return 26 + len(Canvas({}, []).wrap(b.get("text", ""), 13, w - 48)) * 22


def h_stats(b, w): return 116 if b.get("big", True) else 88


def d_list(c, b, x, y, w, h):
    c.card(x, y, w, h); c.card_head(x, y, w, b.get("title", ""))
    for i, it in enumerate(_items(b)):
        yy = y + 78 + i * 43
        c.add(f'<circle cx="{x + 31:g}" cy="{yy - 5:g}" r="4" fill="{c.t["primary"]}"/>')
        if isinstance(it, (list, tuple)):
            c.text(x + 47, yy, it[0], 13, 700, "#49645b", maxw=w - 67)
            if len(it) > 1:
                c.text(x + 47, yy + 17, it[1], 11, 500, SUB_TEXT, maxw=w - 67)
        else:
            c.text(x + 47, yy, it, 13, 500, c.t["text"], maxw=w - 67)


def d_steps(c, b, x, y, w, h):
    c.card(x, y, w, h); c.card_head(x, y, w, b.get("title", ""))
    for i, it in enumerate(_items(b)):
        yy = y + 77 + i * 48
        c.add(f'<circle cx="{x + 32:g}" cy="{yy - 5:g}" r="11" fill="{c.t["primary_soft"]}"/>')
        c.text(x + 32, yy - 1, i + 1, 10, 800, c.t["primary"], "middle")
        main, sub = (it[0], it[1] if len(it) > 1 else "") if isinstance(it, (list, tuple)) else (it, "")
        c.text(x + 54, yy, main, 13, 700 if sub else 500, "#49645b" if sub else c.t["text"], maxw=w - 74)
        if sub:
            c.text(x + 54, yy + 17, sub, 11, 500, SUB_TEXT, maxw=w - 74)


def d_table(c, b, x, y, w, h):
    c.card(x, y, w, h); c.card_head(x, y, w, b.get("title", ""))
    head_actions(c, b, x, y, w)
    cols = list(b.get("columns", [])); acts = b.get("row_actions", [])
    if acts:
        cols.append("操作")
    n = max(1, len(cols)); cw = (w - 40) / n
    c.add(f'<rect x="{x + 20:g}" y="{y + 60:g}" width="{w - 40:g}" height="31" rx="5" fill="{TABLE_HEAD}"/>')
    for j, hd in enumerate(cols):
        c.text(x + 30 + j * cw, y + 81, hd, 11, 700, SUB_TEXT, maxw=cw - 16)
    yy = y + 119
    for row in b.get("rows", []):
        for j, val in enumerate(list(row)[:len(b.get("columns", []))]):
            hd = cols[j] if j < len(cols) else ""
            if j > 0 and (is_status_col(hd) or (tone_of(str(val)) and len(str(val)) <= 5)):
                badge(c, x + 30 + j * cw, yy, val)
            else:
                c.text(x + 30 + j * cw, yy, val, 12, 600 if j == 0 else 500, CELL_FIRST if j == 0 else CELL, maxw=cw - 16)
        if acts:
            ax = x + 30 + (n - 1) * cw
            for a in acts:
                c.text(ax, yy, a, 12, 700, c.t["primary"])
                ax += text_width(a, 12) + 14
        c.add(f'<line x1="{x + 20:g}" y1="{yy + 13:g}" x2="{x + w - 20:g}" y2="{yy + 13:g}" stroke="{ROW_LINE}"/>')
        yy += 43
    if b.get("pager"):
        total = b["pager"] if isinstance(b["pager"], str) else f"共 {len(b.get('rows', []))} 筆"
        c.text(x + 24, y + h - 22, total, 12, 500, SUB_TEXT)
        px = x + w - 24
        for i, label in enumerate(reversed(["‹", "1", "2", "3", "›"])):
            on = label == "1"
            px -= 30
            c.add(f'<rect x="{px:g}" y="{y + h - 40:g}" width="26" height="26" rx="6" fill="{c.t["primary"] if on else "#fff"}" '
                  f'stroke="{c.t["primary"] if on else FIELD_LINE}"/>')
            c.text(px + 13, y + h - 22, label, 12, 700, "#fff" if on else SUB_TEXT, "middle")


def d_form(c, b, x, y, w, h):
    c.card(x, y, w, h); c.card_head(x, y, w, b.get("title", ""))
    head_actions(c, b, x, y, w)
    layout, cols, _ = _form_layout(b, w)
    gap = 15; fw1 = (w - 40 - gap * (cols - 1)) / cols
    for f, col, fy0, span, _hh in layout:
        fx = x + 20 + col * (fw1 + gap); fw = fw1 * span + gap * (span - 1); fy = y + fy0
        c.text(fx, fy + 12, f["label"], 11, 700, LABEL, maxw=fw - 12)
        if f["required"]:
            c.text(fx + text_width(f["label"], 11) + 2, fy + 12, "*", 12, 800, "#c0392b")
        t = f["type"]
        if t in ("radio", "checkbox"):
            ox = fx
            for k, opt in enumerate(f.get("options") or ["選項一", "選項二"]):
                if t == "radio":
                    c.add(f'<circle cx="{ox + 8:g}" cy="{fy + 38:g}" r="8" fill="#fff" stroke="{c.t["primary"] if k == 0 else FIELD_LINE}" stroke-width="2"/>')
                    if k == 0:
                        c.add(f'<circle cx="{ox + 8:g}" cy="{fy + 38:g}" r="4" fill="{c.t["primary"]}"/>')
                else:
                    c.add(f'<rect x="{ox:g}" y="{fy + 30:g}" width="16" height="16" rx="4" fill="{c.t["primary"] if k == 0 else "#fff"}" stroke="{c.t["primary"] if k == 0 else FIELD_LINE}"/>')
                c.text(ox + 24, fy + 43, opt, 12, 600, CELL)
                ox += text_width(opt, 12) + 50
        elif t == "upload":
            c.add(f'<rect x="{fx:g}" y="{fy + 19:g}" width="{fw:g}" height="94" rx="10" fill="{c.t["primary_soft"]}" '
                  f'stroke="{c.t["primary"]}" stroke-dasharray="6 5" opacity=".9"/>')
            c.text(fx + fw / 2, fy + 62, "⇪", 20, 700, c.t["primary"], "middle")
            c.text(fx + fw / 2, fy + 88, f["value"], 12, 600, c.t["primary_dark"], "middle", maxw=fw - 30)
        else:
            hh = 94 if t == "textarea" else 40
            c.add(f'<rect x="{fx:g}" y="{fy + 19:g}" width="{fw:g}" height="{hh}" rx="7" fill="#fff" stroke="{FIELD_LINE}"/>')
            c.text(fx + 10, fy + 44, f["value"], 12, 500, PLACEHOLDER, maxw=fw - 40)
            if t == "select":
                c.text(fx + fw - 14, fy + 44, "▾", 12, 700, SUB_TEXT, "end")
            elif t == "date":
                c.add(f'<rect x="{fx + fw - 28:g}" y="{fy + 31:g}" width="14" height="14" rx="3" fill="none" stroke="{SUB_TEXT}"/>'
                      f'<line x1="{fx + fw - 28:g}" y1="{fy + 36:g}" x2="{fx + fw - 14:g}" y2="{fy + 36:g}" stroke="{SUB_TEXT}"/>')
        if f.get("help"):
            c.text(fx, fy + 19 + (94 if t in ("textarea", "upload") else 40) + 17, f["help"], 11, 500, SUB_TEXT, maxw=fw)


def d_kv(c, b, x, y, w, h):
    c.card(x, y, w, h)
    if b.get("title"):
        c.text(x + 30, y + 42, b["title"], 20, 800, c.t["nav_text"], maxw=w - 60)
    cols = max(1, b.get("cols", 3 if w > 900 else 2 if w > 500 else 1)); cw = (w - 60) / cols
    for i, (k, v) in enumerate(_items(b)):
        cx = x + 30 + (i % cols) * cw; cy = y + 86 + (i // cols) * 62
        c.text(cx, cy, k, 14, 600, SUB_TEXT, maxw=cw - 20)
        c.text(cx, cy + 28, v, 16, 700, c.t["nav_text"], maxw=cw - 20)


def d_text(c, b, x, y, w, h):
    c.card(x, y, w, h)
    yy = y + 24
    if b.get("title"):
        c.card_head(x, y, w, b["title"]); yy = y + 66
    for p in b.get("paragraphs", []):
        for line in c.wrap(p, 14, w - 40):
            yy += 24
            c.text(x + 20, yy - 6, line, 14, 500, c.t["text"])


def d_notice(c, b, x, y, w, h):
    warn = b.get("tone") == "warn"
    bg, line, fg = ("#fff6e6", "#ecd2a6", "#8a5a1c") if warn else (c.t["primary_soft"], c.t["border"], c.t["primary_dark"])
    c.add(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="12" fill="{bg}" stroke="{line}"/>')
    for i, ln in enumerate(c.wrap(b.get("text", ""), 13, w - 48)):
        c.text(x + 24, y + 30 + i * 22, ln, 13, 600, fg)


def d_actions(c, b, x, y, w, h):
    btns = [bt if isinstance(bt, dict) else {"label": bt} for bt in b.get("buttons", [])]
    widths = [text_width(bt["label"], 14) + 40 for bt in btns]
    bx = x + w - sum(widths) - 12 * (len(btns) - 1) if b.get("align", "right") == "right" else x
    for bt, bw in zip(btns, widths):
        c.button(bx, y + 2, bt["label"], bt.get("style") == "primary")
        bx += bw + 12


def d_section(c, b, x, y, w, h):
    c.text(x, y + 26, b.get("text", ""), 23, 800, c.t["nav_text"], maxw=w)


def d_stats(c, b, x, y, w, h):
    items = _items(b); n = max(1, len(items)); gap = 16 if h == 88 else 30; sw = (w - gap * (n - 1)) / n
    for i, it in enumerate(items):
        sx = x + i * (sw + gap)
        c.card(sx, y, sw, h)
        if h == 88:   # 後台統計卡：標籤、數值、右側註記
            c.text(sx + 18, y + 29, it[0], 13, 600, SUB_TEXT, maxw=sw - 36)
            c.text(sx + 18, y + 59, it[1], 22, 800, c.t["primary"])
            if len(it) > 2:
                c.text(sx + sw - 12, y + 59, it[2], 11, 500, "#8a9891", "end")
        else:         # 前台大數字卡：數值在上、說明在下
            c.text(sx + 25, y + 52, it[1], 29, 800, c.t["primary"])
            c.text(sx + 25, y + 86, it[0], 15, 600, "#71847d", maxw=sw - 50)


# ---------- 加強元件：查詢列、頁籤、圖表、歷程、卡片、明細頁首、註記 ----------

def h_filters(b, w): return 92


def d_filters(c, b, x, y, w, h):
    """一列查詢條件＋查詢／重設按鈕。fields 同表單欄位寫法。"""
    c.card(x, y, w, h)
    fields = [_field(f) for f in b.get("fields", [])][:5]
    btn_w = 190
    n = max(1, len(fields)); gap = 14; fw = (w - 40 - btn_w - gap * n) / n
    for i, f in enumerate(fields):
        fx = x + 20 + i * (fw + gap)
        c.text(fx, y + 28, f["label"], 11, 700, LABEL, maxw=fw)
        c.add(f'<rect x="{fx:g}" y="{y + 36:g}" width="{fw:g}" height="38" rx="7" fill="#fff" stroke="{FIELD_LINE}"/>')
        c.text(fx + 10, y + 60, f["value"], 12, 500, PLACEHOLDER, maxw=fw - 34)
        if f["type"] in ("select", "date"):
            c.text(fx + fw - 12, y + 60, "▾", 12, 700, SUB_TEXT, "end")
    rx = x + w - 20
    rx -= small_button(c, rx, y + 40, "重設") + 8
    small_button(c, rx, y + 40, b.get("submit", "查詢"), primary=True)


def h_tabs(b, w): return 46


def d_tabs(c, b, x, y, w, h):
    """頁籤列：items 為 [名稱] 或 [名稱, 數量]；active 為選中的索引（預設 0）。"""
    c.add(f'<line x1="{x:g}" y1="{y + h - 1:g}" x2="{x + w:g}" y2="{y + h - 1:g}" stroke="{FIELD_LINE}"/>')
    tx = x
    for i, it in enumerate(_items(b)):
        label, count = (it[0], it[1] if len(it) > 1 else None) if isinstance(it, (list, tuple)) else (it, None)
        on = i == b.get("active", 0)
        tw = text_width(label, 14) + (text_width(str(count), 11) + 22 if count is not None else 0) + 28
        c.text(tx + 14, y + 28, label, 14, 800 if on else 600, c.t["primary"] if on else SUB_TEXT)
        if count is not None:
            cx = tx + 14 + text_width(label, 14) + 8
            c.add(f'<rect x="{cx:g}" y="{y + 14:g}" width="{text_width(str(count), 11) + 14:g}" height="19" rx="9.5" '
                  f'fill="{c.t["primary_soft"] if on else "#eef2ef"}"/>')
            c.text(cx + 7, y + 28, count, 11, 700, c.t["primary"] if on else SUB_TEXT)
        if on:
            c.add(f'<rect x="{tx:g}" y="{y + h - 3:g}" width="{tw:g}" height="3" rx="1.5" fill="{c.t["primary"]}"/>')
        tx += tw + 6


def h_chart(b, w): return 290


def d_chart(c, b, x, y, w, h):
    """長條圖：labels 與 values 等長；unit 為數值單位（選填）。"""
    c.card(x, y, w, h); c.card_head(x, y, w, b.get("title", ""))
    labels, values = b.get("labels", []), [float(v) for v in b.get("values", [])]
    if not values:
        return
    top = max(values) or 1
    left, bottom, ch = x + 50, y + h - 40, h - 120
    for k in range(4):
        gy = bottom - ch * k / 3
        c.add(f'<line x1="{left:g}" y1="{gy:g}" x2="{x + w - 24:g}" y2="{gy:g}" stroke="{ROW_LINE}"/>')
        c.text(left - 8, gy + 4, f"{top * k / 3:,.0f}", 10, 500, SUB_TEXT, "end")
    n = len(values); slot = (x + w - 24 - left) / n; bw = min(38, slot * .55)
    for i, (lab, v) in enumerate(zip(labels, values)):
        bh = ch * v / top; bx = left + slot * i + (slot - bw) / 2
        c.add(f'<rect x="{bx:g}" y="{bottom - bh:g}" width="{bw:g}" height="{bh:g}" rx="5" fill="{c.t["primary"]}" '
              f'opacity="{.55 + .45 * (i == n - 1):g}"/>')
        c.text(bx + bw / 2, bottom + 18, lab, 11, 600, SUB_TEXT, "middle", maxw=slot - 4)
    if b.get("unit"):
        c.text(x + w - 24, y + 31, b["unit"], 11, 600, SUB_TEXT, "end")


def h_timeline(b, w): return 72 + len(_items(b)) * 58


def d_timeline(c, b, x, y, w, h):
    """處理歷程：items 為 [時間, 標題, 說明]，第一筆為最新。"""
    c.card(x, y, w, h); c.card_head(x, y, w, b.get("title", "處理歷程"))
    items = _items(b)
    for i, it in enumerate(items):
        it = list(it) + ["", "", ""]
        yy = y + 82 + i * 58
        if i < len(items) - 1:
            c.add(f'<line x1="{x + 31:g}" y1="{yy + 4:g}" x2="{x + 31:g}" y2="{yy + 54:g}" stroke="{FIELD_LINE}" stroke-width="2"/>')
        c.add(f'<circle cx="{x + 31:g}" cy="{yy - 4:g}" r="7" fill="{c.t["primary"] if i == 0 else "#fff"}" stroke="{c.t["primary"]}" stroke-width="2"/>')
        c.text(x + 50, yy, it[1], 13, 700, CELL_FIRST, maxw=w - 230)
        c.text(x + w - 20, yy, it[0], 11, 500, SUB_TEXT, "end")
        c.text(x + 50, yy + 19, it[2], 12, 500, SUB_TEXT, maxw=w - 70)


def h_cards(b, w):
    cols = b.get("cols", 3 if w > 900 else 2 if w > 500 else 1)
    rows = math.ceil(len(_items(b)) / max(1, cols))
    return (40 if b.get("title") else 0) + rows * 268 + (rows - 1) * 20


def d_cards(c, b, x, y, w, h):
    """卡片牆（前台常用）：items 為 {title, meta, tag, button} 或 [標題, 說明, 標籤]；上方是圖片示意區。"""
    cols = max(1, b.get("cols", 3 if w > 900 else 2 if w > 500 else 1)); gap = 20
    cw = (w - gap * (cols - 1)) / cols
    yy = y
    if b.get("title"):
        c.text(x, y + 24, b["title"], 20, 800, c.t["nav_text"], maxw=w); yy += 40
    for i, it in enumerate(_items(b)):
        d = it if isinstance(it, dict) else {"title": it[0], "meta": it[1] if len(it) > 1 else "", "tag": it[2] if len(it) > 2 else ""}
        cx = x + (i % cols) * (cw + gap); cy = yy + (i // cols) * (268 + gap)
        c.card(cx, cy, cw, 268)
        c.add(f'<path d="M{cx:g} {cy + 16:g} q0 -16 16 -16 h{cw - 32:g} q16 0 16 16 v124 h{-cw:g} z" fill="{c.t["primary_soft"]}"/>')
        c.add(f'<circle cx="{cx + cw - 46:g}" cy="{cy + 48:g}" r="22" fill="{c.t["primary"]}" opacity=".16"/>'
              f'<path d="M{cx + 24:g} {cy + 122:g} l{cw * .22:g} -46 l{cw * .16:g} 30 l{cw * .14:g} -20 l{cw * .2:g} 36 z" fill="{c.t["primary"]}" opacity=".22"/>')
        if d.get("tag"):
            badge(c, cx + 16, cy + 30, d["tag"], (c.t["surface"], c.t["primary"]))
        c.text(cx + 18, cy + 172, d.get("title", ""), 16, 800, c.t["nav_text"], maxw=cw - 36)
        for k, ln in enumerate(c.wrap(d.get("meta", ""), 12, cw - 36)[:2]):
            c.text(cx + 18, cy + 196 + k * 19, ln, 12, 500, SUB_TEXT)
        if d.get("button"):
            c.text(cx + 18, cy + 250, d["button"] + " →", 13, 750, c.t["primary"])


def h_summary(b, w): return 132


def d_summary(c, b, x, y, w, h):
    """明細頁首：title、status（狀態標籤）、meta（[[欄位, 值]…] 一列）、actions（右側按鈕）。"""
    c.card(x, y, w, h)
    c.text(x + 26, y + 44, b.get("title", ""), 22, 800, c.t["nav_text"], maxw=w - 360)
    if b.get("status"):
        badge(c, x + 34 + text_width(b.get("title", ""), 22), y + 41, b["status"], size=12)
    meta = b.get("meta", [])
    mw = (w - 52) / max(1, len(meta))
    for i, (k, v) in enumerate(meta):
        c.text(x + 26 + i * mw, y + 84, k, 11, 600, SUB_TEXT, maxw=mw - 16)
        c.text(x + 26 + i * mw, y + 108, v, 14, 700, CELL_FIRST, maxw=mw - 16)
    rx = x + w - 24
    for i, label in enumerate(reversed(b.get("actions", []))):
        rx -= small_button(c, rx, y + 22, label, primary=(i == 0)) + 8


def h_caption(b, w): return 18


def d_caption(c, b, x, y, w, h):
    c.text(x + w if b.get("align") == "right" else x, y + 13, b.get("text", ""), 11, 500, "#98a69f",
           "end" if b.get("align") == "right" else None, maxw=w)


BLOCKS = {
    "list": (h_list, d_list), "steps": (h_steps, d_steps), "table": (h_table, d_table), "form": (h_form, d_form),
    "kv": (h_kv, d_kv), "text": (h_text, d_text), "notice": (h_notice, d_notice), "actions": (h_actions, d_actions),
    "section": (h_section, d_section), "stats": (h_stats, d_stats),
    "filters": (h_filters, d_filters), "tabs": (h_tabs, d_tabs), "chart": (h_chart, d_chart),
    "timeline": (h_timeline, d_timeline), "cards": (h_cards, d_cards), "summary": (h_summary, d_summary),
    "caption": (h_caption, d_caption),
}


# ---------- 版型 ----------

def logo(x, y, width) -> str:
    path = ROOT / BRAND.get("logo", "") if BRAND.get("logo") else None
    if not path or not path.exists():
        return ""
    src = path.read_text(encoding="utf-8")
    m = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', src)
    vw, vh = (float(m.group(1)), float(m.group(2))) if m else (1000.0, 200.0)
    inner = re.sub(r"<\?xml.*?\?>|<title[^>]*>.*?</title>|<desc[^>]*>.*?</desc>", "", src, flags=re.S)
    inner = inner[inner.index(">", inner.index("<svg")) + 1: inner.rindex("</svg>")].strip()
    return (f'<svg x="{x}" y="{y}" width="{width}" height="{round(width * vh / vw, 1):g}" viewBox="0 0 {vw:g} {vh:g}" '
            f'preserveAspectRatio="xMidYMid meet" data-logo="{path.stem}">{inner}</svg>')


def nav_group(key: str, pid: str, active: str | None, style: str, warnings: list[str]) -> str:
    import nav
    menu = next((m for m in sitemap_menus() if m.key == key), None)
    if menu is None:
        warnings.append(f"共用選單 nav: {key} 尚未在網站地圖.md › 共用選單設定，選單留空")
        return f'<g data-nav="{key}"></g>'
    if active and menu.active.get(pid) != active:
        menu = dataclasses.replace(menu, active={**menu.active, pid: active})
    if pid not in menu.pages:
        warnings.append(f"{pid} 尚未列在共用選單「{menu.title}」的頁面表，之後 nav.py 不會更新它的選單")
    lines = (nav.render_sidebar if style == "sidebar" else nav.render_topbar)(menu, pid)
    return f'<g data-nav="{key}">\n' + "\n".join(lines) + "\n</g>"


def layout_rows(desc: dict, L: dict, public: bool, warnings: list[str]):
    rows = list(desc.get("rows", []))
    if desc.get("stats"):
        rows.insert(0, [{"type": "stats", "items": desc["stats"], "big": False}])
    placed, y = [], L["top"]
    for row in rows:
        row = row if isinstance(row, list) else [row]
        if len(row) > 3:
            warnings.append("一列最多 3 個區塊，多的已略過")
            row = row[:3]
        for b in row:
            if b.get("type") not in BLOCKS:
                raise SystemExit(f"錯誤｜未知的區塊 type：{b.get('type')}（可用：{'、'.join(BLOCKS)}）")
        row = [{**b, "big": public} if b["type"] == "stats" and "big" not in b else b for b in row]
        flex = [float(b.get("flex", 1)) for b in row]   # 同列寬度比例，例如表單 2：說明 1
        free = L["cw"] - L["gap"] * (len(row) - 1)
        ws = [free * f / sum(flex) for f in flex]
        hs = [BLOCKS[b["type"]][0](b, bw) for b, bw in zip(row, ws)]
        bx = L["x"]
        for i, b in enumerate(row):
            fixed = b["type"] in ("notice", "actions", "section", "tabs", "caption", "filters")
            placed.append((b, bx, y, ws[i], hs[i] if fixed else max(hs)))
            bx += ws[i] + L["gap"]
        y += max(hs) + L["vgap"]
    return placed, y


def build(desc: dict) -> tuple[str, list[str]]:
    warnings: list[str] = []
    pid, name = desc["id"], desc["name"]
    column = desc.get("region") or INDEX_COLUMN.get(expected_region(pid), "")
    preset = MOCKUP.get(column, {})
    t = region_theme(column)
    backend = preset.get("layout", "backend" if column in ("org", "admin") else "public") == "backend"
    L = BACKEND if backend else PUBLIC
    c = Canvas(t, warnings)
    if not backend and desc.get("hero"):
        L = {**L, "top": 116 + 310 + 30}
    placed, end = layout_rows(desc, L, not backend, warnings)
    H = max(L["h"], int(math.ceil(end + L["foot"] + (20 if backend else 0))))
    W = L["w"]
    c.add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="title desc">')
    c.add(f'<title id="title">{esc(name)}</title>')
    c.add(f'<desc id="desc">{esc(desc.get("desc", ""))}</desc>')
    c.add(f'<defs><style>text{{font-family:{t["font"]}}} .muted{{fill:#74877f}}</style>'
          '<filter id="sh" x="-10%" y="-10%" width="120%" height="130%"><feDropShadow dx="0" dy="3" stdDeviation="5" '
          'flood-color="#1e453d" flood-opacity=".07"/></filter></defs>')
    c.add(f'<rect width="{W}" height="{H}" fill="{t["page_bg"]}"/>')
    if backend:
        c.add(f'<rect x="0" y="0" width="248" height="{H}" fill="{t["sidebar"]}"/>')
        c.add(f'<rect x="0" y="0" width="248" height="82" fill="{t["surface"]}"/>')
        lg = logo(14, 9, 220)
        c.add(lg) if lg else c.text(20, 48, BRAND.get("name", ""), 18, 800, t["ink"], maxw=210)
        c.text(20, 71, preset.get("label", ""), 10, 650, "#657870")
        c.text(22, 110, preset.get("sublabel", ""), 12, 600, "#a4bcb3")
        if preset.get("nav"):
            c.add(nav_group(preset["nav"], pid, desc.get("active"), "sidebar", warnings))
        ident = (preset.get("identity") or ["", "", ""]) + ["", "", ""]
        c.add(f'<rect x="18" y="{H - 142}" width="212" height="112" rx="13" fill="#ffffff" opacity=".08"/>')
        c.text(32, H - 108, ident[0], 12, 500, "#b5c9c0"); c.text(32, H - 81, ident[1], 13, 700, "#fff"); c.text(32, H - 53, ident[2], 12, 500, "#d3e4db")
        c.add(f'<rect x="248" y="0" width="1352" height="72" fill="{t["surface"]}"/><line x1="248" y1="71" x2="1600" y2="71" stroke="#e3e9e3"/>')
        c.text(280, 43, preset.get("account", ""), 14, 600, "#536b64")
        c.text(1470, 43, "說明　　通知　　", 14, 500, "#6e827a")
        c.add('<circle cx="1544" cy="36" r="18" fill="#e8f0e9"/>')
        c.text(1544, 41, desc.get("avatar", "王"), 12, 700, "#3e7566", "middle")
        c.text(280, 119, name, 28, 800, t["ink"], maxw=1080)
        c.text(280, 151, desc.get("subtitle", desc.get("desc", "")), 14, 500, t["muted"], maxw=1080)
        badge = desc.get("badge", preset.get("badge", ""))
        if badge:
            c.add(f'<rect x="1375" y="96" width="185" height="36" rx="18" fill="{t["primary_soft"]}"/>')
            c.text(1467, 119, badge, 12, 700, t["primary"], "middle", maxw=170)
    else:
        c.add(f'<rect x="0" y="0" width="{W}" height="82" fill="{t["surface"]}"/><line x1="0" y1="81" x2="{W}" y2="81" stroke="#e6ebe5"/>')
        lg = logo(48, 10, 330) if preset.get("brand", "logo") == "logo" else ""
        c.add(lg) if lg else c.text(48, 50, BRAND.get("name", ""), 20, 800, t["nav_text"], maxw=600)
        if preset.get("nav"):
            c.add(nav_group(preset["nav"], pid, desc.get("active"), "topbar", warnings))
        else:
            for i, item in enumerate(preset.get("nav_items", [])):
                on = item == desc.get("active")
                c.text(710 + 115 * i, 48, item, 15, 700 if on else 600, t["nav_active"] if on else t["nav_text"])
        bx = W - 60
        btns = list(preset.get("buttons", []))
        for i, label in reversed(list(enumerate(btns))):
            bw = text_width(label, 14) + 40
            bx -= bw
            c.button(bx, 20, label, primary=(len(btns) > 1 and i == len(btns) - 1), h=42)
            bx -= 15
        if preset.get("header_note"):
            c.text(W - 48, 47, preset["header_note"], 14, 600, "#627a72", "end")
        hero = desc.get("hero")
        if hero:
            c.add(f'<g data-block="hero"><rect x="64" y="116" width="{W - 128}" height="310" rx="26" fill="{t["primary_soft"]}"/>')
            c.text(104, 176, hero.get("eyebrow", ""), 15, 750, "#c47b5b", maxw=W - 300)
            c.text(104, 232, hero.get("title", name), 34, 800, t["nav_text"], maxw=W - 300)
            text_w = W - 300 if not hero.get("art", True) else W - 640
            for i, ln in enumerate(hero.get("lead", [])):
                c.text(104, 275 + 35 * i, ln, 17 if i == 0 else 15, 500, "#5c746b", maxw=text_w)
            if hero.get("search"):
                c.add(f'<rect x="104" y="342" width="560" height="52" rx="26" fill="#fff" stroke="{FIELD_LINE}"/>')
                c.text(132, 374, hero["search"], 14, 500, PLACEHOLDER, maxw=380)
                c.button(664 - 118, 348, hero.get("search_button", "搜尋"), True, 40)
            elif hero.get("cta"):
                bx = 104
                for k, label in enumerate(hero["cta"]):
                    bx += c.button(bx, 352, label, k == 0, 44) + 14
            if hero.get("art", True):   # 右側插圖示意（抽象幾何）
                ax = W - 520
                c.add(f'<rect x="{ax:g}" y="146" width="400" height="250" rx="22" fill="{t["surface"]}" opacity=".9"/>'
                      f'<rect x="{ax + 24:g}" y="170" width="170" height="14" rx="7" fill="{t["primary"]}" opacity=".35"/>'
                      f'<rect x="{ax + 24:g}" y="196" width="250" height="10" rx="5" fill="{t["primary"]}" opacity=".15"/>'
                      f'<rect x="{ax + 24:g}" y="226" width="110" height="150" rx="14" fill="{t["primary"]}" opacity=".22"/>'
                      f'<rect x="{ax + 146:g}" y="226" width="110" height="150" rx="14" fill="{t["primary"]}" opacity=".14"/>'
                      f'<rect x="{ax + 268:g}" y="226" width="108" height="150" rx="14" fill="{t["primary"]}" opacity=".3"/>'
                      f'<circle cx="{ax + 360:g}" cy="150" r="44" fill="{t["primary"]}" opacity=".12"/>')
            c.add("</g>")
    for b, x, y, w, h in placed:
        c.add(f'<g data-block="{b["type"]}">')
        BLOCKS[b["type"]][1](c, b, x, y, w, h)
        c.add("</g>")
    foot = (preset.get("footer") or ["", ""]) + ["", ""]
    if backend:
        c.add(f'<line x1="280" y1="{H - 30}" x2="1560" y2="{H - 30}" stroke="{FOOT_LINE}"/>')
        c.text(280, H - 8, foot[0], 11, 500, FOOT_TEXT); c.text(1560, H - 8, foot[1], 11, 500, FOOT_TEXT, "end")
    else:
        c.add(f'<line x1="72" y1="{H - 37}" x2="{W - 72}" y2="{H - 37}" stroke="{FOOT_LINE}"/>')
        c.text(72, H - 14, foot[0], 12, 500, "#98a69f"); c.text(W - 72, H - 14, foot[1], 12, 500, "#98a69f", "end")
    c.add("</svg>")
    if H > L["h"]:
        warnings.append(f"內容較多，畫布高度由 {L['h']} 加高為 {H}")
    return "<?xml version='1.0' encoding='utf-8'?>\n" + "\n".join(c.out) + "\n", warnings


def main() -> int:
    args = sys.argv[1:]
    if "--example" in args:
        kind = args[args.index("--example") + 1] if len(args) > args.index("--example") + 1 else "backend"
        print(json.dumps(EXAMPLES.get(kind, EXAMPLES["backend"]), ensure_ascii=False, indent=2))
        return 0
    files = [a for a in args if not a.startswith("--") and (args.index(a) == 0 or args[args.index(a) - 1] != "--out")]
    if len(files) != 1:
        print(__doc__)
        return 2
    desc = json.loads(Path(files[0]).read_text(encoding="utf-8"))
    for key in ("id", "name"):
        if not desc.get(key):
            print(f"錯誤｜頁面描述缺少 {key}")
            return 1
    svg, warnings = build(desc)
    out = Path(args[args.index("--out") + 1]) if "--out" in args else SCREENS / f"{desc['id']}_{desc['name']}.svg"
    existing = [p for p in SCREENS.glob(f"{desc['id']}_*.svg") if p != out] if "--out" not in args else []
    if existing:
        print(f"錯誤｜{desc['id']} 已有 SVG：{existing[0].name}（同一 ID 只能有一張）")
        return 1
    if out.exists() and "--force" not in args:
        print(f"錯誤｜{out.name} 已存在，不覆蓋；修改請局部編輯 SVG（確定是未調整過的初稿才加 --force）")
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg, encoding="utf-8")
    print(f"已產生｜{out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}")
    for w in warnings:
        print("提醒｜" + w)
    if "--out" not in args:
        print("接著：規格加該頁段落（含「**畫面文字（依 SVG 順序）**」標題）→ sync_screen_text.py "
              f"{desc['id']} → 網站地圖.md 加按鈕 → index_build.py → svg_bundle.py → check.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
