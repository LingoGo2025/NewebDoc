#!/usr/bin/env python3
"""流程同步：由 `@order` 產生 PUML 頁面圖例，並把流程資料寫回 index.html。

用法：
  python3 scripts/flow_sync.py            # 更新所有流程的圖例與 index.html 流程 JSON
  python3 scripts/flow_sync.py --check    # 只檢查是否已同步（不寫檔）

圖例位於 PUML `title` 下方、`' [legend:begin]`～`' [legend:end]` 之間，由本工具產生，不手動編輯。
樣式位於 `@startuml` 下方、`' [style:begin]`～`' [style:end]` 之間，同樣由本工具產生：
  - 統一字型、顏色與群組／備註樣式（流程圖配色，見 AGENTS.md「流程圖設計規範」）；
  - 參與者宣告依規格「系統架構 › 流程圖參與者類別」表加上 `<<代號>>`（database 一律 data），
    樣式區塊只為該圖用到的類別產生顏色；表內沒有的參與者不加類別，由 check.py 報錯；
  - 沒有 `title` 行時依 `@title` 補上；
  - 回傳箭頭 `A --> B` 改為灰色 `A -[#7C8F88]-> B`，突顯主流程。
改完 PUML 後仍需自行渲染 SVG：`plantuml -tsvg flows/<key>.puml`。
"""
from __future__ import annotations

import json
import re
import sys

from _common import FLOW_DATA_CATEGORY, FLOWS, INDEX, flow_list, flow_palette, read, screen_files, screen_name

BEGIN, END = "' [legend:begin]", "' [legend:end]"
LEGEND_RE = re.compile(rf"{re.escape(BEGIN)}\n.*?{re.escape(END)}\n", re.S)
STYLE_BEGIN, STYLE_END = "' [style:begin]", "' [style:end]"
STYLE_RE = re.compile(rf"{re.escape(STYLE_BEGIN)}\n.*?{re.escape(STYLE_END)}\n", re.S)
DECL_RE = re.compile(r'^(actor|participant|database|boundary|control|entity|queue|collections)\s+"([^"]*)"\s+as\s+(\w+)(?:\s+<<\w+>>)?\s*$', re.M)
RETURN_COLOR = "#7C8F88"
RETURN_RE = re.compile(r"^(\s*\w+) --> (\w+)", re.M)
BASE_STYLE = """skinparam defaultFontName "PingFang TC"
skinparam defaultFontColor #203F3C
skinparam backgroundColor #FFFFFF
skinparam DiagramBorderColor #C9D3CF
skinparam DiagramBorderThickness 2
skinparam shadowing false
skinparam TitleFontSize 18
skinparam TitleFontColor #087E78
skinparam RoundCorner 10
skinparam ArrowColor #2F4A44
skinparam ArrowThickness 1.6
skinparam ArrowFontSize 13
skinparam ParticipantBorderThickness 1.6
skinparam ActorBorderThickness 1.6
skinparam DatabaseBorderThickness 1.6
skinparam SequenceLifeLineBorderColor #5E7770
<style>
sequenceDiagram {
  lifeLine {
    LineThickness 1.4
  }
}
</style>
skinparam SequenceGroupBorderColor #6F9484
skinparam SequenceGroupBorderThickness 1.4
skinparam SequenceGroupBackgroundColor #E8F2EB
skinparam SequenceGroupBodyBackgroundColor #FBFDFC
skinparam SequenceGroupHeaderFontColor #24675C
skinparam SequenceDividerBorderColor #5E7770
skinparam NoteBackgroundColor #FFF8EC
skinparam NoteBorderColor #D9A066
skinparam NoteBorderThickness 1.2
skinparam LegendBackgroundColor #F7FBF9
skinparam LegendBorderColor #C9D3CF
skinparam LegendFontSize 12
hide stereotype"""


def participant_category(kind: str, name: str, members: dict[str, str]) -> str | None:
    return FLOW_DATA_CATEGORY if kind == "database" else members.get(name)


def style_source(text: str, cats: dict[str, dict], members: dict[str, str]) -> str:
    """去掉 !theme、加上類別 stereotype、回傳箭頭改灰色，並重產樣式區塊。"""
    text = re.sub(r"^!theme .*\n", "", text, flags=re.M)
    used: list[tuple[str, str]] = []

    def decl(m: re.Match) -> str:
        kind, name, alias = m.groups()
        code = participant_category(kind, name, members)
        if code in cats:
            if (kind, code) not in used:
                used.append((kind, code))
            return f'{kind} "{name}" as {alias} <<{code}>>'
        return f'{kind} "{name}" as {alias}'

    text = DECL_RE.sub(decl, text)
    text = RETURN_RE.sub(lambda m: f"{m.group(1)} -[{RETURN_COLOR}]-> {m.group(2)}", text)
    lines = [BASE_STYLE]
    for kind, code in used:
        c = cats[code]
        lines.append(f"skinparam {kind}<<{code}>> {{\n  BackgroundColor {c['fill']}\n  BorderColor {c['line']}\n}}")
    block = STYLE_BEGIN + "\n" + "\n".join(lines) + "\n" + STYLE_END + "\n"
    if STYLE_RE.search(text):
        return STYLE_RE.sub(lambda _m: block, text, count=1)
    return re.sub(r"^(@startuml.*\n)", lambda m: m.group(1) + block, text, count=1, flags=re.M)


def legend_block(meta: dict, names: dict[str, str]) -> str:
    pages = meta["order"] or [[p] for p in meta["pages"]]
    lines = ["legend top left", "  **對應頁面（依流程順序）**"]
    for i, step in enumerate(pages, 1):
        lines.append(f"  {i}. " + " ／ ".join(f"{p} {names.get(p, '?')}" for p in step))
    lines.append("endlegend")
    return BEGIN + "\n" + "\n".join(lines) + "\n" + END + "\n"


def synced_source(meta: dict, names: dict[str, str], palette: tuple | None = None) -> str:
    cats, members = palette or flow_palette()
    text = style_source(meta["source"], cats, members)
    block = legend_block(meta, names)
    if not re.search(r"^title ", text, re.M):
        # 沒有 title 行時依 @title 補上（圖例接在 title 之後）
        title = f"title {meta.get('title') or meta['key']}\n"
        if STYLE_END in text:
            text = text.replace(STYLE_END + "\n", STYLE_END + "\n" + title, 1)
        else:
            text = re.sub(r"^(@startuml.*\n)", lambda m: m.group(1) + title, text, count=1, flags=re.M)
    if LEGEND_RE.search(text):
        return LEGEND_RE.sub(lambda _m: block, text, count=1)
    return re.sub(r"^(title .*\n)", lambda m: m.group(1) + block, text, count=1, flags=re.M)


def main() -> int:
    check = "--check" in sys.argv
    names = {k: screen_name(v) for k, v in screen_files().items()}
    palette = flow_palette()
    stale = []
    metas = []
    for meta in flow_list():
        new = synced_source(meta, names, palette)
        if new != meta["source"]:
            stale.append(meta["key"])
            if not check:
                (FLOWS / f"{meta['key']}.puml").write_text(new, encoding="utf-8")
                meta["source"] = new
        metas.append(meta)
    text = read(INDEX)
    m = re.search(r'(<script type="application/json" id="sequence-flow-data">)(.*?)(</script>)', text, re.S)
    old = json.loads(m.group(2))
    by_key = {d["key"]: d for d in old}
    data = []
    for meta in metas:
        d = dict(by_key.get(meta["key"], {}))
        d.update(key=meta["key"], title=meta["title"], summary=meta["summary"], pages=meta["pages"],
                 order=["|".join(step) for step in meta["order"]],
                 puml=f"flows/{meta['key']}.puml", svg=f"flows/{meta['key']}.svg", source=meta["source"])
        data.append(d)
    new_json = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    if new_json != m.group(2):
        stale.append("index.html")
        if not check:
            INDEX.write_text(text[:m.start(2)] + new_json + text[m.end(2):], encoding="utf-8")
    if check:
        print("流程圖例與 index.html 已同步" if not stale else "未同步：" + "、".join(stale) + "（執行 python3 scripts/flow_sync.py）")
        return 1 if stale else 0
    print("已更新：" + ("、".join(stale) if stale else "無需更新"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
