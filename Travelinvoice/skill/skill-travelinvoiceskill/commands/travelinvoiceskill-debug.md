---
description: 協助排查「TravelinvoiceSkill」API 的錯誤代碼與驗章失敗
---

使用者在串接「TravelinvoiceSkill」時遇到錯誤。請依下列方式協助：

1. 載入 `travelinvoiceskill` skill；若使用者提供錯誤代碼，對照相關 `guides/*.md` 的錯誤代碼表說明原因與解法。
2. 若是加解密／驗章失敗，引導使用者用 `test-vectors/` 的標準答案比對，定位是 padding、欄位順序、大小寫或編碼問題。
3. 參考 SKILL.md 的「共通除錯指引」。

使用者遇到的錯誤：$ARGUMENTS
