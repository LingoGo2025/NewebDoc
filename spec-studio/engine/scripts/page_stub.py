#!/usr/bin/env python3
"""新增頁面的規格段落骨架（錨點、標題、基本欄位、開發說明、SA 規格空白骨架、畫面文字標題）。

用法：
  python3 scripts/page_stub.py <頁面ID> <頁面名稱> [--desc "<一句說明>"] [--region "<區域名稱>"] [--dry-run]

依頁面 ID 順序插入規格：放在第一個 ID 比它大的頁面段落之前；沒有時放在最後一個頁面段落之後；
規格還沒有任何頁面時，放在「## 跨頁流程」（或「## 流程頁面順序」「## 更新紀錄」）之前。
已有同 ID 段落時不動。SVG 另以 mockup.py 產生，之後執行 sync_screen_text.py 同步畫面文字。
"""
from __future__ import annotations

import argparse
import sys

from _common import PAGE_RE, SPEC, TEXT_MARKER, expected_region, read, spec_sections

SA_HEADINGS = ["摘要｜頁面目的與入口", "摘要｜關鍵規則", "摘要｜已定案", "摘要｜本頁待確認", "明細｜基本資訊", "明細｜欄位規格",
               "明細｜按鈕與導向", "明細｜畫面狀態", "明細｜本頁錯誤文案", "明細｜資料寫入", "明細｜驗收條件"]


def stub(pid: str, name: str, desc: str, region: str, mobile: str = "") -> list[str]:
    """mobile：手機版示意圖那一行的內容（`screens/mobile/…svg` 或「無相關設計（原因）」）；空白時寫「待補」。"""
    return [f'<a id="{pid.lower()}"></a>', f"### {pid}｜{name}", "",
            f"- 區域：{region}", f"- 目前說明：{desc}", f"- SVG 畫面原稿：`screens/{pid}_{name}.svg`",
            f"- 手機版示意圖：{mobile or '待補（畫手機版，或寫「無相關設計（原因）」）'}",
            "- 開發說明（AI 補充）：", f"  - 【頁面目的】{desc}", "- 開發說明（設計者補充）：", "",
            "**SA 規格（待補）**", "",
            "> 待補：功能確認後再補內容。「摘要」給人審閱，「明細」給開發使用；通用規則見[全站共用規則](#common-rules)。", "",
            *[f"#### {h}" for h in SA_HEADINGS], "", TEXT_MARKER, "", "- （執行 sync_screen_text.py 後產生）", ""]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pid"); ap.add_argument("name")
    ap.add_argument("--desc", default="〔待補一句說明〕"); ap.add_argument("--region", default="")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if not PAGE_RE.match(a.pid):
        print(f"錯誤｜{a.pid} 不符合頁面 ID 規則（project.json › ids）")
        return 1
    sections = spec_sections()
    if any(s.key == a.pid for s in sections):
        print(f"略過｜規格已有 {a.pid} 段落")
        return 0
    lines = read(SPEC).split("\n")
    pages = [s for s in sections if PAGE_RE.match(s.key)]
    after = [s for s in pages if s.key > a.pid]
    if after:
        at = after[0].start - 1
    elif pages:
        at = pages[-1].end
    else:
        at = next((i for key in ("## 跨頁流程", "## 流程頁面順序", "## 更新紀錄")
                   for i, ln in enumerate(lines) if ln.strip() == key), len(lines))
    block = stub(a.pid, a.name, a.desc, a.region or expected_region(a.pid))
    if a.dry_run:
        print("\n".join(block))
        return 0
    SPEC.write_text("\n".join(lines[:at] + block + lines[at:]), encoding="utf-8")
    print(f"已新增｜規格 {a.pid}｜{a.name}（第 {at + 1} 行）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
