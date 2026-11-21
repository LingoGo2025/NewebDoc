#!/usr/bin/env python3
"""查詢一個頁面 ID 或關鍵字會牽動哪些頁面、流程、網站地圖節點、選單與系統架構模組。

用法：
  python3 scripts/impact.py A05              # 頁面 ID
  python3 scripts/impact.py 通知 匯出             # 關鍵字（多個時分別列出）
  python3 scripts/impact.py B12 --lines      # 關鍵字命中時附上規格原文行

輸出只列位置與摘要，修改前再用 section.py 讀需要的段落。
"""
from __future__ import annotations

import re
import sys

from _common import (FUNCTIONAL_FIGURE, FLOWS, ID_RE, architecture_spec, INDEX, SITEMAP, flow_list, index_refs, read,
                     screen_files, sitemap_buttons, sitemap_menus, spec_sections, svg_texts)


def fmt_ids(ids) -> str:
    return " ".join(sorted(set(ids))) or "—"


def by_id(pid: str, ctx: dict) -> set[str]:
    related: set[str] = set()
    sec = ctx["sections"].get(pid)
    print(f"■ {pid}" + (f"｜{sec.heading.split('｜', 1)[-1]}" if sec else "（規格中無此頁）"))
    if sec:
        print(f"  規格：L{sec.start}–{sec.end}（section.py {pid}）")
    for region, items in ctx["buttons"].items():
        for bid, node, line in items:
            if bid == pid:
                print(f"  網站地圖：{region} › {node}（{SITEMAP.name} L{line}）")
    for m in ctx["menus"]:
        if pid in m.pages:
            print(f"  共用選單：{m.title} › 反白「{m.active.get(pid, '無')}」（改選單會一起改 {len(m.pages)} 頁）")
    arch = ctx["arch"]
    mods = [name for name, ids in arch.modules if pid in ids]
    if mods:
        print(f"  系統架構：業務模組 {'、'.join(mods)}（頁面增刪或改歸屬時，同步規格「系統架構」章與 architecture/{FUNCTIONAL_FIGURE}.puml）")
    elif pid in arch.excluded:
        print("  系統架構：暫不歸入模組")
    elif sec:
        print("  系統架構：✗ 未歸入任何業務模組（須補進規格「系統架構 › 業務模組」與功能架構圖）")
    flows = [f for f in ctx["flows"] if pid in f["pages"]]
    for f in flows:
        others = [p for p in f["pages"] if p != pid]
        related |= set(others)
        print(f"  流程：{f['title']}（flow-{f['key']}）→ 同流程頁面 {fmt_ids(others)}")
    ref = next((r for r in ctx["refs"] if r.get("screen-id") == pid), None)
    if ref:
        similar = [x for x in ref.get("similar", "").split(",") if x]
        manage = [x for x in ref.get("manage", "").split(",") if x]
        back = {r["screen-id"] for r in ctx["refs"]
                if pid in r.get("similar", "").split(",") + r.get("manage", "").split(",")} - {pid}
        related |= set(similar) | set(manage) | back
        print(f"  index 相關頁面：類似 {fmt_ids(similar)}｜管理頁 {fmt_ids(manage)}｜被引用 {fmt_ids(back)}")
    mentions = sorted({s.key for s in ctx["sections"].values()
                       if s.key != pid and re.search(rf"\b{pid}\b", s.body) and ID_RE.match(s.key)})
    if mentions:
        related |= set(mentions)
        print(f"  其他頁面說明提到 {pid}：{fmt_ids(mentions)}")
    return related


def by_keyword(word: str, ctx: dict, show_lines: bool) -> set[str]:
    related: set[str] = set()
    print(f"■ 「{word}」")
    screens = {pid: sum(word in t for t in texts) for pid, texts in ctx["texts"].items()}
    hits = {pid: n for pid, n in screens.items() if n}
    if hits:
        related |= set(hits)
        print(f"  SVG 畫面文字（{len(hits)} 頁）：" + " ".join(f"{p}×{n}" for p, n in sorted(hits.items())))
    spec_hits = []
    for s in ctx["sections"].values():
        lines = [ln for ln in s.body.split("\n") if word in ln]
        if lines:
            spec_hits.append((s, lines))
    if spec_hits:
        print(f"  規格說明（不含畫面文字清單，{len(spec_hits)} 段）：" + " ".join(s.key for s, _ in spec_hits))
        related |= {s.key for s, _ in spec_hits if ID_RE.match(s.key)}
        if show_lines:
            for s, lines in spec_hits:
                for ln in lines[:3]:
                    print(f"    {s.key}: {ln.strip()[:90]}")
    for f in ctx["flows"]:
        if word in f["source"]:
            related |= set(f["pages"])
            print(f"  流程：{f['title']}（flow-{f['key']}）頁面 {fmt_ids(f['pages'])}")
    node = None
    map_lines = []
    for n, line in enumerate(ctx["sitemap"].split("\n"), 1):
        if line.startswith("#"):
            node = line.lstrip("#").strip()
        elif word in line and not line.startswith("- 20"):
            map_lines.append(f"L{n}（{node}）")
    if map_lines:
        print(f"  {SITEMAP.name}：" + "、".join(map_lines[:12]) + ("…" if len(map_lines) > 12 else ""))
    for m in ctx["menus"]:
        if word in m.items:
            print(f"  共用選單：{m.title} 有此項目（{len(m.pages)} 頁）")
    idx = sorted({r["screen-id"] for r in ctx["refs"]
                  if word in r.get("title", "") + r.get("description", "")})
    nodes = re.findall(r'<div class="mapnode"><strong>([^<]*' + re.escape(word) + r'[^<]*)</strong>', ctx["index"])
    if idx or nodes:
        print(f"  index.html：卡片標題／說明 {fmt_ids(idx)}" + (f"｜地圖節點 {'、'.join(nodes)}" if nodes else ""))
    return related


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 2
    show_lines = "--lines" in args
    terms = [a for a in args if not a.startswith("--")]
    ctx = {
        "sections": {s.key: s for s in spec_sections()},
        "buttons": sitemap_buttons(),
        "menus": sitemap_menus(),
        "flows": flow_list(),
        "arch": architecture_spec(),
        "refs": [r for r in index_refs() if r["class"] == "screen-ref"],
        "texts": {pid: svg_texts(p) for pid, p in screen_files().items()},
        "sitemap": read(SITEMAP),
        "index": read(INDEX),
    }
    related: set[str] = set()
    for term in terms:
        if ID_RE.match(term.upper()):
            related |= by_id(term.upper(), ctx)
        else:
            related |= by_keyword(term, ctx, show_lines)
        print()
    related -= {t.upper() for t in terms}
    if related:
        print(f"建議一併確認：{fmt_ids(related)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
