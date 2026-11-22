#!/usr/bin/env python3
"""補 SA 規格的素材：一次列出某頁寫 SA 需要的所有資料（唯讀，不改檔）。

用法：
  python3 scripts/sa_context.py <頁面ID>        # 例：B05
  python3 scripts/sa_context.py <頁面ID> <頁面ID> …

列出：頁面說明與所屬模組、畫面文字（依 SVG 順序）、示意圖區塊（欄位、表格欄位、按鈕；限 mockup.py 產生的 SVG）、
相關流程（位置、上一步與下一步、與本頁有關的步驟與分支）、網站地圖關聯（類似、管理、被哪些頁管理）、
本頁待確認、全站共用規則編號。寫法見 規範/spec-writing.md「依示意圖與流程補 SA」。
"""
from __future__ import annotations

import html
import re
import sys

from _common import (PAGE_RE, SCREENS, SPEC, architecture_spec, flow_list, read, sitemap_tree, spec_sections)


def svg_blocks(pid: str) -> list[tuple[str, list[str]]]:
    files = sorted(SCREENS.glob(f"{pid}_*.svg"))
    if not files:
        return []
    src = read(files[0])
    out = []
    for m in re.finditer(r'<g data-block="(\w+)">(.*?)</g>', src, re.S):
        texts = [html.unescape(t) for t in re.findall(r"<text[^>]*>([^<]*)</text>", m.group(2))]
        texts = [t for t in texts if t.strip() and t not in ("*", "▾", "⇪", "‹", "›")]
        if texts:
            out.append((m.group(1), texts))
    return out


def flow_info(pid: str) -> list[str]:
    lines = []
    for f in flow_list():
        if pid not in f["pages"]:
            continue
        order = f["order"] or [[p] for p in f["pages"]]
        pos = next((i for i, step in enumerate(order) if pid in step), None)
        prev = "、".join(order[pos - 1]) if pos else "（起點）"
        nxt = "、".join(order[pos + 1]) if pos is not None and pos + 1 < len(order) else "（終點）"
        lines.append(f"### 流程「{f['title']}」（{f['key']}）")
        lines.append(f"- 摘要：{f['summary']}")
        if pos is not None:
            lines.append(f"- 位置：第 {pos + 1}/{len(order)} 步；上一步 {prev}；下一步 {nxt}")
        alias = dict(re.findall(r'^(?:actor|participant|database|queue|collections) "([^"]+)" as (\w+)', f["source"], re.M))
        name = {v: k for k, v in alias.items()}
        mine = {a for lab, a in alias.items() if pid in lab}
        lines.append("- 步驟（標 ★ 為與本頁有關）：")
        depth = 0
        for raw in f["source"].split("\n"):
            s = raw.strip()
            if re.match(r"^(alt|opt|loop|group)\b", s):
                lines.append(f"  {'  ' * depth}【{s}】"); depth += 1; continue
            if s.startswith("else"):
                lines.append(f"  {'  ' * max(0, depth - 1)}【{s}】"); continue
            if s == "end":
                depth = max(0, depth - 1); continue
            m = re.match(r"^(\w+)\s*(-+(?:\[[^\]]*\])?-*>+)\s*(\w+)\s*:\s*(.*)$", s)
            if m and m.group(1) in name and m.group(3) in name:
                star = "★ " if {m.group(1), m.group(3)} & mine else ""
                arrow = "⇢" if "#7C8F88" in m.group(2) or "--" in m.group(2) else "→"
                lines.append(f"  {'  ' * depth}{star}{name[m.group(1)]} {arrow} {name[m.group(3)]}：{m.group(4)}")
            elif s.lower().startswith("note"):
                txt = s
                for a, n in name.items():
                    txt = re.sub(rf"\b{a}\b", n, txt)
                lines.append(f"  {'  ' * depth}（備註）{txt}")
    return lines


def main() -> int:
    ids = [a.upper() for a in sys.argv[1:]]
    if not ids:
        print(__doc__)
        return 2
    sections = {s.key: s for s in spec_sections()}
    tree = sitemap_tree()
    buttons = {b.id: (r.name, n.title, b) for r in tree for n in r.nodes for b in n.buttons}
    managed_by_me = {}
    for _, _, b in buttons.values():
        for m in b.manage:
            managed_by_me.setdefault(m, []).append(b.id)
    arch = architecture_spec()
    spec_text = read(SPEC)
    common = re.findall(r"^\| ((?:CF|CB|CE|CAC)-\d+) \| ([^|]+) \|", spec_text, re.M)
    for pid in ids:
        if not PAGE_RE.match(pid) or pid not in sections:
            print(f"錯誤｜找不到頁面 {pid}")
            return 1
        sec = sections[pid]
        print(f"# {sec.heading} 的 SA 素材\n")
        body = sec.body
        for key in ("區域", "目前說明", "SVG 畫面原稿", "對應流程"):
            m = re.search(rf"^- {key}：(.*)$", body, re.M)
            if m:
                print(f"- {key}：{m.group(1)}")
        mods = [n for n, ids_ in arch.modules if pid in ids_]
        print(f"- 業務模組：{'、'.join(mods) or '（未歸入）'}")
        sa = re.search(r"\*\*SA 規格(?:（([^）]*)）)?\*\*", body)
        print(f"- SA 狀態：{(sa.group(1) or '已完成') if sa else '（沒有 SA 區塊）'}")
        print("\n## 畫面文字（依 SVG 順序）\n")
        print("、".join(sec.text_list) if sec.text_list else "（沒有畫面文字清單，先執行 sync_screen_text.py）")
        blocks = svg_blocks(pid)
        if blocks:
            print("\n## 示意圖區塊（mockup.py 產生的區塊，依版面由上而下）\n")
            for kind, texts in blocks:
                print(f"- {kind}：{'｜'.join(texts)}")
        print("\n## 相關流程\n")
        print("\n".join(flow_info(pid)) or "（沒有流程包含本頁）")
        print("\n## 網站地圖關聯\n")
        if pid in buttons:
            region, node, b = buttons[pid]
            print(f"- 位置：{region}／{node}")
            print(f"- 說明：{b.desc}")
            print(f"- 類似頁面：{'、'.join(b.similar) or '—'}")
            print(f"- 管理本頁的頁面：{'、'.join(b.manage) or '—'}")
        print(f"- 本頁管理的頁面：{'、'.join(managed_by_me.get(pid, [])) or '—'}")
        pend = re.search(r"#### 摘要｜本頁待確認\n(.*?)(?=\n#### )", body, re.S)
        rows = re.findall(r"^\| (Q\d+) \| ([^|]+) \|", pend.group(1), re.M) if pend else []
        print("\n## 本頁待確認\n")
        print("\n".join(f"- {q}：{t.strip()}" for q, t in rows) or "（無）")
        print("\n## 全站共用規則（只引用編號，不重寫）\n")
        print("、".join(f"{c} {t.strip()[:18]}" for c, t in common) or "（無）")
        print("\n---\n寫法：規範/spec-writing.md「SA 各小節寫法」「依示意圖與流程補 SA」。\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
