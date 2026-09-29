<?php
declare(strict_types=1);

// Tang do thu ba cua bac thang hieu nang: load balancer + nginx tren node +
// php-fpm + mot truy van that co so du lieu. Do dai phan hoi khong doi giua
// cac node de ApacheBench khong dem nham thanh request that bai.

require __DIR__ . '/lib/bootstrap.php';

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

$rows = 0;
$ok = 0;
try {
    $res = db()->query('SELECT COUNT(*) AS c FROM news');
    $rows = (int) $res->fetch_assoc()['c'];
    $ok = 1;
} catch (Throwable) {
    $ok = 0;
}

printf('{"node":"%s","rows":%d,"ok":%d}', node_name(), $rows, $ok);
