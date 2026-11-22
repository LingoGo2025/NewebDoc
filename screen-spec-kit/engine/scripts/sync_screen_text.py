#!/usr/bin/env python3
"""Sync selected SVG text nodes into their Markdown page specs."""
from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from _common import ROOT, SPEC as SPECS, TEXT_MARKER as MARKER


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def screen_svg(page_id: str) -> Path:
    matches = list((ROOT / "screens").glob(f"{page_id}_*.svg"))
    if len(matches) != 1:
        raise ValueError(f"{page_id}: 預期一個 SVG，找到 {len(matches)} 個")
    return matches[0]


def svg_text(path: Path) -> list[str]:
    tree = ET.parse(path)
    values = []
    for node in tree.iter():
        if local_name(node.tag) != "text":
            continue
        value = "".join(node.itertext()).strip()
        if value:
            values.append(value)
    if not values:
        raise ValueError(f"{path.name}: 找不到可同步的 SVG <text> 節點")
    return values


def update_page(document: str, page_id: str) -> str:
    heading = re.search(rf"^### {re.escape(page_id)}｜[^\n]*$", document, re.M)
    if not heading:
        raise ValueError(f"規格中找不到頁面標題：{page_id}")
    start = document.find(MARKER, heading.end())
    if start < 0:
        raise ValueError(f"{page_id}: 找不到畫面文字清單標記")
    list_start = start + len(MARKER)
    boundaries = [pos for token in ("\n\n<a id=", "\n\n## ")
                  if (pos := document.find(token, list_start)) >= 0]
    end = min(boundaries) if boundaries else len(document)
    items = svg_text(screen_svg(page_id))
    replacement = "\n\n" + "\n".join(f"- {item}" for item in items)
    return document[:list_start] + replacement + document[end:]


def main() -> int:
    if len(sys.argv) < 2:
        print("用法：python3 scripts/sync_screen_text.py A01 [A16 ...]", file=sys.stderr)
        return 2
    page_ids = list(dict.fromkeys(arg.upper() for arg in sys.argv[1:]))
    document = SPECS.read_text(encoding="utf-8")
    for page_id in page_ids:
        document = update_page(document, page_id)
    SPECS.write_text(document, encoding="utf-8")
    print("已同步：" + ", ".join(page_ids))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ET.ParseError, ValueError) as error:
        print(f"錯誤：{error}", file=sys.stderr)
        raise SystemExit(1)
