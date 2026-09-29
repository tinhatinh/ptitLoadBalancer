<?php
declare(strict_types=1);

if (realpath($_SERVER['SCRIPT_FILENAME'] ?? '') === realpath(__FILE__)) {
    http_response_code(404);
    exit;
}

function env(string $key, string $default = ''): string
{
    $value = getenv($key);
    return ($value === false || $value === '') ? $default : $value;
}

function node_name(): string
{
    return env('NODE_NAME', 'unknown');
}

function db(): mysqli
{
    static $conn = null;
    static $failed = false;

    if ($conn instanceof mysqli) {
        return $conn;
    }
    // Khi MariaDB khong tra loi, viec mo ket noi keo dai hang chuc giay trong
    // khi load balancer chi cho php-fpm 10 giay (proxy_read_timeout). Khong
    // dat gioi han thi khach hang nhan 504 va request chiem chin slot cua
    // php-fpm. That bai trong 2 giay la du de trang van con phuc vu duoc.
    // Co $failed ngan lan goi tiep theo trong cung request khong phai cho.
    if ($failed) {
        throw new RuntimeException('Khong ket noi duoc co so du lieu.');
    }

    mysqli_report(MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT);
    $candidate = mysqli_init();
    $candidate->options(MYSQLI_OPT_CONNECT_TIMEOUT, 2);
    try {
        $candidate->real_connect(
            env('DB_HOST', 'mysql01'),
            env('DB_USER', 'webapp'),
            env('DB_PASSWORD'),
            env('DB_NAME', 'de07_web'),
            (int) env('DB_PORT', '3306')
        );
        $candidate->set_charset('utf8mb4');
    } catch (Throwable $e) {
        $failed = true;
        throw $e;
    }
    $conn = $candidate;
    return $conn;
}

function db_available(): bool
{
    try {
        db()->query('SELECT 1');
        return true;
    } catch (Throwable) {
        return false;
    }
}

function start_session(): void
{
    if (session_status() === PHP_SESSION_ACTIVE) {
        return;
    }
    session_name('DE07SID');
    session_set_cookie_params([
        'lifetime' => 0,
        'path'     => '/',
        'secure'   => true,
        'httponly' => true,
        'samesite' => 'Lax',
    ]);
    session_start();
}

function current_user(): ?array
{
    start_session();
    return $_SESSION['user'] ?? null;
}

function require_login(): array
{
    $user = current_user();
    if ($user === null) {
        header('Location: /login.php');
        exit;
    }
    return $user;
}

function e(?string $value): string
{
    return htmlspecialchars((string) $value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

function csrf_token(): string
{
    start_session();
    if (empty($_SESSION['csrf'])) {
        $_SESSION['csrf'] = bin2hex(random_bytes(32));
    }
    return $_SESSION['csrf'];
}

function csrf_ok(?string $token): bool
{
    start_session();
    return is_string($token)
        && !empty($_SESSION['csrf'])
        && hash_equals($_SESSION['csrf'], $token);
}

function client_ip(): string
{
    return $_SERVER['REMOTE_ADDR'] ?? '0.0.0.0';
}

/** Doc dong users theo ten dang nhap. Tra ve null khi khong co tai khoan,
 *  nem exception khi khong doc duoc co so du lieu. */
function lookup_user(string $username): ?array
{
    $stmt = db()->prepare(
        'SELECT id, username, password_hash, full_name, role FROM users WHERE username = ?'
    );
    $stmt->bind_param('s', $username);
    $stmt->execute();
    return $stmt->get_result()->fetch_assoc() ?: null;
}

function record_login_attempt(string $username, bool $success): void
{
    try {
        $stmt = db()->prepare(
            'INSERT INTO login_audit (username, success, client_ip, node_name) VALUES (?, ?, ?, ?)'
        );
        $flag = (int) $success;
        $node = node_name();
        $ip   = client_ip();
        $stmt->bind_param('siss', $username, $flag, $ip, $node);
        $stmt->execute();
    } catch (Throwable) {
        // Nhat ky khong duoc phep lam hong luong dang nhap.
    }
}

function render(string $title, string $body, ?array $user): void
{
    $nav_user = $user === null
        ? '<a href="/login.php">Đăng nhập</a>'
        : '<a href="/member.php">' . e($user['full_name']) . '</a> &middot; <a href="/logout.php">Đăng xuất</a>';
    $user_node = node_name();

    echo <<<HTML
<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{$title} &middot; PTIT Bookshelf</title>
<style>
body{font-family:system-ui,"Segoe UI",Arial,sans-serif;margin:0;color:#1b1b1b;background:#f6f7f9}
header{background:#123a63;color:#fff;padding:14px 28px;display:flex;justify-content:space-between;align-items:center}
header a{color:#cfe1f5;text-decoration:none}
main{max-width:900px;margin:26px auto;padding:0 20px}
.card{background:#fff;border:1px solid #dfe3e8;border-radius:6px;padding:16px 18px;margin-bottom:14px}
.meta{color:#5c6672;font-size:13px}
input[type=text],input[type=password]{width:100%;padding:9px;margin:6px 0 14px;border:1px solid #c3cad3;border-radius:4px;box-sizing:border-box}
button{background:#123a63;color:#fff;border:0;padding:10px 20px;border-radius:4px;cursor:pointer}
table{border-collapse:collapse;width:100%}
td,th{border-bottom:1px solid #e3e7ec;padding:8px 10px;text-align:left;font-size:14px}
.badge{display:inline-block;background:#e8f0fa;color:#123a63;border-radius:10px;padding:2px 10px;font-size:13px}
.err{color:#a32020}
footer{text-align:center;color:#7b858f;font-size:13px;padding:24px}
</style>
</head>
<body>
<header>
  <strong>PTIT Bookshelf</strong>
  <nav>{$nav_user} &middot; <span class="badge">node: {$user_node}</span></nav>
</header>
<main>
{$body}
</main>
<footer>Cum may chu web &middot; de tai 07 &middot; nhom 15</footer>
</body>
</html>
HTML;
}
