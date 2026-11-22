#!/usr/bin/env python3
"""訪談進度：列出新專案各訪談階段（questioning.md 第 3 節）的完成狀態。

用法：
  python3 scripts/interview_status.py

判斷方式：範本在各階段要填的位置放了「〔待訪談第 n 階段…〕」標記；填完（或使用者明確表示略過、寫明「無」）
就把標記換成內容；跨階段標記（如「第 2、8 階段後改寫」）歸給最後一個階段。仍有標記的階段列為未完成，並列出標記所在位置。第 11 階段（逐頁細節）另以各頁 SA 規格狀態計算。
全自動起稿（draft_apply.py）寫入的內容標「〔AI 起稿・第 n 階段：待審閱〕」，該階段列為「待審閱」：內容已有初稿，
等使用者逐項確認後由 AI 刪除標記。既有專案沒有標記時，各階段都會顯示完成。
"""
from __future__ import annotations

import re
import sys

from _common import ARCH, INDEX, PAGE_RE, ROOT, SITEMAP, SPEC, architecture_spec, flow_list, read, spec_sections, sitemap_tree

STAGES = ["專案概要", "使用者與角色", "業務規則與用語限制", "區域", "頁面清單", "業務模組", "跨頁流程",
          "外部系統", "對外 API", "全站共用規則", "逐頁細節", "選填（移轉計畫、相關法規）"]
MARK = re.compile(r"〔待訪談第\s*([0-9、，,\s]+?)\s*階段[^〕]*〕")
REVIEW_MARK = re.compile(r"〔AI 起稿・第\s*([0-9、，,\s]+?)\s*階段[^〕]*〕")


def markers(pattern: "re.Pattern[str]" = MARK) -> dict[int, list[str]]:
    """{階段: [位置]}；預設找「待訪談」標記，pattern=REVIEW_MARK 找「AI 起稿」標記。"""
    found: dict[int, list[str]] = {}
    files = [ROOT / "專案規則.md", SPEC, SITEMAP, ROOT / "project.json", INDEX, *sorted(ARCH.glob("*.puml"))]
    for path in files:
        if not path.exists():
            continue
        for n, line in enumerate(read(path).split("\n"), 1):
            for m in pattern.finditer(line):
                # 跨階段標記（如「第 2、8 階段後改寫」）歸給最後一個階段
                num = max(int(x) for x in re.findall(r"\d+", m.group(1)))
                found.setdefault(num, []).append(f"{path.relative_to(ROOT)}:{n}")
    return found


def review_markers() -> dict[int, list[str]]:
    return markers(REVIEW_MARK)


def main() -> int:
    found = markers()
    review = review_markers()
    sections = spec_sections()
    pages = [s for s in sections if PAGE_RE.match(s.key)]
    sa = {"待補": 0, "試做": 0, "完成": 0}
    for s in pages:
        if "**SA 規格（待補）**" in s.body:
            sa["待補"] += 1
        elif "**SA 規格（試做）**" in s.body:
            sa["試做"] += 1
        elif "**SA 規格**" in s.body:
            sa["完成"] += 1
    arch = architecture_spec()
    tree = sitemap_tree()
    facts = {
        2: f"使用者 {len(arch.tables.get('使用者', {}).get('rows', []))} 種",
        4: f"區域 {len(tree)} 個",
        5: f"頁面 {len(pages)} 頁、節點 {sum(len(r.nodes) for r in tree)} 個",
        6: f"業務模組 {len(arch.modules)} 個",
        7: f"流程 {len(flow_list())} 條",
        8: f"外部系統 {len(arch.tables.get('外部系統', {}).get('rows', []))} 個",
        11: f"SA 規格：完成 {sa['完成']}、試做 {sa['試做']}、待補 {sa['待補']}（共 {len(pages)} 頁）",
    }
    print("| 階段 | 狀態 | 資料 | 尚未填的位置 |")
    print("|---|---|---|---|")
    next_stage = None
    for i, name in enumerate(STAGES, 1):
        locs = found.get(i, [])
        if i == 11:
            done = not locs and pages and sa["待補"] == 0
            status = "完成" if done else ("可逐頁進行" if pages else "未開始")
        else:
            done = not locs
            status = "完成" if done else "未完成"
        if done and review.get(i):
            status = "待審閱"
            locs = review[i]
        if not done and next_stage is None:
            next_stage = i
        where = "、".join(locs[:4]) + ("…" if len(locs) > 4 else "")
        print(f"| {i} {name} | {status} | {facts.get(i, '')} | {where} |")
    print()
    pending_review = [i for i in sorted(review) if not found.get(i)]
    if pending_review:
        print(f"AI 起稿待審閱：第 {'、'.join(str(i) for i in pending_review)} 階段（共 {sum(len(review[i]) for i in pending_review)} 處）"
              "→ 依 規範/新專案.md「審閱起稿」逐階段和使用者確認，確認後刪除標記")
    fresh = not pages and not review and 1 in found and 5 in found
    if fresh:
        print("這是剛建立、還沒開始的新專案。若還沒問過使用者，先問要用「全自動」或「階段式」（規範/新專案.md 第 2 步），"
              "使用者選定前不要開始任何階段的訪談。")
        print("- 全自動：用一則訊息列出最多 10 題（每題附 AI 建議），使用者一次回答，之後寫起稿描述並執行 python3 scripts/draft_apply.py <描述.json>")
        print("- 階段式：從第 1 階段「專案概要」開始逐階段問（每階段的問題一次列出）")
    elif pending_review:
        print(f"下一步：審閱第 {pending_review[0]} 階段「{STAGES[pending_review[0] - 1]}」的起稿"
              + (f"；審閱完後再進行第 {next_stage} 階段" if next_stage else ""))
    elif next_stage:
        print(f"下一個階段：第 {next_stage} 階段「{STAGES[next_stage - 1]}」")
        if next_stage > 5 and any(k in found for k in (4, 5)):
            print("提醒：第 4、5 階段（區域、頁面清單）未完成前不畫 SVG、不建流程。")
    else:
        print("各階段都已完成；之後的修改改用 spec-change skill。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
