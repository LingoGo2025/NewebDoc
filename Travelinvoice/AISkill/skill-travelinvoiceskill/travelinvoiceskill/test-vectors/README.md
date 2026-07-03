# 加解密測試向量（答案鑰匙）

本目錄是「TravelinvoiceSkill」Skill 的加解密**標準答案**，由文件來源系統實際運算產生，保證正確。

## 檔案

- `vectors.json`：每支需要加密／簽章的 API，各附一組固定測試 Key/IV、輸入，以及**保證正確的預期輸出**。
- `verify.php`：PHP 參考驗證腳本，重算後與預期輸出比對。
- `verify.js`：Node.js 版驗證腳本（零外部依賴，內建 crypto），供沒有 PHP 的環境使用。

## 怎麼用

### 1) 確認答案鑰匙可重現

擇一執行（結果應完全一致、全部 PASS）：

```bash
php verify.php     # 有 PHP 環境
node verify.js     # 有 Node.js 環境（免安裝套件）
```

### 2) 驗證你用其他語言寫的加解密

1. 取 `vectors.json` 中某支 API 的 AES `key`、`iv`、`plaintext`，呼叫你的加密函式，輸出應等於 `expected_output`（依 `output_encoding` 為 Hex 或 Base64）。
2. 取該 API 的 SHA256 `raw_string`，做 `UPPER(SHA256(raw_string))`，應等於 `expected_signature`。
3. 不相符就表示實作有誤——常見差異：AES padding（注意 PKCS7 B32 為 32-byte 邊界）、欄位排序、簽章大小寫、字元編碼（須 UTF-8）。

> 測試 Key/IV 僅供驗證演算法正確性，**正式串接請改用實際的 HashKey/HashIV**。
