# 新頁面 SVG 初稿：元件組合（通用）

新增頁面時，以 `scripts/mockup.py` 依頁面描述（JSON）組合元件產生 SVG 初稿；之後的修改一律局部編輯 SVG，不重跑工具覆蓋。

## 流程

1. 規格與網站地圖已確定該頁 ID、名稱、所屬區域（訪談第 4、5 階段完成）。
2. 寫頁面描述 JSON（放暫存目錄，不進專案）；`python3 scripts/mockup.py --example backend`（或 `public`）可印範例。
3. `python3 scripts/mockup.py <描述.json>` 產生 `screens/<ID>_<名稱>.svg`；檔案已存在時不覆蓋（確定是沒調整過的初稿才加 `--force`）。
4. 依提示完成：規格加該頁段落（含「**畫面文字（依 SVG 順序）**」）→ `sync_screen_text.py <ID>` → 網站地圖加按鈕 → `index_build.py` → `svg_bundle.py` → `check.py`。
5. 要看版面時用 `--out <暫存路徑>` 產生，再以 `rsvg-convert -w 800` 轉縮小預覽（只放暫存目錄）。

## 版型與配色來源（project.json）

| 設定 | 用途 |
|---|---|
| `theme` | 品牌配色：`primary`（強調、數字、主要按鈕）、`primary_dark`、`primary_soft`（標籤底、步驟圓點）、`sidebar`、`page_bg`、`surface`、`ink`、`heading`、`text`、`muted`、`border`、`nav_text`、`nav_active`、`font`；`theme › regions › <column>` 覆寫某區（例如後台改橘色） |
| `mockup › <column>` | 各區版型：`layout`（`backend` 1600×1080 左側欄／`public` 1440×1000 頂部導覽）、`nav`（共用選單 key）、側欄 `label`／`sublabel`／`identity`、頁首 `account`、`badge`、前台 `brand`／`nav_items`／`buttons`／`header_note`、`footer` |
| `brand` | 正式標誌 `logo`（`assets/` 內 SVG，內嵌為 `data-logo`）與文字名稱 `name` |

同一個 `theme` 也用在 `nav.py` 頂部導覽與 index.html 主色（`index_build.py` 產生 `#project-theme`）。

## 頁面描述

| 欄位 | 說明 |
|---|---|
| `id`、`name`、`desc` | 必填：頁面 ID、名稱（檔名與標題）、一句說明 |
| `region` | 選填：`regions › column`；預設依 `project.json › regions` 判斷 |
| `subtitle`、`badge`、`active`、`avatar` | 選填：標題下說明、右上區域標籤、選單反白項目、頭像字 |
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

- 文字超出寬度會截斷並提醒；內容超過預設高度時畫布自動加高、頁尾下移。
- 每個區塊包在 `<g data-block="<type>">`，之後局部修改可用 grep 定位。
- 頁面描述沒有的東西（插圖、特殊版面）產生後再局部補畫；新增或加高區塊時依 `workflow.md`「文字優先」以座標推算，必要時渲染單張預覽確認。
