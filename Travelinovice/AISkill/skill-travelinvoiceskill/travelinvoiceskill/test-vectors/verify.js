#!/usr/bin/env node
/**
 * 加解密測試向量驗證腳本（Node.js 參考實作，零外部依賴）
 *
 * 用法： node verify.js
 * 作用：讀取同目錄 vectors.json，重算 AES 密文與 SHA256 簽章，與『預期輸出』逐項比對。
 *       全部 PASS 代表答案鑰匙可重現；你用其他語言實作時，可用同一組輸入比對此處的預期輸出。
 */
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const file = path.join(__dirname, 'vectors.json');
if (!fs.existsSync(file)) { console.error('找不到 vectors.json'); process.exit(2); }
const data = JSON.parse(fs.readFileSync(file, 'utf8'));

/* PKCS7 以 32-byte 邊界手動補位（非標準規格） */
function pad32(buf) {
  const padLen = 32 - (buf.length % 32);
  return Buffer.concat([buf, Buffer.alloc(padLen, padLen)]);
}

function aesEncryptVector(plaintext, key, iv, algorithm, padding, outputEncoding) {
  const algo = algorithm.toLowerCase();            // 例如 aes-256-cbc
  const isEcb = algo.indexOf('-ecb') !== -1;
  const cipher = crypto.createCipheriv(algo, Buffer.from(key, 'utf8'), isEcb ? null : Buffer.from(iv, 'utf8'));
  cipher.setAutoPadding(padding !== 'PKCS7 B32'); // 標準 padding 交給函式庫；PKCS7 B32 手動處理
  let input = Buffer.from(plaintext, 'utf8');
  if (padding === 'PKCS7 B32') input = pad32(input);
  const enc = Buffer.concat([cipher.update(input), cipher.final()]);
  return outputEncoding === 'Hex' ? enc.toString('hex') : enc.toString('base64');
}

let total = 0, fail = 0;
for (const api of Object.keys(data)) {
  const vec = data[api];
  console.log('== ' + api + ' ==');
  if (vec.aes) {
    const a = vec.aes; total++;
    let got;
    try { got = aesEncryptVector(a.plaintext, a.key, a.iv, a.algorithm, a.padding, a.output_encoding); }
    catch (e) { got = 'ERROR: ' + e.message; }
    const ok = got === a.expected_output;
    console.log('  [AES] ' + (ok ? 'PASS' : 'FAIL'));
    if (!ok) { fail++; console.log('    expected: ' + a.expected_output); console.log('    got:      ' + got); }
  }
  if (vec.sha256) {
    const s = vec.sha256; total++;
    const got = crypto.createHash('sha256').update(s.raw_string, 'utf8').digest('hex').toUpperCase();
    const ok = got === s.expected_signature;
    console.log('  [SHA256] ' + (ok ? 'PASS' : 'FAIL'));
    if (!ok) { fail++; console.log('    expected: ' + s.expected_signature); console.log('    got:      ' + got); }
  }
}
console.log('\n總計 ' + total + ' 項，PASS ' + (total - fail) + '，FAIL ' + fail);
process.exit(fail > 0 ? 1 : 0);