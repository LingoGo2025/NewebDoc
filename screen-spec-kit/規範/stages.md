# 各訪談階段的寫法

每階段：問（`questioning.md` 第 3 節表格）→ 回放 → 寫入下表位置並移除該階段標記 →執行工具 → `check.py`。檔名以 `project.json › files` 為準（預設：規格 `畫面與流程文字規格.md`、網站地圖 `網站地圖.md`）。

## 1 專案概要

- 規格「## 規格範圍」的專案說明；`專案規則.md`「回答語言」「品牌與素材」。
- `project.json`：`name`；`brand.name`；有正式標誌時放 `assets/<檔名>.svg` 並寫 `brand.logo`；`theme.primary`、`primary_dark`（較深）、`primary_soft`（很淺的底色）、`sidebar`（深色側欄），後台想用不同色時寫 `theme.regions.<column>`。使用者只描述顏色時給 2–3 組色碼讓他選。
- index.html 內容區：`<!-- [slot:hero] -->` 的副標、`<!-- [slot:title] -->`、`<!-- [slot:footer] -->`。
- 工具：`index_build.py`（主色）。

## 2 使用者與角色

- 規格「系統架構 › 使用者」表：使用者｜使用區域｜說明（角色寫在說明）。
- 系統情境圖 `architecture/system_context.puml`：左側加使用者（`actor`），連到所屬入口；讀圖說明在第 8 階段一起改寫。
- 工具：本機 `plantuml -tsvg architecture/system_context.puml` → `svg_bundle.py` → `dev_notes.py`。

## 3 業務規則與用語限制

- `專案規則.md`「業務規則與用語限制」：每條一句。
- 有禁用詞時寫 `project.json › term_rules`：`{"label": "<規則名>", "desc": "<說明>", "terms": ["…"], "allow_pattern": "不|非|無|未"}`（allow_pattern 是允許的否定寫法，例如「不設售價」）。
- 影響頁面範圍的規則（例如沒有結帳頁）在第 5 階段列頁面時引用。

## 4 區域

- `project.json`：
  - `ids.page_prefixes`：依前台 → 後台排序（決定燈箱「管理頁面／結果頁面」方向）；`api_prefix`。
  - `regions`：`{"name", "column", "prefix" 或 "pages", "backend"}`；column 用英文小寫，作為各設定的 key。
  - `index.layout`：網站地圖欄位排列（每組一欄，同組上下堆疊）。
  - `mockup.<column>`：`layout`（`backend` 側欄／`public` 頂部導覽）、側欄與頁首頁尾文字、`nav`（共用選單 key）。
- 網站地圖「全站區域」表（區域｜對象／用途｜示意圖數）與「網站地圖節點」下每區的 `### 區域名稱` 與 `_區域說明_`，名稱須與 `regions.name` 相同；刪掉範本多出的區域。
- `專案規則.md`「區域歸屬」。
- 架構圖兩張的入口方塊與 `regions` 一致（名稱、顏色；規格「圖例」同步）。
- 工具：`index_build.py` → `plantuml` 兩張架構圖 → `svg_bundle.py` → `check.py`。

## 5 頁面清單

- 網站地圖「網站地圖節點」：每區 `#### 節點` ＋ 說明段落 ＋「頁面／按鈕：」清單，每個按鈕一定有「  - 說明：」（寫法見 `workflow.md`「網站地圖寫法」）。API 按鈕在第 9 階段補。
- 「全站區域」表的示意圖數同步。
- 共用選單：`### <名稱>（nav: <key>）`、`- 樣式：sidebar|topbar`、`- 套用頁面：`、表格（順序｜選單項目｜反白頁面）；key 與 `mockup.<column>.nav` 一致。
- 每頁：
  1. `python3 scripts/page_stub.py <ID> <名稱> --desc "<一句說明>"`（規格段落骨架）。
  2. 頁面描述 JSON（暫存目錄），只放標題、說明與一個 `notice`「畫面內容待第 11 階段逐頁細節」→ `python3 scripts/mockup.py <描述.json>`。
- 架構圖：功能架構圖入口層方塊列出各區頁面 ID。
- 工具：`sync_screen_text.py <ID…>` → `index_build.py` → `nav.py` → `plantuml` 功能架構圖 → `svg_bundle.py` → `dev_notes.py` → `check.py`。

## 6 業務模組

- 規格「系統架構 › 業務模組」表（模組｜涵蓋頁面），每頁都要歸入；暫不歸入的寫 `- 暫不歸入模組：<ID>（原因）`。「共用服務」表（共用服務｜用途｜連到的外部系統）。
- 功能架構圖：業務模組層 `rectangle "<模組>\n<ID…>" as M<n>`、共用服務層；新增的顏色同步寫進規格「圖例」（`architecture.md` 設計規範）。
- 讀圖說明「功能架構圖」改寫為 2–3 句，移除標記。
- 工具：`plantuml` → `svg_bundle.py` → `dev_notes.py` → `check.py`（會比對模組與圖）。

## 7 跨頁流程

- 每條流程 `flows/<key>.puml`：檔頭 `@title`、`@pages`、`@order`、`@summary`（`flows.md`），參與者名稱先加進規格「流程圖參與者類別」表。
- 規格「## 跨頁流程」每條：`<a id="flow-<key>"></a>`、`### 流程名稱`、`- 頁面：`、`- 流程摘要：`、`- SVG：…；PlantUML：…`。
- 相關頁面的規格加 `- 對應流程：[流程名稱](#flow-<key>)`。
- 工具：`flow_sync.py` → `plantuml -tsvg flows/<key>.puml` → `svg_bundle.py` → `check.py`。

## 8 外部系統

- 規格「系統架構 › 外部系統」表（外部系統｜需求類別｜交換資料｜依據｜狀態）；需求類別須列在「外部系統需求類別」表。介接細節未知時狀態寫「待確認」。
- 系統情境圖右側加外部系統與連線；讀圖說明「系統情境圖」改寫；圖例同步。`專案規則.md`「配色對照」整理。
- index.html 內容區 `<!-- [slot:external-intro] -->` 可改寫一句引言。
- 工具：`plantuml` → `svg_bundle.py` → `dev_notes.py` → `check.py`。

## 9 對外 API

- 沒有對外 API：在規格「## API 介接」寫明「本專案沒有對外 API」，`project.json` 移除 API 區域（含 `index.layout`、`mockup.api`）、網站地圖刪 `### API`、架構圖刪 API 入口與圖例，移除標記。
- 有：每支 API 在網站地圖 API 區加 `- 按鈕（API01）：\`<名稱>\`（說明）`＋「  - 說明：」＋`- 流程圖：\`flows/<key>.svg\``；規格「## API 介接」寫 `<a id="api-api01"></a>`、`### API01｜名稱`、對應頁面、流程、開發說明與 `**API 規格（待確認）**` 四個小節（`spec-writing.md`）；欄位與加解密依原則 6 標待確認。API 流程照第 7 階段寫法，並歸入業務模組。
- 工具：`flow_sync.py` → `plantuml` → `index_build.py` → `svg_bundle.py` → `dev_notes.py` → `check.py`。

## 10 全站共用規則

- 規格「## 全站共用規則（試做）」各表：共用欄位規則（CF-01…）、共用表單行為（CB-01…）、共用錯誤文案（CE-01…）、共用驗收條件（CAC-01…）、非功能需求條列。使用者同意的通用做法標「（預設規則）」。
- 工具：`dev_notes.py` → `inventory.py` → `check.py`。

## 11 逐頁細節（可分次）

- 一次一頁或一個節點：問欄位、狀態、按鈕、文案、錯誤情境。
- 寫規格該頁「目前說明」「開發說明（AI 補充）」，SA 規格依 `spec-writing.md`「依示意圖與流程補 SA」逐頁補（先 `python3 scripts/sa_context.py <ID>` 取得素材），改為 `**SA 規格（試做）**`，使用者確認後改為 `**SA 規格**`（共用部分引用第 10 階段編號）。
- SVG：寫完整的頁面描述 JSON，`python3 scripts/mockup.py <描述.json> --force`（只限第 5 階段產生、尚未手動調整的初稿）；之後的修改局部編輯 SVG。
- 工具：`sync_screen_text.py <ID>` → `svg_bundle.py` → `dev_notes.py` → `check.py`。

## 12 選填

- 規格「舊系統移轉計畫（選填）」「相關法規（選填）」章與 index.html 內容區 `migration`、`regulations`：使用者提供內容時寫入；略過時保留「選填・待補」。
- 刪除 `專案規則.md`「目前狀態」裡的第 12 階段標記。
