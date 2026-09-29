<?php
declare(strict_types=1);

require __DIR__ . '/lib/bootstrap.php';

start_session();
$error = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (!csrf_ok($_POST['csrf'] ?? null)) {
        $error = 'Mã bảo vệ không hợp lệ.';
    } else {
        $username = trim((string) ($_POST['username'] ?? ''));
        $password = (string) ($_POST['password'] ?? '');

        if ($username === '' || $password === '') {
            $error = 'Cần nhập đầy đủ tên đăng nhập và mật khẩu.';
        } else {
            $stmt = db()->prepare('SELECT id, username, password_hash, full_name, role FROM users WHERE username = ?');
            $stmt->bind_param('s', $username);
            $stmt->execute();
            $row = $stmt->get_result()->fetch_assoc();

            if ($row !== null && password_verify($password, $row['password_hash'])) {
                // Rotating the identifier after privilege change blocks
                // session fixation, section 3.2.2 of the course textbook.
                session_regenerate_id(true);
                $_SESSION['user'] = [
                    'id'        => (int) $row['id'],
                    'username'  => $row['username'],
                    'full_name' => $row['full_name'],
                    'role'      => $row['role'],
                ];
                record_login_attempt($username, true);
                header('Location: /member.php');
                exit;
            }

            record_login_attempt($username, false);
            $error = 'Sai tên đăng nhập hoặc mật khẩu.';
        }
    }
}

$token = csrf_token();

render(
    'Đăng nhập',
    '<div class="card" style="max-width:420px;margin:40px auto">'
    . '<h2>Đăng nhập</h2>'
    . ($error !== '' ? '<p class="err">' . e($error) . '</p>' : '')
    . '<form method="post" action="/login.php">'
    . '<input type="hidden" name="csrf" value="' . e($token) . '">'
    . '<label>Tên đăng nhập<input type="text" name="username" autocomplete="username" required></label>'
    . '<label>Mật khẩu<input type="password" name="password" autocomplete="current-password" required></label>'
    . '<button type="submit">Đăng nhập</button>'
    . '</form>'
    . '</div>',
    null
);
