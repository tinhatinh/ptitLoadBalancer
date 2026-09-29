<?php
declare(strict_types=1);

require __DIR__ . '/lib/bootstrap.php';

$user = require_login();
$sid  = session_id();

render(
    'Trang thành viên',
    '<div class="card">'
    . '<h2>Xin chào ' . e($user['full_name']) . '</h2>'
    . '<table>'
    . '<tr><th>Tên đăng nhập</th><td>' . e($user['username']) . '</td></tr>'
    . '<tr><th>Phân quyền</th><td>' . e($user['role']) . '</td></tr>'
    . '<tr><th>Node đang phục vụ</th><td>' . e(node_name()) . '</td></tr>'
    . '<tr><th>Định danh phiên (8 ký tự đầu)</th><td>' . e(substr($sid, 0, 8)) . '</td></tr>'
    . '<tr><th>Kho lưu phiên</th><td>' . e((string) ini_get('session.save_handler')) . '</td></tr>'
    . '</table>'
    . '<p class="meta">Bấm <a href="/member.php">nạp lại</a> nhiều lần để xem node thay đổi '
    . 'trong khi phiên vẫn còn hiệu lực.</p>'
    . '</div>',
    $user
);
