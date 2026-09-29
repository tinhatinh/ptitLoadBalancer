<?php
declare(strict_types=1);

require __DIR__ . '/lib/bootstrap.php';

$user   = current_user();
$items  = [];
$broken = false;

try {
    $res   = db()->query(
        'SELECT id, title, summary, author, published_at FROM news ORDER BY published_at DESC'
    );
    $items = $res->fetch_all(MYSQLI_ASSOC);
} catch (Throwable) {
    $broken = true;
}

$body = '';

if ($broken) {
    $body .= '<div class="card"><p class="err">Node này không kết nối được cơ sở dữ liệu, '
        . 'chỉ còn trang tĩnh.</p></div>';
}

foreach ($items as $row) {
    $body .= sprintf(
        '<article class="card"><h2>%s</h2><p>%s</p><p class="meta">%s &middot; %s</p></article>',
        e($row['title']),
        e($row['summary']),
        e($row['author']),
        e($row['published_at'])
    );
}

$body .= sprintf(
    '<div class="card"><h2>Node đang phục vụ trang này</h2>'
    . '<table>'
    . '<tr><th>Tên node</th><td>%s</td></tr>'
    . '<tr><th>IP khách hàng node nhìn thấy</th><td>%s</td></tr>'
    . '<tr><th>Kho lưu phiên đang dùng</th><td>%s</td></tr>'
    . '<tr><th>Cơ sở dữ liệu</th><td>%s</td></tr>'
    . '</table></div>',
    e(node_name()),
    e(client_ip()),
    e((string) ini_get('session.save_handler')),
    db_available() ? 'kết nối được' : 'không kết nối được'
);

render('Trang chủ', $body, $user);
