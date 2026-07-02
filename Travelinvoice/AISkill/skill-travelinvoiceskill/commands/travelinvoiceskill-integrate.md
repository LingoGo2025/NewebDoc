---
description: 協助串接「TravelinvoiceSkill」的 API，產出並驗證程式碼
---

你要協助使用者串接「TravelinvoiceSkill」的 API。請依下列流程進行：

1. 先載入本專案的 `travelinvoiceskill` skill（讀取其 SKILL.md），依「API 對照表」確認使用者需求對應哪一支 API，並讀取對應的 `guides/*.md`。
2. 產出程式碼前，先完成 SKILL.md 的「串接前置確認」（HashKey/HashIV、測試或正式環境、UTF-8）。
3. 依 guide 的欄位定義與加密規格撰寫程式碼。
4. 完成加解密／簽章後，**務必用 `test-vectors/` 的標準答案自我驗證**，全部相符再交付。

使用者的需求：$ARGUMENTS
