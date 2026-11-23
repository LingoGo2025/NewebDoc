#!/usr/bin/env python3
"""示意圖的圖示與插圖（mockup.py 使用）：取代圓點、山形圖片框這類佔位圖，讓初稿更像真實產品。

- 圖示：24×24 線條圖示（本工具自繪），`icon(name, x, y, size, color)` 回傳 SVG 片段；
  `guess_icon(文字)` 依關鍵字挑圖示（卡片、統計卡、清單沒指定 icon 時使用）。
- 插圖：`art(kind, t, x, y, w, h, **opts)` 回傳 SVG 片段，kind 有
  map（街道地圖＋標記）、plate（車牌辨識畫面）、car（車輛側面）、receipt（收據）、qr（QR Code）、
  document（文件）、phone（手機畫面）、preview（產品預覽卡）、id_card（證件）。
  插圖只用幾何圖形與文字繪製，不引用外部圖片。

本檔沒有命令列用法；直接執行會印出所有圖示與插圖名稱。
"""
from __future__ import annotations

import hashlib
import html
import re

# 24×24 線條圖示（stroke 繪製；「h.01」是圓點）
ICONS: dict[str, str] = {
    "car": "M5 16.5h14v-4.2l-1.9-4.8a1.6 1.6 0 0 0-1.5-1H8.4a1.6 1.6 0 0 0-1.5 1L5 12.3z M5 12.3h14 M7.5 16.5v2 M16.5 16.5v2 M8 14.4h.01 M16 14.4h.01",
    "parking": "M6 3h12a3 3 0 0 1 3 3v12a3 3 0 0 1-3 3H6a3 3 0 0 1-3-3V6a3 3 0 0 1 3-3z M9.5 17V7h3.5a3 3 0 0 1 0 6H9.5",
    "pin": "M12 21s-6.5-5.8-6.5-11a6.5 6.5 0 0 1 13 0c0 5.2-6.5 11-6.5 11z M12 7.6a2.4 2.4 0 1 1 0 4.8a2.4 2.4 0 1 1 0-4.8z",
    "card": "M5 5h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2z M3 10h18 M7 15h4",
    "clock": "M12 3a9 9 0 1 1 0 18a9 9 0 1 1 0-18z M12 7.5V12l3 2",
    "check": "M12 3a9 9 0 1 1 0 18a9 9 0 1 1 0-18z M8.2 12.4l2.6 2.6l5-5.4",
    "x": "M12 3a9 9 0 1 1 0 18a9 9 0 1 1 0-18z M9 9l6 6 M15 9l-6 6",
    "alert": "M12 3.5l9 16H3z M12 10v4.2 M12 17.2h.01",
    "info": "M12 3a9 9 0 1 1 0 18a9 9 0 1 1 0-18z M12 11v5.5 M12 7.8h.01",
    "search": "M11 4a7 7 0 1 1 0 14a7 7 0 1 1 0-14z M16.2 16.2L20.5 20.5",
    "bell": "M6 16.5V11a6 6 0 0 1 12 0v5.5l1.8 1.8H4.2z M10 20.5a2 2 0 0 0 4 0",
    "user": "M12 4a4 4 0 1 1 0 8a4 4 0 1 1 0-8z M4.5 20.5a7.5 7.5 0 0 1 15 0",
    "users": "M9 4.5a3.5 3.5 0 1 1 0 7a3.5 3.5 0 1 1 0-7z M2.5 20a6.5 6.5 0 0 1 13 0 M16 4.8a3.3 3.3 0 0 1 0 6.4 M18 14a6 6 0 0 1 3.5 6",
    "file": "M6 3h8l5 5v13H6z M14 3v5h5 M9 13h6 M9 17h6",
    "calendar": "M5 5h14a1 1 0 0 1 1 1v14H4V6a1 1 0 0 1 1-1z M4 10h16 M8 3v4 M16 3v4 M8 14h.01 M12 14h.01 M16 14h.01",
    "chart": "M4 20h16 M7 16.5v-5 M12 16.5V7 M17 16.5v-8",
    "settings": "M4 7h9 M17 7h3 M4 17h3 M11 17h9 M15 4.5v5 M9 14.5v5",
    "camera": "M4 8h3.2l1.8-2.6h6l1.8 2.6H20v11.5H4z M12 10.5a3.5 3.5 0 1 1 0 7a3.5 3.5 0 1 1 0-7z",
    "receipt": "M6 3h12v18l-2.4-1.6L13.2 21l-2.4-1.6L8.4 21L6 19.4z M9 8h6 M9 12h6 M9 16h3.5",
    "qr": "M4 4h6v6H4z M14 4h6v6h-6z M4 14h6v6H4z M14 14h2.5v2.5H14z M18 18h2v2h-2z M18 14h2 M14 18.5v1.5h2",
    "phone": "M8 2.5h8a2 2 0 0 1 2 2v15a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2v-15a2 2 0 0 1 2-2z M10.5 18.5h3",
    "mail": "M4 5.5h16a1 1 0 0 1 1 1v11a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-11a1 1 0 0 1 1-1z M3.5 7l8.5 6l8.5-6",
    "home": "M3.5 11L12 4l8.5 7 M5.5 9.5V20h13V9.5 M10 20v-5.5h4V20",
    "shield": "M12 3l7.5 2.8v5.7c0 4.6-3.2 8-7.5 9.5c-4.3-1.5-7.5-4.9-7.5-9.5V5.8z M9 12l2.2 2.2L15.2 10",
    "wallet": "M4 7.5h15a1 1 0 0 1 1 1V19H5a1 1 0 0 1-1-1z M4 7.5l11.5-3.3V7.5 M15.5 13.2h2",
    "ticket": "M3 7h18v3.2a1.8 1.8 0 0 0 0 3.6V17H3v-3.2a1.8 1.8 0 0 0 0-3.6z M14.5 7v10",
    "building": "M5 21V4h10v17 M15 9h4v12 M3 21h18 M8 8h.01 M11.5 8h.01 M8 12h.01 M11.5 12h.01 M8 16h.01 M11.5 16h.01",
    "upload": "M12 15.5V4 M7.5 8.5L12 4l4.5 4.5 M4 15v4.5h16V15",
    "download": "M12 4v11.5 M7.5 11L12 15.5L16.5 11 M4 15v4.5h16V15",
    "device": "M3.5 8l12-3.2l1.8 6.2l-12 3.2z M17 7.5l3.5-1 M9.5 13.2l1 3.8 M6 20h7.5 M10.5 17v3",
    "gate": "M4 20V9 M2.5 20h3 M4 10.5h16.5v3H4 M8 10.5l-2 3 M12 10.5l-2 3 M16 10.5l-2 3 M20 10.5l-2 3",
    "list": "M9 6.5h11 M9 12h11 M9 17.5h11 M4.5 6.5h.01 M4.5 12h.01 M4.5 17.5h.01",
    "lock": "M6 11h12v9.5H6z M8.5 11V8a3.5 3.5 0 0 1 7 0v3 M12 15v2",
    "plus": "M12 5v14 M5 12h14",
    "refresh": "M19.5 12a7.5 7.5 0 1 1-2.2-5.3 M19.5 4.5v3.8h-3.8",
    "help": "M12 3a9 9 0 1 1 0 18a9 9 0 1 1 0-18z M9.6 9.3a2.5 2.5 0 1 1 3.5 2.3c-.7.3-1.1.9-1.1 1.6v.6 M12 16.8h.01",
    "money": "M3.5 6.5h17v11h-17z M12 9.5a2.5 2.5 0 1 1 0 5a2.5 2.5 0 1 1 0-5z M6.5 9.5h.01 M17.5 14.5h.01",
    "bolt": "M13 3L5.5 13.5h5.5l-1 7.5l7.5-10.5H12z",
    "navigation": "M12 3l7 18l-7-4l-7 4z",
    "edit": "M4 20h4L19 9l-4-4L4 16z M13.5 6.5l4 4",
    "trash": "M4.5 6.5h15 M9 6.5V4h6v2.5 M6.5 6.5l1 13.5h9l1-13.5 M10 10.5v6 M14 10.5v6",
    "logout": "M14 4h5v16h-5 M10 8l-4 4l4 4 M6 12h9",
    "menu": "M4 7h16 M4 12h16 M4 17h16",
    "star": "M12 3.5l2.6 5.4l5.9.8l-4.3 4.1l1 5.8L12 16.8l-5.2 2.8l1-5.8l-4.3-4.1l5.9-.8z",
    "tag": "M3.5 12.5V4h8.5l8.5 8.5l-8.5 8.5z M8 8h.01",
    "route": "M6 19a2 2 0 1 1 0-4a2 2 0 1 1 0 4z M18 9a2 2 0 1 1 0-4a2 2 0 1 1 0 4z M8 17h7.5a3 3 0 0 0 0-6h-7a3 3 0 0 1 0-6H16",
    "headset": "M4.5 14v-2a7.5 7.5 0 0 1 15 0v2 M4.5 14h3v5h-3z M16.5 14h3v5h-3z M19.5 19c0 1.5-2 2-5 2",
    "wifi": "M3.5 9.5a12 12 0 0 1 17 0 M6.5 12.8a7.5 7.5 0 0 1 11 0 M9.5 16a3.2 3.2 0 0 1 5 0 M12 19h.01",
    "key": "M8 15a4 4 0 1 1 0-8a4 4 0 1 1 0 8z M11.5 11H21 M18 11v3 M15 11v2.5",
}

# 關鍵字 → 圖示（依序比對，先中先用）
ICON_HINTS: list[tuple[str, str]] = [
    (r"車牌|辨識|攝影|鏡頭|照片", "camera"), (r"設備|閘門控制|感測|硬體|離線", "device"), (r"柵欄|閘門|出場|入場|進出", "gate"),
    (r"充電", "bolt"), (r"車位|停車場|場站|空位", "parking"), (r"車輛|車主|汽車|機車", "car"),
    (r"地圖|附近|位置|地址|導航", "pin"), (r"路線|交通", "route"),
    (r"付款|繳費|支付|刷卡|信用卡|金流", "card"), (r"收據|發票|帳單|明細|對帳", "receipt"),
    (r"營收|金額|收入|費用|費率|價格|方案費|退款", "money"), (r"錢包|儲值|點數", "wallet"),
    (r"月租|方案|票|優惠|折扣|券", "ticket"), (r"QR|掃碼|條碼", "qr"),
    (r"審核|核准|驗證|安全|權限|稽核", "shield"), (r"異常|警示|告警|錯誤|失敗|逾期", "alert"),
    (r"通知|提醒|訊息|推播", "bell"), (r"信箱|Email|郵件", "mail"), (r"客服|聯絡|諮詢", "headset"),
    (r"人員|角色|帳號|會員們|使用者們", "users"), (r"會員|個人|帳戶|登入|本人", "user"), (r"密碼|鎖", "lock"),
    (r"報表|統計|趨勢|分析|總覽|營運", "chart"), (r"時間|時數|期限|到期|排程|即時", "clock"),
    (r"日期|日曆|預約|行事曆", "calendar"), (r"申請|文件|資料|表單|合約|規格", "file"),
    (r"上傳", "upload"), (r"下載|匯出", "download"), (r"設定|參數|管理", "settings"),
    (r"查詢|搜尋|找", "search"), (r"說明|常見問題|FAQ|幫助", "help"), (r"首頁|服務", "home"),
    (r"完成|成功|已", "check"), (r"清單|紀錄|列表", "list"),
]


def guess_icon(text: str, default: str = "info") -> str:
    for pattern, name in ICON_HINTS:
        if re.search(pattern, text or ""):
            return name
    return default


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def icon(name: str, x: float, y: float, size: float = 20, color: str = "#087e78", sw: float = 2) -> str:
    """畫圖示：(x, y) 為左上角。不認得的名稱改用 info。"""
    d = ICONS.get(name) or ICONS["info"]
    k = size / 24
    return (f'<g data-icon="{esc(name)}" transform="translate({x:g} {y:g}) scale({k:.4g})" fill="none" stroke="{color}" '
            f'stroke-width="{sw / k:.3g}" stroke-linecap="round" stroke-linejoin="round"><path d="{d}"/></g>')


def icon_badge(name: str, cx: float, cy: float, r: float, fill: str, color: str) -> str:
    """圓底圖示（中心 cx, cy）。"""
    size = r * 1.05
    return (f'<circle cx="{cx:g}" cy="{cy:g}" r="{r:g}" fill="{fill}"/>' + icon(name, cx - size / 2, cy - size / 2, size, color))


# ---------- 插圖 ----------

_CLIP = [0]


def _clip(x, y, w, h, rx=14) -> tuple[str, str]:
    _CLIP[0] += 1
    cid = f"artclip{_CLIP[0]}"
    return cid, f'<clipPath id="{cid}"><rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="{rx:g}"/></clipPath>'


def _seed(s: str) -> int:
    return int(hashlib.md5(str(s).encode("utf-8")).hexdigest()[:8], 16)


TONE_PIN = {"ok": None, "warn": "#d98a1c", "bad": "#c0392b", "off": "#8d9a94"}
PIN_POS = [(.26, .40), (.56, .24), (.72, .58), (.40, .76), (.86, .30), (.14, .64), (.62, .84), (.47, .48)]
STREETS = ["中山路", "民生東路", "復興北路", "光復南路", "健康路", "八德路"]


def _pin_tone(status: str) -> str:
    if re.search(r"滿|已滿|0 位|暫停|關閉|停用", status or ""):
        return "bad"
    if re.search(r"少|即將|剩", status or ""):
        return "warn"
    if re.search(r"未開放|離線|未營業", status or ""):
        return "off"
    return "ok"


def map_art(t: dict, x, y, w, h, pins=None, streets=None, selected=0, here=True, controls=True, rx=14) -> str:
    """街道地圖：pins 為 [[標記文字, 名稱, 狀態]]（標記文字例如空位數「42」）。"""
    pins = pins or [["42", "", ""], ["8", "", "剩"], ["滿", "", "滿"], ["120", "", ""]]
    streets = streets or STREETS
    cid, clip = _clip(x, y, w, h, rx)
    o = [f'<defs>{clip}</defs><g clip-path="url(#{cid})">',
         f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" fill="#eef1ea"/>']
    # 街廓（淺色建物）
    for i in range(14):
        bx = x + ((i * 97) % 100) / 100 * w; by = y + ((i * 61) % 100) / 100 * h
        o.append(f'<rect x="{bx:g}" y="{by:g}" width="{w * .09:g}" height="{h * .1:g}" rx="3" fill="#e3e8df"/>')
    o.append(f'<rect x="{x + w * .52:g}" y="{y + h * .36:g}" width="{w * .16:g}" height="{h * .16:g}" rx="8" fill="#d5e8cf"/>')   # 公園
    o.append(f'<path d="M{x - 10:g} {y + h * .93:g} C{x + w * .3:g} {y + h * .82:g} {x + w * .62:g} {y + h * 1.02:g} {x + w + 10:g} {y + h * .88:g}" '
             f'stroke="#cfe2ee" stroke-width="{max(12, h * .07):g}" fill="none"/>')   # 河
    vx = [.18, .47, .79]; hy = [.30, .66]
    for i, fx in enumerate(vx):
        o.append(f'<line x1="{x + w * fx:g}" y1="{y:g}" x2="{x + w * fx:g}" y2="{y + h:g}" stroke="#fff" stroke-width="{9 if i != 1 else 14}"/>')
    for i, fy in enumerate(hy):
        o.append(f'<line x1="{x:g}" y1="{y + h * fy:g}" x2="{x + w:g}" y2="{y + h * fy:g}" stroke="#fff" stroke-width="{14 if i == 0 else 9}"/>')
    o.append(f'<line x1="{x:g}" y1="{y + h * .95:g}" x2="{x + w * .62:g}" y2="{y:g}" stroke="#fff" stroke-width="8"/>')
    # 路名
    o.append(f'<text x="{x + w * .03:g}" y="{y + h * .30 - 10:g}" font-size="10" font-weight="600" fill="#97a49c">{esc(streets[0])}</text>')
    o.append(f'<text x="{x + w * .82:g}" y="{y + h * .66 - 8:g}" font-size="10" font-weight="600" fill="#97a49c">{esc(streets[1 % len(streets)])}</text>')
    o.append(f'<text transform="translate({x + w * .47 + 12:g} {y + h * .08:g}) rotate(90)" font-size="10" font-weight="600" fill="#97a49c">{esc(streets[2 % len(streets)])}</text>')
    if here:   # 目前位置
        hx, hy_ = x + w * .44, y + h * .56
        o.append(f'<circle cx="{hx:g}" cy="{hy_:g}" r="16" fill="#2f7de1" opacity=".16"/><circle cx="{hx:g}" cy="{hy_:g}" r="6.5" fill="#2f7de1" stroke="#fff" stroke-width="2.5"/>')
    for i, pin in enumerate(pins[:len(PIN_POS)]):
        pin = list(pin) + ["", "", ""]
        label, name, status = str(pin[0]), str(pin[1]), str(pin[2])
        tone = _pin_tone(status or label)
        color = TONE_PIN[tone] or t.get("primary", "#087e78")
        px, py = x + w * PIN_POS[i][0], y + h * PIN_POS[i][1]
        bw = max(38, len(label) * 9 + 30)
        on = i == selected
        o.append(f'<g data-pin="{esc(label)}">')
        o.append(f'<path d="M{px - bw / 2:g} {py - 34:g} h{bw:g} a4 4 0 0 1 4 4 v18 a4 4 0 0 1 -4 4 h{-(bw / 2 - 6):g} l-6 7 l-6 -7 h{-(bw / 2 - 6):g} a4 4 0 0 1 -4 -4 v-18 a4 4 0 0 1 4 -4z" '
                 f'fill="{color if on or tone != "ok" else "#fff"}" stroke="{color}" stroke-width="2"/>')
        o.append(icon("parking", px - bw / 2 + 5, py - 30, 14, "#fff" if (on or tone != "ok") else color, 2.2))
        o.append(f'<text x="{px - bw / 2 + 23:g}" y="{py - 18:g}" font-size="12" font-weight="800" fill="{"#fff" if (on or tone != "ok") else color}">{esc(label)}</text>')
        if on and name:
            nw = len(name) * 12 + 20
            o.append(f'<rect x="{px - nw / 2:g}" y="{py + 10:g}" width="{nw:g}" height="22" rx="11" fill="#fff" stroke="#dfe6e0"/>'
                     f'<text x="{px:g}" y="{py + 25:g}" font-size="11" font-weight="700" fill="#2f4a44" text-anchor="middle">{esc(name)}</text>')
        o.append("</g>")
    if controls:
        cx = x + w - 46
        o.append(f'<rect x="{cx:g}" y="{y + 14:g}" width="32" height="64" rx="8" fill="#fff" stroke="#dfe6e0"/>'
                 f'<line x1="{cx + 6:g}" y1="{y + 46:g}" x2="{cx + 26:g}" y2="{y + 46:g}" stroke="#e6ebe6"/>'
                 + icon("plus", cx + 7, y + 21, 18, "#4f665e") +
                 f'<line x1="{cx + 10:g}" y1="{y + 62:g}" x2="{cx + 22:g}" y2="{y + 62:g}" stroke="#4f665e" stroke-width="2" stroke-linecap="round"/>'
                 f'<rect x="{cx:g}" y="{y + h - 48:g}" width="32" height="32" rx="8" fill="#fff" stroke="#dfe6e0"/>'
                 + icon("navigation", cx + 7, y + h - 41, 18, "#2f7de1"))
    o.append("</g>")
    return "".join(o)


def plate_art(t: dict, x, y, w, h, plate="ABC-1234", stamp="2026-11-23 08:42:15", camera="入口 A1", score="98%", rx=12) -> str:
    """車牌辨識畫面：攝影機畫面＋車頭＋車牌框選。"""
    cid, clip = _clip(x, y, w, h, rx)
    o = [f'<defs>{clip}<linearGradient id="{cid}g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#4a5359"/>'
         f'<stop offset="1" stop-color="#2a3035"/></linearGradient></defs><g clip-path="url(#{cid})">',
         f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" fill="url(#{cid}g)"/>']
    for k in range(5):   # 地面標線
        lx = x + w * (.1 + k * .2)
        o.append(f'<line x1="{lx:g}" y1="{y + h:g}" x2="{x + w / 2 + (lx - x - w / 2) * .35:g}" y2="{y + h * .55:g}" stroke="#5c666c" stroke-width="2"/>')
    W = min(w * .56, h * 1.15); H = W * .66; cx = x + w / 2; y0 = y + h * .93 - H
    body = "#b7c1c8"
    o.append(f'<path d="M{cx - W * .30:g} {y0:g} H{cx + W * .30:g} L{cx + W * .41:g} {y0 + H * .40:g} H{cx - W * .41:g} Z" fill="{body}"/>')
    o.append(f'<path d="M{cx - W * .26:g} {y0 + H * .05:g} H{cx + W * .26:g} L{cx + W * .35:g} {y0 + H * .36:g} H{cx - W * .35:g} Z" fill="#273038"/>')
    o.append(f'<path d="M{cx - W * .2:g} {y0 + H * .09:g} L{cx - W * .05:g} {y0 + H * .09:g} L{cx - W * .17:g} {y0 + H * .3:g} Z" fill="#fff" opacity=".08"/>')
    o.append(f'<rect x="{cx - W * .5:g}" y="{y0 + H * .37:g}" width="{W:g}" height="{H * .48:g}" rx="{W * .07:g}" fill="{body}"/>')
    o.append(f'<rect x="{cx - W * .54:g}" y="{y0 + H * .36:g}" width="{W * .08:g}" height="{H * .07:g}" rx="3" fill="{body}"/>'
             f'<rect x="{cx + W * .46:g}" y="{y0 + H * .36:g}" width="{W * .08:g}" height="{H * .07:g}" rx="3" fill="{body}"/>')
    for side in (-1, 1):
        o.append(f'<rect x="{cx + side * W * .32 - W * .09:g}" y="{y0 + H * .47:g}" width="{W * .18:g}" height="{H * .09:g}" rx="5" fill="#f3f0d6"/>')
        o.append(f'<rect x="{cx + side * W * .38 - W * .07:g}" y="{y0 + H * .82:g}" width="{W * .14:g}" height="{H * .17:g}" rx="4" fill="#1d2226"/>')
    o.append(f'<rect x="{cx - W * .17:g}" y="{y0 + H * .49:g}" width="{W * .34:g}" height="{H * .08:g}" rx="4" fill="#4b545a"/>')
    pw, ph = W * .3, H * .12; py = y0 + H * .63
    fs = max(9, ph * .62)
    o.append(f'<rect x="{cx - pw / 2:g}" y="{py:g}" width="{pw:g}" height="{ph:g}" rx="3" fill="#fbfbf7" stroke="#20262a" stroke-width="1.5"/>')
    o.append(f'<text x="{cx:g}" y="{py + ph * .76:g}" font-size="{fs:.3g}" font-weight="800" fill="#1b2125" text-anchor="middle" '
             f'font-family="Menlo,Consolas,monospace">{esc(plate)}</text>')
    g = "#35d07f"
    o.append(f'<rect x="{cx - pw / 2 - 6:g}" y="{py - 6:g}" width="{pw + 12:g}" height="{ph + 12:g}" fill="none" stroke="{g}" stroke-width="2.5"/>')
    fz = 12 if w >= 380 else 10
    lbl = f"{plate}  {score}" if score else plate
    lw = len(lbl) * fz * .62 + 14
    lx = min(cx - pw / 2 - 6, x + w - lw - 6)
    o.append(f'<rect x="{lx:g}" y="{py - 28:g}" width="{lw:g}" height="20" fill="{g}"/>'
             f'<text x="{lx + 7:g}" y="{py - 14:g}" font-size="{fz}" font-weight="800" fill="#0f2a1b" font-family="Menlo,Consolas,monospace">{esc(lbl)}</text>')
    stamp_w = len(stamp) * fz * .62; cam_w = sum(fz if ord(ch) > 0x2E80 else fz * .6 for ch in camera)
    o.append(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="28" fill="#000" opacity=".35"/>'
             f'<circle cx="{x + 14:g}" cy="{y + 14:g}" r="4.5" fill="#ff4d4d"/>'
             f'<text x="{x + 26:g}" y="{y + 19:g}" font-size="{fz}" font-weight="700" fill="#fff" font-family="Menlo,Consolas,monospace">{esc(stamp)}</text>')
    if stamp_w + cam_w + 50 < w:
        o.append(f'<text x="{x + w - 12:g}" y="{y + 19:g}" font-size="{fz}" font-weight="700" fill="#fff" text-anchor="end">{esc(camera)}</text>')
    else:   # 窄畫面：攝影機名稱放左下角
        o.append(f'<rect x="{x:g}" y="{y + h - 26:g}" width="{cam_w + 20:g}" height="26" fill="#000" opacity=".35"/>'
                 f'<text x="{x + 10:g}" y="{y + h - 9:g}" font-size="{fz}" font-weight="700" fill="#fff">{esc(camera)}</text>')
    o.append("</g>")
    return "".join(o)


def car_art(t: dict, x, y, w, h, color=None, plate="") -> str:
    """車輛側面（列表卡片、我的車輛）。"""
    color = color or t.get("primary", "#087e78")
    W = min(w * .8, h * 1.9); H = W * .42; cx = x + w / 2; base = y + h / 2 + H / 2
    lx = cx - W / 2
    o = [f'<ellipse cx="{cx:g}" cy="{base + 2:g}" rx="{W * .5:g}" ry="{H * .07:g}" fill="#000" opacity=".08"/>',
         f'<path d="M{lx + W * .04:g} {base - H * .18:g} Q{lx:g} {base - H * .5:g} {lx + W * .14:g} {base - H * .55:g} L{lx + W * .3:g} {base - H * .62:g} '
         f'Q{lx + W * .4:g} {base - H * .98:g} {lx + W * .55:g} {base - H * .98:g} L{lx + W * .7:g} {base - H * .96:g} Q{lx + W * .8:g} {base - H * .9:g} '
         f'{lx + W * .88:g} {base - H * .58:g} L{lx + W * .97:g} {base - H * .5:g} Q{lx + W:g} {base - H * .3:g} {lx + W * .97:g} {base - H * .18:g} Z" fill="{color}"/>',
         f'<path d="M{lx + W * .36:g} {base - H * .62:g} Q{lx + W * .43:g} {base - H * .88:g} {lx + W * .55:g} {base - H * .88:g} L{lx + W * .6:g} {base - H * .88:g} '
         f'L{lx + W * .6:g} {base - H * .62:g} Z" fill="#dfeaf0"/>',
         f'<path d="M{lx + W * .64:g} {base - H * .62:g} L{lx + W * .64:g} {base - H * .88:g} L{lx + W * .69:g} {base - H * .87:g} Q{lx + W * .77:g} {base - H * .82:g} '
         f'{lx + W * .82:g} {base - H * .62:g} Z" fill="#dfeaf0"/>']
    for fx in (.24, .78):
        o.append(f'<circle cx="{lx + W * fx:g}" cy="{base - H * .16:g}" r="{H * .2:g}" fill="#263036"/><circle cx="{lx + W * fx:g}" cy="{base - H * .16:g}" r="{H * .09:g}" fill="#c9d1d6"/>')
    if plate:
        o.append(f'<rect x="{lx + W * .9 - 30:g}" y="{base - H * .42:g}" width="44" height="13" rx="2" fill="#fff" stroke="#333"/>'
                 f'<text x="{lx + W * .9 - 8:g}" y="{base - H * .42 + 10:g}" font-size="8" font-weight="800" fill="#222" text-anchor="middle">{esc(plate)}</text>')
    return "".join(o)


def receipt_art(t: dict, x, y, w, h, title="繳費收據", lines=None, total=None) -> str:
    lines = lines or [["停車時數", "2 小時 15 分"], ["應付金額", "NT$ 120"]]
    pw = min(w * .7, 260); px = x + (w - pw) / 2
    ph = min(h * .86, 96 + len(lines) * 22 + (40 if total else 0)); py = y + (h - ph) / 2
    teeth = "".join(f" l{pw / 16:g} 8 l{pw / 16:g} -8" for _ in range(8))
    o = [f'<path d="M{px:g} {py:g} h{pw:g} v{ph:g} H{px:g} Z" fill="#fff" stroke="#e1e7e2" filter="url(#sh)"/>',
         f'<path d="M{px:g} {py + ph:g}{teeth}" fill="none" stroke="#e1e7e2"/>',
         f'<text x="{px + pw / 2:g}" y="{py + 30:g}" font-size="13" font-weight="800" fill="#2b4a44" text-anchor="middle">{esc(title)}</text>',
         f'<line x1="{px + 16:g}" y1="{py + 44:g}" x2="{px + pw - 16:g}" y2="{py + 44:g}" stroke="#e6ebe6" stroke-dasharray="4 4"/>']
    yy = py + 68
    for k, v in lines:
        o.append(f'<text x="{px + 18:g}" y="{yy:g}" font-size="11" font-weight="600" fill="#7d8e87">{esc(k)}</text>'
                 f'<text x="{px + pw - 18:g}" y="{yy:g}" font-size="11" font-weight="700" fill="#3d554e" text-anchor="end">{esc(v)}</text>')
        yy += 22
    if total:
        o.append(f'<line x1="{px + 16:g}" y1="{yy - 8:g}" x2="{px + pw - 16:g}" y2="{yy - 8:g}" stroke="#e6ebe6"/>'
                 f'<text x="{px + 18:g}" y="{yy + 12:g}" font-size="12" font-weight="800" fill="#2b4a44">{esc(total[0])}</text>'
                 f'<text x="{px + pw - 18:g}" y="{yy + 12:g}" font-size="15" font-weight="800" fill="{t.get("primary", "#087e78")}" text-anchor="end">{esc(total[1])}</text>')
    return "".join(o)


def qr_art(t: dict, x, y, size, seed="qr") -> str:
    n = 25; cell = size / n; s = _seed(seed)
    o = [f'<rect x="{x - 8:g}" y="{y - 8:g}" width="{size + 16:g}" height="{size + 16:g}" rx="8" fill="#fff" stroke="#e1e7e2"/>']
    def finder(fx, fy):
        return (f'<rect x="{x + fx * cell:g}" y="{y + fy * cell:g}" width="{7 * cell:g}" height="{7 * cell:g}" fill="#1d2b28"/>'
                f'<rect x="{x + (fx + 1) * cell:g}" y="{y + (fy + 1) * cell:g}" width="{5 * cell:g}" height="{5 * cell:g}" fill="#fff"/>'
                f'<rect x="{x + (fx + 2) * cell:g}" y="{y + (fy + 2) * cell:g}" width="{3 * cell:g}" height="{3 * cell:g}" fill="#1d2b28"/>')
    cells = []
    for i in range(n):
        for j in range(n):
            if (i < 8 and j < 8) or (i < 8 and j > n - 9) or (i > n - 9 and j < 8):
                continue
            s = (s * 1103515245 + 12345) & 0x7FFFFFFF
            if s % 100 < 47:
                cells.append(f"M{x + j * cell:.1f} {y + i * cell:.1f}h{cell:.2f}v{cell:.2f}h-{cell:.2f}z")
    o.append(f'<path d="{"".join(cells)}" fill="#1d2b28"/>')
    o += [finder(0, 0), finder(n - 7, 0), finder(0, n - 7)]
    return "".join(o)


def document_art(t: dict, x, y, w, h, title="文件") -> str:
    pw = min(w * .5, h * .62); ph = pw * 1.3; px = x + (w - pw) / 2; py = y + (h - ph) / 2
    o = [f'<rect x="{px + 10:g}" y="{py + 8:g}" width="{pw:g}" height="{ph:g}" rx="6" fill="#e8eee9"/>',
         f'<path d="M{px:g} {py:g} h{pw * .72:g} l{pw * .28:g} {pw * .28:g} v{ph - pw * .28:g} h{-pw:g} z" fill="#fff" stroke="#dfe6e0"/>',
         f'<path d="M{px + pw * .72:g} {py:g} v{pw * .28:g} h{pw * .28:g}" fill="#eef3ef" stroke="#dfe6e0"/>',
         f'<text x="{px + 14:g}" y="{py + 30:g}" font-size="12" font-weight="800" fill="#2b4a44">{esc(title)}</text>']
    for k in range(5):
        o.append(f'<rect x="{px + 14:g}" y="{py + 48 + k * 18:g}" width="{(pw - 28) * (.95 - (k % 3) * .2):g}" height="7" rx="3.5" fill="#e3e9e4"/>')
    o.append(f'<rect x="{px + 14:g}" y="{py + ph - 34:g}" width="{pw * .38:g}" height="20" rx="4" fill="{t.get("primary_soft", "#e6f2eb")}"/>')
    return "".join(o)


def id_card_art(t: dict, x, y, w, h, title="行車執照") -> str:
    cw = min(w * .78, h * 1.5); ch = cw * .62; cx = x + (w - cw) / 2; cy = y + (h - ch) / 2
    p = t.get("primary", "#087e78")
    o = [f'<rect x="{cx:g}" y="{cy:g}" width="{cw:g}" height="{ch:g}" rx="10" fill="#fff" stroke="#dce4de"/>',
         f'<rect x="{cx:g}" y="{cy:g}" width="{cw:g}" height="{ch * .2:g}" rx="10" fill="{p}" opacity=".85"/>',
         f'<rect x="{cx:g}" y="{cy + ch * .12:g}" width="{cw:g}" height="{ch * .08:g}" fill="{p}" opacity=".85"/>',
         f'<text x="{cx + 14:g}" y="{cy + ch * .14:g}" font-size="11" font-weight="800" fill="#fff">{esc(title)}</text>',
         f'<rect x="{cx + 14:g}" y="{cy + ch * .32:g}" width="{cw * .24:g}" height="{ch * .5:g}" rx="5" fill="#e9efea"/>',
         icon("car", cx + 14 + cw * .12 - 14, cy + ch * .57 - 14, 28, "#9fb1a8")]
    for k in range(4):
        o.append(f'<rect x="{cx + cw * .34:g}" y="{cy + ch * .36 + k * ch * .13:g}" width="{cw * (.52 - (k % 2) * .14):g}" height="7" rx="3.5" fill="#e3e9e4"/>')
    return "".join(o)


def preview_art(t: dict, x, y, w, h, title="", label="", items=None, button="", icon_name=None, status="") -> str:
    """產品預覽卡（前台主視覺右側）：小標、圖示＋標題、幾行重點、按鈕。"""
    items = items or []
    p = t.get("primary", "#087e78")
    o = [f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="20" fill="#fff" filter="url(#sh)"/>']
    if label:
        o.append(f'<text x="{x + 24:g}" y="{y + 34:g}" font-size="12" font-weight="700" fill="#7b8d86">{esc(label)}</text>')
    iy = y + (54 if label else 26)
    o.append(f'<rect x="{x + 20:g}" y="{iy:g}" width="{w - 40:g}" height="{h - (iy - y) - 20:g}" rx="14" fill="{t.get("page_bg", "#f5f6f2")}"/>')
    o.append(icon_badge(icon_name or guess_icon(title, "home"), x + 58, iy + 40, 22, t.get("primary_soft", "#e6f2eb"), p))
    o.append(f'<text x="{x + 92:g}" y="{iy + 36:g}" font-size="16" font-weight="800" fill="#284944">{esc(title)}</text>')
    if status:
        o.append(f'<text x="{x + 92:g}" y="{iy + 56:g}" font-size="12" font-weight="600" fill="#6e827a">{esc(status)}</text>')
    yy = iy + 92
    for k, v in items[:4]:
        o.append(f'<text x="{x + 40:g}" y="{yy:g}" font-size="12" font-weight="600" fill="#7d8e87">{esc(k)}</text>'
                 f'<text x="{x + w - 40:g}" y="{yy:g}" font-size="14" font-weight="800" fill="#2f4a44" text-anchor="end">{esc(v)}</text>')
        yy += 28
    if button:
        bw = len(button) * 13 + 34
        o.append(f'<rect x="{x + w - 40 - bw:g}" y="{y + h - 70:g}" width="{bw:g}" height="34" rx="17" fill="{p}"/>'
                 f'<text x="{x + w - 40 - bw / 2:g}" y="{y + h - 48:g}" font-size="13" font-weight="750" fill="#fff" text-anchor="middle">{esc(button)}</text>')
    return "".join(o)


def phone_art(t: dict, x, y, w, h, title="", items=None, button="", screen="card") -> str:
    """手機畫面（前台主視覺右側）：screen 為 card（預覽卡）或 map（地圖）。"""
    pw = min(w, h * .52); ph = h; px = x + (w - pw) / 2
    o = [f'<rect x="{px:g}" y="{y:g}" width="{pw:g}" height="{ph:g}" rx="30" fill="#1f2a28"/>',
         f'<rect x="{px + 9:g}" y="{y + 9:g}" width="{pw - 18:g}" height="{ph - 18:g}" rx="23" fill="{t.get("page_bg", "#f5f6f2")}"/>',
         f'<rect x="{px + pw / 2 - 30:g}" y="{y + 16:g}" width="60" height="8" rx="4" fill="#1f2a28"/>']
    sx, sy, sw, sh = px + 9, y + 34, pw - 18, ph - 52
    if screen == "map":
        o.append(map_art(t, sx, sy, sw, sh * .62, controls=False, rx=4))
        o.append(f'<rect x="{sx + 8:g}" y="{sy + sh * .62 - 6:g}" width="{sw - 16:g}" height="{sh * .38:g}" rx="14" fill="#fff"/>')
        o.append(f'<text x="{sx + 22:g}" y="{sy + sh * .62 + 20:g}" font-size="12" font-weight="800" fill="#284944">{esc(title)}</text>')
        for k, (a, b) in enumerate((items or [])[:2]):
            o.append(f'<text x="{sx + 22:g}" y="{sy + sh * .62 + 42 + k * 18:g}" font-size="10" font-weight="600" fill="#7d8e87">{esc(a)}</text>'
                     f'<text x="{sx + sw - 22:g}" y="{sy + sh * .62 + 42 + k * 18:g}" font-size="11" font-weight="800" fill="#2f4a44" text-anchor="end">{esc(b)}</text>')
        if button:
            o.append(f'<rect x="{sx + 20:g}" y="{sy + sh - 40:g}" width="{sw - 40:g}" height="28" rx="14" fill="{t.get("primary", "#087e78")}"/>'
                     f'<text x="{sx + sw / 2:g}" y="{sy + sh - 21:g}" font-size="11" font-weight="750" fill="#fff" text-anchor="middle">{esc(button)}</text>')
    else:
        o.append(preview_art(t, sx + 6, sy + 10, sw - 12, sh - 20, title=title, items=items, button=button))
    return "".join(o)


ART_KINDS = {"map", "plate", "car", "receipt", "qr", "document", "id_card", "preview", "phone"}


def art(kind: str, t: dict, x, y, w, h, **o) -> str:
    """依 kind 畫插圖；opts 依各插圖函式（不認得的鍵略過）。"""
    if kind == "map":
        return map_art(t, x, y, w, h, pins=o.get("pins"), streets=o.get("streets"), selected=o.get("selected", 0),
                       here=o.get("here", True), controls=o.get("controls", True))
    if kind == "plate":
        return plate_art(t, x, y, w, h, plate=o.get("plate", "ABC-1234"), stamp=o.get("stamp", "2026-11-23 08:42:15"),
                         camera=o.get("camera", "入口 A1"), score=o.get("score", "98%"))
    if kind == "car":
        return car_art(t, x, y, w, h, color=o.get("color"), plate=o.get("plate", ""))
    if kind == "receipt":
        return receipt_art(t, x, y, w, h, title=o.get("label") or o.get("title", "收據"), lines=o.get("items"), total=o.get("total"))
    if kind == "qr":
        size = min(w, h) - 30
        return qr_art(t, x + (w - size) / 2, y + (h - size) / 2, size, seed=o.get("seed", "qr"))
    if kind == "document":
        return document_art(t, x, y, w, h, title=o.get("label") or o.get("title", "文件"))
    if kind == "id_card":
        return id_card_art(t, x, y, w, h, title=o.get("label") or o.get("title", "證件"))
    if kind == "phone":
        return phone_art(t, x, y, w, h, title=o.get("title", ""), items=o.get("items"), button=o.get("button", ""),
                         screen=o.get("screen", "card"))
    return preview_art(t, x, y, w, h, title=o.get("title", ""), label=o.get("label", ""), items=o.get("items"),
                       button=o.get("button", ""), icon_name=o.get("icon"), status=o.get("status", ""))


if __name__ == "__main__":
    print("圖示：" + "、".join(ICONS))
    print("插圖：" + "、".join(sorted(ART_KINDS)))
