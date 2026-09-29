<?php
declare(strict_types=1);

// Diem kiem tra suc khoe: khong mo session, khong doc co so du lieu,
// khong tra ve phien ban PHP hay duong dan. Chi du thong tin de ket luan
// node con song hay chet.
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

require __DIR__ . '/lib/bootstrap.php';

echo json_encode([
    'status' => 'ok',
    'node'   => node_name(),
], JSON_UNESCAPED_SLASHES);
