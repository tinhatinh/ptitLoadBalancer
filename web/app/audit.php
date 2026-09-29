<?php
declare(strict_types=1);

require __DIR__ . '/lib/bootstrap.php';

$user = require_login();
if ($user['role'] !== 'admin') {
    http_response_code(403);
    render('Cấm', '<div class="card"><p class="err">Chỉ quản trị viên mới xem được nhật ký đăng nhập.</p></div>', $user);
    exit;
}

$stmt = db()->prepare('SELECT username, success, client_ip, node_name, occurred_at FROM login_audit ORDER BY id DESC LIMIT 50');
$stmt->execute();
$rows = $stmt->get_result()->fetch_all(MYSQLI_ASSOC);

$body = '<div class="card"><h2>Nhật ký đăng nhập (50 bản ghi gần nhất)</h2>'
    . '<table><tr><th>Thời điểm</th><th>Tên đăng nhập</th><th>Kết quả</th><th>IP khách hàng</th><th>Ghi từ node</th></tr>';

foreach ($rows as $r) {
    $body .= sprintf(
        '<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>',
        e($r['occurred_at']),
        e($r['username']),
        ((int) $r['success'] === 1) ? 'thành công' : 'thất bại',
        e($r['client_ip']),
        e($r['node_name'])
    );
}

if ($rows === []) {
    $body .= '<tr><td colspan="5">Chưa có bản ghi nào.</td></tr>';
}

$body .= '</table><p class="meta">Nhật ký nằm trong cơ sở dữ liệu dùng chung nên không mất đi khi một node bị tắt.</p></div>';

render('Nhật ký đăng nhập', $body, $user);
