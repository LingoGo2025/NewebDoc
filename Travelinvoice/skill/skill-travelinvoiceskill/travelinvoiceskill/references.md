# TravelinvoiceSkill — 端點與參考連結

本檔列出各 API 的正式／測試端點，供串接時設定環境變數參考。

## 作廢電子收據API

- 說明：此API可以於開立後下一個單月15日前作廢旅行業代收轉付電子收據
- 正式端點：`https://api.travelinvoice.com.tw/invoice_invalid`
- 測試端點：`https://capi.travelinvoice.com.tw/invoice_invalid`
- 加密方式：AES256 + SHA256
- 完整說明：[`guides/void-e-receipt-api.md`](guides/void-e-receipt-api.md)

## 單筆查詢收據作廢資料API

- 說明：此API可以查詢單筆電子收據的作廢資料參數、進度及狀態。
- 正式端點：`https://api.travelinvoice.com.tw/invoice_search`
- 測試端點：`https://capi.travelinvoice.com.tw/invoice_search`
- 加密方式：AES256 + SHA256
- 完整說明：[`guides/query-single-voided-receipt-api.md`](guides/query-single-voided-receipt-api.md)

## 單筆查詢收據折讓資料API

- 說明：此API可以查詢單筆電子收據的折讓資料參數、進度及狀態。
- 正式端點：`https://api.travelinvoice.com.tw/invoice_search`
- 測試端點：`https://capi.travelinvoice.com.tw/invoice_search`
- 加密方式：AES256 + SHA256
- 完整說明：[`guides/query-single-receipt-allowance-api.md`](guides/query-single-receipt-allowance-api.md)

## 單筆查詢收據開立資料API

- 說明：此API可以查詢單筆電子收據目前的各項參數及狀態，適合於需要單筆資料的狀態確認，或是預約開立後的資料反查
- 正式端點：`https://api.travelinvoice.com.tw/invoice_search`
- 測試端點：`https://capi.travelinvoice.com.tw/invoice_search`
- 加密方式：AES256 + SHA256
- 完整說明：[`guides/query-single-issued-receipt-api.md`](guides/query-single-issued-receipt-api.md)

## 批次查詢收據折讓資料API

- 說明：此API可以批次查詢收據的折讓資料參數、進度及狀態。
- 正式端點：`https://api.travelinvoice.com.tw/invoice_searchall`
- 測試端點：`https://capi.travelinvoice.com.tw/invoice_searchall`
- 加密方式：AES256 + SHA256
- 完整說明：[`guides/batch-query-receipt-allowance-api.md`](guides/batch-query-receipt-allowance-api.md)

## 批次查詢收據開立資料API

- 說明：此API可以批次查詢電子收據的開立資料參數、進度及狀態。
- 正式端點：`https://api.travelinvoice.com.tw/invoice_searchall`
- 測試端點：`https://capi.travelinvoice.com.tw/invoice_searchall`
- 加密方式：AES256 + SHA256
- 完整說明：[`guides/batch-query-issued-receipt-api.md`](guides/batch-query-issued-receipt-api.md)

## 批次查詢電子收據作廢資料API

- 說明：此API可以批次查詢收據作廢資料參數、進度及狀態。
- 正式端點：`https://api.travelinvoice.com.tw/invoice_searchall`
- 測試端點：`https://capi.travelinvoice.com.tw/invoice_searchall`
- 加密方式：AES256 + SHA256
- 完整說明：[`guides/batch-query-voided-e-receipt-api.md`](guides/batch-query-voided-e-receipt-api.md)

## 折讓電子收據API

- 說明：此API可以於開立後任何時間進行旅行業代收轉付電子收據折讓作業，但折讓單一旦經確認後，該收據將不能開立作廢單
- 正式端點：`https://api.travelinvoice.com.tw/allowance_issue`
- 測試端點：`https://capi.travelinvoice.com.tw/allowance_issue`
- 加密方式：AES256 + SHA256
- 完整說明：[`guides/allowance-e-receipt-api.md`](guides/allowance-e-receipt-api.md)

## 自訂編號查詢電子收據開立資料API

- 說明：此API可用旅行社自訂編號來查詢電子收據的開立資料參數、進度及狀態，適合自訂編號重複的旅行社。
- 正式端點：`https://api.travelinvoice.com.tw/invoice_searchall`
- 測試端點：`https://capi.travelinvoice.com.tw/invoice_searchall`
- 加密方式：AES256 + SHA256
- 完整說明：[`guides/query-e-receipt-by-custom-id-api.md`](guides/query-e-receipt-by-custom-id-api.md)

## 補發通知信API

- 說明：此API可以補發收據開立、作廢單或折讓單的系統通知信
- 正式端點：`https://api.travelinvoice.com.tw/notification_resend`
- 測試端點：`https://capi.travelinvoice.com.tw/notification_resend`
- 加密方式：AES256 + SHA256
- 完整說明：[`guides/resend-notification-api.md`](guides/resend-notification-api.md)

## 觸發或取消作廢資料API

- 說明：此API用於管理待確認的作廢資料，如直接確認作廢資料，或是取消這個待確認作廢資料
- 正式端點：`https://api.travelinvoice.com.tw/invalid_touch_issue`
- 測試端點：`https://capi.travelinvoice.com.tw/invalid_touch_issue`
- 加密方式：AES256 + SHA256
- 完整說明：[`guides/trigger-cancel-void-data-api.md`](guides/trigger-cancel-void-data-api.md)

## 觸發或取消待確認折讓資料API

- 說明：此API用於管理待確認的折讓資料，如直接確認折讓資料，或是取消這個待確認折讓資料
- 正式端點：`https://api.travelinvoice.com.tw/allowance_touch_issue`
- 測試端點：`https://capi.travelinvoice.com.tw/allowance_touch_issue`
- 加密方式：AES256 + SHA256
- 完整說明：[`guides/trigger-cancel-pending-allowance-api.md`](guides/trigger-cancel-pending-allowance-api.md)

## 觸發或取消預約收據API

- 說明：此API對於未到期之預約收據，進行提前開立或取消預約
- 正式端點：`https://api.travelinvoice.com.tw/invoice_touch_issue`
- 測試端點：`https://capi.travelinvoice.com.tw/invoice_touch_issue`
- 加密方式：AES256 + SHA256
- 完整說明：[`guides/trigger-cancel-scheduled-receipt-api.md`](guides/trigger-cancel-scheduled-receipt-api.md)

## 變更收據API

- 說明：此API可編輯部分收據資料（限未上傳,未列印之收據）
- 正式端點：`https://api.travelinvoice.com.tw/invoice_edit`
- 測試端點：`https://capi.travelinvoice.com.tw/invoice_edit`
- 加密方式：AES256 + SHA256
- 完整說明：[`guides/update-receipt-api.md`](guides/update-receipt-api.md)

## 開立電子收據API

- 說明：此API可以開立旅行業代收轉付電子收據，可以開立及時收據及預約開立收據
- 正式端點：`https://api.travelinvoice.com.tw/invoice_issue`
- 測試端點：`https://capi.travelinvoice.com.tw/invoice_issue`
- 加密方式：AES256 + SHA256
- 完整說明：[`guides/issue-e-receipt-api.md`](guides/issue-e-receipt-api.md)

