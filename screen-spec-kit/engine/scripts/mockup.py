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
  rows                      區塊列：[[區塊, 區塊], [區塊]]；同列等寬並排（最多 3 個）
區塊 type：list、steps、table、form、kv、text、notice、actions、section、stats（各欄位見 --example）。
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
    return sum(size if ord(c) > 0x2E80 else size * 0.58 for c in str(s))


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


# ---------- 區塊：height(block, w) 與 draw(c, block, x, y, w, h) ----------

def _items(b):
    return b.get("items", [])


def h_list(b, w): return 80 + len(_items(b)) * 43
def h_steps(b, w): return 80 + len(_items(b)) * 48
def h_table(b, w): return 100 + len(b.get("rows", [])) * 43
def h_form(b, w): return 82 + math.ceil(len(b.get("fields", [])) / max(1, b.get("cols", 2 if w > 500 else 1))) * 87
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
    cols = b.get("columns", []); n = max(1, len(cols)); cw = (w - 40) / n
    c.add(f'<rect x="{x + 20:g}" y="{y + 60:g}" width="{w - 40:g}" height="31" rx="5" fill="{TABLE_HEAD}"/>')
    for j, hd in enumerate(cols):
        c.text(x + 30 + j * cw, y + 81, hd, 11, 700, SUB_TEXT, maxw=cw - 16)
    yy = y + 119
    for row in b.get("rows", []):
        for j, val in enumerate(list(row)[:n]):
            c.text(x + 30 + j * cw, yy, val, 12, 600 if j == 0 else 500, CELL_FIRST if j == 0 else CELL, maxw=cw - 16)
        c.add(f'<line x1="{x + 20:g}" y1="{yy + 13:g}" x2="{x + w - 20:g}" y2="{yy + 13:g}" stroke="{ROW_LINE}"/>')
        yy += 43


def d_form(c, b, x, y, w, h):
    c.card(x, y, w, h); c.card_head(x, y, w, b.get("title", ""))
    cols = max(1, b.get("cols", 2 if w > 500 else 1)); gap = 15; fw = (w - 40 - gap * (cols - 1)) / cols
    for i, f in enumerate(b.get("fields", [])):
        label, val = (f[0], f[1] if len(f) > 1 else "請輸入") if isinstance(f, (list, tuple)) else (f, "請輸入")
        fx = x + 20 + (i % cols) * (fw + gap); fy = y + 66 + (i // cols) * 87
        c.text(fx, fy + 12, label, 11, 700, LABEL, maxw=fw)
        c.add(f'<rect x="{fx:g}" y="{fy + 19:g}" width="{fw:g}" height="40" rx="7" fill="#fff" stroke="{FIELD_LINE}"/>')
        c.text(fx + 10, fy + 44, val, 12, 500, PLACEHOLDER, maxw=fw - 20)


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


BLOCKS = {
    "list": (h_list, d_list), "steps": (h_steps, d_steps), "table": (h_table, d_table), "form": (h_form, d_form),
    "kv": (h_kv, d_kv), "text": (h_text, d_text), "notice": (h_notice, d_notice), "actions": (h_actions, d_actions),
    "section": (h_section, d_section), "stats": (h_stats, d_stats),
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
        w = (L["cw"] - L["gap"] * (len(row) - 1)) / len(row)
        for b in row:
            if b.get("type") not in BLOCKS:
                raise SystemExit(f"錯誤｜未知的區塊 type：{b.get('type')}（可用：{'、'.join(BLOCKS)}）")
        row = [{**b, "big": public} if b["type"] == "stats" and "big" not in b else b for b in row]
        hs = [BLOCKS[b["type"]][0](b, w) for b in row]
        for i, b in enumerate(row):
            placed.append((b, L["x"] + i * (w + L["gap"]), y, w, max(hs) if b["type"] not in ("notice", "actions", "section") else hs[i]))
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
            for i, ln in enumerate(hero.get("lead", [])):
                c.text(104, 275 + 35 * i, ln, 17 if i == 0 else 15, 500, "#5c746b", maxw=W - 300)
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
