# screen-spec-kit 安裝引導（給 AI 照著做）

你是協助使用者導入 screen-spec-kit 的 AI（Claude Code、Codex 或其他能執行指令的 AI 工具）。使用者通常是在一個空資料夾開啟你，貼上一段提示詞請你讀這份檔案。請照下列步驟進行。

## 進行方式

- 全程使用繁體中文（台灣用語）。使用者可能不是工程師：每一步開始前用一句話說明要做什麼，完成後用一句話回報結果，不要貼大段指令輸出。
- 安裝軟體、修改 PATH 或環境變數前，先說明要裝什麼、為什麼；你的工具詢問權限時，請使用者按允許。
- **需要密碼的指令（安裝 Homebrew、`sudo`）不要代為輸入**：請使用者自己在「終端機」App（Windows 為 PowerShell）執行，完成後告訴你。
- Windows 上把本檔與工具訊息裡的 `python3` 換成 `python`（沒有時用 `py -3`）；路徑 `~/NewebDoc/PMSkill` 即 `%USERPROFILE%\NewebDoc\PMSkill`。
- 不要修改工具組（`~/NewebDoc/PMSkill`）裡的檔案；它由 Git 更新。
- 中途需要重開 AI 工具時（例如新裝的軟體還不在 PATH），告訴使用者：重開後在同一個資料夾貼上同一段提示詞，你會從尚未完成的步驟接續（每一步都先檢查是否已完成）。

## 步驟 1：確認系統與目前資料夾

1. 判斷作業系統（macOS、Windows 或 Linux）與目前資料夾路徑。
2. 看目前資料夾是不是空的，記下來，步驟 4 會用到。
3. 如果目前資料夾已經是畫面規格專案（有 `project.json` 與 `規範/`），使用者要的多半是修改或接續：跳到文末「其他情況」。

## 步驟 2：取得工具組

工具組放在 GitHub repo `lingogo2025/NewebDoc` 的 `PMSkill/` 資料夾。下載到家目錄的 `NewebDoc` 資料夾，**只取 `PMSkill/`**（這個 repo 還有其他大型資料夾，不要整個下載）；工具組位置是 `~/NewebDoc/PMSkill`，所有專案共用。以下稱「工具組資料夾」。

1. `~/NewebDoc` 已存在且是 Git repo：執行 `git -C ~/NewebDoc pull` 更新；如果裡面沒有 `PMSkill/`，再執行 `git -C ~/NewebDoc sparse-checkout add PMSkill`（不是部分下載的完整 clone 則不需要）。
2. 不存在：
   - 先確認有 Git（`git --version`，需 2.25 以上）。沒有時安裝：macOS 執行 `xcode-select --install`（會跳出視窗，請使用者按「安裝」並等它完成）；Windows 執行 `winget install --id Git.Git -e`，裝完可能要重開 AI 工具。
   - 部分下載（只取 `PMSkill/` 與 repo 根目錄的少數檔案）：

```bash
git clone --filter=blob:none --sparse https://github.com/lingogo2025/NewebDoc.git ~/NewebDoc
```

```bash
git -C ~/NewebDoc sparse-checkout set PMSkill
```

3. `~/NewebDoc` 已存在但不是 Git repo（例如解壓縮的資料夾）：不要覆蓋，問使用者要保留還是改名後重新下載。
4. 確認 `~/NewebDoc/PMSkill/tools/doctor.py` 存在。

## 步驟 3：檢查並安裝所需軟體

1. 在工具組資料夾執行環境檢查：

```bash
python3 tools/doctor.py
```

   沒有 Python 時先安裝：macOS 執行 `xcode-select --install` 或 `brew install python`；Windows 執行 `winget install --id Python.Python.3.12 -e`。

2. 依「缺少」那幾行附的指令逐一安裝，然後再執行一次 `doctor.py`，直到最後一行是「環境：全部就緒」。說明：
   - **macOS**：主要用 Homebrew，`brew install plantuml` 會一併裝好 Java 與 Graphviz。沒有 Homebrew 時，`doctor.py` 會印出安裝指令；這一步需要密碼，請使用者自己在「終端機」App 執行。
   - **Windows**：用 `winget` 安裝 Git、Python、Java、Graphviz；PlantUML 用 `python tools/doctor.py --install-plantuml` 下載官方版，再照它的提示把 `.bin` 資料夾加入 PATH。另外執行 `setx PYTHONUTF8 1`，避免中文編碼錯誤。Windows 上這些設定都要重開 AI 工具後才會生效。
   - 「選用」的軟體（`rsvg-convert`）缺少時可以略過。
3. 不要用線上 PlantUML 伺服器或其他會把圖檔原稿送到外部的方式代替本機 PlantUML。

## 步驟 4：建立專案

1. 問使用者兩件事，一次問完：
   - **專案名稱**（例如「活動報名平台」），以及一句話說明這個系統做什麼（不知道也沒關係，訪談時會再問）。
   - **專案放哪裡**：目前資料夾是空的，就建議直接放在目前資料夾；不是空的，就建議在目前資料夾裡新建一個以專案名稱命名的子資料夾。
2. 建立專案（`<資料夾>` 用絕對路徑；目前資料夾就用 `.` 的絕對路徑）：

```bash
python3 ~/NewebDoc/PMSkill/tools/init_project.py "<資料夾>" --name "<專案名稱>"
```

3. 最後一行應為 `check.py：OK…` 且錯誤 0。有錯誤時把訊息告訴使用者，不要自行修改工具組。

## 步驟 5：開始訪談

1. 之後的工作都在專案資料夾內進行。先讀專案的入口檔 `AGENTS.md`，再依它的指示讀 `規範/README.md`、`規範/新專案.md`、`專案規則.md` 與 `project.json`。
2. 執行 `python3 scripts/interview_status.py` 確認進度，從第 1 階段開始，依 `規範/新專案.md` 逐階段訪談使用者並填入內容。
3. 如果專案建在子資料夾，告訴使用者：之後要在那個資料夾開啟 AI，AI 才會自動讀到專案的入口檔；接續訪談時說「先跑 interview_status.py，從下一個未完成的階段繼續」即可。

## 其他情況

- **接續訪談**：目前資料夾已是專案，`interview_status.py` 顯示還有未完成階段 → 先確認工具組已更新，再從下一個未完成的階段繼續。
- **修改既有專案**：目前資料夾已是專案 → 依專案入口檔與 `規範/修改專案.md` 進行，不要建立新專案。
- **升級既有專案**：專案的 `check.py` 提醒工具組有新版 → 先執行 `git -C ~/NewebDoc pull`，再執行 `python3 ~/NewebDoc/PMSkill/tools/upgrade_project.py "<專案資料夾>" --dry-run`，把會變更的檔案告訴使用者，同意後去掉 `--dry-run` 正式升級。
- **Claude Code plugin**：不需要安裝也能完整使用。只有使用者要求時才安裝（`claude plugin marketplace add ~/NewebDoc/PMSkill`，再 `claude plugin install screen-spec-kit@screen-spec-kit`）。
