---
name: travelinvoiceskill
description: "協助串接「旅行業代收轉付電子收據」相關 API（作廢電子收據API、單筆查詢收據作廢資料API、單筆查詢收據折讓資料API、單筆查詢收據開立資料API、批次查詢收據折讓資料API、批次查詢收據開立資料API 等），採 AES256 + SHA256 加密。當使用者需要產生上述 API 的串接程式碼、查詢欄位定義／錯誤代碼、或處理加密簽章時使用。"
---

# TravelinvoiceSkill

本 Skill 封裝「旅行業代收轉付電子收據」的 API 串接文件，協助你依需求快速產出正確的串接程式碼。

## 使用流程（重要）

1. 先依下方「API 對照表」判斷使用者需求對應哪一支 API，**讀取對應的 `guides/*.md`** 取得完整欄位定義、加密規格與範例。
2. 產出程式碼前，**務必先完成下方「串接前置確認」**。
3. 依 guide 的欄位表、加密規格與請求／回應範例撰寫程式碼；錯誤代碼一律對照 guide 內的錯誤代碼表。
4. **產出加解密／簽章程式碼後，務必用 `test-vectors/` 的標準答案自我驗證**（見下方「加解密自我驗證」），全部相符才算完成。

> 需要結構化資料時，可讀 `api-manifest.json`（各 API 的端點／欄位／簽章／錯誤代碼機器可讀版），比解析 Markdown 表格更穩。

## API 對照表（決策樹）

| 當使用者想要… | 對應 API | 加密 | 說明文件 |
|----------------|----------|------|----------|
| 此API可以於開立後下一個單月15日前作廢旅行業代收轉付電子收據 | 作廢電子收據API | AES256 + SHA256 | [`guides/void-e-receipt-api.md`](guides/void-e-receipt-api.md) |
| 此API可以查詢單筆電子收據的作廢資料參數、進度及狀態。 | 單筆查詢收據作廢資料API | AES256 + SHA256 | [`guides/query-single-voided-receipt-api.md`](guides/query-single-voided-receipt-api.md) |
| 此API可以查詢單筆電子收據的折讓資料參數、進度及狀態。 | 單筆查詢收據折讓資料API | AES256 + SHA256 | [`guides/query-single-receipt-allowance-api.md`](guides/query-single-receipt-allowance-api.md) |
| 此API可以查詢單筆電子收據目前的各項參數及狀態，適合於需要單筆資料的狀態確認，或是預約開立後的資料反查 | 單筆查詢收據開立資料API | AES256 + SHA256 | [`guides/query-single-issued-receipt-api.md`](guides/query-single-issued-receipt-api.md) |
| 此API可以批次查詢收據的折讓資料參數、進度及狀態。 | 批次查詢收據折讓資料API | AES256 + SHA256 | [`guides/batch-query-receipt-allowance-api.md`](guides/batch-query-receipt-allowance-api.md) |
| 此API可以批次查詢電子收據的開立資料參數、進度及狀態。 | 批次查詢收據開立資料API | AES256 + SHA256 | [`guides/batch-query-issued-receipt-api.md`](guides/batch-query-issued-receipt-api.md) |
| 此API可以批次查詢收據作廢資料參數、進度及狀態。 | 批次查詢電子收據作廢資料API | AES256 + SHA256 | [`guides/batch-query-voided-e-receipt-api.md`](guides/batch-query-voided-e-receipt-api.md) |
| 此API可以於開立後任何時間進行旅行業代收轉付電子收據折讓作業，但折讓單一旦經確認後，該收據將不能開立作廢單 | 折讓電子收據API | AES256 + SHA256 | [`guides/allowance-e-receipt-api.md`](guides/allowance-e-receipt-api.md) |
| 此API可用旅行社自訂編號來查詢電子收據的開立資料參數、進度及狀態，適合自訂編號重複的旅行社。 | 自訂編號查詢電子收據開立資料API | AES256 + SHA256 | [`guides/query-e-receipt-by-custom-id-api.md`](guides/query-e-receipt-by-custom-id-api.md) |
| 此API可以補發收據開立、作廢單或折讓單的系統通知信 | 補發通知信API | AES256 + SHA256 | [`guides/resend-notification-api.md`](guides/resend-notification-api.md) |
| 此API用於管理待確認的作廢資料，如直接確認作廢資料，或是取消這個待確認作廢資料 | 觸發或取消作廢資料API | AES256 + SHA256 | [`guides/trigger-cancel-void-data-api.md`](guides/trigger-cancel-void-data-api.md) |
| 此API用於管理待確認的折讓資料，如直接確認折讓資料，或是取消這個待確認折讓資料 | 觸發或取消待確認折讓資料API | AES256 + SHA256 | [`guides/trigger-cancel-pending-allowance-api.md`](guides/trigger-cancel-pending-allowance-api.md) |
| 此API對於未到期之預約收據，進行提前開立或取消預約 | 觸發或取消預約收據API | AES256 + SHA256 | [`guides/trigger-cancel-scheduled-receipt-api.md`](guides/trigger-cancel-scheduled-receipt-api.md) |
| 此API可編輯部分收據資料（限未上傳,未列印之收據） | 變更收據API | AES256 + SHA256 | [`guides/update-receipt-api.md`](guides/update-receipt-api.md) |
| 此API可以開立旅行業代收轉付電子收據，可以開立及時收據及預約開立收據 | 開立電子收據API | AES256 + SHA256 | [`guides/issue-e-receipt-api.md`](guides/issue-e-receipt-api.md) |

## 串接前置確認（產出程式碼前必做）

在撰寫任何串接程式碼前，**必須**主動向使用者確認以下事項；若未提供，**禁止**將文件中的示範值寫死，
應改以環境變數／設定檔保存，並於回覆中明確告知使用者：

1. 是否已取得對應環境的 HashKey 與 HashIV？（請勿使用文件示範值）
2. 串接目標為「測試」還是「正式」環境？（測試與正式網址、Key／IV 均不通用）
3. 字串一律以 UTF-8 編碼後再進行加密／簽章。

## 安全護欄（務必遵守）

- **未經使用者明確確認，不得呼叫正式（production）端點**；預設一律使用測試環境。
- **不得**在 log、主控台輸出、測試輸出或錯誤訊息中印出 HashKey／HashIV 或完整 PostData 明文。
- 金鑰（Key／IV）不得寫死於前端，也不得提交至公開版本庫；一律以環境變數／設定檔保存。
- 正式上線前確認環境隔離、憑證，以及（如適用）對方要求的 IP 白名單。

## 共通除錯指引

| 現象 | 最可能原因 | 解決方式 |
|------|-----------|----------|
| 加解密結果不符 | Key／IV 錯誤、AES 模式或 padding 不符 | 對照 guide 的加密規格，確認模式與 PKCS#7 padding |
| 簽章（CheckValue）驗證失敗 | 欄位組合順序錯誤或含多餘空白 | 嚴格依 guide 的 SHA256 欄位順序組字串，值前後不得有空白 |
| 回應 HTTP 200 但狀態非成功 | 業務邏輯錯誤 | 讀取回應 body 的狀態欄位，對照 guide 錯誤代碼表 |

## 加解密自我驗證（重要）

`test-vectors/vectors.json` 是由文件來源系統**實際運算產出的「標準答案」**：每支需要加密／簽章的 API，都附有一組固定測試 Key/IV、輸入，以及**保證正確的預期輸出**。

產出加解密程式碼後，請務必執行下列驗證，**不要只憑規格猜測即交付**：

1. 用 `vectors.json` 中該 API 的 `key`、`iv`、`plaintext`（AES）或 `raw_string`（SHA256）作為輸入，呼叫你寫的加解密函式。
2. 比對你的輸出是否等於 `expected_output`（AES，依 `output_encoding` 為 Hex／Base64）／`expected_signature`（SHA256）。
3. **完全相符**才代表加解密實作正確；不符請依差異（padding、欄位順序、大小寫、編碼）修正後再次比對。
4. 也可執行本 skill `test-vectors/` 目錄內的參考腳本自我驗證：有 PHP 用 `php verify.php`、有 Node 用 `node verify.js`（請以該目錄為工作目錄或用完整路徑，勿假設當前工作目錄），會重算並逐項回報 PASS／FAIL。

> 加解密是整個串接最易錯、最難查的環節；務必以此標準答案驗證後再交付程式碼。

## 端點與外部連結

詳見 [`references.md`](references.md)。
