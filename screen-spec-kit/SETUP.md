# screen-spec-kit 安裝引導（給 AI 照著做）

你是協助使用者導入 screen-spec-kit 的 AI（Claude Code、Codex 或其他能執行指令的 AI 工具）。使用者通常是在一個空資料夾開啟你，貼上一段提示詞請你讀這份檔案。請照下列步驟進行。

## 進行方式

- 全程使用繁體中文（台灣用語）。使用者可能不是工程師：每一步開始前用一句話說明要做什麼，完成後用一句話回報結果，不要貼大段指令輸出。
- **不要自己安裝軟體**（不要用 winget、Homebrew、安裝程式或 sudo）。軟體一律由使用者自己執行「安裝腳本」安裝：它下載免安裝版 Python 與 PlantUML 到家目錄的 `NewebDoc/env`，不需要系統管理員權限，也不受 AI 工具沙盒的限制。
- 不要修改工具組（`~/NewebDoc/screen-spec-kit`）裡的檔案。
- 中途需要重開 AI 工具時，告訴使用者：重開後在同一個資料夾貼上同一段提示詞，你會從尚未完成的步驟接續（每一步都先檢查是否已完成）。

### 路徑與指令

| | macOS | Windows |
|---|---|---|
| 工具組 | `~/NewebDoc/screen-spec-kit` | `%USERPROFILE%\NewebDoc\screen-spec-kit` |
| 安裝腳本的軟體 | `~/NewebDoc/env/bin` | `%USERPROFILE%\NewebDoc\env\bin`、`env\python` |
| Python 指令 | 依序試 `python3`、`~/NewebDoc/env/bin/python3` | 依序試 `%USERPROFILE%\NewebDoc\env\python\python.exe`、`python` |
| PlantUML 指令 | `plantuml`，找不到用 `~/NewebDoc/env/bin/plantuml` | `plantuml`，找不到用 `%USERPROFILE%\NewebDoc\env\bin\plantuml.cmd` |

剛跑完安裝腳本時，AI 工具的終端機還沒讀到新的 PATH：**直接用上表的完整路徑**，不必重開。以下指令寫 `python3` 的地方，換成你找到的 Python。Windows 上執行 Python 前先設 `$env:PYTHONUTF8=1`（PowerShell），避免中文編碼錯誤。

### 安裝腳本（請使用者自己執行）

- **Windows**：在 PowerShell 貼上（開始選單搜尋「PowerShell」，不需要系統管理員）：

```powershell
[Net.ServicePointManager]::SecurityProtocol=3072; $w=New-Object Net.WebClient; $w.Encoding=[Text.Encoding]::UTF8; iex $w.DownloadString('https://lingogo2025.github.io/NewebDoc/screen-spec-kit/setup-windows.ps1')
```

- **macOS**：在「終端機」App 貼上：

```bash
curl -fsSL https://lingogo2025.github.io/NewebDoc/screen-spec-kit/setup-mac.sh | bash
```

腳本可重複執行，已裝好的會略過；最後一行是「完成！」就表示環境就緒。

## 步驟 1：確認系統與目前資料夾

1. 判斷作業系統（macOS 或 Windows）與目前資料夾路徑。
2. 看目前資料夾是不是空的，記下來，步驟 3 會用到。
3. 如果目前資料夾已經是畫面規格專案（有 `project.json` 與 `規範/`），使用者要的多半是修改或接續：跳到文末「其他情況」。

## 步驟 2：確認環境

1. 依上表找 Python，執行環境檢查：

```bash
python3 ~/NewebDoc/screen-spec-kit/tools/doctor.py
```

2. 最後一行是「環境：全部就緒」→ 進行步驟 3。
3. 找不到 Python、找不到工具組，或檢查結果有「缺少」→ 把上面「安裝腳本」中這台電腦用的那一行給使用者，請他自己在 PowerShell／終端機執行，跑完告訴你；之後回到本步驟第 1 點重新檢查（用完整路徑，不必重開 AI 工具）。
4. 使用者執行腳本後仍失敗，把腳本最後的錯誤訊息整理給使用者，不要改用其他方式自行安裝。

## 步驟 3：建立專案

1. 問使用者兩件事，一次問完：
   - **專案名稱**（例如「活動報名平台」），以及一句話說明這個系統做什麼（不知道也沒關係，訪談時會再問）。
   - **專案放哪裡**：目前資料夾是空的，就建議直接放在目前資料夾；不是空的，就建議在目前資料夾裡新建一個以專案名稱命名的子資料夾。
2. 建立專案（`<資料夾>` 用絕對路徑）：

```bash
python3 ~/NewebDoc/screen-spec-kit/tools/init_project.py "<資料夾>" --name "<專案名稱>"
```

3. 最後一行應為 `check.py：OK…` 且錯誤 0。有錯誤時把訊息告訴使用者，不要自行修改工具組。

## 步驟 4：開始訪談

1. 之後的工作都在專案資料夾內進行。先讀專案的入口檔 `AGENTS.md`，再依它的指示讀 `規範/README.md`、`規範/新專案.md`、`專案規則.md` 與 `project.json`。
2. 執行 `python3 scripts/interview_status.py` 確認進度，從第 1 階段開始，依 `規範/新專案.md` 逐階段訪談使用者並填入內容。
3. 規範裡的 `plantuml -tsvg …` 指令，PlantUML 不在 PATH 時改用上表的完整路徑。
4. 如果專案建在子資料夾，告訴使用者：之後要在那個資料夾開啟 AI，AI 才會自動讀到專案的入口檔；接續訪談時說「先跑 interview_status.py，從下一個未完成的階段繼續」即可。

## 其他情況

- **接續訪談**：目前資料夾已是專案，`interview_status.py` 顯示還有未完成階段 → 從下一個未完成的階段繼續。
- **修改既有專案**：目前資料夾已是專案 → 依專案入口檔與 `規範/修改專案.md` 進行，不要建立新專案。
- **升級既有專案**：專案的 `check.py` 提醒工具組有新版，或使用者要求更新 → 先更新工具組 `python3 ~/NewebDoc/screen-spec-kit/tools/update_kit.py`，再執行 `python3 ~/NewebDoc/screen-spec-kit/tools/upgrade_project.py "<專案資料夾>" --dry-run`，把會變更的檔案告訴使用者，同意後去掉 `--dry-run` 正式升級。
- **Claude Code plugin**：不需要安裝也能完整使用。只有使用者要求時才安裝（`claude plugin marketplace add ~/NewebDoc/screen-spec-kit`，再 `claude plugin install screen-spec-kit@screen-spec-kit`）；工具組裡沒有 `.claude-plugin/` 資料夾時無法安裝，告訴使用者請維護者補上傳。
