# 新頁面 SVG 初稿：元件組合（通用）

新增頁面時，以 `scripts/mockup.py` 依頁面描述（JSON）組合元件產生 SVG 初稿；之後的修改一律局部編輯 SVG，不重跑工具覆蓋。

## 流程

1. 規格與網站地圖已確定該頁 ID、名稱、所屬區域（訪談第 4、5 階段完成）。
2. 寫頁面描述 JSON（放暫存目錄，不進專案）；`python3 scripts/mockup.py --example backend`（或 `public`）可印範例。
3. `python3 scripts/mockup.py <描述.json>` 產生 `screens/<ID>_<名稱>.svg`；檔案已存在時不覆蓋（確定是沒調整過的初稿才加 `--force`）。
4. 依提示完成：規格加該頁段落（含「**畫面文字（依 SVG 順序）**」）→ `sync_screen_text.py <ID>` → 網站地圖加按鈕 → `index_build.py` → `svg_bundle.py` → `check.py`。
5. 要看版面時用 `--out <暫存路徑>` 產生，再以 `rsvg-convert -w 800` 轉縮小預覽（只放暫存目錄）；多頁一起看用 `python3 scripts/preview.py <ID…>`（縮圖總覽＋文字檢查）。

## 手機版

- `python3 scripts/mockup.py <描述.json> --mobile` 用同一份描述產生 390 寬手機版到 `screens/mobile/<ID>_<名稱>.svg`：區塊自動改成單欄、表格變卡片、按鈕滿版，頁首下方是頁籤列（取同一份共用選單或 `nav_items`，反白項目會捲到看得見）。
- 描述可加 `mobile_rows`（手機版專用的區塊列，取代 `rows`）、`nav_items`（手機版頁籤列項目，`[]` 表示不顯示）、`brand_text`（頁首改寫文字品牌，例如收款單位自己的網站）。
- 規格該頁寫 `- 手機版示意圖：` 一行（見 `workflow.md`）；不需要手機版的頁面寫「無相關設計（原因）」。

## 像真實網站的原則

- 示意圖是「真實上線的樣子」，不是線框圖：用這個產品特有的元素（地圖、車牌辨識畫面、收據、證件、狀態格、金額明細、付款方式），不用灰色方塊或山形圖片框。
- 文字用真實感的內容（名稱、地址、編號、時間、單筆金額）；畫面上不寫「示意」「待確認」「選項一」，工具會在右下角標「AI 起稿示意」。費率表、收費標準與政策期限不推測（見 `新專案.md`）。
- 多步驟流程每頁加 `stepper`；送出後有結果頁（`result`），成功與失敗各一。
- 圖示與插圖都由 `scripts/mockup_art.py` 繪製（本工具自繪的線條圖示，不引用外部圖片）；`python3 scripts/mockup_art.py` 列出可用名稱。

## 版型與配色來源（project.json）

| 設定 | 用途 |
|---|---|
| `theme` | 品牌配色：`primary`（強調、數字、主要按鈕）、`primary_dark`、`primary_soft`（標籤底、步驟圓點）、`sidebar`、`page_bg`、`surface`、`ink`、`heading`、`text`、`muted`、`border`、`nav_text`、`nav_active`、`font`；`theme › regions › <column>` 覆寫某區（例如後台改橘色） |
| `mockup › <column>` | 各區版型：`layout`（`backend` 1600×1080 左側欄／`public` 1440×1000 頂部導覽；主要畫面一律是桌機版，手機版另以 `--mobile` 產生）、`mobile`（`true` 表示這一區新頁面也要畫手機版）、`nav`（共用選單 key）、側欄 `label`／`sublabel`／`identity`、頁首 `account`、`badge`、前台 `brand`／`nav_items`／`buttons`／`header_note`、`footer` |
| `brand` | 正式標誌 `logo`（`assets/` 內 SVG，內嵌為 `data-logo`）與文字名稱 `name` |

同一個 `theme` 也用在 `nav.py` 頂部導覽與 index.html 主色（`index_build.py` 產生 `#project-theme`）。

## 頁面描述

| 欄位 | 說明 |
|---|---|
| `id`、`name`、`desc` | 必填：頁面 ID、名稱（檔名與標題）、一句說明 |
| `region` | 選填：`regions › column`；預設依 `project.json › regions` 判斷 |
| `subtitle`、`badge`、`active`、`avatar` | 選填：標題下說明、右上區域標籤、選單反白項目、頭像字 |
| `layout` | 選填：覆寫該區版型（`backend`、`public`） |
| `mobile_rows`、`nav_items`、`brand_text` | 選填（手機版）：見上方「手機版」 |
| `bare` | 選填：`true` 時不畫側欄與選單，內容置中（登入、註冊、忘記密碼） |
| `back` | 選填（mobile）：頁首改成「‹ 返回＋頁名」 |
| `hero` | 選填（public）：`eyebrow`、`title`、`lead`（字串陣列） |
| `stats` | 選填：`[[標籤, 數值, 註記], …]`，頁首下一排統計卡 |
| `rows` | 區塊列：`[[區塊, 區塊], [區塊]]`，同列等寬並排、等高，最多 3 個 |

## 區塊（`type`）

| type | 欄位 | 用途 |
|---|---|---|
| `list` | `title`、`items`（字串或 `[主文, 副文]`） | 重點清單 |
| `steps` | `title`、`items` | 編號步驟 |
| `table` | `title`、`columns`、`rows` | 資料表 |
| `form` | `title`、`fields`（`[標籤, 提示]`）、`cols` | 表單欄位 |
| `kv` | `title`、`items`（`[標籤, 內容]`）、`cols` | 資訊卡（標籤＋內容） |
| `text` | `title`、`paragraphs` | 說明段落（自動換行） |
| `notice` | `text`、`tone`（`info`／`warn`） | 提醒框；待確認事項用 `warn` |
| `actions` | `buttons`（字串或 `{label, style: "primary"}`）、`align` | 按鈕列（預設靠右） |
| `section` | `text` | 區段大標（前台） |
| `stats` | `items` | 統計卡（後台小卡、前台大數字卡自動切換） |
| `filters` | `fields`、`submit` | 一列查詢條件＋查詢／重設按鈕（列表頁上方） |
| `tabs` | `items`（`[名稱, 數量]`）、`active` | 頁籤列 |
| `chart` | `title`、`labels`、`values`、`unit` | 長條圖（總覽頁趨勢） |
| `timeline` | `title`、`items`（`[時間, 標題, 說明]`） | 處理歷程（明細頁） |
| `cards` | `title`、`items`（`{title, meta, tag, button}`）、`cols` | 卡片牆，上方有圖片示意區（前台） |
| `summary` | `title`、`status`、`meta`（`[[欄位, 值]…]`）、`actions` | 明細頁首：標題、狀態標籤、重點欄位、按鈕 |
| `caption` | `text`、`align` | 小字註記（例如「AI 起稿示意」） |
| `stepper` | `items`（步驟名稱）、`current`（0 起算） | 多步驟流程上方進度 |
| `result` | `tone`（`ok`／`bad`／`warn`／`info`）、`title`、`text`、`items`（`[欄位, 值]`）、`buttons`（最後一個為主按鈕） | 成功／失敗結果頁主體 |
| `price` | `title`、`items`（`[項目, 金額]`）、`total`、`note` | 金額明細 |
| `choice` | `title`、`items`（`{title, meta, icon, right}`）、`selected`、`cols` | 選項卡（付款方式、方案、時段） |
| `map` | `title`、`pins`（`[標記文字, 名稱, 狀態]`；狀態含「滿」紅、「剩」橘）、`search`、`height`、`legend` | 地圖＋標記 |
| `tiles` | `title`、`items`（`[名稱, 狀態]`）、`cols`、`legend` | 狀態格（車位、座位、設備） |
| `media` | `title`、`art`（`plate`、`id_card`、`receipt`、`qr`、`document`、`car`、`map`、`phone`、`preview`）、`side`（`[欄位, 值]`）、`caption`、`height`；其餘欄位傳給插圖（如 `plate`、`stamp`、`camera`、`score`、`label`） | 產品特有的畫面元素 |
| `empty` | `icon`、`title`、`text`、`button` | 空狀態（查無資料） |

- `list` 的項目可寫 `{icon, title, sub, right}` 或 `[主文, 副文, 右側值]`，會畫成「圖示＋主副文＋右側時間或狀態」（通知、待辦）。
- `cards` 的項目可加 `icon`、`stat`（`[數字, 說明]`）、`art`（插圖種類）；沒寫 `icon` 時依文字自動挑圖示。統計卡（`stats`）後台版也會依標籤自動加圖示。
- `form` 欄位型態另有 `switch`（開關）；`checkbox` 沒有 `options` 時畫成單一勾選，標籤寫在方框旁。
- 區塊寬度小於 520 時（手機版或窄欄）自動改成手機排版：表格變小卡清單、查詢列變搜尋框＋篩選、按鈕滿版、明細欄位改為左標籤右內容。
- 前台 `hero` 的 `art`：`false`（不畫）、插圖種類字串，或 `{kind, …}`（例如 `{"kind": "phone", "screen": "map", "title": …, "items": […], "button": …}`）；沒寫時畫 `preview` 預覽卡（內容取 `hero › preview`）。
- `table` 另可加 `actions`（標題列右側按鈕，最後一個為主按鈕）、`row_actions`（每列操作連結）、`pager`（分頁列，可寫「共 128 筆」）；欄名含「狀態／結果／審核／進度」或值像狀態（已核准、待審核、異常…）時自動畫成彩色標籤。
- `form`／`filters` 欄位：`"名稱*"` 表示必填；也可寫 `[標籤, 提示, 型態]` 或 `{label, type, help, options}`，型態有 `text`、`select`、`date`、`textarea`、`upload`、`radio`、`checkbox`，沒寫時依欄位名稱推測（例如含「日期」→ 日期、含「狀態／類型／場站」→ 下拉、含「說明／備註」→ 多行、含「檔案／影本」→ 上傳）。
- 同一列的區塊可設 `flex` 調整寬度比例（例如表單 `2`、填寫說明 `1`）。
- 前台 `hero` 可加 `search`（搜尋框提示字）、`cta`（按鈕）、`art`（右側插圖，見上方說明）。

- 文字超出寬度會截斷並提醒；內容超過預設高度時畫布自動加高、頁尾下移。
- 每個區塊包在 `<g data-block="<type>">`，之後局部修改可用 grep 定位。
- 頁面描述沒有的東西（插圖、特殊版面）產生後再局部補畫；新增或加高區塊時依 `workflow.md`「文字優先」以座標推算，必要時渲染單張預覽確認。
