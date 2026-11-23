#!/usr/bin/env python3
"""新頁面 SVG 示意圖：依頁面描述（JSON）以元件組合產生初稿。

用法：
  python3 scripts/mockup.py <描述.json>              # 產生 screens/<ID>_<名稱>.svg（檔案已存在時不覆蓋）
  python3 scripts/mockup.py <描述.json> --force      # 覆寫（只用於尚未手動調整過的初稿）
  python3 scripts/mockup.py <描述.json> --out <路徑>  # 輸出到指定檔案（例如暫存目錄預覽）
  python3 scripts/mockup.py <描述.json> --mobile     # 產生手機版 screens/mobile/<ID>_<名稱>.svg（桌機版仍是主要畫面）
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
  summary（明細頁首：標題＋狀態標籤＋重點欄位＋按鈕）、caption（小字註記），
  stepper（多步驟進度）、result（成功／失敗結果）、price（金額明細）、choice（選項卡，例如付款方式、方案）、
  map（地圖＋標記）、tiles（狀態格，例如車位、設備）、media（插圖：車牌辨識畫面、證件、收據、QR Code…）、empty（空狀態）。
  圖示與插圖見 mockup_art.py；cards／list／stats 沒指定 icon 時依文字自動挑選。
版型：project.json › mockup › <column> › layout 為 backend 或 public（桌機版，主要畫面）；需要手機版的頁面另以 --mobile
  產生 390 寬手機版到 screens/mobile/（描述可加 mobile_rows 取代手機版的區塊列）。layout: mobile 仍可用，但一般不把主要畫面設成手機版。
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
from mockup_art import ART_KINDS, art, guess_icon, icon, icon_badge

BACKEND = {"w": 1600, "h": 1080, "x": 280, "cw": 1280, "gap": 18, "vgap": 15, "top": 185, "foot": 30}
PUBLIC = {"w": 1440, "h": 1000, "x": 76, "cw": 1288, "gap": 30, "vgap": 28, "top": 116, "foot": 60}
MOBILE = {"w": 390, "h": 844, "x": 16, "cw": 358, "gap": 12, "vgap": 14, "top": 120, "foot": 70}
NARROW = 520   # 區塊寬度小於此值時改用手機排版（表格變卡片、按鈕滿版…）


def narrow(w) -> bool:
    return w < NARROW
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
    "ok": ("#e3f4ea", "#1f7a4d", r"啟用|已核准|核准|成功|已付款|完成|正常|有效|已上傳|已開立|營業中|上線|通過|已結案|已處理|已繳費|在場|空位|可停|有空位|已放行|已退款|上架"),
    "warn": ("#fff2d9", "#9a6200", r"待|審核中|處理中|即將|候補|草稿|未讀|排程|部分|使用中|佔用|保留|剩餘|退款中"),
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


def _rich_list(b) -> bool:
    """清單項目有 icon、右側文字或 dict 寫法時，改用較高的列（圖示＋主副文＋右側值）。"""
    return bool(b.get("icons")) or any(isinstance(it, dict) or (isinstance(it, (list, tuple)) and len(it) > 2) for it in _items(b))


def h_list(b, w): return 70 + len(_items(b)) * 58 if _rich_list(b) else 80 + len(_items(b)) * 43
def h_steps(b, w): return 80 + len(_items(b)) * 48
def h_table(b, w):
    if narrow(w):   # 手機：每列一張小卡
        return 62 + len(b.get("rows", [])) * 64 + (46 if b.get("pager") else 0)
    return 100 + len(b.get("rows", [])) * 43 + (46 if b.get("pager") else 0)
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
                      "radio": "", "checkbox": "", "switch": ""}.get(t, "請輸入")
    return d


def _form_layout(b, w):
    """回傳 [(field, col, row_y, span)] 與總高度；textarea、upload 佔整列。"""
    cols = 1 if narrow(w) else max(1, b.get("cols", 2 if w > 500 else 1))
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
def h_kv(b, w):
    if narrow(w):
        return (66 if b.get("title") else 20) + len(_items(b)) * 40 + 8
    return 66 + math.ceil(len(_items(b)) / max(1, b.get("cols", 3 if w > 900 else 2 if w > 500 else 1))) * 62 + 10
def h_section(b, w): return 34
def h_actions(b, w):
    n = len(b.get("buttons", []))
    return n * 48 + (n - 1) * 10 if narrow(w) and n else 44


def h_text(b, w):
    lines = sum(len(Canvas({}, []).wrap(p, 14, w - 40)) for p in b.get("paragraphs", []))
    return (66 if b.get("title") else 24) + lines * 24 + 12


def h_notice(b, w):
    return 26 + len(Canvas({}, []).wrap(b.get("text", ""), 13, w - 48)) * 22


def _stat_cols(b, w) -> int:
    n = max(1, len(_items(b)))
    return min(n, 2) if narrow(w) else n


def h_stats(b, w):
    one = 116 if b.get("big", True) else 88
    rows = math.ceil(max(1, len(_items(b))) / _stat_cols(b, w))
    return rows * one + (rows - 1) * 12


def d_list(c, b, x, y, w, h):
    c.card(x, y, w, h); c.card_head(x, y, w, b.get("title", ""))
    head_actions(c, b, x, y, w)
    if _rich_list(b):   # 圖示＋主文＋副文＋右側值（通知、待辦、紀錄）
        for i, it in enumerate(_items(b)):
            d = it if isinstance(it, dict) else {"title": it[0] if isinstance(it, (list, tuple)) else it,
                                                  "sub": it[1] if isinstance(it, (list, tuple)) and len(it) > 1 else "",
                                                  "right": it[2] if isinstance(it, (list, tuple)) and len(it) > 2 else ""}
            yy = y + 66 + i * 58
            name = d.get("icon") or guess_icon(f"{d.get('title', '')}{d.get('sub', '')}", "info")
            tone = tone_of(str(d.get("right", ""))) if d.get("right") else None
            c.add(icon_badge(name, x + 40, yy + 26, 17, c.t["primary_soft"], c.t["primary"]))
            right_w = text_width(str(d.get("right", "")), 12) + 24 if d.get("right") else 0
            c.text(x + 68, yy + 22, d.get("title", ""), 13, 700, CELL_FIRST, maxw=w - 88 - right_w)
            if d.get("sub"):
                c.text(x + 68, yy + 41, d["sub"], 12, 500, SUB_TEXT, maxw=w - 88 - right_w)
            if d.get("right"):
                if tone and len(str(d["right"])) <= 6:
                    badge(c, x + w - 20 - text_width(str(d["right"]), 11) - 18, yy + 30, d["right"])
                else:
                    c.text(x + w - 20, yy + 30, d["right"], 12, 500, SUB_TEXT, "end")
            if i < len(_items(b)) - 1:
                c.add(f'<line x1="{x + 68:g}" y1="{yy + 56:g}" x2="{x + w - 20:g}" y2="{yy + 56:g}" stroke="{ROW_LINE}"/>')
        return
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


def d_table_narrow(c, b, x, y, w, h):
    """手機版表格：第一欄當標題、狀態欄放右側標籤，其餘欄位合成一行摘要。"""
    c.card(x, y, w, h); c.card_head(x, y, w, b.get("title", ""))
    head_actions(c, b, x, y, w)
    cols = list(b.get("columns", []))
    for i, row in enumerate(b.get("rows", [])):
        row = [str(v) for v in row]
        yy = y + 62 + i * 64
        st = next((j for j, hd in enumerate(cols) if j > 0 and j < len(row) and (is_status_col(hd) or (tone_of(row[j]) and len(row[j]) <= 5))), None)
        bw = text_width(row[st], 11) + 18 if st is not None else 0
        c.text(x + 20, yy + 24, row[0] if row else "", 14, 700, CELL_FIRST, maxw=w - 60 - bw)
        if st is not None:
            badge(c, x + w - 20 - bw, yy + 24, row[st])
        rest = "・".join(v for j, v in enumerate(row[1:], 1) if j != st and v)
        c.text(x + 20, yy + 46, rest, 12, 500, SUB_TEXT, maxw=w - 54)
        c.text(x + w - 18, yy + 46, "›", 16, 600, "#a3b0aa", "end")
        c.add(f'<line x1="{x + 20:g}" y1="{yy + 62:g}" x2="{x + w - 20:g}" y2="{yy + 62:g}" stroke="{ROW_LINE}"/>')
    if b.get("pager"):
        total = b["pager"] if isinstance(b["pager"], str) else f"共 {len(b.get('rows', []))} 筆"
        c.text(x + w / 2, y + h - 18, f"{total}・載入更多", 12, 600, c.t["primary"], "middle")


def d_table(c, b, x, y, w, h):
    if narrow(w):
        return d_table_narrow(c, b, x, y, w, h)
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
        t = f["type"]
        if not (t == "checkbox" and not f.get("options")):
            c.text(fx, fy + 12, f["label"], 11, 700, LABEL, maxw=fw - 12)
        if f["required"] and not (t == "checkbox" and not f.get("options")):
            c.text(fx + text_width(f["label"], 11) + 2, fy + 12, "*", 12, 800, "#c0392b")
        if t == "switch":
            c.add(f'<rect x="{fx:g}" y="{fy + 26:g}" width="44" height="24" rx="12" fill="{c.t["primary"]}"/>'
                  f'<circle cx="{fx + 32:g}" cy="{fy + 38:g}" r="9" fill="#fff"/>')
            c.text(fx + 56, fy + 43, f.get("value") if f.get("value") not in ("請輸入", "") else "已啟用", 12, 600, CELL)
        elif t == "checkbox" and not f.get("options"):   # 單一勾選（同意條款、記住車牌）：標籤寫在方框旁
            c.add(f'<rect x="{fx:g}" y="{fy + 30:g}" width="16" height="16" rx="4" fill="{c.t["primary"]}" stroke="{c.t["primary"]}"/>'
                  f'<path d="M{fx + 4:g} {fy + 38:g} l3 3 l6 -6" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round"/>')
            c.text(fx + 24, fy + 43, f["label"], 12, 600, CELL, maxw=fw - 24)
        elif t in ("radio", "checkbox"):
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
    if narrow(w):   # 手機：標籤在左、內容在右
        c.card(x, y, w, h)
        yy = y + 20
        if b.get("title"):
            c.card_head(x, y, w, b["title"]); yy = y + 66
        for i, (k, v) in enumerate(_items(b)):
            kw = min(text_width(k, 13), w * .38)
            c.text(x + 20, yy + i * 40 + 16, k, 13, 600, SUB_TEXT, maxw=w * .38)
            c.text(x + w - 20, yy + i * 40 + 16, v, 14 if text_width(v, 14) <= w - 56 - kw else 12, 700, c.t["nav_text"], "end", maxw=w - 56 - kw)
            if i < len(_items(b)) - 1:
                c.add(f'<line x1="{x + 20:g}" y1="{yy + i * 40 + 30:g}" x2="{x + w - 20:g}" y2="{yy + i * 40 + 30:g}" stroke="{ROW_LINE}"/>')
        return
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
    if narrow(w):   # 手機：滿版按鈕，主要動作在最上面
        btns = sorted(btns, key=lambda bt: bt.get("style") != "primary")
        for i, bt in enumerate(btns):
            by = y + i * 58; prim = bt.get("style") == "primary"
            c.add(f'<rect x="{x:g}" y="{by:g}" width="{w:g}" height="48" rx="24" fill="{c.t["primary"] if prim else "#fff"}" '
                  f'stroke="{c.t["primary"] if prim else FIELD_LINE}"/>')
            c.text(x + w / 2, by + 30, bt["label"], 15, 750, "#fff" if prim else c.t["nav_active"], "middle")
        return
    widths = [text_width(bt["label"], 14) + 40 for bt in btns]
    bx = x + w - sum(widths) - 12 * (len(btns) - 1) if b.get("align", "right") == "right" else x
    for bt, bw in zip(btns, widths):
        c.button(bx, y + 2, bt["label"], bt.get("style") == "primary")
        bx += bw + 12


def d_section(c, b, x, y, w, h):
    c.text(x, y + 26, b.get("text", ""), 23, 800, c.t["nav_text"], maxw=w)


def d_stats(c, b, x, y, w, h):
    items = _items(b); n = _stat_cols(b, w); big = b.get("big", True); one = 116 if big else 88
    gap = 12 if narrow(w) else (16 if not big else 30); sw = (w - gap * (n - 1)) / n
    for i, it in enumerate(items):
        sx = x + (i % n) * (sw + gap); sy = y + (i // n) * (one + 12)
        c.card(sx, sy, sw, one)
        name = it[3] if len(it) > 3 else guess_icon(str(it[0]), "")
        if not big:   # 後台統計卡：標籤、數值、右側註記、右上圖示
            c.text(sx + 18, sy + 29, it[0], 13, 600, SUB_TEXT, maxw=sw - (66 if name else 36))
            room = sw - 36 - (34 if name and sw > 150 else 0)   # 右上有圖示時，數值不可壓到圖示
            c.text(sx + 18, sy + 59, it[1], 22 if text_width(str(it[1]), 22) <= room else 17, 800, c.t["primary"], maxw=sw - 36)
            if name and sw > 150:
                c.add(icon_badge(name, sx + sw - 30, sy + 28, 15, c.t["primary_soft"], c.t["primary"]))
            if len(it) > 2 and it[2]:
                below = narrow(w) or (name and sw > 150)   # 窄卡片或有圖示時，註記放數值下方，避免重疊
                c.text(sx + sw - 12 if not narrow(w) else sx + 18, sy + 78 if narrow(w) else (sy + 76 if below else sy + 59), it[2], 11, 500,
                       "#8a9891", None if narrow(w) else "end", maxw=sw - 30)
        else:         # 前台大數字卡：數值在上、說明在下
            c.text(sx + 25, sy + 52, it[1], 29 if sw > 200 else 24, 800, c.t["primary"], maxw=sw - 40)
            c.text(sx + 25, sy + 86, it[0], 15 if sw > 200 else 13, 600, "#71847d", maxw=sw - 50)


# ---------- 加強元件：查詢列、頁籤、圖表、歷程、卡片、明細頁首、註記 ----------

def h_filters(b, w): return 64 if narrow(w) else 92


def d_filters(c, b, x, y, w, h):
    """一列查詢條件＋查詢／重設按鈕。fields 同表單欄位寫法。"""
    fields = [_field(f) for f in b.get("fields", [])][:5]
    if narrow(w):   # 手機：一個搜尋框＋篩選按鈕
        first = fields[0]["label"] if fields else "關鍵字"
        c.add(f'<rect x="{x:g}" y="{y + 8:g}" width="{w - 96:g}" height="46" rx="23" fill="#fff" stroke="{FIELD_LINE}"/>')
        c.add(icon("search", x + 16, y + 21, 20, SUB_TEXT))
        c.text(x + 44, y + 36, f"搜尋{first}", 13, 500, PLACEHOLDER, maxw=w - 150)
        c.add(f'<rect x="{x + w - 86:g}" y="{y + 8:g}" width="86" height="46" rx="23" fill="#fff" stroke="{FIELD_LINE}"/>')
        c.add(icon("settings", x + w - 74, y + 21, 18, c.t["nav_active"]))
        c.text(x + w - 50, y + 36, "篩選", 13, 700, c.t["nav_active"])
        return
    c.card(x, y, w, h)
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
        if tx + tw > x + w + 1:
            break
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


def h_timeline(b, w): return 72 + len(_items(b)) * (74 if narrow(w) else 58)


def d_timeline(c, b, x, y, w, h):
    """處理歷程：items 為 [時間, 標題, 說明]，第一筆為最新。"""
    c.card(x, y, w, h); c.card_head(x, y, w, b.get("title", "處理歷程"))
    items = _items(b); step = 74 if narrow(w) else 58
    for i, it in enumerate(items):
        it = list(it) + ["", "", ""]
        yy = y + 82 + i * step
        if i < len(items) - 1:
            c.add(f'<line x1="{x + 31:g}" y1="{yy + 4:g}" x2="{x + 31:g}" y2="{yy + step - 4:g}" stroke="{FIELD_LINE}" stroke-width="2"/>')
        c.add(f'<circle cx="{x + 31:g}" cy="{yy - 4:g}" r="7" fill="{c.t["primary"] if i == 0 else "#fff"}" stroke="{c.t["primary"]}" stroke-width="2"/>')
        if narrow(w):   # 手機：時間放在說明下方
            c.text(x + 50, yy, it[1], 13, 700, CELL_FIRST, maxw=w - 70)
            c.text(x + 50, yy + 19, it[2], 12, 500, SUB_TEXT, maxw=w - 70)
            c.text(x + 50, yy + 37, it[0], 11, 500, "#9aa7a1")
            continue
        c.text(x + 50, yy, it[1], 13, 700, CELL_FIRST, maxw=w - 230)
        c.text(x + w - 20, yy, it[0], 11, 500, SUB_TEXT, "end")
        c.text(x + 50, yy + 19, it[2], 12, 500, SUB_TEXT, maxw=w - 70)


def h_cards(b, w):
    if narrow(w):
        n = len(_items(b))
        return (40 if b.get("title") else 0) + n * 96 + (n - 1) * 12
    cols = b.get("cols", 3 if w > 900 else 2 if w > 500 else 1)
    rows = math.ceil(len(_items(b)) / max(1, cols))
    return (40 if b.get("title") else 0) + rows * 268 + (rows - 1) * 20


def _card_item(it) -> dict:
    return it if isinstance(it, dict) else {"title": it[0], "meta": it[1] if len(it) > 1 else "", "tag": it[2] if len(it) > 2 else ""}


def _card_art_opts(d: dict) -> dict:
    return {k: v for k, v in d.items() if k not in ("title", "meta", "tag", "button", "icon", "art", "stat")}


def d_cards(c, b, x, y, w, h):
    """卡片牆（前台常用）：items 為 {title, meta, tag, button} 或 [標題, 說明, 標籤]；上方是圖片示意區。"""
    yy = y
    if b.get("title"):
        c.text(x, y + 24, b["title"], 20, 800, c.t["nav_text"], maxw=w); yy += 40
    if narrow(w):   # 手機：橫式小卡（圖示、標題、說明、右側數字或箭頭）
        for i, it in enumerate(_items(b)):
            d = _card_item(it); cy = yy + i * 108
            c.card(x, cy, w, 96)
            name = d.get("icon") or guess_icon(f"{d.get('title', '')}{d.get('meta', '')}", "home")
            c.add(icon_badge(name, x + 40, cy + 48, 22, c.t["primary_soft"], c.t["primary"]))
            stat = d.get("stat")
            rw = 70 if stat else 24
            c.text(x + 76, cy + 40, d.get("title", ""), 15, 800, c.t["nav_text"], maxw=w - 96 - rw)
            c.text(x + 76, cy + 62, d.get("meta", ""), 12, 500, SUB_TEXT, maxw=w - 96 - rw)
            if d.get("tag"):
                c.text(x + 76, cy + 80, d["tag"], 11, 700, c.t["primary"], maxw=w - 96 - rw)
            if stat:
                c.text(x + w - 18, cy + 46, stat[0], 20, 800, c.t["primary"], "end")
                c.text(x + w - 18, cy + 64, stat[1] if len(stat) > 1 else "", 11, 600, SUB_TEXT, "end")
            else:
                c.text(x + w - 18, cy + 54, "›", 20, 600, "#a3b0aa", "end")
        return
    cols = max(1, b.get("cols", 3 if w > 900 else 2 if w > 500 else 1)); gap = 20
    cw = (w - gap * (cols - 1)) / cols
    for i, it in enumerate(_items(b)):
        d = _card_item(it)
        cx = x + (i % cols) * (cw + gap); cy = yy + (i // cols) * (268 + gap)
        c.card(cx, cy, cw, 268)
        c.add(f'<path d="M{cx:g} {cy + 16:g} q0 -16 16 -16 h{cw - 32:g} q16 0 16 16 v124 h{-cw:g} z" fill="{c.t["primary_soft"]}"/>')
        if d.get("art") in ART_KINDS:   # 指定插圖（地圖、車輛、收據…）
            c.add(f'<g data-art="{d["art"]}">' + art(d["art"], c.t, cx + 1, cy + 1, cw - 2, 139, **_card_art_opts(d)) + "</g>")
        else:   # 圖示＋重點數字
            name = d.get("icon") or guess_icon(f"{d.get('title', '')}{d.get('meta', '')}", "home")
            c.add(icon_badge(name, cx + 50, cy + 84, 28, c.t["surface"], c.t["primary"]))
            if d.get("stat"):
                st = d["stat"]
                c.text(cx + cw - 22, cy + 88, st[0], 30, 800, c.t["primary"], "end")
                c.text(cx + cw - 22, cy + 112, st[1] if len(st) > 1 else "", 12, 600, c.t["primary_dark"], "end")
        if d.get("tag"):
            badge(c, cx + 16, cy + 30, d["tag"], (c.t["surface"], c.t["primary"]))
        c.text(cx + 18, cy + 172, d.get("title", ""), 16, 800, c.t["nav_text"], maxw=cw - 36)
        for k, ln in enumerate(c.wrap(d.get("meta", ""), 12, cw - 36)[:2]):
            c.text(cx + 18, cy + 196 + k * 19, ln, 12, 500, SUB_TEXT)
        if d.get("button"):
            c.text(cx + 18, cy + 250, d["button"] + " →", 13, 750, c.t["primary"])


def h_summary(b, w):
    if narrow(w):
        return 92 + len(b.get("meta", [])) * 34 + (58 if b.get("actions") else 0)
    return 132


def d_summary(c, b, x, y, w, h):
    """明細頁首：title、status（狀態標籤）、meta（[[欄位, 值]…] 一列）、actions（右側按鈕）。"""
    if narrow(w):   # 手機：標題、狀態、欄位逐列、按鈕在下方
        c.card(x, y, w, h)
        c.text(x + 20, y + 38, b.get("title", ""), 18, 800, c.t["nav_text"], maxw=w - 40)
        if b.get("status"):
            badge(c, x + 20, y + 68, b["status"], size=12)
        for i, (k, v) in enumerate(b.get("meta", [])):
            yy = y + 104 + i * 34
            c.text(x + 20, yy, k, 13, 600, SUB_TEXT, maxw=w * .38)
            c.text(x + w - 20, yy, v, 14, 700, CELL_FIRST, "end", maxw=w * .55)
        acts = b.get("actions", [])
        if acts:
            bw = (w - 40 - 10 * (len(acts) - 1)) / len(acts); by = y + h - 56
            for i, label in enumerate(acts):
                prim = i == len(acts) - 1
                c.add(f'<rect x="{x + 20 + i * (bw + 10):g}" y="{by:g}" width="{bw:g}" height="40" rx="20" '
                      f'fill="{c.t["primary"] if prim else "#fff"}" stroke="{c.t["primary"] if prim else FIELD_LINE}"/>')
                c.text(x + 20 + i * (bw + 10) + bw / 2, by + 25, label, 13, 750, "#fff" if prim else c.t["nav_active"], "middle", maxw=bw - 12)
        return
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


# ---------- 流程與真實感元件：步驟、結果、金額、選項、地圖、狀態格、插圖、空狀態 ----------

def h_stepper(b, w): return 64 if narrow(w) else 78


def d_stepper(c, b, x, y, w, h):
    """多步驟進度：items 為步驟名稱，current 為目前步驟索引（0 起算）。"""
    items = [str(i) for i in _items(b)]; cur = int(b.get("current", 0)); n = max(1, len(items))
    c.card(x, y, w, h)
    if narrow(w):
        c.text(x + 20, y + 26, f"步驟 {cur + 1}／{n}", 11, 700, SUB_TEXT)
        c.text(x + 20 + text_width(f"步驟 {cur + 1}／{n}", 11) + 10, y + 26, items[cur] if items else "", 14, 800, c.t["nav_text"], maxw=w - 120)
        c.add(f'<rect x="{x + 20:g}" y="{y + 40:g}" width="{w - 40:g}" height="6" rx="3" fill="{TABLE_HEAD}"/>'
              f'<rect x="{x + 20:g}" y="{y + 40:g}" width="{(w - 40) * (cur + 1) / n:g}" height="6" rx="3" fill="{c.t["primary"]}"/>')
        return
    sw = (w - 40) / n
    for i, label in enumerate(items):
        cx = x + 20 + i * sw + 18; cy = y + 39
        done, on = i < cur, i == cur
        if i < n - 1:
            lx = cx + 26 + text_width(label, 14)
            c.add(f'<line x1="{lx:g}" y1="{cy:g}" x2="{x + 20 + (i + 1) * sw + 2:g}" y2="{cy:g}" stroke="{c.t["primary"] if done else FIELD_LINE}" stroke-width="2"/>')
        if done:
            c.add(f'<circle cx="{cx:g}" cy="{cy:g}" r="14" fill="{c.t["primary"]}"/>'
                  f'<path d="M{cx - 6:g} {cy:g} l4 4 l8 -8" fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>')
        else:
            c.add(f'<circle cx="{cx:g}" cy="{cy:g}" r="14" fill="{c.t["primary"] if on else "#fff"}" stroke="{c.t["primary"] if on else FIELD_LINE}" stroke-width="2"/>')
            c.text(cx, cy + 5, i + 1, 13, 800, "#fff" if on else SUB_TEXT, "middle")
        c.text(cx + 22, cy + 5, label, 14, 800 if on else 600, c.t["nav_text"] if (on or done) else SUB_TEXT, maxw=sw - 50)


RESULT_TONE = {"ok": ("check", "#e3f4ea", "#1f7a4d"), "bad": ("x", "#fde7e7", "#b3261e"),
               "warn": ("alert", "#fff2d9", "#9a6200"), "info": ("info", None, None)}


def _result_lines(c, b, w):
    return c.wrap(b.get("text", ""), 14, min(w - 80, 560))


def h_result(b, w):
    lines = len(_result_lines(Canvas({}, []), b, w))
    n = len(b.get("items", []))
    btn = len(b.get("buttons", []))
    return (150 + lines * 24 + (n * 36 + 30 if n else 0) + ((btn * 58 if narrow(w) else 60) if btn else 0) + 26)


def d_result(c, b, x, y, w, h):
    """結果頁主體：tone（ok／bad／warn／info）、title、text、items（[[欄位, 值]]）、buttons（最後一個為主按鈕）。"""
    name, fill, ink = RESULT_TONE.get(b.get("tone", "ok"), RESULT_TONE["ok"])
    fill, ink = fill or c.t["primary_soft"], ink or c.t["primary"]
    c.card(x, y, w, h)
    cx = x + w / 2
    c.add(f'<circle cx="{cx:g}" cy="{y + 68:g}" r="44" fill="{fill}" opacity=".55"/>' + icon_badge(b.get("icon") or name, cx, y + 68, 32, fill, ink))
    c.text(cx, y + 142, b.get("title", ""), 22 if not narrow(w) else 19, 800, c.t["nav_text"], "middle", maxw=w - 40)
    yy = y + 150
    for ln in _result_lines(c, b, w):
        yy += 24
        c.text(cx, yy, ln, 14, 500, c.t["text"], "middle")
    items = b.get("items", [])
    if items:
        bw = min(w - 40, 520); bx = cx - bw / 2; by = yy + 20
        c.add(f'<rect x="{bx:g}" y="{by:g}" width="{bw:g}" height="{len(items) * 36 + 14:g}" rx="12" fill="{c.t["page_bg"]}"/>')
        for i, (k, v) in enumerate(items):
            c.text(bx + 18, by + 31 + i * 36, k, 13, 600, SUB_TEXT, maxw=bw * .4)
            c.text(bx + bw - 18, by + 31 + i * 36, v, 14, 750, CELL_FIRST, "end", maxw=bw * .56)
        yy = by + len(items) * 36 + 14
    btns = b.get("buttons", [])
    if btns:
        labels = [bt["label"] if isinstance(bt, dict) else bt for bt in btns]
        if narrow(w):
            for i, label in enumerate(reversed(labels)):
                prim = i == 0; by = yy + 22 + i * 58
                c.add(f'<rect x="{x + 20:g}" y="{by:g}" width="{w - 40:g}" height="48" rx="24" fill="{c.t["primary"] if prim else "#fff"}" stroke="{c.t["primary"] if prim else FIELD_LINE}"/>')
                c.text(cx, by + 30, label, 15, 750, "#fff" if prim else c.t["nav_active"], "middle")
        else:
            total = sum(text_width(l, 14) + 40 for l in labels) + 12 * (len(labels) - 1)
            bx = cx - total / 2
            for i, label in enumerate(labels):
                bx += c.button(bx, yy + 24, label, i == len(labels) - 1, 44) + 12


def h_price(b, w):
    note = len(Canvas({}, []).wrap(b.get("note", ""), 11, w - 40)[:3]) if b.get("note") else 0
    return 66 + len(_items(b)) * 36 + 62 + (12 + note * 17 if note else 0)


def d_price(c, b, x, y, w, h):
    """金額明細：items（[[項目, 金額]]）、total（[標籤, 金額]）、note（小字）。"""
    c.card(x, y, w, h); c.card_head(x, y, w, b.get("title", "金額明細"))
    yy = y + 84
    for k, v in _items(b):
        c.text(x + 20, yy, k, 14, 500, c.t["text"], maxw=w * .55)
        c.text(x + w - 20, yy, v, 14, 650, CELL_FIRST, "end")
        yy += 36
    c.add(f'<line x1="{x + 20:g}" y1="{yy - 16:g}" x2="{x + w - 20:g}" y2="{yy - 16:g}" stroke="{DIVIDER}" stroke-dasharray="5 4"/>')
    tot = b.get("total") or ["應付金額", ""]
    c.text(x + 20, yy + 18, tot[0], 15, 800, c.t["nav_text"])
    c.text(x + w - 20, yy + 20, tot[1], 26, 800, c.t["primary"], "end")
    for i, ln in enumerate(c.wrap(b.get("note", ""), 11, w - 40)[:3] if b.get("note") else []):
        c.text(x + 20, yy + 52 + i * 17, ln, 11, 500, SUB_TEXT)


def _choice_cols(b, w):
    return 1 if narrow(w) else max(1, b.get("cols", min(len(_items(b)), 3) if w > 700 else 1))


def h_choice(b, w):
    rows = math.ceil(len(_items(b)) / _choice_cols(b, w))
    return (66 if b.get("title") else 16) + rows * 80 + (rows - 1) * 12 + 18


def d_choice(c, b, x, y, w, h):
    """選項卡（付款方式、方案、時段）：items 為 {title, meta, icon, right} 或 [標題, 說明, 右側]；selected 為選中索引。"""
    c.card(x, y, w, h)
    top = y + 16
    if b.get("title"):
        c.card_head(x, y, w, b["title"]); top = y + 66
    cols = _choice_cols(b, w); gap = 12; ow = (w - 40 - gap * (cols - 1)) / cols
    for i, it in enumerate(_items(b)):
        d = it if isinstance(it, dict) else {"title": it[0], "meta": it[1] if len(it) > 1 else "", "right": it[2] if len(it) > 2 else ""}
        ox = x + 20 + (i % cols) * (ow + gap); oy = top + (i // cols) * 92
        on = i == b.get("selected", 0)
        c.add(f'<rect x="{ox:g}" y="{oy:g}" width="{ow:g}" height="80" rx="12" fill="{c.t["primary_soft"] if on else "#fff"}" '
              f'stroke="{c.t["primary"] if on else FIELD_LINE}" stroke-width="{2 if on else 1}"/>')
        c.add(f'<circle cx="{ox + 24:g}" cy="{oy + 40:g}" r="9" fill="#fff" stroke="{c.t["primary"] if on else FIELD_LINE}" stroke-width="2"/>')
        if on:
            c.add(f'<circle cx="{ox + 24:g}" cy="{oy + 40:g}" r="4.5" fill="{c.t["primary"]}"/>')
        name = d.get("icon") or guess_icon(f"{d.get('title', '')}{d.get('meta', '')}", "card")
        c.add(icon(name, ox + 44, oy + 28, 24, c.t["primary"] if on else SUB_TEXT))
        rw = text_width(str(d.get("right", "")), 13) + 16 if d.get("right") else 0
        c.text(ox + 80, oy + 36, d.get("title", ""), 14, 750, CELL_FIRST, maxw=ow - 96 - rw)
        c.text(ox + 80, oy + 56, d.get("meta", ""), 12, 500, SUB_TEXT, maxw=ow - 96 - rw)
        if d.get("right"):
            c.text(ox + ow - 16, oy + 46, d["right"], 13, 750, c.t["primary"] if on else CELL, "end")


def h_map(b, w):
    mh = b.get("height", 260 if narrow(w) else 380)
    return (66 if b.get("title") else 16) + mh + (34 if b.get("legend", True) else 0) + 16


def d_map(c, b, x, y, w, h):
    """地圖＋標記：pins 為 [[標記文字, 名稱, 狀態]]（狀態含「滿」紅色、「剩／少」橘色）；search 為地圖上的搜尋框提示字。"""
    c.card(x, y, w, h)
    top = y + 16
    if b.get("title"):
        c.card_head(x, y, w, b["title"]); head_actions(c, b, x, y, w); top = y + 64
    mh = b.get("height", 260 if narrow(w) else 380)
    c.add(art("map", c.t, x + 16, top, w - 32, mh, pins=b.get("pins"), streets=b.get("streets"), selected=b.get("selected", 0)))
    if b.get("search"):
        sw_ = min(w - 110, 380)
        c.add(f'<rect x="{x + 30:g}" y="{top + 14:g}" width="{sw_:g}" height="40" rx="20" fill="#fff" stroke="{FIELD_LINE}" filter="url(#sh)"/>')
        c.add(icon("search", x + 44, top + 24, 18, SUB_TEXT))
        c.text(x + 70, top + 39, b["search"], 13, 500, PLACEHOLDER, maxw=sw_ - 56)
    if b.get("legend", True):
        lx = x + 20; ly = top + mh + 26
        for label, color in (b.get("legend_items") or [["有空位", c.t["primary"]], ["即將額滿", "#d98a1c"], ["已滿", "#c0392b"]]):
            c.add(f'<circle cx="{lx + 5:g}" cy="{ly - 4:g}" r="5" fill="{color}"/>')
            c.text(lx + 15, ly, label, 12, 600, SUB_TEXT)
            lx += text_width(label, 12) + 36


def _tile_cols(b, w):
    return max(1, b.get("cols", max(3, int((w - 40) / (82 if narrow(w) else 96)))))


def h_tiles(b, w):
    rows = math.ceil(len(_items(b)) / _tile_cols(b, w))
    return (66 if b.get("title") else 16) + rows * 64 + (34 if b.get("legend", True) else 0) + 8


def d_tiles(c, b, x, y, w, h):
    """狀態格（車位、設備、座位）：items 為 [[名稱, 狀態]]，依狀態上色（可用／使用中／異常…）。"""
    c.card(x, y, w, h)
    top = y + 16
    if b.get("title"):
        c.card_head(x, y, w, b["title"]); head_actions(c, b, x, y, w); top = y + 64
    cols = _tile_cols(b, w); gap = 10; tw = (w - 40 - gap * (cols - 1)) / cols
    seen = {}
    for i, it in enumerate(_items(b)):
        label, status = (list(it) + [""])[:2]
        fill, ink = tone_of(str(status)) or ("#eef2ef", "#5a6f68")
        seen.setdefault(str(status), (fill, ink))
        tx = x + 20 + (i % cols) * (tw + gap); ty = top + (i // cols) * 64
        c.add(f'<rect x="{tx:g}" y="{ty:g}" width="{tw:g}" height="54" rx="10" fill="{fill}" stroke="{ink}" stroke-opacity=".25"/>')
        c.text(tx + 12, ty + 23, label, 13, 800, ink, maxw=tw - 20)
        c.text(tx + 12, ty + 42, status, 11, 600, ink, maxw=tw - 20)
    if b.get("legend", True):
        lx = x + 20; ly = y + h - 18
        for status, (fill, ink) in list(seen.items())[:5]:
            c.add(f'<rect x="{lx:g}" y="{ly - 11:g}" width="14" height="14" rx="4" fill="{fill}" stroke="{ink}" stroke-opacity=".4"/>')
            c.text(lx + 20, ly, status, 12, 600, SUB_TEXT)
            lx += text_width(status, 12) + 44


def _media_split(b, w):
    return bool(b.get("side")) and not narrow(w) and w > 640


def h_media(b, w):
    ah = b.get("height", 230 if narrow(w) else 280)
    side = len(b.get("side", []))
    body = ah if _media_split(b, w) else ah + (side * 40 + 10 if side else 0)
    return (66 if b.get("title") else 16) + body + (30 if b.get("caption") else 0) + 16


def d_media(c, b, x, y, w, h):
    """插圖區：art 為 plate（車牌辨識畫面）、car、receipt、qr、document、id_card、map、phone、preview；
    side 為旁邊的資訊列 [[欄位, 值]]；caption 為圖說。其餘欄位傳給插圖（例如 plate、stamp、camera、score）。"""
    c.card(x, y, w, h)
    top = y + 16
    if b.get("title"):
        c.card_head(x, y, w, b["title"]); head_actions(c, b, x, y, w); top = y + 64
    ah = b.get("height", 230 if narrow(w) else 280)
    opts = {k: v for k, v in b.items() if k not in ("type", "title", "art", "side", "caption", "flex", "height", "actions", "art_title")}
    if b.get("art_title"):   # 插圖內的標題（例如預覽卡的活動名稱）
        opts["title"] = b["art_title"]
    split = _media_split(b, w)
    aw = (w - 32) * .52 if split else w - 32
    c.add(f'<g data-art="{b.get("art", "preview")}">' + art(b.get("art", "preview"), c.t, x + 16, top, aw, ah, **opts) + "</g>")
    side = b.get("side", [])
    if side:
        sx, sy, sw = (x + 16 + aw + 24, top + 6, w - 32 - aw - 24) if split else (x + 20, top + ah + 10, w - 40)
        for i, (k, v) in enumerate(side):
            yy = sy + i * 40 + 24
            c.text(sx, yy, k, 13, 600, SUB_TEXT, maxw=sw * .4)
            tone = tone_of(str(v)) if len(str(v)) <= 6 else None
            if tone:
                badge(c, sx + sw - text_width(str(v), 11) - 18, yy, v)
            else:
                c.text(sx + sw, yy, v, 14, 700, CELL_FIRST, "end", maxw=sw * .58)
            c.add(f'<line x1="{sx:g}" y1="{yy + 14:g}" x2="{sx + sw:g}" y2="{yy + 14:g}" stroke="{ROW_LINE}"/>')
    if b.get("caption"):
        c.text(x + 20, y + h - 18, b["caption"], 12, 500, SUB_TEXT, maxw=w - 40)


def h_empty(b, w): return 250


def d_empty(c, b, x, y, w, h):
    """空狀態：icon、title、text、button。"""
    c.card(x, y, w, h)
    cx = x + w / 2
    c.add(icon_badge(b.get("icon") or guess_icon(b.get("title", ""), "search"), cx, y + 70, 34, c.t["page_bg"], SUB_TEXT))
    c.text(cx, y + 136, b.get("title", "目前沒有資料"), 17, 800, c.t["nav_text"], "middle", maxw=w - 40)
    c.text(cx, y + 162, b.get("text", ""), 13, 500, SUB_TEXT, "middle", maxw=w - 40)
    if b.get("button"):
        bw = text_width(b["button"], 14) + 40
        c.button(cx - bw / 2, y + 186, b["button"], True, 40)


BLOCKS = {
    "list": (h_list, d_list), "steps": (h_steps, d_steps), "table": (h_table, d_table), "form": (h_form, d_form),
    "kv": (h_kv, d_kv), "text": (h_text, d_text), "notice": (h_notice, d_notice), "actions": (h_actions, d_actions),
    "section": (h_section, d_section), "stats": (h_stats, d_stats),
    "filters": (h_filters, d_filters), "tabs": (h_tabs, d_tabs), "chart": (h_chart, d_chart),
    "timeline": (h_timeline, d_timeline), "cards": (h_cards, d_cards), "summary": (h_summary, d_summary),
    "caption": (h_caption, d_caption),
    "stepper": (h_stepper, d_stepper), "result": (h_result, d_result), "price": (h_price, d_price),
    "choice": (h_choice, d_choice), "map": (h_map, d_map), "tiles": (h_tiles, d_tiles), "media": (h_media, d_media),
    "empty": (h_empty, d_empty),
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
    lines = nav.STYLES[style]["render"](menu, pid)
    return f'<g data-nav="{key}">\n' + "\n".join(lines) + "\n</g>"


def layout_rows(desc: dict, L: dict, public: bool, warnings: list[str]):
    rows = list(desc.get("rows", []))
    if desc.get("stats"):
        rows.insert(0, [{"type": "stats", "items": desc["stats"], "big": False}])
    if L["w"] == MOBILE["w"] or L.get("cw", 0) <= 460:   # 手機或置中窄版：每個區塊各占一列
        rows = [[b] for row in rows for b in (row if isinstance(row, list) else [row])]
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


def hero_art(c: "Canvas", hero: dict, x, y, w, h) -> None:
    """前台主視覺右側：art 為 False（不畫）、插圖種類字串（map、phone、plate…）或 {kind, …選項}；
    沒指定時畫產品預覽卡（preview），內容取自 hero › preview。"""
    spec = hero.get("art", True)
    if spec is False:
        return
    if isinstance(spec, str):
        spec = {"kind": spec}
    elif not isinstance(spec, dict):
        spec = {"kind": "preview"}
    opts = {**(hero.get("preview") or {}), **{k: v for k, v in spec.items() if k != "kind"}}
    opts.setdefault("title", hero.get("title", "")[:14])
    kind = spec.get("kind", "preview")
    if kind == "phone":
        c.add(f'<g data-art="phone">' + art("phone", c.t, x + w - 250, y - 22, 250, h + 44, **opts) + "</g>")
    else:
        c.add(f'<g data-art="{kind}">' + art(kind, c.t, x, y, w, h, **opts) + "</g>")


def mobile_chrome(c: "Canvas", desc: dict, preset: dict, pid: str, H: int, warnings: list[str], variant: bool = False) -> None:
    """手機版頁首（品牌、通知、選單）與頁首下方的頁籤列。"""
    t = c.t; W = MOBILE["w"]
    c.add(f'<rect x="0" y="0" width="{W}" height="56" fill="{t["surface"]}"/><line x1="0" y1="55.5" x2="{W}" y2="55.5" stroke="#e6ebe5"/>')
    if desc.get("back"):
        c.text(16, 36, "‹", 26, 500, t["nav_text"])
        c.text(W / 2, 35, desc.get("back") if isinstance(desc.get("back"), str) else desc["name"], 16, 800, t["nav_text"], "middle", maxw=W - 120)
    elif desc.get("brand_text"):   # 頁首改寫文字品牌（例如收款單位自己的網站）
        c.text(16, 35, desc["brand_text"], 17, 800, t["nav_text"], maxw=W - 110)
    else:
        lg = logo(16, 12, 150) if preset.get("brand", "logo") == "logo" else ""
        c.add(lg) if lg else c.text(16, 35, BRAND.get("name", ""), 17, 800, t["nav_text"], maxw=220)
    c.add(icon("bell", W - 82, 16, 22, t["nav_text"]) + icon("menu", W - 44, 16, 22, t["nav_text"]))
    if preset.get("nav") and not variant:
        c.add(nav_group(preset["nav"], pid, desc.get("active"), "tabbar", warnings))
    else:
        # 手機版變體：選單項目取共用選單（只畫不登記，nav.py 不改 screens/mobile/），沒有時用 nav_items
        menu = next((m for m in sitemap_menus() if m.key == preset.get("nav")), None) if preset.get("nav") else None
        items = desc["nav_items"] if "nav_items" in desc else (menu.items if menu else preset.get("nav_items", []))
        active = desc.get("active") or (menu.active.get(pid) if menu else None)
        x = 16.0
        # 反白項目超出畫面時，整列往左捲到看得見（如同手機上滑動頁籤列）
        widths = [text_width(it, 14) + 28 for it in items]
        if active in items:
            k = items.index(active)
            end = 16 + sum(widths[:k + 1]) + 8 * k
            x -= max(0, end - (W - 16))
        c.add('<g data-mobile-nav="1">')
        for item in items:
            on = item == active
            w = text_width(item, 14) + 28
            c.add(f'<rect x="{x:g}" y="66" width="{w:g}" height="32" rx="16" fill="{t["primary"] if on else "#ffffff"}" stroke="{t["primary"] if on else "#dfe6e0"}"/>')
            c.text(x + 14, 87, item, 14, 700 if on else 600, "#fff" if on else t["nav_text"])
            x += w + 8
        c.add("</g>")


def build(desc: dict) -> tuple[str, list[str]]:
    warnings: list[str] = []
    pid, name = desc["id"], desc["name"]
    column = desc.get("region") or INDEX_COLUMN.get(expected_region(pid), "")
    preset = MOCKUP.get(column, {})
    t = region_theme(column)
    layout = desc.get("layout") or preset.get("layout", "backend" if column in ("org", "admin") else "public")
    variant = desc.get("variant") == "mobile"   # 手機版變體（screens/mobile/）
    if variant:
        layout = "mobile"
        if desc.get("mobile_rows"):
            desc = {**desc, "rows": desc["mobile_rows"]}
    mobile = layout == "mobile"
    backend = layout == "backend"
    L = MOBILE if mobile else BACKEND if backend else PUBLIC
    bare = bool(desc.get("bare"))   # 登入、註冊這類獨立頁：不畫側欄與選單，內容置中
    if bare:
        W0 = L["w"]; cw = min(460, W0 - 32)
        L = {"w": W0, "h": 844 if mobile else 900, "x": (W0 - cw) / 2, "cw": cw, "gap": 16, "vgap": 16,
             "top": 150 if mobile else 200, "foot": 60}
    c = Canvas(t, warnings)
    hero = desc.get("hero")
    hero_h = 0
    show_title = mobile and not bare and not hero and column != "public" and not desc.get("hide_title", False)
    has_tabs = bool(desc["nav_items"]) if "nav_items" in desc else bool(preset.get("nav") or preset.get("nav_items"))
    if bare:
        pass
    elif mobile:
        top = MOBILE["top"] if has_tabs else 72
        if hero:
            lines = c.wrap(hero.get("title", name), 24, 358 - 40)
            lead = [ln for p in hero.get("lead", [])[:2] for ln in c.wrap(p, 14, 358 - 40)]
            hero_h = 30 + (22 if hero.get("eyebrow") else 0) + len(lines) * 32 + len(lead) * 22 + 78
            top += hero_h + 16
        elif show_title:
            sub_lines = c.wrap(desc.get("subtitle", desc.get("desc", "")), 13, 358)[:2]
            top += 70 + 18 * (len(sub_lines) - 1)
        L = {**L, "top": top}
    elif not backend and hero:
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
    if bare:
        c.add(f'<rect width="{W}" height="{min(H, 360 if not mobile else 240)}" fill="{t["sidebar"] if backend else t["primary_soft"]}"/>')
        lg = logo(W / 2 - 110, 60, 220)
        ink = "#fff" if backend else t["nav_text"]
        c.add(lg) if lg else c.text(W / 2, 96 if not mobile else 80, BRAND.get("name", ""), 26 if not mobile else 22, 800, ink, "middle", maxw=W - 40)
        c.text(W / 2, 132 if not mobile else 110, preset.get("label", "") if backend else "", 13, 600, "#a4bcb3" if backend else t["muted"], "middle")
    elif mobile:
        mobile_chrome(c, desc, preset, pid, H, warnings, variant)
        if hero:
            hy = MOBILE["top"] if has_tabs else 72
            c.add(f'<g data-block="hero"><rect x="16" y="{hy}" width="358" height="{hero_h}" rx="20" fill="{t["primary_soft"]}"/>')
            yy = hy + 30
            if hero.get("eyebrow"):
                c.text(36, yy, hero["eyebrow"], 12, 750, "#c47b5b", maxw=318); yy += 22
            for ln in c.wrap(hero.get("title", name), 24, 318):
                yy += 32 if yy > hy + 30 or not hero.get("eyebrow") else 30
                c.text(36, yy - 4, ln, 24, 800, t["nav_text"])
            yy += 4
            for p in hero.get("lead", [])[:2]:
                for ln in c.wrap(p, 14, 318):
                    yy += 22
                    c.text(36, yy - 2, ln, 14, 500, "#5c746b")
            by = hy + hero_h - 66
            if hero.get("search"):
                c.add(f'<rect x="32" y="{by:g}" width="326" height="48" rx="24" fill="#fff" stroke="{FIELD_LINE}"/>')
                c.add(icon("search", 48, by + 13, 20, SUB_TEXT))
                c.text(76, by + 30, hero["search"], 13, 500, PLACEHOLDER, maxw=270)
            elif hero.get("cta"):
                labels = hero["cta"][:2]; bw = (326 - 10 * (len(labels) - 1)) / len(labels)
                for k, label in enumerate(labels):
                    c.add(f'<rect x="{32 + k * (bw + 10):g}" y="{by:g}" width="{bw:g}" height="46" rx="23" fill="{t["primary"] if k == 0 else "#fff"}"/>')
                    c.text(32 + k * (bw + 10) + bw / 2, by + 29, label, 14, 750, "#fff" if k == 0 else t["nav_active"], "middle", maxw=bw - 16)
            c.add("</g>")
        elif show_title:
            ty = MOBILE["top"] if has_tabs else 72
            c.text(16, ty + 30, name, 22, 800, t["ink"], maxw=358)
            for i, ln in enumerate(c.wrap(desc.get("subtitle", desc.get("desc", "")), 13, 358)[:2]):
                c.text(16, ty + 52 + i * 18, ln, 13, 500, t["muted"], maxw=358)
    elif backend:
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
        c.add(icon("help", 1452, 24, 22, "#6e827a") + icon("bell", 1490, 24, 22, "#6e827a"))
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
        if hero:
            c.add(f'<g data-block="hero"><rect x="64" y="116" width="{W - 128}" height="310" rx="26" fill="{t["primary_soft"]}"/>')
            c.text(104, 176, hero.get("eyebrow", ""), 15, 750, "#c47b5b", maxw=W - 300)
            c.text(104, 232, hero.get("title", name), 34, 800, t["nav_text"], maxw=W - 300 if hero.get("art") is False else W - 680)
            text_w = W - 300 if hero.get("art") is False else W - 680
            for i, ln in enumerate(hero.get("lead", [])):
                c.text(104, 275 + 35 * i, ln, 17 if i == 0 else 15, 500, "#5c746b", maxw=text_w)
            if hero.get("search"):
                c.add(f'<rect x="104" y="342" width="560" height="52" rx="26" fill="#fff" stroke="{FIELD_LINE}"/>')
                c.add(icon("search", 124, 356, 22, SUB_TEXT))
                c.text(154, 374, hero["search"], 14, 500, PLACEHOLDER, maxw=380)
                c.button(664 - 118, 348, hero.get("search_button", "搜尋"), True, 40)
            elif hero.get("cta"):
                bx = 104
                for k, label in enumerate(hero["cta"]):
                    bx += c.button(bx, 352, label, k == 0, 44) + 14
            hero_art(c, hero, W - 560, 140, 440, 262)
            c.add("</g>")
    for b, x, y, w, h in placed:
        c.add(f'<g data-block="{b["type"]}">')
        BLOCKS[b["type"]][1](c, b, x, y, w, h)
        c.add("</g>")
    foot = (preset.get("footer") or ["", ""]) + ["", ""]
    if bare:
        c.text(W / 2, H - 24, foot[0], 11, 500, FOOT_TEXT, "middle", maxw=W - 32)
    elif mobile:
        c.add(f'<line x1="16" y1="{H - 44}" x2="{W - 16}" y2="{H - 44}" stroke="{FOOT_LINE}"/>')
        c.text(W / 2, H - 20, foot[0], 11, 500, FOOT_TEXT, "middle", maxw=W - 32)
    elif backend:
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
    mobile = "--mobile" in args or desc.get("variant") == "mobile"
    if mobile:
        desc["variant"] = "mobile"
    svg, warnings = build(desc)
    folder = SCREENS / "mobile" if mobile else SCREENS
    out = Path(args[args.index("--out") + 1]) if "--out" in args else folder / f"{desc['id']}_{desc['name']}.svg"
    existing = [p for p in folder.glob(f"{desc['id']}_*.svg") if p != out] if "--out" not in args else []
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
    if "--out" not in args and mobile:
        print(f"接著：規格該頁寫「- 手機版示意圖：`screens/mobile/{out.name}`」→ svg_bundle.py → dev_notes.py → check.py")
    elif "--out" not in args:
        print("接著：規格加該頁段落（含「**畫面文字（依 SVG 順序）**」標題）→ sync_screen_text.py "
              f"{desc['id']} → 網站地圖.md 加按鈕 → index_build.py → svg_bundle.py → check.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
