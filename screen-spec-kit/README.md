# screen-spec-kit

畫面規格與示意圖工具組。以 Markdown 規格為基準，維護頁面 SVG、網站地圖、跨頁流程（PlantUML）、系統架構圖與 index.html 燈箱。

**不綁定 AI**：設計規範是一般 Markdown（`規範/`），每個專案各有一份複本；專案的 `AGENTS.md`、`CLAUDE.md`、`GEMINI.md`、`.github/copilot-instructions.md` 是內容相同的入口檔，只指向 `規範/`、`專案規則.md` 與 `project.json`，不寫規範。同一個專案可以換用不同的 AI 接續。Claude Code 另有 plugin 形式的 skill 入口（`skills/`）。

## 快速開始（給同事）

打開入門頁 https://lingogo2025.github.io/NewebDoc/PMSkill/，照著做：在空資料夾開啟 Claude Code 或 Codex，貼上這段提示詞：

```text
請幫我導入 screen-spec-kit 並建立新專案：先讀取 https://lingogo2025.github.io/NewebDoc/PMSkill/SETUP.md（可以用 curl 下載來讀），再照裡面的步驟一步一步做。
```

AI 會依 `SETUP.md`：把工具組下載到 `~/NewebDoc/PMSkill`、用 `tools/doctor.py` 檢查並安裝所需軟體（macOS 用 Homebrew、Windows 用 winget）、建立專案，然後開始訪談。

## 內容

| 路徑 | 用途 |
|---|---|
| `index.html` | 入門頁（GitHub Pages 首頁）：選 AI 工具、複製提示詞 |
| `SETUP.md` | 給 AI 照著做的安裝引導：取得工具組、檢查環境、建立專案、開始訪談 |
| `使用手冊.html` | 詳細使用手冊 |
| `規範/` | 共用設計規範（從示範專案匯出）：`README.md` 總覽、`修改專案.md`、`新專案.md`、`workflow.md`、`questioning.md`、`stages.md`、`spec-writing.md`、`flows.md`、`architecture.md`、`index-page.md`、`mockup.md` |
| `skills/spec-change/SKILL.md` | Claude 入口：修改既有專案 → 讀專案的 `規範/` |
| `skills/spec-new/SKILL.md` | Claude 入口：從零建立新專案 → 讀 `規範/新專案.md` |
| `engine/scripts/` | 引擎：同步與檢查工具、SVG 元件庫 `mockup.py`、入口檔產生 `ai_entry.py`（建立或升級專案時複製到專案 `scripts/`） |
| `engine/index.template.html` | 引擎：index.html 範本（樣式、燈箱、流程位置、完整度；內容區為通用骨架） |
| `template/` | 空白專案骨架：`project.json`、`專案規則.md`、規格、網站地圖、架構圖骨架 |
| `tools/doctor.py` | 環境檢查：列出缺少的軟體與這台電腦的安裝指令；`--install-plantuml` 下載官方 PlantUML（Windows 用） |
| `tools/init_project.py` | 建立空白專案 |
| `tools/upgrade_project.py` | 把專案的引擎與 `規範/` 升級到目前 plugin 版本 |
| `tools/sync_kit.py` | 示範專案 → plugin 一鍵同步（檢查、匯出引擎與規範、升版、自我測試） |
| `tools/build_engine.py` | 只匯出（`sync_kit.py` 內部使用） |

專案端：
- **入口檔**：`AGENTS.md`、`CLAUDE.md`、`GEMINI.md`、`.github/copilot-instructions.md`，由 `scripts/ai_entry.py` 產生，內容相同。
- **規範與規則**：`規範/`（共用規範複本）、`專案規則.md`（專案專屬規則）。
- **設定與引擎**：`project.json`（專案設定，含 `engine_version`、`kit`）、`scripts/`（引擎複本）、`index.html`（引擎＋內容區）。

## 取得與更新

工具組公開放在 GitHub repo `lingogo2025/NewebDoc` 的 `PMSkill/` 資料夾（入門頁 https://lingogo2025.github.io/NewebDoc/PMSkill/）。這個 repo 還有其他大型資料夾，所以**只部分下載 `PMSkill/`**，放在家目錄 `~/NewebDoc/PMSkill`（Windows 為 `%USERPROFILE%\NewebDoc\PMSkill`），所有專案共用；專案的 `project.json › kit.path` 會記成 `~/NewebDoc/PMSkill`，換到同事電腦也找得到：

```bash
git clone --filter=blob:none --sparse https://github.com/lingogo2025/NewebDoc.git ~/NewebDoc
```

```bash
git -C ~/NewebDoc sparse-checkout set PMSkill
```

之後取得新版，再以「升級既有專案」的指令更新各專案：

```bash
git -C ~/NewebDoc pull
```

## 建立新專案

```bash
python3 tools/init_project.py "<新資料夾>" --name "<專案名稱>"
```

建立後 `check.py` 應為 0 錯誤；接著依 `規範/新專案.md` 逐階段訪談填入內容（任何 AI 從專案入口檔開始即可；Claude 也可用 `spec-new` skill）（`python3 scripts/interview_status.py` 看進度，中斷後可接續）。

## 升級既有專案

```bash
python3 tools/upgrade_project.py "<專案資料夾>" --dry-run
```

```bash
python3 tools/upgrade_project.py "<專案資料夾>"
```

升級前自動備份到 `<專案>/.engine_backup/`；只換 `scripts/`、`規範/` 與 index.html 的引擎部分，並重產入口檔（舊版專案的 `AGENTS.md` 會改名為 `專案規則.md`），保留內容區（`<!-- [slot:…] -->`）與產生區（網站地圖、專案設定、流程資料），Markdown、SVG、流程、架構圖都不動。

## 維護（示範專案 → plugin）

捐款平台專案是示範專案，也是引擎來源（`project.json › kit.engine_source`），還會持續調整；plugin 跟著改：

- **引擎與共用規範**（`scripts/`、`規範/`、index.html 內容區以外）：在示範專案改，`check.py` 會提醒與 plugin 不同，然後執行

```bash
python3 tools/sync_kit.py "../捐款平台_全頁面示意圖"
```

  會先跑示範專案的 `check.py`（有錯就停止）、匯出引擎與 `規範/`、版本加一、同步示範專案的 `engine_version`，並在暫存資料夾建空白專案自我測試。
- **範本**（`template/`）：直接改 plugin 的檔案，再執行 `sync_kit.py … --bump` 升版與自我測試。
- plugin 的 `規範/` 是匯出的複本，不要直接改（下次同步會被覆蓋）。
- 每次升版在下方「更新紀錄」寫一行，然後把本資料夾的內容手動上傳到 GitHub 的 `NewebDoc/PMSkill/`（不要上傳 `.DS_Store`、`.bin/`、`__pycache__/`），同事 `git pull` 就拿到新版。其他專案的 `check.py` 會提醒 plugin 有新版，以 `upgrade_project.py` 升級。
- 規則歸屬（哪些帶回 plugin、哪些留在專案）見 `規範/修改專案.md`「示範專案與 plugin 同步」。
- 新增功能時加 `--minor` 升次版號（例如 0.6.1 → 0.7.0）。
- 入門頁 `index.html` 由 `NewebDoc` 的 GitHub Pages 發布。頁面內一律用相對路徑（`SETUP.md`、`使用手冊.html`）；提示詞裡的 `SETUP.md` 網址由頁面依所在位置自動換成完整網址，搬移位置不用改頁面。`SETUP.md`、README、使用手冊裡的 GitHub 下載指令（`lingogo2025/NewebDoc`）則要一起改。

index.html 的內容區有 9 個：`title`、`project-css`、`hero`、`architecture`、`cards`、`external-intro`、`migration`、`regulations`、`footer`（定義在 `tools/slots.py`）。

## Claude Code 安裝（選用）

不安裝也能用：任何 AI 從專案的入口檔開始，就會讀到專案內的 `規範/`。安裝後 Claude Code 會多兩個 skill 入口（`spec-change`、`spec-new`）。

先依「取得與更新」下載工具組，再從本機資料夾安裝：

```bash
claude plugin marketplace add ~/NewebDoc/PMSkill
```

```bash
claude plugin install screen-spec-kit@screen-spec-kit
```

工具組 `git pull` 後，以 `claude plugin marketplace update screen-spec-kit` 更新 plugin。

使用手冊（給同事看的 HTML）：`使用手冊.html`。

## 規劃

目標：之後的案子性質各不相同，但產出的網頁功能（網站地圖、燈箱、流程位置、完整度等）與設計規範一致。分三層：

- **引擎**（每案相同，放 plugin）：`scripts/`、index.html 外殼（樣式、燈箱、流程位置、完整度）。
- **規範**（共用＋每案填空）：`spec-change` skill（通用）＋每案 `AGENTS.md` 骨架與 `project.json`（訪談填入）。
- **內容**（每案不同）：規格、網站地圖、SVG、流程、架構圖。

已定案（2026-11-21）：

| 項目 | 決定 |
|---|---|
| 引擎放法 | 初始化時複製進案子並標版本號，另有升級指令；未安裝 plugin 也能用 |
| 網站地圖 | index.html 網站地圖區塊由 `網站地圖.md`＋`project.json` 自動產生 |
| 首頁結構 | 固定區塊（系統架構、網站地圖、外部系統串接、舊系統移轉、相關法規、完整度）＋選用說明卡位置 |
| 視覺 | 版型、字型、元件形狀共用；主色與 Logo 由 `project.json` 主題設定，訪談第 1 階段詢問 |
| 捐款平台 | 搬到新引擎當第一個驗證案（改前備份，重產結果與現版逐字一致） |
| SVG | 從捐款平台現有畫面抽元件範本，AI 依規格組合 |
| 試跑 | 第 5 步以假的預約／報名系統從頭試跑，放暫存目錄 |

步驟：

1. ✅ 專案設定抽到 `project.json`
2. ✅ 通用規範與專案規則拆開，`spec-change` skill
3. 範本與初始化
   - 3a ✅ index.html 拆成引擎與內容：`index_build.py` 由網站地圖產生網站地圖區塊與 `#project-config`，區域判斷改讀 `project.json`，以捐款平台驗證
   - 3b ✅ `template/` 空白專案骨架、`engine/`（工具＋index.html 範本）、`tools/` 初始化／升級／匯出引擎；index.html 加內容區標記；訪談補第 3 階段「業務規則與用語限制」
4. ✅ SVG 元件庫 `scripts/mockup.py`（頁面描述 JSON → SVG 初稿）＋`project.json › theme`／`mockup`／`brand`；主題色同時套用到頂部導覽與 index.html 主色
5. ✅ `spec-new` 訪談 skill（`references/stages.md`）、`interview_status.py`（訪談進度）、`page_stub.py`（頁面規格骨架）；以假的活動報名平台從頭跑完 12 階段，`check.py` 0 錯誤

## 更新紀錄

- 0.7.0（2026-11-21）：一段提示詞導入。新增入門頁 `index.html`（GitHub Pages）、給 AI 照做的 `SETUP.md`、環境檢查 `tools/doctor.py`（macOS／Windows／Linux 安裝指令、`--install-plantuml`）；工具組固定放 `~/NewebDoc/PMSkill`（GitHub `lingogo2025/NewebDoc` 的 `PMSkill/`，部分下載），`init_project.py` 的 `kit.path` 改記 `~/…`，`check.py` 支援 `~`；Windows 相容：引擎與工具一律以 UTF-8 輸出、子程序設 `PYTHONUTF8`，`plantuml` 以完整路徑執行（支援 `plantuml.cmd`）；`sync_kit.py` 新增 `--minor`，升版後重產入口檔。
- 0.6.1（2026-11-21）：準備發布到 GitHub。新增 `.gitignore`；marketplace 名稱由 `screen-spec-kit-local` 改為 `screen-spec-kit`（安裝指令改為 `screen-spec-kit@screen-spec-kit`）；README 與使用手冊補上 clone、pull 與從 GitHub 安裝 plugin 的方式，維護流程加上 commit／push。
- 0.6.0（2026-11-21）：規範不綁定 AI。共用規範從 `skills/*/references/` 移到中立的 `規範/`（示範專案為來源，複製進每個專案）；`skills/` 只剩入口；專案規則改放 `專案規則.md`；新增 `scripts/ai_entry.py` 產生內容相同的 `AGENTS.md`、`CLAUDE.md`、`GEMINI.md`、`.github/copilot-instructions.md`，`check.py` 第 16 項檢查；建立、升級、同步工具都處理 `規範/`，升級會把舊版 `AGENTS.md` 改名為 `專案規則.md`。
- 0.5.1（2026-11-21）：示範專案與 plugin 同步機制。新增 `tools/sync_kit.py`（檢查、匯出引擎、自動升版、空白專案自我測試；`--bump` 用於只改規則或範本時）；`project.json` 新增 `kit`（plugin 位置；示範專案標 `engine_source`）；`check.py` 第 15 項：示範專案引擎與 plugin 不同時提醒同步，其他專案在 plugin 有新版時提醒升級；spec-change `SKILL.md` 新增「示範專案與 plugin 同步」（修改歸屬表）。
- 0.5.0（2026-11-21）：路線 5。新增 `spec-new` skill 與 `references/stages.md`；引擎新增 `interview_status.py`、`page_stub.py`；範本 12 個階段的位置統一放「〔待訪談第 n 階段〕」標記。以假的活動報名平台試跑全部階段，修正 3 個問題：跨階段標記改歸最後一個階段；訪談第 6 階段前頁面未歸模組改為提醒；`flow_sync.py` 在 PUML 缺 `title` 行時依 `@title` 補上（否則單頁流程沒有圖例）。
- 0.4.0（2026-11-21）：路線 4。新增 `scripts/mockup.py` 元件庫（10 種區塊、後台與前台兩種版型、自動排版與加高、文字截斷提醒）與 `references/mockup.md`；`project.json` 新增 `theme`、`mockup`、`brand`；`nav.py` 頂部導覽與 index.html 主色（`#project-theme`）改讀 `theme`；表格區塊高度修正（舊產生器最後一列會超出卡片 7px）；訪談第 1、4 階段補問品牌主色與各區版型。
- 0.3.0（2026-11-21）：路線 3b。新增 `engine/`（自捐款平台匯出的 11 個工具與 index.html 範本）、`template/` 空白專案、`tools/`（`init_project.py`、`upgrade_project.py`、`build_engine.py`、`slots.py`）；index.html 分引擎、內容區、產生區，折疊區塊編號改由 `index_build.py` 自動產生；`questioning.md` 新增第 3 階段「業務規則與用語限制」（共 12 階段）；SKILL.md、`workflow.md`、`index-page.md` 補引擎與內容區規則。
- 0.2.0（2026-11-21）：路線 3a。`references/workflow.md` 新增「網站地圖寫法」與 `index_build.py` 工具說明；SKILL.md 收尾清單與不可做清單、`index-page.md` 燈箱區域判斷與文件責任同步更新；README 寫入三層架構與定案決定。
- 0.1.2（2026-11-21）：`questioning.md` 第 3 節訪談階段由 8 個擴為 11 個，補上業務模組（功能架構圖）、對外 API、全站共用規則三個缺口，並加「網頁呈現」欄對照首頁區塊與燈箱；`index-page.md` 新增首頁區塊時須同步確認有階段會問到。
- 0.1.1（2026-11-21）：新增 `references/questioning.md` 提問規則（通用原則 9 條、修改時的四種問題與提問順序、新專案訪談 8 階段）；SKILL.md 標準流程第 2 步與對照表、`workflow.md` 第 2 步改為引用它。
- 0.1.0（2026-11-21）：建立 plugin 與 `spec-change` skill，通用規則從捐款平台專案 AGENTS.md 拆出。
