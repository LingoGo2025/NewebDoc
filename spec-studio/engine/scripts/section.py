#!/usr/bin/env python3
"""只印出規格中指定頁面／流程的段落，預設略過自動產生的畫面文字清單。

用法：
  python3 scripts/section.py A05 B12            # 頁面說明
  python3 scripts/section.py flow-donation_gift_redemption API01
  python3 scripts/section.py A05 --text         # 連同畫面文字清單
  python3 scripts/section.py 待確認              # 以「## 」章節標題關鍵字取整章
  python3 scripts/section.py --list             # 列出所有段落 key 與行號
"""
from __future__ import annotations

import sys

from _common import SPEC, read, spec_sections


def chapter(keyword: str) -> str:
    """以「## 」章節標題關鍵字取整章，例如：待確認、更新紀錄、規格範圍。"""
    lines = read(SPEC).split("\n")
    for i, line in enumerate(lines):
        if line.startswith("## ") and keyword in line:
            end = next((j for j in range(i + 1, len(lines)) if lines[j].startswith("## ")), len(lines))
            return f"<!-- {SPEC.name} L{i + 1}–{end} -->\n" + "\n".join(lines[i:end]).strip() + "\n"
    return ""


def main() -> int:
    args = sys.argv[1:]
    sections = spec_sections()
    if not args or "--list" in args:
        for s in sections:
            print(f"{s.key:<38} L{s.start:<5} {s.heading}")
        return 0
    with_text = "--text" in args
    wanted = [a for a in args if not a.startswith("--")]
    lookup = {}
    for s in sections:
        lookup[s.key.upper()] = s
        lookup[s.anchor.upper()] = s
        if s.anchor.startswith("flow-"):
            lookup[s.anchor[5:].upper()] = s
    missing = 0
    for key in wanted:
        s = lookup.get(key.upper())
        if not s and chapter(key):
            print(chapter(key))
            continue
        if not s:
            print(f"（找不到 {key}；可用 --list 查看）\n")
            missing += 1
            continue
        print(f"<!-- {SPEC.name} L{s.start}–{s.end} -->")
        print(s.body)
        if s.text_list:
            if with_text:
                print("\n**畫面文字（依 SVG 順序）**\n")
                print("\n".join(f"- {t}" for t in s.text_list))
            else:
                print(f"\n（畫面文字 {len(s.text_list)} 行已略過；加 --text 顯示）")
        print()
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
