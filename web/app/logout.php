<?php
declare(strict_types=1);

require __DIR__ . '/lib/bootstrap.php';

start_session();
$_SESSION = [];
if (ini_get('session.use_cookies')) {
    setcookie(session_name(), '', [
        'expires'  => time() - 3600,
        'path'     => '/',
        'secure'   => true,
        'httponly' => true,
        'samesite' => 'Lax',
    ]);
}
session_destroy();
header('Location: /login.php');
exit;
