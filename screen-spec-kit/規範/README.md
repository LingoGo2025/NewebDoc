# 共用設計規範（screen-spec-kit）

本資料夾是畫面規格／示意圖專案的共用設計規範，不綁定任何 AI 工具：Claude、Codex、Gemini、Copilot、Cursor 等都從專案的入口檔（`AGENTS.md`、`CLAUDE.md`、`GEMINI.md`、`.github/copilot-instructions.md`）被導到這裡。版本見 `project.json › engine_version`。

## 先讀

| 要做的事 | 讀 |
|---|---|
| 修改既有專案（任何修改都從這裡開始） | `修改專案.md`，再依其中的對照表讀需要的檔案 |
| 從零建立新專案 | `新專案.md` |

接著讀專案根目錄的 `專案規則.md`（專案專屬規則）與 `project.json`（專案設定）；與本資料夾衝突時以專案為準。

## 檔案

| 檔案 | 內容 |
|---|---|
| `修改專案.md` | 修改既有專案的標準流程、收尾清單、不可做、示範專案與 plugin 同步 |
| `新專案.md` | 從零建立新專案的訪談流程 |
| `workflow.md` | 修改流程、工具注意事項、網站地圖寫法、內容維護 |
| `questioning.md` | 提問規則：通用原則、修改時的四種問題、新專案 12 個訪談階段 |
| `stages.md` | 各訪談階段寫到哪裡、怎麼寫、跑什麼工具 |
| `spec-writing.md` | 開發說明、SA 規格、API 規格寫法 |
| `flows.md` | 頁面與流程連動、流程圖設計規範 |
| `architecture.md` | 頁面與架構連動、架構圖設計規範 |
| `index-page.md` | 燈箱、首頁區塊、文件完整度、文件責任 |
| `mockup.md` | 新頁面 SVG 初稿：元件、頁面描述、品牌配色與各區版型 |

## 維護

- 示範專案（`project.json › kit.engine_source` 為 true）的 `規範/` 是來源，改完執行 `sync_kit.py` 帶回 plugin。
- 其他專案的 `規範/` 是複本，以 `upgrade_project.py` 升級時整份替換；不要在那裡改。
- 規範不寫進 AI 入口檔或 `專案規則.md`；入口檔由 `scripts/ai_entry.py` 產生。
