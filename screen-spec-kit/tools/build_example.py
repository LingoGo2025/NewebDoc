#!/usr/bin/env python3
"""維護者用：把一個專案打包成「單一 HTML 檔」範例，放進工具組 examples/，供入門頁展示。

用法：
  python3 tools/build_example.py <專案資料夾> <名稱> [縮圖.svg …]
      產生 examples/<名稱>.html，並更新入門頁的範例縮圖；縮圖可指定專案內的 SVG 相對路徑
      （例如 screens/A04_臨停線上繳費.svg flows/monthly_application.svg），沒指定就自動挑

為什麼：GitHub 網頁上傳一次最多 100 個檔案；整個範例專案有 50 多個檔案，打包後只剩 1 個。
做法：
  - assets/svg_sources.js、dev_notes.js、inventory.js 直接內嵌進 index.html（燈箱本來就從 svg_sources 顯示 SVG）
  - 架構圖縮圖 <img> 改成內嵌的 data URI
  - 「下載 SVG」改從內嵌的 SVG 內容產生檔案（不需要另外的 SVG 檔）
  - 入門頁 index.html 的「成果長這樣」三張縮圖改為內嵌圖片（<!-- [gallery:begin] -->～<!-- [gallery:end] --> 之間）
範例只給人看，不會被安裝腳本下載（update_kit.py 略過 examples/）。
"""
from __future__ import annotations

import base64
import html
import json
import re
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
GALLERY = [("screens", "每頁示意圖（附 SA 規格）"), ("flows", "跨頁流程圖"), ("architecture", "系統架構圖")]

DOWNLOAD_PATCH = """<script>
// 單檔範例：「下載 SVG」從內嵌的 SVG 內容產生檔案（沒有另外的 SVG 檔）
document.addEventListener('click', function (e) {
  var a = e.target.closest && e.target.closest('a[download]');
  if (!a) return;
  var key = a.getAttribute('href') || '';
  try { key = decodeURIComponent(key); } catch (err) {}
  var src = (window.SVG_SOURCES || {})[key];
  if (!src) return;
  e.preventDefault();
  var url = URL.createObjectURL(new Blob([src], { type: 'image/svg+xml' }));
  var tmp = document.createElement('a');
  tmp.href = url; tmp.download = key.split('/').pop();
  document.body.appendChild(tmp); tmp.click(); tmp.remove();
  setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
}, true);
</script>
"""


def data_uri(svg: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")


def build(project: Path, name: str) -> dict[str, str]:
    page = (project / "index.html").read_text(encoding="utf-8")

    def inline(m: re.Match) -> str:
        js = (project / m.group(1)).read_text(encoding="utf-8").replace("</script", "<\\/script")
        return f"<script>\n{js}\n</script>"

    page = re.sub(r'<script src="(assets/[^"]+\.js)"></script>', inline, page)
    left = re.findall(r'<script src="([^"]+)"', page)
    if left:
        raise SystemExit(f"錯誤｜還有外部腳本沒內嵌：{left}")

    def img(m: re.Match) -> str:
        path = project / html.unescape(m.group(1))
        return f'src="{data_uri(path.read_text(encoding="utf-8"))}"' if path.exists() else m.group(0)

    page = re.sub(r'src="((?:architecture|screens|flows)/[^"]+\.svg)"', img, page)
    page = page.replace("</body>", DOWNLOAD_PATCH + "</body>", 1)
    out = KIT / "examples" / f"{name}.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(page, encoding="utf-8")
    print(f"已產生｜{out.relative_to(KIT)}（{out.stat().st_size // 1024} KB）")
    # 入門頁縮圖：各取一張（頁面示意圖取第一個 form 類頁面以外的第一張也可；這裡取規格中最具代表性的第一張）
    picks = {}
    for folder, _ in GALLERY:
        files = sorted((project / folder).glob("*.svg"))
        prefer = {"screens": [f for f in files if "首頁" not in f.stem and "登入" not in f.stem],
                  "flows": [f for f in files if not f.stem.startswith("api_")],
                  "architecture": [f for f in files if f.stem == "functional_architecture"]}.get(folder) or files
        if prefer:
            picks[folder] = prefer[0]
    return picks


def update_landing(name: str, title: str, picks: dict[str, Path]) -> None:
    landing = KIT / "index.html"
    text = landing.read_text(encoding="utf-8")
    figs = []
    for folder, caption in GALLERY:
        p = picks.get(folder)
        if not p:
            continue
        figs.append(f'    <figure>\n      <a href="examples/{name}.html"><img src="{data_uri(p.read_text(encoding="utf-8"))}" '
                    f'alt="範例{caption}：{html.escape(p.stem)}" loading="lazy"></a>\n      <figcaption>{caption}</figcaption>\n    </figure>')
    block = "<!-- [gallery:begin] -->\n  <div class=\"gallery\">\n" + "\n".join(figs) + "\n  </div>\n  <!-- [gallery:end] -->"
    if "<!-- [gallery:begin] -->" not in text:
        raise SystemExit("錯誤｜入門頁 index.html 找不到 <!-- [gallery:begin] --> 標記")
    text = re.sub(r"<!-- \[gallery:begin\] -->.*?<!-- \[gallery:end\] -->", lambda m: block, text, flags=re.S)
    text = re.sub(r'href="examples/[^"]+\.html"', f'href="examples/{name}.html"', text)
    landing.write_text(text, encoding="utf-8")
    print(f"已更新｜入門頁範例縮圖（{title}）")


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 2:
        print(__doc__)
        return 2
    project, name = Path(args[0]).resolve(), args[1]
    if not (project / "index.html").exists():
        print(f"錯誤｜{project} 不是畫面規格專案（找不到 index.html）")
        return 1
    title = json.loads((project / "project.json").read_text(encoding="utf-8")).get("name", name)
    picks = build(project, name)
    for extra in args[2:]:   # 指定的縮圖
        path = project / extra
        if not path.exists():
            print(f"錯誤｜找不到縮圖 {extra}")
            return 1
        picks[Path(extra).parts[0]] = path
    update_landing(name, title, picks)
    return 0


if __name__ == "__main__":
    sys.exit(main())
