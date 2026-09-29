# Ghi chú trả lời hội đồng (không nằm trong báo cáo)

File này chứa những phần đã rút khỏi báo cáo để báo cáo gọn, cộng các điểm
hội đồng có thể hỏi. Không build file này vào `.docx`.

## 1. Những gì đề tài KHÔNG kiểm tra về mặt tấn công

Bảng kiểm ở mục 3.6 chỉ chứng minh cấu hình đang chạy. Nếu hội đồng hỏi
"vậy hệ thống có chống được tấn công không", câu trả lời trung thực là đề tài
không đo điều đó: chưa có request tấn công thật cho SQL injection, XSS, CSRF,
session fixation, bỏ qua giới hạn tần suất, HTTP request smuggling, và chưa đánh
giá TLS ở chiều sâu (danh sách mật mã, chuỗi chứng chỉ, hạ phiên bản, phục hồi
phiên).

Lý do: đề tài số 7 yêu cầu kiểm tra phân phối request và khả năng đáp ứng khi
một máy chủ gặp sự cố, tức hai thuộc tính phục vụ tính sẵn dùng. Các tấn công
trên nhắm vào tính bí mật và tính toàn vẹn, cần công cụ quét riêng và môi trường
cách ly riêng.

Chi tiết việc cần làm nếu mở rộng nằm ở `docs/HUONG-DAN-TIEP-TUC.md`, kèm nhận
xét về nơi mã nguồn còn đất diễn.

## 2. Hai hạn chế đã rút khỏi mục 3.7

- **Đoạn từ load balancer về node là HTTP thuần.** Đã trình bày ở mục 2.7.5
  như một đánh đổi có chủ đích của việc kết thúc TLS tập trung. Nếu bị hỏi:
  backend đang ở mạng `internal` không định tuyến được từ ngoài, và node chỉ
  trả lời đúng địa chỉ của load balancer; khi node nằm ở máy vật lý khác thì
  phải bật TLS giữa hai đầu.
- **MariaDB và Redis là hai điểm hỏng đơn lẻ.** Đã nằm trong phần định hướng
  phát triển của Kết luận (nhân bản MariaDB, Redis Sentinel). Nếu bị hỏi: đúng,
  cụm hiện chịu được một node web chết, không chịu được Redis chết.

## 2b. Vì sao chọn `allow`/`deny` ở nginx mà không chọn iptables hay mTLS

Hội đồng có thể hỏi "nói triển khai firewall hoặc mTLS sao lại chỉ thêm hai dòng
nginx". Trả lời:

- **iptables trong container** cần `cap_add: NET_ADMIN` và gói `iptables` trong
  image Alpine của node. Nó chặn được ở tầng 3/4, mạnh hơn, nhưng phải đổi
  Dockerfile, đổi compose và cho container quyền quản trị mạng. Trong phạm vi
  đề tài, cái cần chứng minh là "node không phục vụ người gọi lạ", và tầng ứng
  dụng chứng minh được điều đó với đúng một cuộc gọi kiểm chứng lại được.
- **mTLS giữa LB và node** phải đổi node sang nghe TLS, sinh CA, chứng chỉ server
  cho ba node, chứng chỉ client cho LB, bật `proxy_ssl_*` và SNI ở chiều LB.
  Việc đó làm thay đổi toàn bộ đường truyền đang được đo ở mục 3.5 nên cần đo
  lại từ đầu; để ngỏ như hướng phát triển.
- **Điều lớp `allow`/`deny` không chặn được**: kẻ tấn công trong mạng backend vẫn
  thấy cổng 80 mở và nhận về 403, tức biết dịch vụ tồn tại; và vì đoạn trong là
  HTTP thuần nên đọc được nội dung, dù không đọc được dữ liệu ứng dụng. Nói rõ
  giới hạn này ở mục 2.7.3.

## 2c. Vì sao phép đo failover phải chạy 12 lần

Bảng 3.2 trước đây lấy từ một vòng đo duy nhất, nên "chín mẫu chậm" là một quan
sát đơn lẻ. Chạy lại 12 vòng cho thấy con số đó ổn định: 9, 9, 9, 9, 10, 8, 9, 8,
8, 8, 9, 9, trung bình 8,8 với nửa khoảng tin cậy 0,4. Hai con số dao động mạnh
hơn là tổng số mẫu của một vòng (174 đến 232) và thời gian đáp ứng trung bình
(77 đến 130 ms), vì vòng đo dừng theo thời gian chứ không theo số request.

## 2d. Lỗi của chính công cụ đo đã gặp khi lặp lại phép failover

- Lần lặp thứ 10 không tạo được bảng tổng hợp mới, và script gom dữ liệu lấy lại
  tệp của lần thứ 9, nên bảng 12 vòng có một dòng trùng. Nguyên nhân sâu hơn:
  sửa file `failover.sh` trong khi nó đang chạy. Đã loại dòng đó và chạy bù một
  vòng sạch.
- `retries-*.log` gom từ access log của container `lb01`, mà log này chỉ mất khi
  container khởi động lại. Chạy nhiều vòng liên tiếp nên các vòng sau đếm cả
  lần thử lại của vòng trước (8, 18, 27, 36, ... tăng dần vô lý). Đã sửa bằng
  cách ghi lại mốc dòng của log trước khi mở vòng đo và chỉ cắt từ mốc đó.

## 3. Câu hỏi hay gặp và điểm chốt

**Vì sao không dùng HAProxy?** nginx có sẵn ở cả hai vai trò, và đề tài cần một
điểm khác biệt là để nguyên nginx mã nguồn mở để thấy giới hạn của kiểm tra sức
khỏe thụ động. HAProxy có `option httpchk`, sẽ loại được các request chờ hai
giây; đó là hướng phát triển đã ghi.

**Vì sao round robin đều hơn least_conn trong khi lý thuyết nói ngược lại?**
Least connection chọn theo số kết nối đang mở. Ba node đồng chất, đáp ứng 30
byte như nhau, nên tại thời điểm chọn các node gần như hòa nhau; thuật toán
quyết định trên mẫu nhiễu rất nhỏ và tích lũy sai số đó (độ lệch 10,2 request
so với 1,0 của round robin). Least connection chỉ có lợi khi node không đồng
chất hoặc có request chậm.

**Số liệu có tin được không?** Mỗi cấu hình 20 lượt độc lập, có lượt làm nóng
bị loại, báo cáo trung bình kèm khoảng tin cậy 95% và kiểm định Welch. Kết luận
nào khoảng tin cậy chồng lên nhau thì báo cáo nói rõ là chưa xếp hạng được.

**Vì sao thông qua chỉ khoảng 800 req/s?** Đó là giới hạn của ba node nginx cộng
php-fpm trên một máy tính. Bản thân bộ cân bằng tải đạt 31.360 req/s khi tự trả
lời. Nếu bị hỏi "load balancer có phải nút cổ chai không", câu trả lời là không,
với điều kiện nói rõ đang đo đường nào.

**Mất một node thì hệ thống chậm đi bao nhiêu?** Trung bình chỉ giảm 7,7%, nhưng
phương sai tăng gấp bốn và request chậm nhất nhảy từ 54 ms lên 1048 ms. Tác
động nằm ở đuôi phân phối, không nằm ở mức trung bình.

**ip_hash có gì đáng nói?** Với một địa chỉ nguồn, toàn bộ lưu lượng đi về một
node. Đường `/healthz` thì ip_hash còn nhanh hơn (một node gánh đủ, không phải
chia), nhưng đường phải truy vấn cơ sở dữ liệu thì chậm hơn 10,4%. Đây là ví dụ
vì sao không được chọn thuật toán chỉ vì một con số thông qua.

## 4. Lỗi đã gặp và cách sửa (nếu bị hỏi "thu được gì")

Bốn lỗi im lặng, không báo lỗi mà chỉ làm tính năng mất tác dụng:

1. `limit_req` không áp dụng cho location chỉ có `return` (rewrite chạy trước
   preaccess).
2. `location ~ ^/(config\.php|\.env)` đặt sau `~ \.php$` nên không bao giờ
   được chọn; phải dùng `location =`.
3. php-fpm `clear_env = yes` mặc định xóa biến môi trường của container.
4. Bản thân kiểm tra giới hạn tần suất đếm "Non-2xx" trên cổng 80, nơi mọi
   request đều là 301 chuyển hướng, nên nó báo đạt liên tục.

Một lỗi thuộc về phương pháp đo: script đổi thuật toán load balancer nhưng
không đặt lại, nên phép đo chạy sau bị dính `ip_hash` và toàn bộ lưu lượng dồn
về một node mà không có lỗi nào được báo. Sau này mọi script đo tự đặt cấu hình
của nó.

## 5. Hai lỗi ứng dụng tìm ra khi cho MariaDB chết hẳn

Nếu bị hỏi "hệ thống phản ứng thế nào khi cơ sở dữ liệu chết", đây là câu trả
lời, kèm hai lỗi đã sửa trong lượt soát cuối:

- `POST /login.php` trả 500 với thân rỗng. Tệp này gọi `db()` mà không bọc
  `try/catch`, trong khi `index.php` và `dbping.php` thì có. Exception thoát ra
  ngoài làm php-fpm ghi stack trace, kèm đường dẫn tuyệt đối của node, vào
  `error.log`. Khách hàng không thấy gì vì `display_errors` tắt, nhưng log thì
  có.
- `GET /index.php` trả 504 sau đúng 10 giây, tức chạm `proxy_read_timeout` của
  load balancer chứ ứng dụng chưa kịp tự trả lời. Nguyên nhân sâu: `new mysqli()`
  không đặt thời hạn chờ, mà tên `mysql01` khi container đã dừng thì mỗi lần
  phân giải mất khoảng 5 giây; một request gọi tới hai lần nên vượt ngưỡng.

Sau khi sửa (`MYSQLI_OPT_CONNECT_TIMEOUT` hai giây, nhớ lần thất bại trong cùng
request, bọc `try/catch` ở `login.php` và `audit.php`) thì: trang chủ trả 200 kèm
dòng "không kết nối được cơ sở dữ liệu", `dbping.php` trả 200 với `"ok":0`, đăng
nhập trả 503 kèm thông báo mời thử lại, còn `/healthz` vẫn 200 trong 8 ms vì
không chạm tới cơ sở dữ liệu. Ba đường đầu vẫn mất khoảng 5 giây, đó là thời gian
phân giải tên của Docker DNS chứ không phải thời gian kết nối TCP; giới hạn này
nên nói thẳng nếu bị hỏi tiếp, hướng khắc phục là tĩnh tên `mysql01` trong
`/etc/hosts` của node hoặc cho `DB_HOST` bằng địa chỉ IP.

Cũng trong lượt soát này, phép kiểm định số vòng của failover được siết lại:
dòng thiếu dữ liệu trong bảng 12 vòng trước đây bị dụng cụ tổng hợp loại im
lặng, còn `verify_numbers.py` chỉ yêu cầu "từ 10 vòng". Nay bắt buộc đúng 12 và
báo lỗi nếu có dòng bị loại.

## 6. Lỗi tầng hạ tầng và cơ sở dữ liệu tìm ra ở lượt soát cuối

Các lỗi dưới đây chỉ lộ ra khi thử đường đi ngược, tức tắt hẳn một dịch vụ hoặc
đưa dữ liệu ngoài biên độ, chứ không lộ ra khi hệ thống chạy đúng.

- **Redis đặt `allkeys-lru` cho kho phiên.** Khoá phiên và khoá cache bị đối xử
  như nhau, nên khi đầy bộ nhớ Redis loại cả phiên đang hoạt động và người dùng
  bị đăng xuất không kèm lỗi nào. Đổi sang `noeviction`: thà ghi thất bại và
  thấy lỗi còn hơn mất phiên trong im lặng.
- **Load balancer không chờ node.** `depends_on` dạng ngắn chỉ sắp thứ tự tạo
  container, không chờ sẵn sàng, và node web không có healthcheck. Kết quả là
  loạt request đầu sau `docker compose up` có thể nhận 502. Nay mỗi node có
  healthcheck trên `/healthz` và `lb01` chờ cả ba healthy.
- **Chuyển hướng 301 mất cổng.** `return 301 https://$host$request_uri` biến
  `http://localhost:8080` thành `https://localhost/`, nơi không có gì nghe, vì
  HTTPS được công bố ở 8443. Đã sửa bằng `map` chỉ chấp nhận đúng hai giá trị
  Host của máy chủ, không lấy chuỗi Host tuỳ ý của khách hàng vì cách đó mở thêm
  một cổng chuyển hướng qua header Host.
- **Cổng của load balancer binds trên mọi giao diện.** Nghĩa là mọi máy trong
  cùng mạng gọi được vào một load balancer tự ký mang mật khẩu dev. Nay bind
  `127.0.0.1`.
- **Tên đăng nhập không phân biệt hoa thường.** Cột `username` thừa hưởng
  `utf8mb4_uca1400_ai_ci` của MariaDB 11.4, nên `DANHPT` và `dànhpt` cùng trả về
  dòng của `danhpt`: một tài khoản đăng nhập được bằng biến thể tên khác. Đã
  chuyển sang `utf8mb4_bin` và kiểm chứng: `DANHPT` với mật khẩu đúng bị từ chối.
- **Nhật ký đăng nhập mất dấu vết đúng chỗ cần nhất.** `login_audit.username`
  dài 64 ký tự và MariaDB chạy `STRICT_TRANS_TABLES`; username 65 ký tự trở lên
  làm INSERT báo lỗi 1406, còn `record_login_attempt()` nuốt mọi exception để
  không phá luồng đăng nhập. Hệ quả là một chuỗi brute-force dùng tên dài để lại
  không một dòng trong `/audit.php`. Nay giá trị được cắt đúng chiều dài cột
  trước khi ghi.
- **Tài khoản ứng dụng có `ALL PRIVILEGES`.** Image MariaDB cấp toàn quyền trên
  schema cho `webapp`, trong khi mã nguồn chỉ chạy hai câu SELECT và một câu
  INSERT. Thêm `mysql/init/02_grants.sql` rút về `SELECT, INSERT`.
- **Cột `news.views` không bao giờ được ghi.** Trang chủ in "%d lượt xem" với
  giá trị luôn bằng 0. Đã bỏ cả cột lẫn dòng hiển thị, thay vì giữ một con số
  không có nguồn.
- **Mốc thời điểm trong nhật ký là UTC mà không ghi rõ trục.** Container
  MariaDB chạy UTC, người đọc ở Việt Nam lệch bảy giờ. Tiêu đề cột nay là
  "Thời điểm (UTC)".
- **`ssl_session_tickets` còn bật**, cho phép phục hồi phiên không qua bắt tay
  mà không có đường thu hồi; chứng chỉ là RSA nên các bộ mật mã ECDSA trong danh
  sách không bao giờ được chọn.
- **`gen_certs.sh` không đặt quyền 600 cho khoá riêng.** Trên Linux file sinh ra
  theo umask của hệ thống tức 0644; trên Windows thuộc tính này không có ý nghĩa
  nên không kiểm chứng bằng mắt được.
- **File keepalived mẫu không khởi động được**: `auth_pass CHANGE_ME` dài 9 ký
  tự trong khi keepalived giới hạn mật khẩu VRRP ở 8 ký tự. README của thư mục
  này nêu một tên directive không có trong file và mâu thuẫn với chính file về
  multicast so với unicast.

Hai điểm về phương pháp đáng nói hơn cả danh sách trên. Một là
`verify_numbers.py` từng in "KHOP" trong khi báo cáo tự mâu thuẫn (193 ở phần
văn, 194 ở caption hình), vì hàm kiểm tra chỉ cần *một* trong các cách diễn đạt
là khớp; đã thêm `expect_every()` bắt mọi chỗ phải nhất quán, và đã thử lại bằng
cách cố tình đặt một giá trị sai xem nó có bị bắt không. Hai là ảnh chụp màn
hình cũng là bằng chứng và cũng sai được: ảnh 18 chiếu 193 cạnh caption 194, và
lần dựng lại đầu tiên vẫn ra ảnh cũ vì bỏ qua bước `crop_shots.py` (bài dựng lấy
ảnh từ `figures/`, không phải `screenshots/`).
