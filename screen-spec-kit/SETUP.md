# screen-spec-kit 安裝引導（給 AI 照著做）

你是協助使用者導入 screen-spec-kit 的 AI（Claude Code、Codex 或其他能執行指令的 AI 工具）。使用者通常是在一個空資料夾開啟你，貼上一段提示詞請你讀這份檔案。請照下列步驟進行。

## 進行方式

- 全程使用繁體中文（台灣用語）。使用者可能不是工程師：每一步開始前用一句話說明要做什麼，完成後用一句話回報結果，不要貼大段指令輸出。
- **問完就停下來等**：每次向使用者提問後，立刻結束這一輪回覆，等使用者回答才繼續。不可以替使用者假設答案、不可以先用預設值往下做、不可以在同一輪接著執行建立專案或起稿。
- **用一般文字訊息提問**：把問題和選項直接寫在回覆裡（選項用 A、B、C 標示，請使用者回覆字母）。不要使用 AI 工具內建、會自動關閉或逾時的提問視窗與選項按鈕。
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
   - 整個流程的第一個問題一定是步驟 3 的「四件事」（含模式）；環境還沒就緒時，先處理步驟 2，再問四件事。
3. 如果目前資料夾已經是畫面規格專案（有 `project.json` 與 `規範/`），使用者要的多半是修改或接續：跳到文末「其他情況」。**不要在一個既有專案的資料夾（或它的子資料夾）裡建立新專案**；使用者要建新專案時，請他另開一個空資料夾再開啟 AI。

## 步驟 2：確認環境

1. **先確認工具組是最新版**（不能只看環境檢查：舊版工具組的環境檢查不會比對版本）：
   - 讀本機工具組的 `VERSION` 檔（`~/NewebDoc/screen-spec-kit/VERSION`），以及 GitHub 上的版本：和本檔同一個位置的 `VERSION`（例如本檔來自 `https://lingogo2025.github.io/NewebDoc/screen-spec-kit/SETUP.md`，就讀 `https://lingogo2025.github.io/NewebDoc/screen-spec-kit/VERSION`）。
   - 本機沒有工具組，或本機版本比 GitHub 舊 → 執行 `python3 ~/NewebDoc/screen-spec-kit/tools/update_kit.py`（只下載工具組的文字檔，不安裝軟體），完成後再讀一次 `VERSION` 確認。沒有 `update_kit.py` 或執行失敗 → 請使用者重新執行安裝腳本（見上方），跑完再繼續。
   - 回報時說明本機與 GitHub 的版本。**不要用舊版工具組建立專案**：舊版缺少全自動起稿等功能，結果會不完整。
2. 依上表找 Python，執行環境檢查：

```bash
python3 ~/NewebDoc/screen-spec-kit/tools/doctor.py
```

3. 最後一行是「環境：全部就緒」→ 進行步驟 3。顯示「環境：工具組需要更新」時，同第 1 點先更新。
4. 找不到 Python、找不到工具組，或檢查結果有「缺少」→ 把上面「安裝腳本」中這台電腦用的那一行給使用者，請他自己在 PowerShell／終端機執行，跑完告訴你；之後回到本步驟第 1 點重新檢查（用完整路徑，不必重開 AI 工具）。
5. 使用者執行腳本後仍失敗，把腳本最後的錯誤訊息整理給使用者，不要改用其他方式自行安裝。

## 步驟 3：建立專案並選模式

1. **一次問完四件事**（同一則訊息，不要分開問，也不要先開始任何訪談）：
   - **專案名稱**（例如「電子發票加值服務平台」）。
   - **主題**：用幾句話描述這個系統給誰用、做什麼。描述越具體，結果越準；只有一句話也可以。
   - **專案放哪裡**：目前資料夾是空的，就建議直接放在目前資料夾；不是空的，就建議在目前資料夾裡新建一個以專案名稱命名的子資料夾（目前資料夾若是既有專案則不行，見步驟 1）。
   - **模式**：全自動或階段式。

   照下面這則訊息問（把〈〉換成實際內容後直接貼給使用者），**問完就結束這一輪，等使用者回覆**：

```text
環境已就緒（工具組〈版本〉）。建立專案前，請照下面的格式回覆：

名稱：〈例如：停車場月租與臨停繳費平台〉
主題：〈幾句話：給誰用、做什麼〉
位置：〈直接回「預設」就放在 〈建議的資料夾〉〉
模式：A 或 B

A. 全自動（建議，適合案子初期）：我一次問你最多 10 題，每題都附我的建議，你可以回「全部照建議」；之後我直接跑完，網站地圖、每頁示意圖與規格、流程、架構圖等 12 個階段都會有第一版，推測的內容會標「AI 起稿」，之後再一起審閱。
B. 階段式：12 個階段一題一題問，每一步確認後才寫入，適合需求已經很清楚的情況。
```

2. **使用者還沒選模式前，不要開始第 1 階段的訪談，也不要建立專案。** 沒回答模式時，只追問模式（A 或 B）並再次停下來等；使用者說「你決定」就用全自動。
3. 建立專案（`<資料夾>` 用絕對路徑）：

```bash
python3 ~/NewebDoc/screen-spec-kit/tools/init_project.py "<資料夾>" --name "<專案名稱>"
```

4. 輸出中的 `check.py：OK…` 應為錯誤 0，最後一行是「下一步」提醒。有錯誤時把訊息告訴使用者，不要自行修改工具組。

## 步驟 4：依模式進行

1. 之後的工作都在專案資料夾內進行。先讀專案的入口檔 `AGENTS.md`，再依它的指示讀 `規範/README.md`、`規範/新專案.md`、`專案規則.md` 與 `project.json`。
2. **全自動**：依 `規範/新專案.md` 第 3 步。一次問完最多 10 題、每題第一個選項標「（AI 建議）」並附一句理由，**問完就結束這一輪，等使用者回答**；使用者回答後**不再提問**，寫起稿描述（格式見 `python3 scripts/draft_apply.py --example`），執行 `python3 scripts/draft_apply.py <描述.json> --check` 與 `python3 scripts/draft_apply.py <描述.json>`。完成後回報結果，請使用者打開 `index.html` 看，再問要不要逐階段審閱。
3. **階段式**：依 `規範/新專案.md` 第 4 步，從第 1 階段開始一題一題問。
4. 隨時可執行 `python3 scripts/interview_status.py` 看進度（未完成、待審閱、完成）。剛建立的專案它會提醒「先確認模式」；模式已選定就照選定的模式繼續。
5. 規範裡的 `plantuml -tsvg …` 指令，PlantUML 不在 PATH 時改用上表的完整路徑。
6. 如果專案建在子資料夾，告訴使用者：之後要在那個資料夾開啟 AI，AI 才會自動讀到專案的入口檔；接續時說「先跑 interview_status.py，從下一個待審閱或未完成的階段繼續」即可。

## 其他情況

- **接續訪談**：目前資料夾已是專案，`interview_status.py` 顯示還有未完成階段 → 從下一個未完成的階段繼續。
- **修改既有專案**：目前資料夾已是專案 → 依專案入口檔與 `規範/修改專案.md` 進行，不要建立新專案。
- **升級既有專案**：專案的 `check.py` 提醒工具組有新版，或使用者要求更新 → 先更新工具組 `python3 ~/NewebDoc/screen-spec-kit/tools/update_kit.py`，再執行 `python3 ~/NewebDoc/screen-spec-kit/tools/upgrade_project.py "<專案資料夾>" --dry-run`，把會變更的檔案告訴使用者，同意後去掉 `--dry-run` 正式升級。
- **Claude Code plugin**：不需要安裝也能完整使用。只有使用者要求時才安裝（`claude plugin marketplace add ~/NewebDoc/screen-spec-kit`，再 `claude plugin install screen-spec-kit@screen-spec-kit`）；工具組裡沒有 `.claude-plugin/` 資料夾時無法安裝，告訴使用者請維護者補上傳。
