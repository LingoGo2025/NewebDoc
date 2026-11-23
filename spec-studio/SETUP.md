# screen-spec-kit 安裝引導（給 AI 照著做）

你是協助使用者導入 screen-spec-kit 的 AI（Claude Code、Codex 或其他能執行指令的 AI 工具）。使用者通常是在一個空資料夾開啟你，貼上一段提示詞請你讀這份檔案。請照下列步驟進行。

## 進行方式

- 全程使用繁體中文（台灣用語）。使用者可能不是工程師：每一步開始前用一句話說明要做什麼，完成後用一句話回報結果，不要貼大段指令輸出。
- **問完就停下來等**：每次向使用者提問後，立刻結束這一輪回覆，等使用者回答才繼續。不可以替使用者假設答案、不可以先用預設值往下做、不可以在同一輪接著執行建立專案或起稿。
- **一律用文字提問，問題一次全部列出**：不要用 AI 工具內建的選單、提問卡或問卷網頁（Codex 的選單不穩定，會一出現就關閉）。同一輪要問的問題放在**同一則訊息**裡全部列出，請使用者**一次回答**；不要拆成好幾則、不要一題一題問。
  - 每題加編號（1、2、3…）。有固定選項的題目把選項列在題目下方，用 A、B、C 標示；第一個選項是你的建議，標「（建議）」並寫一句理由；最後註明「也可以直接描述」。
  - 沒有固定選項的題目（專案名稱、主題）附一個範例答案。
  - 訊息最後寫出回答方式，例如：「請一次回覆，例如：1. 停車場繳費平台　2. 給車主線上繳月租…　3A　4A」，有建議答案時加上「也可以回『全部照建議』，或只寫要改的題號」。
  - 使用者漏答的題目：有建議的照建議，沒有建議的標「待確認」，不要為了漏答再問一輪（專案名稱與主題除外）。
- **不要自己安裝軟體**（不要用 winget、Homebrew、安裝程式或 sudo）。軟體一律由使用者自己執行「安裝腳本」安裝：它下載免安裝版 Python 與 PlantUML 到家目錄的 `NewebDoc/env`，不需要系統管理員權限，也不受 AI 工具沙盒的限制。
- 不要修改工具組（`~/NewebDoc/spec-studio`）裡的檔案。
- 中途需要重開 AI 工具時，告訴使用者：重開後在同一個資料夾貼上同一段提示詞，你會從尚未完成的步驟接續（每一步都先檢查是否已完成）。

### 路徑與指令

| | macOS | Windows |
|---|---|---|
| 工具組 | `~/NewebDoc/spec-studio` | `%USERPROFILE%\NewebDoc\spec-studio` |
| 安裝腳本的軟體 | `~/NewebDoc/env/bin` | `%USERPROFILE%\NewebDoc\env\bin`、`env\python` |
| Python 指令 | 依序試 `python3`、`~/NewebDoc/env/bin/python3` | 依序試 `%USERPROFILE%\NewebDoc\env\python\python.exe`、`python` |
| PlantUML 指令 | `plantuml`，找不到用 `~/NewebDoc/env/bin/plantuml` | `plantuml`，找不到用 `%USERPROFILE%\NewebDoc\env\bin\plantuml.cmd` |

剛跑完安裝腳本時，AI 工具的終端機還沒讀到新的 PATH：**直接用上表的完整路徑**，不必重開。以下指令寫 `python3` 的地方，換成你找到的 Python。Windows 上執行 Python 前先設 `$env:PYTHONUTF8=1`（PowerShell），避免中文編碼錯誤。

### 安裝腳本（請使用者自己執行）

- **Windows**：在 PowerShell 貼上（開始選單搜尋「PowerShell」，不需要系統管理員）：

```powershell
[Net.ServicePointManager]::SecurityProtocol=3072; $w=New-Object Net.WebClient; $w.Encoding=[Text.Encoding]::UTF8; iex $w.DownloadString('https://lingogo2025.github.io/NewebDoc/spec-studio/setup-windows.ps1')
```

- **macOS**：在「終端機」App 貼上：

```bash
curl -fsSL https://lingogo2025.github.io/NewebDoc/spec-studio/setup-mac.sh | bash
```

腳本可重複執行，已裝好的會略過；最後一行是「完成！」就表示環境就緒。

## 步驟 1：確認系統與目前資料夾

1. 判斷作業系統（macOS 或 Windows）與目前資料夾路徑。
2. 看目前資料夾是不是空的，記下來，步驟 3 會用到。
   - 整個流程的第一個問題一定是步驟 3 的「四件事」（含模式）；環境還沒就緒時，先處理步驟 2，再問四件事。
3. 如果目前資料夾已經是畫面規格專案（有 `project.json` 與 `規範/`），使用者要的多半是修改或接續：跳到文末「其他情況」。**不要在一個既有專案的資料夾（或它的子資料夾）裡建立新專案**；使用者要建新專案時，請他另開一個空資料夾再開啟 AI。

## 步驟 2：確認環境

1. **先和 GitHub 比對版本（一定要做，不能只看本機）**：執行

```bash
python3 ~/NewebDoc/spec-studio/tools/update_kit.py
```

   （Windows：`& "$env:USERPROFILE\NewebDoc\env\python\python.exe" "$env:USERPROFILE\NewebDoc\spec-studio\tools\update_kit.py"`）。它直接連 GitHub 讀最新版號，本機較舊就自動下載更新（只下載工具組的文字檔，不安裝軟體）。看最後一行「版本｜本機 …、GitHub …：…」：
   - **已是最新／已更新到最新／本機較新** → 繼續第 2 點。剛更新過、而你讀的是更新前的 `SETUP.md` 時，重新讀一次本機的 `SETUP.md` 再繼續。
   - **GitHub 無法連線**（結束代碼 3）→ 多半是 AI 工具的沙盒擋住網路。**用允許連網的權限重新執行同一個指令**：Codex 請以「需要提升權限（在沙盒外執行）」的方式重跑，畫面會跳出核准，告訴使用者按「允許」；Claude Code 會詢問是否允許網路，請使用者同意。
   - 提升權限後仍無法連線，或這個 AI 工具不能提升權限 → 請使用者在自己的 PowerShell／終端機執行上方「安裝腳本」那一行（它會把工具組更新到最新版），跑完告訴你，你再執行一次本指令確認。使用者的網路本身連不到 GitHub（例如公司網路擋住）時，經使用者同意後以本機版本繼續，回報時註明「未與 GitHub 比對」。
   - **不要用網頁搜尋、網頁讀取工具或其他網址來判斷版本**：它們常是快取或已刪除的舊版。版本一律以本指令的輸出為準；`SETUP.md` 也以本機那份為準（網址版只在本機還沒有工具組時，用來取得安裝腳本）。
   - 沒有 `update_kit.py`（工具組不存在）→ 請使用者執行安裝腳本，跑完再回到本點。
   - 工具組只認上表的位置（`~/NewebDoc/spec-studio`）；家目錄 `NewebDoc` 裡其他名稱的資料夾是舊版，不要使用。
   - 回報時說明本機與 GitHub 的版本。**不要用舊版工具組建立專案**：舊版缺少新功能，結果會不完整。
   - 使用者覺得每次核准很麻煩時，可以告訴他選用的設定（由他自己決定、自己修改）：在 `~/.codex/config.toml` 加上 `[sandbox_workspace_write]` 與 `network_access = true`，讓 Codex 在沙盒內可以連網（部分 macOS 版本的 Codex 可能不生效，那時照上面的核准方式即可）。不要替使用者修改這個設定，也不要建議關閉沙盒。
2. 依上表找 Python，執行環境檢查：

```bash
python3 ~/NewebDoc/spec-studio/tools/doctor.py
```

3. 最後一行是「環境：全部就緒」→ 進行步驟 3。顯示「環境：工具組需要更新」時，回到第 1 點更新。
4. 找不到 Python、找不到工具組，或檢查結果有「缺少」→ 把上面「安裝腳本」中這台電腦用的那一行給使用者，請他自己在 PowerShell／終端機執行，跑完告訴你；之後回到本步驟第 1 點重新檢查（用完整路徑，不必重開 AI 工具）。
5. 使用者執行腳本後仍失敗，把腳本最後的錯誤訊息整理給使用者，不要改用其他方式自行安裝。

## 步驟 3：建立專案並選模式

1. **用一則訊息列出四題**（格式見上方「進行方式」），問完就結束這一輪，等使用者一次回答：
   1. **專案名稱**（例如「停車場繳費平台」）
   2. **主題**：用幾句話描述這個系統給誰用、做什麼；越具體，第一版越準。
   3. **專案位置**：A. 放在目前資料夾〈路徑〉（目前資料夾是空的時為建議）　B. 在目前資料夾裡新建以專案名稱命名的子資料夾（不是空的時為建議）　C. 其他路徑（請寫出）
   4. **建立模式**：A. 全自動（建議）：再一次列出最多 10 題，你一次回答後直接產出 12 個階段的第一版，推測內容標「AI 起稿」，之後再一起審閱　B. 階段式：12 個階段逐階段問，每階段確認後才寫入
2. 使用者只回答部分題目時：位置、模式沒答就用建議；名稱或主題沒答，只補問缺的那幾題。
3. **使用者回答這四題之前，不要開始第 1 階段的訪談，也不要建立專案。** 使用者說「你決定」或沒答模式，就用全自動。
4. 建立專案（`<資料夾>` 用絕對路徑；位置選「新建子資料夾」時，用目前資料夾加上專案名稱）：

```bash
python3 ~/NewebDoc/spec-studio/tools/init_project.py "<資料夾>" --name "<專案名稱>"
```

5. 輸出中的 `check.py：OK…` 應為錯誤 0，最後一行是「下一步」提醒。有錯誤時把訊息告訴使用者，不要自行修改工具組。

## 步驟 4：依模式進行

1. 之後的工作都在專案資料夾內進行。先讀專案的入口檔 `AGENTS.md`，再依它的指示讀 `規範/README.md`、`規範/新專案.md`、`專案規則.md` 與 `project.json`。
2. **全自動**：依 `規範/新專案.md` 第 3 步。一次問完最多 10 題、每題第一個選項標「（AI 建議）」並附一句理由，**用一則文字訊息全部列出，請使用者一次回答**（格式見上方「進行方式」；告訴使用者可以回「全部照建議」，或只寫要改的題號），**問完就結束這一輪，等使用者回答**；使用者回答後**不再提問**，寫起稿描述（格式見 `python3 scripts/draft_apply.py --example`），執行 `python3 scripts/draft_apply.py <描述.json> --check` 與 `python3 scripts/draft_apply.py <描述.json>`。完成後回報結果，請使用者打開 `index.html` 看，再問要不要逐階段審閱。
3. **階段式**：依 `規範/新專案.md` 第 4 步，從第 1 階段開始逐階段問；每個階段的問題一樣用一則訊息全部列出，使用者一次回答。
4. 隨時可執行 `python3 scripts/interview_status.py` 看進度（未完成、待審閱、完成）。剛建立的專案它會提醒「先確認模式」；模式已選定就照選定的模式繼續。
5. 規範裡的 `plantuml -tsvg …` 指令，PlantUML 不在 PATH 時改用上表的完整路徑。
6. 如果專案建在子資料夾，告訴使用者：之後要在那個資料夾開啟 AI，AI 才會自動讀到專案的入口檔；接續時說「先跑 interview_status.py，從下一個待審閱或未完成的階段繼續」即可。

## 其他情況

- **接續訪談**：目前資料夾已是專案，`interview_status.py` 顯示還有未完成階段 → 從下一個未完成的階段繼續。
- **修改既有專案**：目前資料夾已是專案 → 依專案入口檔與 `規範/修改專案.md` 進行，不要建立新專案。
- **升級既有專案**：專案的 `check.py` 提醒工具組有新版，或使用者要求更新 → 先更新工具組 `python3 ~/NewebDoc/spec-studio/tools/update_kit.py`（被沙盒擋住時同步驟 2 第 1 點：以允許連網的權限重跑，仍不行請使用者執行安裝腳本），再執行 `python3 ~/NewebDoc/spec-studio/tools/upgrade_project.py "<專案資料夾>" --dry-run`，把會變更的檔案告訴使用者，同意後去掉 `--dry-run` 正式升級。
- **Claude Code plugin**：不需要安裝也能完整使用。只有使用者要求時才安裝（`claude plugin marketplace add ~/NewebDoc/spec-studio`，再 `claude plugin install screen-spec-kit@screen-spec-kit`）；工具組裡沒有 `.claude-plugin/` 資料夾時無法安裝，告訴使用者請維護者補上傳。
