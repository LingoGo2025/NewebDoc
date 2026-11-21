#!/usr/bin/env python3
"""把 screens/*.svg、flows/*.svg 與 architecture/*.svg 原始碼打包成 assets/svg_sources.js。

index.html 以 <script src> 載入這份檔案，燈箱就能把 SVG 內嵌進頁面、選取與複製文字；
直接雙擊開檔（file://）時瀏覽器會擋 fetch，但不會擋 <script src>。

用法：
  python3 scripts/svg_bundle.py          # 重新產生 assets/svg_sources.js
  python3 scripts/svg_bundle.py --check  # 只檢查是否過期（check.py 也會呼叫）

任何頁面、流程或架構圖 SVG 有改動（含 plantuml 重新渲染、nav.py 更新選單）後都要重跑。
"""
from __future__ import annotations

import json
import sys

from _common import ARCH, FLOWS, ROOT

SCREENS = ROOT / "screens"
OUTPUT = ROOT / "assets" / "svg_sources.js"
HEADER = "// 由 scripts/svg_bundle.py 產生，請勿手動編輯；SVG 改動後重新執行。\n"


def build() -> str:
    files = sorted(SCREENS.glob("*.svg")) + sorted(FLOWS.glob("*.svg")) + sorted(ARCH.glob("*.svg"))
    data = {p.relative_to(ROOT).as_posix(): p.read_text(encoding="utf-8") for p in files}
    body = json.dumps(data, ensure_ascii=False, indent=0, separators=(",", ":"))
    # 避免 SVG 內容裡的 </script> 之類字串影響載入
    body = body.replace("</", "<\\/")
    return HEADER + "window.SVG_SOURCES=" + body + ";\n"


def is_stale() -> bool:
    return not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != build()


def main() -> int:
    if "--check" in sys.argv:
        if is_stale():
            print("✗ assets/svg_sources.js 已過期，請執行 python3 scripts/svg_bundle.py")
            return 1
        print("OK｜assets/svg_sources.js 與 SVG 一致")
        return 0
    content = build()
    OUTPUT.write_text(content, encoding="utf-8")
    print(f"已更新 {OUTPUT.relative_to(ROOT)}（{len(content.encode('utf-8')) // 1024} KB）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
