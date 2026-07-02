# TravelinvoiceSkill — API 串接指引

本指引協助 AI 開發工具串接「旅行業代收轉付電子收據」的 API。文件與測試向量位於專案中的 `travelinvoiceskill/` 目錄。

## 使用流程

1. 依下方「API 對照表」判斷需求對應哪一支 API，讀取對應的 `travelinvoiceskill/guides/*.md` 取得欄位定義、加密規格與範例。
2. 產出程式碼前，先完成「串接前置確認」。
3. 依 guide 的欄位表與加密規格撰寫程式碼；錯誤代碼對照 guide 內的錯誤代碼表。
4. 產出加解密／簽章程式碼後，用 `travelinvoiceskill/test-vectors/vectors.json` 的標準答案自我驗證，全部相符才交付。

> 需要結構化資料時，可讀 `travelinvoiceskill/api-manifest.json`（各 API 的端點／欄位／簽章／錯誤代碼機器可讀版），比解析 Markdown 表格更穩。

## API 對照表

| 當使用者想要… | 對應 API | 加密 | 說明文件 |
|----------------|----------|------|----------|
| 此API可以於開立後下一個單月15日前作廢旅行業代收轉付電子收據 | 作廢電子收據API | AES256 + SHA256 | `travelinvoiceskill/guides/void-e-receipt-api.md` |
| 此API可以查詢單筆電子收據的作廢資料參數、進度及狀態。 | 單筆查詢收據作廢資料API | AES256 + SHA256 | `travelinvoiceskill/guides/query-single-voided-receipt-api.md` |
| 此API可以查詢單筆電子收據的折讓資料參數、進度及狀態。 | 單筆查詢收據折讓資料API | AES256 + SHA256 | `travelinvoiceskill/guides/query-single-receipt-allowance-api.md` |
| 此API可以查詢單筆電子收據目前的各項參數及狀態，適合於需要單筆資料的狀態確認，或是預約開立後的資料反查 | 單筆查詢收據開立資料API | AES256 + SHA256 | `travelinvoiceskill/guides/query-single-issued-receipt-api.md` |
| 此API可以批次查詢收據的折讓資料參數、進度及狀態。 | 批次查詢收據折讓資料API | AES256 + SHA256 | `travelinvoiceskill/guides/batch-query-receipt-allowance-api.md` |
| 此API可以批次查詢電子收據的開立資料參數、進度及狀態。 | 批次查詢收據開立資料API | AES256 + SHA256 | `travelinvoiceskill/guides/batch-query-issued-receipt-api.md` |
| 此API可以批次查詢收據作廢資料參數、進度及狀態。 | 批次查詢電子收據作廢資料API | AES256 + SHA256 | `travelinvoiceskill/guides/batch-query-voided-e-receipt-api.md` |
| 此API可以於開立後任何時間進行旅行業代收轉付電子收據折讓作業，但折讓單一旦經確認後，該收據將不能開立作廢單 | 折讓電子收據API | AES256 + SHA256 | `travelinvoiceskill/guides/allowance-e-receipt-api.md` |
| 此API可用旅行社自訂編號來查詢電子收據的開立資料參數、進度及狀態，適合自訂編號重複的旅行社。 | 自訂編號查詢電子收據開立資料API | AES256 + SHA256 | `travelinvoiceskill/guides/query-e-receipt-by-custom-id-api.md` |
| 此API可以補發收據開立、作廢單或折讓單的系統通知信 | 補發通知信API | AES256 + SHA256 | `travelinvoiceskill/guides/resend-notification-api.md` |
| 此API用於管理待確認的作廢資料，如直接確認作廢資料，或是取消這個待確認作廢資料 | 觸發或取消作廢資料API | AES256 + SHA256 | `travelinvoiceskill/guides/trigger-cancel-void-data-api.md` |
| 此API用於管理待確認的折讓資料，如直接確認折讓資料，或是取消這個待確認折讓資料 | 觸發或取消待確認折讓資料API | AES256 + SHA256 | `travelinvoiceskill/guides/trigger-cancel-pending-allowance-api.md` |
| 此API對於未到期之預約收據，進行提前開立或取消預約 | 觸發或取消預約收據API | AES256 + SHA256 | `travelinvoiceskill/guides/trigger-cancel-scheduled-receipt-api.md` |
| 此API可編輯部分收據資料（限未上傳,未列印之收據） | 變更收據API | AES256 + SHA256 | `travelinvoiceskill/guides/update-receipt-api.md` |
| 此API可以開立旅行業代收轉付電子收據，可以開立及時收據及預約開立收據 | 開立電子收據API | AES256 + SHA256 | `travelinvoiceskill/guides/issue-e-receipt-api.md` |

## 串接前置確認（產出程式碼前必做）

1. 是否已取得對應環境的 HashKey 與 HashIV？（請勿寫死文件示範值，改用環境變數／設定檔）
2. 串接目標為「測試」還是「正式」環境？（網址與 Key／IV 均不通用）
3. 字串一律以 UTF-8 編碼後再進行加密／簽章。

## 安全護欄（務必遵守）

- **未經使用者明確確認，不得呼叫正式（production）端點**；預設一律使用測試環境。
- **不得**在 log、主控台輸出、測試輸出或錯誤訊息中印出 HashKey／HashIV 或完整 PostData 明文。
- 金鑰（Key／IV）不得寫死於前端，也不得提交至公開版本庫；一律以環境變數／設定檔保存。
- 正式上線前確認環境隔離、憑證，以及（如適用）對方要求的 IP 白名單。

## 共通除錯指引

- 加解密結果不符：確認 AES 模式與 padding（注意本系列常見的 PKCS7 32-byte 邊界）、Key／IV 是否正確。
- 簽章驗證失敗：嚴格依 guide 的欄位順序組字串，值前後不得有空白，且不可對值做 URL encode。
- 回應 HTTP 200 但狀態非成功：讀回應 body 的狀態欄位，對照 guide 錯誤代碼表。

## 加解密自我驗證

`travelinvoiceskill/test-vectors/vectors.json` 是實算產出的標準答案：用其中的 `key`／`iv`／`plaintext`（AES）與 `raw_string`（SHA256）作為輸入，
計算後應分別等於 `expected_output` 與 `expected_signature`。不符請依差異（padding、欄位順序、大小寫、編碼）修正。
亦可執行 `travelinvoiceskill/test-vectors/` 內的參考腳本取得結果：`php verify.php`（有 PHP）或 `node verify.js`（有 Node、免安裝套件）。
