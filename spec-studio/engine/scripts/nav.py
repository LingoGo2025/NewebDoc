#!/usr/bin/env python3
"""依「網站地圖.md › 共用選單」表格，批次更新各 SVG 的選單區塊。

用法：
  python3 scripts/nav.py              # 套用所有選單
  python3 scripts/nav.py member       # 只套用 nav: member 這組選單（key 見表格標題的 nav: xxx）
  python3 scripts/nav.py --check      # 只檢查，不寫檔（check.py 也會呼叫）

只替換 <g data-nav="key">…</g> 區塊；第一次執行時會把舊的選單元素包進這個群組。
選單文字有變動的頁面，會自動同步規格中的「畫面文字（依 SVG 順序）」清單。
"""
from __future__ import annotations

import re
import sys

from _common import SCREENS, SPEC, THEME, Menu, read, screen_files, sitemap_menus, svg_texts

# ---------- 樣式 ----------

ELEMENT = re.compile(r"<(?:text|rect)\b[^>]*?(?:/>|>[^<]*</text>)")


def elements(block: str) -> list[str]:
    """取出選單元素並忽略空白差異（如 ` />` 與 `/>`）。"""
    return [re.sub(r"\s+", " ", re.sub(r"\s*/>", "/>", e)) for e in ELEMENT.findall(block)]


def render_sidebar(menu: Menu, page: str) -> list[str]:
    if len(menu.items) > 14:
        raise ValueError(f"{menu.title}: 側欄最多 14 項，目前 {len(menu.items)} 項")
    out = []
    for i, item in enumerate(menu.items):
        y = 155 + 55 * i
        if menu.active.get(page) == item:
            out.append(f'<rect x="13" y="{y - 27}" width="222" height="44" rx="10" fill="#ffffff" opacity=".14"/>')
            out.append(f'<text x="29" y="{y}" font-size="15" font-weight="700" fill="#fff">{item}</text>')
        else:
            out.append(f'<text x="29" y="{y}" font-size="15" font-weight="500" fill="#c2d2cb">{item}</text>')
    return out


def render_topbar(menu: Menu, page: str) -> list[str]:
    n = len(menu.items)
    step = 115 if n <= 4 else (1190 - 70 - 710) // (n - 1)
    if step < 80:
        raise ValueError(f"{menu.title}: 頂部導覽放不下 {n} 項（與右側按鈕重疊），請縮減項目")
    out = []
    for i, item in enumerate(menu.items):
        x = 710 + step * i
        if menu.active.get(page) == item:
            out.append(f'<text x="{x}" y="48" font-size="15" font-weight="700" fill="{THEME["nav_active"]}">{item}</text>')
        else:
            out.append(f'<text x="{x}" y="48" font-size="15" font-weight="600" fill="{THEME["nav_text"]}">{item}</text>')
    return out


def _tw(s: str, size: float) -> float:
    return sum(size if ord(c) > 0x2E80 else size * (0.3 if c == " " else 0.55) for c in str(s))


def render_tabbar(menu: Menu, page: str) -> list[str]:
    """手機版（mockup layout: mobile）頁首下方的橫向頁籤列；超出畫面寬度的項目被裁切，如同可左右滑動。"""
    out, x = [], 16.0
    for item in menu.items:
        w = _tw(item, 14) + 28
        if menu.active.get(page) == item:
            out.append(f'<rect x="{x:g}" y="66" width="{w:g}" height="32" rx="16" fill="{THEME["primary"]}"/>')
            out.append(f'<text x="{x + 14:g}" y="87" font-size="14" font-weight="700" fill="#fff">{item}</text>')
        else:
            out.append(f'<rect x="{x:g}" y="66" width="{w:g}" height="32" rx="16" fill="#ffffff" stroke="#dfe6e0"/>')
            out.append(f'<text x="{x + 14:g}" y="87" font-size="14" font-weight="600" fill="{THEME["nav_text"]}">{item}</text>')
        x += w + 8
    return out


STYLES = {
    "sidebar": {
        "render": render_sidebar,
        # 舊版（未包 <g>）：從第一個選單項目到「目前身分」框之前
        "legacy": re.compile(r'(?:<rect x="13" [^>]*/>\s*)?<text x="29" y="155".*?(?=\s*<rect x="18" y="938")', re.S),
        "allowed": re.compile(r'^<(?:text x="29"|rect x="13")'),
    },
    "topbar": {
        "render": render_topbar,
        # 舊版：從第一個導覽文字到右側 CTA 按鈕之前
        "legacy": re.compile(r'<text x="710" y="48".*?(?=\s*<rect x="1210" y="20")', re.S),
        "allowed": re.compile(r'^<text x="\d+" y="48"'),
    },
    "tabbar": {
        "render": render_tabbar,
        "legacy": re.compile(r"(?!x)x"),   # 新樣式，沒有舊版
        "allowed": re.compile(r"(?!x)x"),
    },
}


def locate(svg: str, menu: Menu) -> tuple[int, int] | None:
    m = re.search(rf'<g data-nav="{menu.key}">.*?</g>', svg, re.S)
    if m:
        return m.span()
    style = STYLES[menu.style]
    m = style["legacy"].search(svg)
    if not m:
        return None
    if not all(style["allowed"].match(e) for e in ELEMENT.findall(m.group(0))):
        return None
    return m.span()


def build(menu: Menu, page: str) -> str:
    lines = STYLES[menu.style]["render"](menu, page)
    return f'<g data-nav="{menu.key}">\n' + "\n".join(lines) + "\n</g>"


def validate(menu: Menu) -> list[str]:
    errors = []
    if menu.style not in STYLES:
        errors.append(f"{menu.title}: 未知樣式 {menu.style!r}（可用：{', '.join(STYLES)}）")
    for pid in menu.active:
        if pid not in menu.pages:
            errors.append(f"{menu.title}: 反白頁面 {pid} 不在套用頁面內")
    if menu.style in ("sidebar", "tabbar"):
        missing = [p for p in menu.pages if p not in menu.active]
        if missing:
            errors.append(f"{menu.title}: 以下頁面沒有指定反白項目：{' '.join(missing)}")
    return errors


def run(keys: list[str], write: bool) -> tuple[list[str], list[str], list[str]]:
    """回傳 (錯誤或差異訊息, 已變更的頁面 ID, 已同步畫面文字的頁面 ID)。"""
    menus = sitemap_menus()
    if keys:
        unknown = set(keys) - {m.key for m in menus}
        if unknown:
            return [f"找不到選單：{', '.join(sorted(unknown))}"], []
        menus = [m for m in menus if m.key in keys]
    files = screen_files()
    problems, changed, resync = [], [], []
    for menu in menus:
        errs = validate(menu)
        problems += errs
        if menu.style not in STYLES or (errs and write):
            continue  # 表格有誤時不寫檔；檢查模式仍逐頁比對
        for page in menu.pages:
            path = files.get(page)
            if not path:
                problems.append(f"{menu.title}: 找不到 {page} 的 SVG")
                continue
            svg = read(path)
            span = locate(svg, menu)
            if not span:
                problems.append(f"{menu.title}: {page} 找不到可辨識的選單區塊（樣式不同？需手動處理）")
                continue
            old_block = svg[span[0]:span[1]]
            new_block = build(menu, page)
            if old_block == new_block:
                continue
            if not write:
                if elements(old_block) != elements(new_block):
                    problems.append(f"{menu.title}: {page} 選單與表格不一致（執行 nav.py {menu.key} 更新）")
            else:
                before = svg_texts(path)
                path.write_text(svg[:span[0]] + new_block + svg[span[1]:], encoding="utf-8")
                changed.append(page)
                if svg_texts(path) != before:
                    resync.append(page)
    if write and resync:
        from sync_screen_text import update_page
        doc = read(SPEC)
        for page in resync:
            doc = update_page(doc, page)
        SPEC.write_text(doc, encoding="utf-8")
    return problems, changed, resync


def main() -> int:
    args = sys.argv[1:]
    check = "--check" in args
    keys = [a for a in args if not a.startswith("--")]
    try:
        problems, changed, resync = run(keys, write=not check)
    except ValueError as error:
        print(f"錯誤：{error}", file=sys.stderr)
        return 1
    if check:
        for p in problems:
            print(p)
        print("選單一致" if not problems else f"共 {len(problems)} 項不一致")
        return 1 if problems else 0
    for p in problems:
        print("略過：" + p)
    print(f"已更新 {len(changed)} 張 SVG：{' '.join(changed) or '無'}")
    if resync:
        print(f"已同步規格畫面文字：{' '.join(resync)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
