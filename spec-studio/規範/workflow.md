# 修改流程、工具與內容維護（通用）

適用範圍：專案根目錄內的 `index.html`、`screens/`、`flows/`、`architecture/`、`scripts/`、`assets/`、`project.json` 與 Markdown 規格。檔名以 `project.json › files` 為準，以下用預設名稱：規格 `畫面與流程文字規格.md`、網站地圖 `網站地圖.md`。

## 修改流程（省 token）

不要整份讀取規格（約半數是自動產生的畫面文字清單）、`index.html` 或 SVG；先用工具找出範圍，只讀、只改被點到的段落。

1. **查影響範圍**：`python3 scripts/impact.py <頁面ID或關鍵字…>`，列出相關頁面、流程、網站地圖節點、共用選單與 index 關聯。
2. **向使用者確認範圍**：回報影響清單，區分「確定要改」與「待確認」，使用者同意後再動手。需求本身不明確時先問，不自行補規格。提問方式依 `questioning.md`（通用原則與四種問題：需求釐清、規則衝突、待確認定案、範圍確認）。
3. **讀需要的段落**：`python3 scripts/section.py <ID|flow-key|章節關鍵字…>`（預設略過畫面文字清單，需要時加 `--text`）；網站地圖只讀相關節點的行號範圍。
4. **改 Markdown → 局部改 SVG／index.html／流程**（頁面功能、欄位、狀態、文案有變時，依最後定案的設計同步更新該頁「開發說明（AI 補充）」，見 `spec-writing.md`）：
   - SVG 用 grep 定位要改的元素，不整檔讀取。
   - 共用選單（側欄、頂部導覽）只改 `網站地圖.md › 共用選單` 表格，再執行 `python3 scripts/nav.py`，不要逐張手改。
   - 網站地圖（區域、節點、按鈕、按鈕說明、類似／管理頁面）只改 `網站地圖.md › 網站地圖節點`，再執行 `python3 scripts/index_build.py` 重產 index.html 網站地圖區塊，不手改 HTML（寫法見下方「網站地圖寫法」）。
   - 流程：改 `flows/<key>.puml` 後執行 `python3 scripts/flow_sync.py`（產生頁面圖例並更新 index.html 流程資料），再以**本機** `plantuml -tsvg flows/<key>.puml` 渲染 SVG。不要用 `render_plantuml.py`，它會把流程原稿送到線上伺服器。
5. **記錄**：在對應 Markdown 的更新紀錄加一行。
6. **同步與檢查**：`python3 scripts/sync_screen_text.py <ID…>`（有改畫面時）；網站地圖節點、區域設定或 SVG 檔名有變時執行 `python3 scripts/index_build.py`；任何頁面或流程 SVG 有改動（含 `nav.py`、`plantuml` 重新渲染）後執行 `python3 scripts/svg_bundle.py`；規格各頁「開發說明」有改動後執行 `python3 scripts/dev_notes.py`；**每次修改都要**在記錄之後執行 `python3 scripts/inventory.py`，同步首頁「文件內容與完整度」；最後 `python3 scripts/check.py`；錯誤須修正，提醒則回報使用者。

## 文字優先、不看圖（預設）

- 討論與確認需求一律以 Markdown 文字進行（`section.py`、`impact.py` 的輸出），不為了討論而轉 PNG 或讀取圖片。
- 先把 Markdown 規格改好並經使用者同意，再用工具局部改 SVG；改完以 `sync_screen_text.py`、`check.py` 驗證文字與一致性，不以看圖代替。
- 預設不渲染預覽圖。只有以下情形才渲染：使用者要求看圖；新增／加高區塊、卡片，需確認有無重疊或被裁切（一次只看單張、縮小尺寸）；全自動起稿或一次新增多頁後的「視覺自檢」（`python3 scripts/preview.py` 拼成縮圖總覽，見 `新專案.md`）。預覽圖只放暫存目錄，不進專案，不算交付檔（與下方「內容維護」第 4 條不衝突）。
- 文字檢查無法發現版面問題（重疊、超出卡片）。改 SVG 時先以座標推算：新增內容須落在所屬卡片高度內，加高卡片時其下方元素同步下移；仍無把握時才依上一條渲染單張確認。

## 工具注意事項

- 唯讀檢查：`check.py`、`impact.py`、`section.py`、`interview_status.py`、`index_build.py --check`、`nav.py --check`、`flow_sync.py --check`、`svg_bundle.py --check`、`dev_notes.py --check`、`inventory.py --check`，屬標準流程，不受「內容維護」第 8 條「不新增或執行測試」限制。
- 會改檔的工具：`draft_apply.py`（全自動起稿，只用於剛建立、尚無頁面的專案，見 `新專案.md`）、`page_stub.py`（新增頁面的規格段落骨架，已有同 ID 不動）、`mockup.py`（只產生新頁面 SVG 初稿，不覆蓋既有檔）、`sync_screen_text.py`、`index_build.py`、`nav.py`、`flow_sync.py`、`svg_bundle.py`、`dev_notes.py`、`inventory.py`，以及本機 `plantuml` 渲染；只對受影響的頁面或流程執行（`svg_bundle.py`、`inventory.py` 一律整包重產）。
- `assets/svg_sources.js` 由 `svg_bundle.py` 產生，不手動編輯也不整檔讀取；index.html 燈箱靠它內嵌 SVG，雙擊開檔（file://）也能選取、複製文字。過期時 `check.py` 會報錯。`assets/dev_notes.js`、`assets/inventory.js` 同樣由工具產生，不手改。
- 新增頁面的 SVG 初稿用 `mockup.py` 以元件組合產生（見 `mockup.md`），不從零手寫、不重跑已過時的產生器。
- 新增頁面時，規格段落須先有 `**畫面文字（依 SVG 順序）**` 標題（內容可暫放一行）再執行 `sync_screen_text.py`；否則文字會寫進下一頁的清單。
- index.html 內 `<!-- [sitemap:begin] -->`～`<!-- [sitemap:end] -->` 與 `<script id="project-config">` 由 `index_build.py` 產生，不手動編輯；折疊區塊導引數字也由它依序重編。
- **手機版示意圖**：桌機版是每頁的主要示意圖（`screens/<ID>_<名稱>.svg`）；需要手機版的頁面另有一張 390 寬的手機版（`screens/mobile/<ID>_<名稱>.svg`，檔名與桌機版相同），兩者並存，燈箱以「手機版」頁籤顯示。規格每頁在「SVG 畫面原稿」下一行寫 `- 手機版示意圖：`，內容是手機版 SVG 路徑，或「無相關設計（原因）」（例如後台以桌機操作為主）；預設要有手機版，不需要時才寫無相關設計。`check.py` 會核對這一行與檔案。
- index.html 分三種區域：內容區 `<!-- [slot:名稱] -->`（標題、頁首、架構圖說明、說明卡、外部系統引言、移轉計畫、相關法規、頁尾；樣式用 `/* [slot:project-css] */`）由專案維護；產生區（網站地圖、專案設定、流程資料）由工具產生；其餘是引擎，由 plugin 提供（`project.json › engine_version`），升級時整份替換。
- SVG 內 `<g data-nav="…">` 區塊由 `nav.py` 產生，不手動編輯；選單樣式或位置要改時修改 `scripts/nav.py`。
- PUML 內 `' [legend:begin]`～`' [legend:end]` 與 `' [style:begin]`～`' [style:end]` 之間由 `flow_sync.py` 產生，不手動編輯（見 `flows.md`）。
- 系統架構圖（系統情境圖、功能架構圖）放 `architecture/`，不放 `flows/`（`flows/` 的 PUML 一律被當成跨頁流程檢查）。細節見 `architecture.md`。
- 專案設定 `project.json`：`scripts/` 從這裡讀取專案專屬設定，包括規格／網站地圖／index 檔名（`files`）、頁面 ID 字首與位數（`ids`）、網站地圖區域與 index 欄位（`regions`：明列 `pages` 優先，再依 `prefix` 判斷；`backend: true` 表示後台區域，燈箱「流程位置」會標註區域名稱）、index 網站地圖欄位排列（`index.layout`：每組一欄，同組上下堆疊）、品牌配色與各區版型（`theme`、`mockup`、`brand`，見 `mockup.md`）、架構圖檔名與圖名（`architecture`）、畫面用語檢查（`term_rules`）、完整度各列說明的專案用語（`inventory_desc`）。區域歸屬、ID 規則、架構圖或用語規則有變時，先改規格與 `專案規則.md`，再同步 `project.json`。文件格式慣例（章節標題、標記文字、選單版型、流程圖樣式）屬於工具本身，不放在 `project.json`。
- 新增工具或改變流程時，同步更新 `規範/` 的對應檔案與 `index-page.md`「文件責任」。

## 網站地圖寫法

`index_build.py` 只讀 `網站地圖.md` 的「## 網站地圖節點」章，格式如下（區域名稱須與 `project.json › regions` 一致）：

```markdown
### <區域名稱>

_<區域說明>_

- 地圖說明：<選填；index.html 欄位副標的簡短版，沒有時用上一行>

#### <節點標題>

<節點完整說明（一段）>

- 地圖說明：<選填；index.html 卡片的簡短版，沒有時用上一段；不得新增或改變功能範圍>

頁面／按鈕：
- [<頁面ID>](<規格檔>#<錨點>) <頁面名稱>
  - 說明：<必填；燈箱說明，一兩句>
  - 類似：<選填；類似頁面 ID，以頓號分隔 → 燈箱「相關頁面」>
  - 管理：<選填；管理此頁內容的後台頁面 ID → 燈箱「管理頁面」>
```

- 頁面按鈕的標題取自 `screens/<ID>_<名稱>.svg` 檔名，所以頁面改名時要同步改 SVG 檔名與規格標題。
- API 按鈕寫成 `- 按鈕（<API ID>）：\`<API 名稱>\`（說明）`，下接 `  - 說明：`，同節點再寫 `- 流程圖：\`flows/<key>.svg\``。
- 區域「共 n 頁」自動計算；區域內有 API 按鈕時不顯示。

## 內容維護

1. 修改前依上方流程，以 `impact.py`／`section.py` 確認頁面 ID、所屬區域、目前文案、跨頁關聯及未決事項（`section.py 待確認`）。
2. Markdown 是產品邏輯和畫面文案的基準。先更新受影響的規格，再以局部修改同步 SVG、`index.html` 與流程原稿。只改受影響頁面，不重畫或重寫未變更畫面。
3. 儘量局部編輯現有 SVG 元素，避免重建整張 SVG、重複輸出未變更區塊，或把整份 SVG 貼入文件。完成 SVG 後使用 `scripts/sync_screen_text.py <頁面ID...>` 同步該頁可見文字清單，再核對產品邏輯與頁面說明。
4. SVG 是畫面原稿及網站地圖／燈箱預覽的唯一日常格式；不產生、不維護 PNG 副本，也不把 PNG 放進專案。只有使用者明確要求 PNG／點陣輸出時才產生。
5. 保留 `index.html` 目前網站地圖、點擊放大燈箱、SVG 縮放及相關頁面導覽的呈現方式。頁面示意圖一律從網站地圖按鈕進入，不另建頁面圖庫、圖卡或分頁；燈箱直接載入 SVG 並提供 SVG 原檔下載。
6. 示意圖需要平台 Logo 時，以 `screens/` 相對路徑 `../assets/<正式標誌>.svg` 共用 `assets/` 的正式 SVG（檔名見 `專案規則.md`），不要把 Logo 點陣圖或 base64 複製嵌入每張畫面。
7. 每次變更都檢查是否連帶影響，以 `scripts/check.py` 的檢查為準（項目見其檔頭說明）：網站地圖按鈕唯一性、各區域歸屬（`project.json › regions` 與 `專案規則.md`）、跨頁流程與頁面清單、頁面 ID 與 SVG 路徑、網站地圖各欄頁數、流程 JSON／PlantUML／SVG、待確認事項及 Markdown 更新紀錄。逐區比對 ID 清單，確保每張頁面圖或 API 流程圖恰有一個所屬區域入口。
8. API、金流、法規或商業政策的未知內容不可自行補成既定規格；標示待確認。交付前核對 Markdown 與 HTML／SVG／PlantUML 的標題、說明、頁面 ID、連結及狀態一致。除非使用者要求，不新增或執行測試（上方的唯讀檢查工具除外）。
9. **開發說明維護（每次必做）**：見 `spec-writing.md`「開發說明維護」。
