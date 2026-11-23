#!/usr/bin/env python3
"""把規格中每頁的「開發說明」打包成 assets/dev_notes.js，供燈箱「開發說明」頁籤使用。

規格寫法（放在各頁「對應流程」行之後）：
  - 開發說明（AI 補充）：
    - 項目（AI 依現有規格整理，未知內容標示待確認）
  - 開發說明（設計者補充）：
    - 項目（設計者要求補充才寫；沒有就留空，燈箱仍保留此區塊）

  **SA 規格（試做）**          ← 選填，放在開發說明之後、畫面文字之前
  > 說明                        ← 區塊開頭的引言（選填）
  #### 1. 小節標題
  | 欄 | 欄 |                   ← Markdown 表格
  - 條列                        ← 條列項目
  #### 摘要｜…                  ← 給人審閱，燈箱展開顯示
  #### 明細｜…                  ← 給開發使用，燈箱預設收合
  有 SA 規格的頁面，燈箱會多出「SA 規格」頁籤；沒有的頁面不顯示該頁籤。

另有章節「## 全站共用規則（試做）」（寫法同上，用 #### 分小節），打包為 "_common"，
燈箱在有 SA 規格的頁面底部以收合區塊顯示。

API（`### API01｜…`）同樣有「開發說明」兩段，另以 `**API 規格（…）**` 標記開始介接規格區塊（寫法同 SA 規格，
`####` 小節：介接資訊、傳送欄位、回傳欄位｜…、加解密方式），打包為該 API 的 "api"；「- 對應頁面：」行的頁面 ID
打包為 "pages"。燈箱 API 模式依小節標題分到「傳送欄位／回傳欄位／加解密方式」頁籤與右側「介接資訊」。

說明對照：頁面 SVG 的區塊加 data-note="<標籤>"（標籤同開發說明的【標籤】），燈箱「說明」按鈕依此把說明標在畫面上；
各頁有對應記號的標籤打包為 "anchors"。重新產生時若某條說明原本有對應、現在記號不見了（區塊被刪或拆開），會印出提醒，
該條說明改列為整頁說明。

另打包規格「## 系統架構」章（讀圖說明、圖例、各表格、暫不歸入模組）與 architecture/*.puml 原稿為 "_architecture"，
供系統情境圖／功能架構圖的專屬燈箱（圖說明、對照表、複製語法）使用。

用法：
  python3 scripts/dev_notes.py          # 重新產生 assets/dev_notes.js
  python3 scripts/dev_notes.py --check  # 只檢查是否過期（check.py 也會呼叫）
"""
from __future__ import annotations

import json
import re
import sys

from _common import MOBILE_KEY, MOBILE_NONE, note_label, note_markers, screen_files, ANY_ID, ARCH, ARCH_FIGURES, PAGE_ID, ROOT, SPEC, TEXT_MARKER, architecture_spec, read

OUTPUT = ROOT / "assets" / "dev_notes.js"
HEADER = "// 由 scripts/dev_notes.py 產生，請勿手動編輯；規格「開發說明」改動後重新執行。\n"
AI_KEY = "- 開發說明（AI 補充）"
DESIGNER_KEY = "- 開發說明（設計者補充）"
COMMON_HEADING = "## 全站共用規則"
SA_RE = re.compile(r"\*\*SA 規格(?:（[^）]*）)?\*\*$")
API_RE = re.compile(r"\*\*API 規格(?:（[^）]*）)?\*\*$")
PAGES_KEY = "- 對應頁面："


def _cells(line: str) -> list[str]:
    return [c.strip().replace("`", "") for c in line.strip().strip("|").split("|")]


def _sa_add(sa: dict, line: str) -> None:
    """把 SA 規格區塊的一行加入結構：{note, sections:[{title, blocks:[table|list]}]}。"""
    text = line.strip()
    if not text:
        if sa["sections"] and sa["sections"][-1]["blocks"]:
            sa["sections"][-1]["blocks"][-1]["closed"] = True
        return
    if text.startswith("#### "):
        sa["sections"].append({"title": text[5:].strip(), "blocks": []})
        return
    if text.startswith("> ") and not sa["sections"]:
        sa["note"] = (sa.get("note", "") + " " + text[2:]).strip()
        return
    if not sa["sections"]:
        sa["sections"].append({"title": "", "blocks": []})
    blocks = sa["sections"][-1]["blocks"]
    last = blocks[-1] if blocks and not blocks[-1].get("closed") else None
    if text.startswith("|"):
        cells = _cells(text)
        if all(re.fullmatch(r":?-{3,}:?", c) for c in cells):
            return
        if last and last["type"] == "table":
            last["rows"].append(cells)
        else:
            blocks.append({"type": "table", "head": cells, "rows": []})
    elif text.startswith("- "):
        if last and last["type"] == "list":
            last["items"].append(text[2:])
        else:
            blocks.append({"type": "list", "items": [text[2:]]})
    else:
        blocks.append({"type": "list", "items": [text]})


def _sa_clean(sa: dict) -> dict:
    for sec in sa["sections"]:
        for block in sec["blocks"]:
            block.pop("closed", None)
    return sa


def parse() -> dict[str, dict]:
    notes: dict[str, dict] = {}
    pid, bucket, sa = None, None, None
    for line in read(SPEC).split("\n"):
        m = re.match(rf"### ({ANY_ID})｜", line)
        if m:
            pid, bucket, sa = m.group(1), None, None
            continue
        if line.startswith("## "):
            pid, bucket, sa = None, None, None
            if line.startswith(COMMON_HEADING):
                sa = notes.setdefault("_common", {}).setdefault("sa", {"sections": []})
            continue
        if not pid:
            if sa is not None and not line.startswith("<a id="):
                _sa_add(sa, line)
            continue
        if line.strip() == TEXT_MARKER:
            sa = None
            continue
        if SA_RE.match(line.strip()) or API_RE.match(line.strip()):
            bucket = None
            key = "sa" if SA_RE.match(line.strip()) else "api"
            sa = notes.setdefault(pid, {"ai": [], "designer": []}).setdefault(key, {"sections": []})
            continue
        if sa is not None:
            if not line.startswith("<a id="):
                _sa_add(sa, line)
            continue
        if line.startswith(MOBILE_KEY):   # 手機版示意圖：路徑或「無相關設計（原因）」
            value = line[len(MOBILE_KEY):].strip()
            path = re.search(r"`(screens/mobile/[^`]+\.svg)`", value)
            notes.setdefault(pid, {"ai": [], "designer": []})["mobile"] = (
                {"svg": path.group(1)} if path else {"none": value or MOBILE_NONE})
            bucket = None
            continue
        if line.startswith(PAGES_KEY):
            notes.setdefault(pid, {"ai": [], "designer": []})["pages"] = re.findall(rf"\b{PAGE_ID}\b", line)
            bucket = None
        elif line.startswith(AI_KEY):
            bucket = notes.setdefault(pid, {"ai": [], "designer": []})["ai"]
        elif line.startswith(DESIGNER_KEY):
            bucket = notes.setdefault(pid, {"ai": [], "designer": []})["designer"]
        elif line.startswith("  - ") and bucket is not None:
            bucket.append(line[4:].strip())
        else:
            bucket = None
    for item in notes.values():
        for key in ("sa", "api"):
            if key in item:
                _sa_clean(item[key])
    return notes


def architecture_data() -> dict:
    arch = architecture_spec()
    return {
        "guides": {key: arch.guides.get(name, "") for key, name in ARCH_FIGURES.items()},
        "legends": {key: arch.legends.get(name, []) for key, name in ARCH_FIGURES.items()},
        "tables": {k: v for k, v in arch.tables.items() if k and k not in ("讀圖說明", "圖例", "流程圖參與者類別")},
        "excluded": sorted(arch.excluded),
        "sources": {p.stem: p.read_text(encoding="utf-8") for p in sorted(ARCH.glob("*.puml"))},
    }


def add_anchors(notes: dict) -> None:
    files = screen_files()
    for pid, item in notes.items():
        if pid.startswith("_") or pid not in files:
            continue
        labels = {note_label(t) for t in item.get("ai", [])}
        found = [m for m in dict.fromkeys(note_markers(files[pid])) if m in labels]
        if found:
            item["anchors"] = found


def old_anchors() -> dict[str, list[str]]:
    if not OUTPUT.exists():
        return {}
    text = OUTPUT.read_text(encoding="utf-8")
    try:
        data = json.loads(text[text.index("=") + 1:].rstrip().rstrip(";").replace("<\\/", "</"))
    except (ValueError, json.JSONDecodeError):
        return {}
    return {k: v.get("anchors", []) for k, v in data.items() if isinstance(v, dict) and not k.startswith("_")}


def build() -> str:
    notes = parse()
    add_anchors(notes)
    notes["_architecture"] = architecture_data()
    body = json.dumps(notes, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return HEADER + "window.DEV_NOTES=" + body + ";\n"


def is_stale() -> bool:
    return not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != build()


def main() -> int:
    if "--check" in sys.argv:
        if is_stale():
            print("✗ assets/dev_notes.js 已過期，請執行 python3 scripts/dev_notes.py")
            return 1
        print("OK｜assets/dev_notes.js 與規格一致")
        return 0
    before = old_anchors()
    notes = parse()
    add_anchors(notes)
    for pid, labels in before.items():
        now = set(notes.get(pid, {}).get("anchors", []))
        still = {note_label(t) for t in notes.get(pid, {}).get("ai", [])}
        lost = [x for x in labels if x not in now and x in still]
        if lost:
            print(f"提醒｜{pid} 的說明「{'、'.join(lost)}」原本對應的區塊記號不見了（區塊刪除或拆開？），現在列為整頁說明；"
                  f"需要時在 SVG 對應區塊加 data-note=\"{lost[0]}\"")
    OUTPUT.write_text(build(), encoding="utf-8")
    pages = [k for k in parse() if not k.startswith("_")]
    print(f"已更新 {OUTPUT.relative_to(ROOT)}（{len(pages)} 頁）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
