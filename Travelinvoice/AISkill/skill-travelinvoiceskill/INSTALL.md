# 安裝說明：TravelinvoiceSkill Skill

本壓縮檔包含一個 Claude Code 的 Agent Skill 與對應的 slash 指令。

## 放置位置

解壓後，將內容放到你的專案（或使用者家目錄）的 `.claude/` 下：

```
.claude/
├── skills/
│   └── travelinvoiceskill/        ← 將本包的「travelinvoiceskill/」整個資料夾放這裡
│       ├── SKILL.md
│       ├── guides/
│       ├── references.md
│       ├── api-manifest.json  ← 機器可讀 API 清單
│       └── test-vectors/   ← 加解密標準答案 + verify.php / verify.js
└── commands/             ← 將本包的「commands/」內 .md 放這裡
    ├── travelinvoiceskill-integrate.md
    ├── travelinvoiceskill-verify.md
    └── travelinvoiceskill-debug.md
```

## 使用（Claude Code）

- Skill 會依其 `description` 在相關需求時自動載入；也可直接叫 Claude「使用 travelinvoiceskill skill」。
- slash 指令：`/travelinvoiceskill-integrate`（串接）、`/travelinvoiceskill-verify`（驗證加解密）、`/travelinvoiceskill-debug`（除錯）。
- 驗證答案鑰匙可重現：`php travelinvoiceskill/test-vectors/verify.php` 或 `node travelinvoiceskill/test-vectors/verify.js`。

## 其他 AI 開發工具（Codex / Cursor / Copilot…）

本包同時附了幾個「工具入口檔」，它們都指向**同一份** `travelinvoiceskill/guides/` 與 `travelinvoiceskill/test-vectors/`。
使用方式：把 `travelinvoiceskill/` 這個資料夾放到你的**專案根目錄**，再依你用的工具放對應的入口檔：

| 工具 | 入口檔（放到專案的位置） |
|------|--------------------------|
| OpenAI Codex / Cursor / Zed 等 | `AGENTS.md`（專案根目錄） |
| GitHub Copilot（VS Code Copilot Chat／Visual Studio／Copilot CLI 共用） | `.github/copilot-instructions.md` |
| Cursor（原生規則） | `.cursor/rules/travelinvoiceskill.mdc` |
| Google Gemini CLI | `GEMINI.md`（專案根目錄） |
| Windsurf（Codeium） | `.windsurf/rules/travelinvoiceskill.md` |
| Cline（VS Code 外掛） | `.clinerules/travelinvoiceskill.md` |
| JetBrains Junie | `.junie/guidelines.md` |
| Aider | `CONVENTIONS.md`（以 `aider --read CONVENTIONS.md` 或設定檔載入） |
| Continue.dev | `.continue/rules/travelinvoiceskill.md` |

```
你的專案/
├── travelinvoiceskill/                     ← 本包的「travelinvoiceskill/」整個資料夾（guides、references、test-vectors）
├── AGENTS.md                       ← Codex / Cursor / Zed
├── GEMINI.md                       ← Google Gemini CLI
├── CONVENTIONS.md                  ← Aider
├── .github/copilot-instructions.md ← GitHub Copilot（VS Code / VS / CLI）
├── .cursor/rules/travelinvoiceskill.mdc
├── .windsurf/rules/travelinvoiceskill.md   ← Windsurf
├── .clinerules/travelinvoiceskill.md       ← Cline
├── .continue/rules/travelinvoiceskill.md   ← Continue.dev
└── .junie/guidelines.md            ← JetBrains Junie
```

> 這些入口檔內以「相對專案根目錄」的路徑引用文件（例如 `travelinvoiceskill/guides/*.md`），所以只要 `travelinvoiceskill/` 放在專案根目錄即可正確解析。
