<?php
/**
 * 加解密測試向量驗證腳本（PHP 參考實作）
 *
 * 用法： php verify.php
 * 作用：讀取同目錄 vectors.json，依各 API 規格重算 AES 密文與 SHA256 簽章，
 *       與『預期輸出』逐項比對。全部 PASS 代表答案鑰匙可重現；
 *       你用其他語言實作時，可用同一組輸入比對此處的預期輸出。
 * 相容：PHP 7.4+
 */

$path = __DIR__ . '/vectors.json';
if (!is_file($path)) { fwrite(STDERR, "找不到 vectors.json\n"); exit(2); }
$data = json_decode(file_get_contents($path), true);
if (!is_array($data)) { fwrite(STDERR, "vectors.json 解析失敗\n"); exit(2); }

/* AES：依 padding 規格重算密文（支援 PKCS7 B32 非標準 32-byte 補位） */
function aes_encrypt_vector($plaintext, $key, $iv, $algorithm, $padding, $outputEncoding) {
    $isEcb = (stripos($algorithm, '-ECB') !== false);
    if ($padding === 'PKCS7 B32') {
        $padLen = 32 - (strlen($plaintext) % 32);
        $padded = $plaintext . str_repeat(chr($padLen), $padLen);
        $raw = $isEcb
            ? openssl_encrypt($padded, $algorithm, $key, OPENSSL_RAW_DATA | OPENSSL_ZERO_PADDING)
            : openssl_encrypt($padded, $algorithm, $key, OPENSSL_RAW_DATA | OPENSSL_ZERO_PADDING, $iv);
    } else {
        $raw = $isEcb
            ? openssl_encrypt($plaintext, $algorithm, $key, OPENSSL_RAW_DATA)
            : openssl_encrypt($plaintext, $algorithm, $key, OPENSSL_RAW_DATA, $iv);
    }
    if ($raw === false) { return false; }
    return ($outputEncoding === 'Hex') ? bin2hex($raw) : base64_encode($raw);
}

$total = 0; $fail = 0;
foreach ($data as $api => $vec) {
    echo "== {$api} ==\n";
    if (isset($vec['aes'])) {
        $a = $vec['aes']; $total++;
        $got = aes_encrypt_vector($a['plaintext'], $a['key'], $a['iv'], $a['algorithm'], $a['padding'], $a['output_encoding']);
        $ok = ($got !== false && hash_equals($a['expected_output'], $got));
        echo '  [AES] ' . ($ok ? 'PASS' : 'FAIL') . "\n";
        if (!$ok) { $fail++; echo '    expected: ' . $a['expected_output'] . "\n" . '    got:      ' . var_export($got, true) . "\n"; }
    }
    if (isset($vec['sha256'])) {
        $s = $vec['sha256']; $total++;
        $got = strtoupper(hash('sha256', $s['raw_string']));
        $ok = hash_equals($s['expected_signature'], $got);
        echo '  [SHA256] ' . ($ok ? 'PASS' : 'FAIL') . "\n";
        if (!$ok) { $fail++; echo '    expected: ' . $s['expected_signature'] . "\n" . '    got:      ' . $got . "\n"; }
    }
}
echo "\n總計 {$total} 項，PASS " . ($total - $fail) . "，FAIL {$fail}\n";
exit($fail > 0 ? 1 : 0);
