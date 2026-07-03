---
description: 用標準測試向量驗證「TravelinvoiceSkill」的加解密／簽章是否正確
---

請用 `travelinvoiceskill` skill 的 `test-vectors/vectors.json` 標準答案，驗證使用者的加解密／簽章實作：

1. 讀取 `test-vectors/vectors.json`。
2. 針對相關 API，取其 AES `key`/`iv`/`plaintext` 與 SHA256 `raw_string` 作為輸入。
3. 用使用者提供的程式碼（或你產出的程式碼）計算輸出，與 `expected_output`／`expected_signature` 比對。
4. 逐項回報 PASS／FAIL；若 FAIL，指出最可能的差異（padding、欄位順序、大小寫、編碼）並修正。
5. 需要參考結果時，定位本 skill 的 `test-vectors/` 目錄，於其中執行 `php verify.php` 或 `node verify.js`（勿假設當前工作目錄）。

要驗證的內容：$ARGUMENTS
