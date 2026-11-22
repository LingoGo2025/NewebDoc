---
name: spec-new
description: 從零建立新的畫面規格／示意圖專案：使用者想開始一個新平台、新系統或新網站的頁面規劃、網站地圖、示意圖或規格文件，且還沒有 project.json 時使用。AI 依訪談階段逐步提問、記錄需求，並以 screen-spec-kit 的範本與引擎產出和既有專案相同功能的 index.html（網站地圖、燈箱、流程位置、完整度）、規格 Markdown、SVG 示意圖、流程與架構圖。專案建好後的修改改用 spec-change。
---

# 建立新的畫面規格專案（spec-new）

本 skill 只是 Claude 的入口。訪談流程與規範是不綁定 AI 的 Markdown：讀本 plugin 的 `規範/新專案.md`（本檔往上兩層的 `規範/`），依它的步驟進行。建立後的專案會有自己的 `規範/` 複本與 `AGENTS.md`、`CLAUDE.md`、`GEMINI.md`、`.github/copilot-instructions.md` 入口檔，換用其他 AI 也能接續。
