#!/usr/bin/env python3
"""視覺自檢：把頁面 SVG 拼成縮圖總覽（PNG），並列出畫面文字的常見問題。

用法：
  python3 scripts/preview.py                 # 全部頁面，每張總覽 12 頁，輸出到系統暫存資料夾
  python3 scripts/preview.py A03 A04 B01     # 只看指定頁面
  python3 scripts/preview.py --big A03       # 單頁大圖（寬 1200）
  python3 scripts/preview.py --out <資料夾>   # 指定輸出位置（不要放在專案裡）
  python3 scripts/preview.py --lint          # 只做文字檢查，不產生圖

需要 rsvg-convert（macOS：brew install librsvg）。沒有時改產生 HTML 總覽，用瀏覽器打開檢視。
預覽圖只放暫存資料夾，不放進專案（規範：不產生 PNG 放進專案）。

文字檢查（不需要 rsvg-convert）：
  - 佔位文字：示意編號、示意資料、服務一、選項一、範例、Lorem…
  - 「待確認」出現在畫面上（AI 起稿註記與費率欄除外）
  - 文字被截斷（…）的數量
  - 同一頁同一段文字重複出現 4 次以上（常見於表格整列相同）
"""
from __future__ import annotations

import base64
import html
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

from _common import CONFIG, SCREENS

PER_SHEET = 12
COLS = 3
THUMB_W = 520
PLACEHOLDER = re.compile(r"示意(?!：)|服務[一二三]|選項[一二三]|範例資料|Lorem|XXX|○○")


def texts(svg: str) -> list[str]:
    return [html.unescape(t) for t in re.findall(r"<text[^>]*>([^<]*)</text>", svg)]


def lint(path: Path) -> list[str]:
    svg = path.read_text(encoding="utf-8")
    ts = [t for t in texts(svg) if not t.startswith("AI 起稿示意")]
    out = []
    ph = [t for t in ts if PLACEHOLDER.search(t)]
    if ph:
        out.append("佔位文字：" + "、".join(dict.fromkeys(ph[:4])))
    pend = [t for t in ts if "待確認" in t]
    if pend:
        out.append("畫面上有「待確認」：" + "、".join(dict.fromkeys(pend[:3])))
    cut = [t for t in ts if t.endswith("…")]
    if len(cut) >= 2:
        out.append(f"{len(cut)} 處文字被截斷，例如「{cut[0]}」")
    rep = [t for t, n in Counter(x for x in ts if len(x) >= 6).items() if n >= 4]
    if rep:
        out.append("同一段文字重複 4 次以上（表格是否整列相同？）：" + "、".join(rep[:3]))
    return out


def size(svg: str) -> tuple[float, float]:
    m = re.search(r'<svg[^>]*width="([\d.]+)"[^>]*height="([\d.]+)"', svg)
    return (float(m.group(1)), float(m.group(2))) if m else (1440.0, 1000.0)


def sheet_svg(paths: list[Path]) -> str:
    """把多張 SVG 以 <image> 嵌入拼成一張；每格上方標頁面 ID 與名稱。"""
    gap, label = 24, 30
    cells = []
    for p in paths:
        svg = p.read_text(encoding="utf-8")
        w, h = size(svg)
        tw = THUMB_W if w > 600 else THUMB_W * .5   # 手機版（390 寬）縮成半欄寬，比例接近實際
        cells.append((p, svg, tw, h * tw / w))
    rows = [cells[i:i + COLS] for i in range(0, len(cells), COLS)]
    out, y = [], gap
    for row in rows:
        rh = max(c[3] for c in row)
        for k, (p, svg, tw, th) in enumerate(row):
            x = gap + k * (THUMB_W + gap)
            data = base64.b64encode(svg.encode("utf-8")).decode()
            out.append(f'<text x="{x}" y="{y + 20}" font-size="16" font-weight="700" fill="#203f3c">{html.escape(p.stem.replace("_", " ", 1))}</text>')
            out.append(f'<rect x="{x - 1}" y="{y + label - 1}" width="{tw + 2:g}" height="{th + 2:g}" fill="none" stroke="#c9d3cc"/>')
            out.append(f'<image x="{x}" y="{y + label}" width="{tw:g}" height="{th:g}" href="data:image/svg+xml;base64,{data}"/>')
        y += label + rh + gap
    W = gap + COLS * (THUMB_W + gap)
    font = '"PingFang TC","Noto Sans TC","Microsoft JhengHei",sans-serif'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{y:g}" viewBox="0 0 {W} {y:g}">'
            f'<style>text{{font-family:{font}}}</style><rect width="100%" height="100%" fill="#eef1ed"/>' + "".join(out) + "</svg>")


def main() -> int:
    args = sys.argv[1:]
    out_dir = Path(args[args.index("--out") + 1]) if "--out" in args else Path(tempfile.gettempdir()) / f"spec-preview-{CONFIG.get('name', 'project')}"
    ids = [a for a in args if re.fullmatch(r"[A-Z]+\d+", a)]
    files = sorted(SCREENS.glob("*.svg"))
    if ids:
        files = [f for f in files if f.name.split("_")[0] in ids]
    if not files:
        print("找不到頁面 SVG")
        return 1
    problems = {f.stem: lint(f) for f in files}
    bad = {k: v for k, v in problems.items() if v}
    print(f"文字檢查｜{len(files)} 頁，{len(bad)} 頁有問題")
    for k, v in bad.items():
        for x in v:
            print(f"  - {k}：{x}")
    if "--lint" in args:
        return 0
    out_dir.mkdir(parents=True, exist_ok=True)
    rsvg = shutil.which("rsvg-convert")
    made = []
    if "--big" in args:
        for f in files:
            target = out_dir / f"{f.stem}.png"
            if rsvg:
                subprocess.run([rsvg, "-w", "1200" if size(f.read_text(encoding="utf-8"))[0] > 600 else "600", str(f), "-o", str(target)], check=True)
                made.append(target)
    else:
        for n in range(0, len(files), PER_SHEET):
            chunk = files[n:n + PER_SHEET]
            src = out_dir / f"總覽_{n // PER_SHEET + 1:02d}.svg"
            src.write_text(sheet_svg(chunk), encoding="utf-8")
            if rsvg:
                target = src.with_suffix(".png")
                subprocess.run([rsvg, str(src), "-o", str(target)], check=True)
                made.append(target)
    if not rsvg:
        page = out_dir / "總覽.html"
        imgs = "".join(f'<figure><figcaption>{html.escape(f.stem)}</figcaption><img src="{f.resolve().as_uri()}"></figure>' for f in files)
        page.write_text("<!doctype html><meta charset=utf-8><style>body{font-family:sans-serif;background:#eef1ed}"
                        "figure{display:inline-block;width:31%;margin:1%;vertical-align:top}img{width:100%;border:1px solid #ccc}"
                        f"</style>{imgs}", encoding="utf-8")
        print(f"找不到 rsvg-convert，改產生 HTML 總覽（用瀏覽器打開）：{page}")
        return 0
    print("縮圖｜" + "\n縮圖｜".join(str(m) for m in made))
    print("逐張看過：每頁一眼看得出是什麼產品與在做什麼、沒有佔位圖或假資料、按鈕與流程一致、文字沒被截斷；"
          "有問題就改起稿描述後執行 draft_apply.py <描述> --screens <ID>（未手動調整的初稿），或局部修改 SVG。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
