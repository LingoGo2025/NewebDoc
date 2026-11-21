---
name: spec-change
description: 修改既有的畫面規格／示意圖專案（根目錄有 project.json 與 scripts/check.py）：新增、刪除、搬移或調整頁面、SVG 示意圖、網站地圖、共用選單、跨頁流程（PlantUML）、系統架構圖、開發說明、SA 規格、API 規格或 index.html 燈箱時使用。依通用設計規範以「先查影響範圍 → 向使用者確認 → 改 Markdown → 局部改圖 → 同步 → 檢查」完成，並維持 Markdown、SVG、流程與 index.html 一致。
---

# 修改畫面規格專案（spec-change）

本 skill 只是 Claude 的入口。規範本身是不綁定 AI 的 Markdown，放在每個專案的 `規範/` 資料夾，Codex、Gemini、Copilot、Cursor 等讀的是同一份；不要把規範寫進 skill、`CLAUDE.md` 或 `AGENTS.md`。

1. 找到專案根目錄（有 `project.json`、`scripts/check.py`）。
2. 讀專案的 `規範/README.md`，依它的指示從 `規範/修改專案.md` 開始，並讀 `專案規則.md` 與 `project.json`。之後完全依這些檔案工作。
3. 專案還沒有 `規範/`（舊版專案）：改讀本 plugin 的 `規範/README.md`（本檔往上兩層），並建議使用者執行 `python3 <plugin>/tools/upgrade_project.py <專案> --dry-run` 升級。
