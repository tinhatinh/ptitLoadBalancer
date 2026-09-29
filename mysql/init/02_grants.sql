-- It quyen han toi thieu cho tai khoan ma ung dung dung.
--
-- Image MariaDB tao `webapp` tu MARIADB_USER va mac dinh phong
-- ALL PRIVILEGES tren toan bo de07_web, tuc la ca DROP, ALTER, DELETE. Ung
-- dung chi lam ba viec: SELECT news, SELECT users, INSERT login_audit.
-- Mot loi SQL injection hay mot container bi chiem cung khong con duoc kha
-- nang xoa bang hay doi cau truc.
--
-- File nay chay sau 01_schema.sql khi volume con trong (docker-entrypoint-initdb.d),
-- nen clone moi la co duoc bang quyen han nay. May da chay lau phai doi theo
-- huong dan trong README.

USE de07_web;

REVOKE ALL PRIVILEGES, GRANT OPTION FROM 'webapp'@'%';

GRANT SELECT, INSERT ON `de07\_web`.* TO 'webapp'@'%';

FLUSH PRIVILEGES;
