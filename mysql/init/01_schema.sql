-- De 07: Web server load balancing cluster
-- Khoi tao du lieu cho cum may chu web.

USE de07_web;

SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS users (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    -- COLLATE utf8mb4_bin la co y. Collation mac dinh cua MariaDB 11.4 la
    -- utf8mb4_uca1400_ai_ci: khong phan biet hoa thuong, khong phan biet dau
    -- va bo khoang trang duoi cung. Khi do 'DANHPT', 'dànhpt' va 'danhpt '
    -- cung tra ve dong cua 'danhpt', nghia la mot tai khoan co the dang nhap
    -- bang bien the cua ten khac. Dinh danh truc thuoc thi phai so sanh
    -- nguyen van; mat khau van duoc kiem tra bang password_verify nen khong
    -- bi anh huong.
    username      VARCHAR(64)  CHARACTER SET utf8mb4 COLLATE utf8mb4_bin
                               NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name     VARCHAR(128) NOT NULL,
    role          ENUM('admin','member') NOT NULL DEFAULT 'member',
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS news (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    title        VARCHAR(200) NOT NULL UNIQUE,
    summary      VARCHAR(400) NOT NULL,
    body         TEXT NOT NULL,
    author       VARCHAR(128) NOT NULL,
    published_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Nhat ky dang nhap. Moi node ghi ve cung mot bang nen sau khi mot node
-- chet, chuoi kien van du de truy van, khong bi mat theo node do.
CREATE TABLE IF NOT EXISTS login_audit (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    username    VARCHAR(64)  NOT NULL,
    success     TINYINT(1)   NOT NULL,
    client_ip   VARCHAR(45)  NOT NULL,
    node_name   VARCHAR(32)  NOT NULL,
    occurred_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_login_audit_time (occurred_at),
    INDEX idx_login_audit_user (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tai khoan demo. Mat khau duoc luu duoi dang bcrypt (password_hash,
-- thuat toan BCRYPT), khong bao gio luu bang chuong. Ca ba tai khoan dung
-- chung mot mat khau lab: Lab@De07. Day la fixture cua moi truong nay, khong
-- phai mat khau that cua ai, nen co the cong khai.
INSERT INTO users (username, password_hash, full_name, role) VALUES
    ('danhpt',    '$2y$10$E5rFGI7yVP6XBFPgHbUCYOELTgfnRpRnZWROuK0eU6P0pHANa7aNq', 'Phan Thành Danh', 'admin'),
    ('hoangtung', '$2y$10$R7qZIYNGUVrCHz62px8COeob7KsFpH7oa/wXRqEDGyC4FAvSLOy/q',  'Nghiêm Xuân Hoàng Tùng', 'member'),
    ('tungtt',    '$2y$10$RPS.cLazkUj6U5nSEv5goO4hNjbuzmePCWy5/j6E8xMuJnwS/VRay',  'Trịnh Thanh Tùng', 'member')
ON DUPLICATE KEY UPDATE password_hash = VALUES(password_hash),
                        full_name = VALUES(full_name);

INSERT INTO news (title, summary, body, author, published_at) VALUES
('Tính sẵn dùng là gì trong bảo mật ứng dụng web',
 'Tính sẵn dùng là một trong ba yêu cầu cơ bản của an toàn thông tin, bên cạnh bí mật và toàn vẹn.',
 'Ba yêu cầu cơ bản của an toàn thông tin là bí mật, toàn vẹn và sẵn dùng. Với ứng dụng web, tấn công làm gián đoạn dịch vụ nhắm trực tiếp vào yêu cầu thứ ba. Cân bằng tải máy chủ web là một biện pháp kỹ thuật phục vụ yêu cầu này: khi một node gặp sự cố, load balancer chuyển yêu cầu sang các node còn lại.',
 'Nhóm 15', '2026-09-01 08:00:00'),
('Load balancer tầng 4 và tầng 7 khác nhau ở đâu',
 'Tầng 4 quyết định theo IP và cổng, tầng 7 đọc được nội dung HTTP nên định tuyến thông minh hơn.',
 'Load balancer tầng 4 làm việc với thông tin của tầng vận chuyển, tức là địa chỉ IP và cổng TCP, nên tốc độ xử lý cao nhưng không phân biệt được đường dẫn URI. Load balancer tầng 7 đọc được header, cookie và đường dẫn nên có thể chuyển /api sang cụm API, chuyển /images sang cụm tĩnh, và duy trì phiên dựa trên cookie.',
 'Nhóm 15', '2026-09-03 10:30:00'),
('Vì sao session phải để ngoài node web',
 'Nếu session lưu trên đĩa của node, mất một node là mất phiên của toàn bộ người dùng đang gắn với node đó.',
 'Khi mỗi node tự lưu session vào tệp cục bộ, người dùng buộc phải được đưa trở lại đúng node cũ, tức là phải dùng cơ chế sticky session. Sticky session làm giảm chất lượng cân bằng tải và khiến việc mất một node trở thành mất dịch vụ với nhóm người dùng gắn vào node đó. Lưu session vào một kho dùng chung như Redis cho phép mọi node phục vụ mọi phiên.',
 'Nhóm 15', '2026-09-05 14:00:00'),
('Ràng buộc khi để load balancer giải mã TLS',
 'TLS kết thúc tại load balancer thì đoạn từ load balancer về node có còn được mã hóa không.',
 'Kết thúc TLS tại load balancer giúp gom chứng chỉ, dùng session cache và offload tính toán mã hóa. Đổi lại, đoạn truyền từ load balancer về node web có thể đi dưới dạng HTTP thuần. Vì vậy node web phải nằm ở mạng riêng không định tuyến được từ ngoài, và nếu hai thành phần khác vật lý thì phải dùng TLS ở cả hai đầu.',
 'Nhóm 15', '2026-09-08 09:15:00'),
('Đo thời gian gián đoạn khi một node chết',
 'Phép đo phải chạy liên tục và ghi timestamp từng request thì mới kết luận được hệ thống chịu lỗi tốt đến đâu.',
 'Cách đo đơn giản là gửi một luồng request đều đặn và ghi lại mã trạng thái kèm thời điểm. Khi phát hiện lỗi, thời gian gián đoạn bằng hiệu giữa thời điểm request thành công đầu tiên sau lỗi và thời điểm request lỗi đầu tiên. Cấu hình max_fails và fail_timeout của nginx quyết định trực tiếp hai con số này.',
 'Nhóm 15', '2026-09-12 16:45:00')
ON DUPLICATE KEY UPDATE title = VALUES(title);
