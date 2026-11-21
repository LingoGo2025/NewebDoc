#!/usr/bin/env python3
"""AI 入口檔：產生內容相同的 AGENTS.md、CLAUDE.md、GEMINI.md、.github/copilot-instructions.md。

用法：
  python3 scripts/ai_entry.py            # 產生或更新入口檔
  python3 scripts/ai_entry.py --check    # 只檢查是否一致（check.py 也會呼叫）

入口檔只告訴 AI 先讀哪些檔案，不寫任何規範：共用設計規範在 `規範/`，專案規則在 `專案規則.md`，
專案設定在 `project.json`。回答語言取自 `專案規則.md`「## 回答語言」的第一段。
要產生哪些入口檔可在 project.json › ai_entries 設定（預設上述四個）。不要手改入口檔。
"""
from __future__ import annotations

import re
import sys

from _common import CONFIG, ROOT, read

DEFAULT_ENTRIES = ["AGENTS.md", "CLAUDE.md", "GEMINI.md", ".github/copilot-instructions.md"]
RULES = ROOT / "專案規則.md"
MARK = "<!-- 由 scripts/ai_entry.py 產生"


def entries() -> list[str]:
    return CONFIG.get("ai_entries") or DEFAULT_ENTRIES


def language() -> str:
    if not RULES.exists():
        return ""
    m = re.search(r"^## 回答語言\s*\n+(.+?)(?:\n\s*\n|\n## |\Z)", read(RULES), re.S | re.M)
    text = m.group(1).strip() if m else ""
    return "" if not text or "〔待訪談" in text else text


def render() -> str:
    names = "、".join(f"`{e}`" for e in entries())
    lang = language()
    lines = [
        f"{MARK}（screen-spec-kit {CONFIG.get('engine_version', '')}）；{names} 內容相同，不手改、不寫規範。 -->",
        f"# {CONFIG.get('name', '')}：AI 工作入口",
        "",
        f"回答語言：{lang}" if lang else "回答語言：見 `專案規則.md`「回答語言」（尚未設定時先問使用者）。",
        "",
        "開始任何工作前，依序閱讀（路徑相對於專案根目錄）：",
        "",
        "1. `規範/README.md`：共用設計規範（維護流程、寫法、提問方式）。修改既有專案從 `規範/修改專案.md` 開始；從零建立新專案看 `規範/新專案.md`。",
        "2. `專案規則.md`：本專案專屬規則；與共用規範衝突時以它為準。",
        "3. `project.json`：專案設定（區域、頁面 ID、配色、各區版型等）。",
        "",
        "規範與專案規則都不寫在本檔；要改規則時改上面兩份檔案（共用規範的改法見 `規範/修改專案.md`「示範專案與 plugin 同步」）。",
    ]
    return "\n".join(lines) + "\n"


def stale() -> list[str]:
    want = render()
    return [e for e in entries() if not (ROOT / e).exists() or read(ROOT / e) != want]


def main() -> int:
    if not RULES.exists():
        print("錯誤｜找不到 專案規則.md（專案專屬規則檔）")
        return 1
    bad = stale()
    if "--check" in sys.argv[1:]:
        if bad:
            print("錯誤｜AI 入口檔未同步：" + "、".join(bad) + " → python3 scripts/ai_entry.py")
            return 1
        print("OK｜AI 入口檔一致")
        return 0
    for e in bad:
        path = ROOT / e
        if path.exists() and MARK not in read(path):
            print(f"提醒｜{e} 原本不是本工具產生的，已覆寫；原內容若有規則請移到 專案規則.md 或 規範/")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render(), encoding="utf-8")
    print(f"已更新｜{'、'.join(bad)}" if bad else "OK｜AI 入口檔一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
