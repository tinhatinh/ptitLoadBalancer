#1 CHƯƠNG 2. THIẾT KẾ VÀ TRIỂN KHAI CỤM MÁY CHỦ WEB CÂN BẰNG TẢI

#2 2.1 Yêu cầu đặt ra

Đề bài yêu cầu xây dựng một cụm gồm hai đến ba máy chủ web phục vụ cùng một website cùng một thành phần cân bằng tải, sau đó kiểm tra phân phối request và khả năng đáp ứng khi một server gặp sự cố. Từ yêu cầu đó và từ bốn vấn đề rút ra ở Kết chương 1, đề tài đặt ra sáu yêu cầu cụ thể cho phần triển khai.

Thứ nhất, cụm có ba node web độc lập, cùng một bản ảnh, cùng nội dung, và bộ cân bằng tải phải chọn được node theo thuật toán khai báo. Thứ hai, khi tắt hẳn một node, dịch vụ vẫn trả lời mà người dùng không phải làm lại thao tác. Thứ ba, phiên đăng nhập không nằm trong node, nên node chết không làm mất phiên. Thứ tư, dữ liệu người dùng đọc từ một cơ sở dữ liệu dùng chung, bảo đảm mọi node trả về cùng nội dung. Thứ năm, node web không được phép tiếp nhận kết nối từ ngoài và không được tiết lộ thông tin hệ thống. Thứ sáu, mọi phép đo ở Chương 3 phải chạy lại được bằng một lệnh và lưu được log thô.

#2 2.2 Kiến trúc tổng thể

[[FIG:kien-truc|Kiến trúc triển khai của cụm ba máy chủ web]]

Toàn bộ hệ thống chạy trên một máy vật lý, tổ chức bằng Docker Compose. Mỗi thành phần là một container thật, nghe trên cổng thật và nói chuyện với nhau qua hai mạng ảo riêng biệt. Lưu thông giữa các thành phần là HTTP và TCP thật, không có lớp mô phỏng.

Việc gom nhiều container vào một máy chỉ thay đổi chỗ đặt thiết bị, không thay đổi đường đi của gói tin: yêu cầu vẫn đi từ máy khách tới bộ cân bằng tải, bộ cân bằng tải vẫn mở một kết nối TCP mới tới node, và node vẫn tự đọc cơ sở dữ liệu.

#3 2.2.1 Hai mạng và lý do tách

Mạng `frontend` (192.168.240.0/24) nối máy khách với bộ cân bằng tải. Mạng `backend` (172.20.0.0/24) nối bộ cân bằng tải với ba node, kho phiên và cơ sở dữ liệu. Mạng backend khai báo `internal: true`, nghĩa là Docker không cấp cho nó đường ra bên ngoài và không định tuyến nó đi đâu cả.

Hệ quả kiểm chứng được bằng lệnh: gọi thẳng một node từ máy khách thì không nối được, gọi từ node này sang node khác trong cùng mạng thì vẫn bình thường. Đây là biện pháp cách ly chính của đề tài, đặt ở tầng mạng thay vì dựa vào cấu hình trên node.

[[FIG:luong-request|Đường đi của một yêu cầu qua cụm]]

[[FIG:anh-hinh-02|Kiểm tra cấu hình mạng: mạng backend khai báo internal nên không có đường ra ngoài|16]]

#3 2.2.2 Quy hoạch địa chỉ

[[TAB:dia-chi|Bảng địa chỉ và cổng của các thành phần]]
tbl:
| Thành phần | Container | Địa chỉ | Vai trò | Cổng công bố ra máy |
| Bộ cân bằng tải | lb01 | 192.168.240.10 và 172.20.0.10 | nginx 1.27, TLS, chọn node | 8080, 8443 |
| Node web 1 | web01 | 172.20.0.11 | nginx và php-fpm 8.3 | không |
| Node web 2 | web02 | 172.20.0.12 | nginx và php-fpm 8.3 | không |
| Node web 3 | web03 | 172.20.0.13 | nginx và php-fpm 8.3 | không |
| Kho phiên | redis01 | 172.20.0.20 | Redis 7, lưu session | không |
| Cơ sở dữ liệu | mysql01 | 172.20.0.30 | MariaDB 11.4 | không |
| Máy đo | client01 | 192.168.240.20 | curl, ab | không |
#tc

Chỉ `lb01` có cổng công bố ra máy chủ. Máy khách trong mạng nội bộ gọi tới 192.168.240.10, còn khi cần xem bằng trình duyệt thì gọi qua cổng 8443 của máy chủ.

[[FIG:anh-hinh-01|Trạng thái cụm sau khi khởi động: bảy container đang chạy và chỉ lb01 có cổng công bố ra máy chủ|16]]

#3 2.2.3 Vì sao phải có một container máy đo riêng

Nếu phát yêu cầu từ Windows thì Docker Desktop sẽ dịch địa chỉ nguồn qua NAT, mọi request đều mang cùng một địa chỉ và không phân biệt được. Hai hệ quả: phép thử ip hash cho kết quả vô nghĩa, và chuỗi IP trong log không còn là bằng chứng. Container `client01` nằm cùng mạng frontend với bộ cân bằng tải nên địa chỉ nguồn là thật, giữ được ý nghĩa cho cả hai phép đo.

#2 2.3 Tổ chức mã nguồn

Cây thư mục của đề tài như sau.

[[TAB:cay-thu-muc|Cấu trúc thư mục của đề tài]]
tbl:
| Đường dẫn | Nội dung |
| docker-compose.yml | Khai báo bảy service, hai mạng, một volume |
| nginx/lb/nginx.conf | Cấu hình gốc của bộ cân bằng tải, vùng giới hạn tần suất, định dạng log |
| nginx/lb/templates/default.conf.template | Khối upstream và hai server block, điền tham số bằng biến môi trường |
| web/Dockerfile | Ảnh node web: Alpine 3.20, nginx, php-fpm 8.3, phpredis |
| web/nginx.conf | Cấu hình nginx trên từng node |
| web/entrypoint.sh | Khởi động php-fpm và nginx, sinh cấu hình phiên lúc chạy |
| web/app | Ứng dụng PHP demo |
| mysql/init/01_schema.sql | Bảng users, news, login_audit và dữ liệu mẫu |
| scripts | Sáu script đo và điều khiển |
| results | Log thô của mọi phép đo |
#tc

#2 2.4 Triển khai node web

#3 2.4.1 Ảnh container của node

Ba node dùng chung một ảnh, chỉ khác nhau biến môi trường `NODE_NAME`. Ảnh dựng trên Alpine 3.20 với hai gói `nginx` và `php83-fpm` đóng gói sẵn của phân phối, nên không phải biên dịch gì.

Một chi tiết bắt buộc phải sửa: php-fpm đặt `clear_env = yes` theo mặc định, nghĩa là nó xóa toàn bộ biến môi trường của container trước khi chạy tiến trình con. Nếu không đổi thành `clear_env = no`, ứng dụng gọi `getenv('DB_HOST')` sẽ nhận giá trị rỗng và không nối được cơ sở dữ liệu, dù trong shell của container biến đó vẫn tồn tại. Đây là lỗi chỉ lộ ra khi chạy thật.

#3 2.4.2 nginx trên node

Node nhận yêu cầu trên cổng 80, chuyển tệp tin tĩnh trực tiếp và đưa tệp `.php` sang php-fpm ở 127.0.0.1:9000. Đoạn cấu hình đáng chú ý:

```
allow 172.20.0.10;      # lb01
allow 127.0.0.1;        # kiem tra noi bo trong container
deny  all;

add_header X-Node "@NODE_NAME@" always;
fastcgi_hide_header  X-Powered-By;

map $http_x_real_ip $client_addr {
    default  $http_x_real_ip;
    ""       $remote_addr;
}

location ~ \.php$ {
    fastcgi_param REMOTE_ADDR $client_addr;
    ...
}
```

Ba dòng `allow`/`deny` buộc node chỉ phục vụ đúng bộ cân bằng tải. Cách viết tự nhiên là `set_real_ip_from` kết hợp `real_ip_header X-Forwarded-For` để `$remote_addr` luôn là IP khách hàng, nhưng làm vậy thì các quy tắc chặn lại lấy đúng cái đích cần chặn làm điều kiện: module realip chạy ở giai đoạn preaccess trước module access, nên khi `deny` được xét thì `$remote_addr` đã bị ghi đè bằng địa chỉ đọc từ tiêu đề, tức là từ dữ liệu người gọi gửi lên. Node vì thế không dùng realip nữa; IP khách hàng đi qua một tiêu đề riêng do bộ cân bằng tải ghi là `X-Real-IP`, được đưa vào log và truyền cho PHP qua `fastcgi_param REMOTE_ADDR`. Dòng log ở node và ở bộ cân bằng tải vẫn ghi cùng một địa chỉ khách hàng, nên truy được một yêu cầu xuyên hai tầng, nhưng quyết định cho-phép chỉ dựa trên địa chỉ của bao TCP thật.

`@NODE_NAME@` được thay bằng tên node thật trong `entrypoint.sh` lúc khởi động. Header này là dụng cụ đo của đề tài: không có nó thì không đếm được request rơi vào node nào. Trong hệ thống thật nên tắt.

Hai chi tiết về thứ tự ưu tiên của `location` chỉ lộ ra khi thử bằng request thật.

Đường `/healthz` lúc đầu viết là `try_files $uri /healthz.php =404` đặt trong `location = /healthz`. Cách viết đó cho phép nginx trả chính tệp `healthz.php` như một tệp tĩnh, tức là in ra mã nguồn PHP thay vì thực thi nó. Bản hiện tại bỏ `try_files` và khai báo thẳng `fastcgi_param SCRIPT_FILENAME /var/www/public/healthz.php`, nên đường duy nhất tới tệp PHP là qua khối xử lý FastCGI.

Rule chặn tệp cấu hình từng được viết `location ~ ^/(config\.php|\.env)` và đặt sau `location ~ \.php$`. nginx xét các regex theo thứ tự xuất hiện trong tệp, nên request tới `/config.php` đã bị khối xử lý `.php` bắt trước và rule chặn không bao giờ chạy, không kèm dấu hiệu nào. Viết lại thành `location = /config.php` thì đúng, vì match tuyệt đối có ưu tiên cao hơn mọi regex. Đây cũng là dạng lỗi im lặng: nginx vẫn nhận cấu hình, chỉ là điều khai báo để chặn thì không bao giờ được chọn.

#3 2.4.3 Ứng dụng demo

Ứng dụng viết bằng PHP, gồm trang chủ liệt kê bài viết đọc từ MariaDB, trang đăng nhập, trang thành viên yêu cầu có phiên, trang nhật ký dành cho quản trị viên, và đường `/healthz`.

Vài điểm liên quan tới bảo mật phiên được làm đúng theo giáo trình. Mật khẩu lưu bằng `password_hash` với bcrypt, không lưu dạng thuần. Câu truy vấn dùng `prepare` và `bind_param`. Sau khi xác thực thành công, `session_regenerate_id(true)` được gọi để đổi định danh phiên, chặn tấn công cố định phiên. Token chống CSRF sinh bằng `random_bytes(32)` và so bằng `hash_equals`.

Nhật ký đăng nhập ghi vào bảng `login_audit` kèm cột `node_name`. Vì bảng nằm trong cơ sở dữ liệu dùng chung, chuỗi sự kiện không mất đi khi một node bị tắt, khác với ghi ra tệp cục bộ của node.

#2 2.5 Cấu hình bộ cân bằng tải

#3 2.5.1 Khối upstream

```
upstream web_cluster {
    ${LB_ALGO_DIRECTIVE}

    server web01:${BACKEND_PORT} max_fails=${MAX_FAILS} fail_timeout=${FAIL_TIMEOUT};
    server web02:${BACKEND_PORT} max_fails=${MAX_FAILS} fail_timeout=${FAIL_TIMEOUT};
    server web03:${BACKEND_PORT} max_fails=${MAX_FAILS} fail_timeout=${FAIL_TIMEOUT};

    keepalive 32;
}
```

Image nginx chính thức có sẵn cơ chế thay thế biến môi trường vào các file template khi container khởi động, nên thuật toán và các ngưỡng trở thành tham số chạy được mà không phải sửa file cấu hình. Đổi thuật toán chỉ cần khởi động lại `lb01` với một biến môi trường khác.

Vòng `keepalive 32` giữ lại các kết nối tới node đã mở xong, tránh phải bắt tay TCP lại cho từng yêu cầu.

[[TAB:tham-so|Các tham số đưa ra biến môi trường]]
tbl:
| Biến | Mặc định | Ý nghĩa |
| LB_ALGO_DIRECTIVE | least_conn; | Dòng khai báo thuật toán trong upstream; để trống nghĩa là round robin |
| MAX_FAILS | 2 | Số lần lỗi liên tiếp để đánh dấu node không đạt |
| FAIL_TIMEOUT | 10s | Thời gian node bị loại, đồng thời là cửa sổ đếm lỗi |
| BACKEND_PORT | 80 | Cổng node lắng nghe |
| SESSION_STORE | redis | redis hoặc file, dùng để đối chứng ở Chương 3 |
#tc

#3 2.5.2 Chuyển tiếp và phát hiện lỗi

```
proxy_connect_timeout 2s;
proxy_read_timeout    10s;
proxy_next_upstream   error timeout http_500 http_502 http_503 http_504;
proxy_next_upstream_tries 2;
```

`proxy_connect_timeout 2s` là khoảng thời gian tối đa nginx chờ một node chấp nhận kết nối TCP. `proxy_next_upstream` liệt kê những trường hợp được phép chuyển sang node khác. Hai tham số này cùng quyết định độ dài của khoảng chờ mà người dùng phải chịu khi node đã chết, đo ở Chương 3.

Vì nginx bản mã nguồn mở không có kiểm tra sức khỏe chủ động, node chỉ bị phát hiện khi có một yêu cầu thật gửi tới và thất bại. Chi phí của cơ chế thụ động này chính là các request phải chờ hết 2 giây.

#3 2.5.3 Định dạng log

```
log_format lb_trace '$remote_addr - [$time_local] "$request" '
                    'status=$status upstream=$upstream_addr '
                    'upstream_status=$upstream_status '
                    'upstream_time=$upstream_response_time '
                    'req_time=$request_time xff="$http_x_forwarded_for"';
```

Biến `$upstream_addr` ghi lại mọi node mà nginx đã thử cho một yêu cầu. Một dòng log có hai địa chỉ cách nhau bởi dấu phẩy là bằng chứng của việc chuyển node, và `$upstream_status` cho biết node đầu trả mã gì. Toàn bộ số liệu failover trong Chương 3 lấy từ trường này.

#2 2.6 Kho phiên dùng chung

Phiên được chuyển sang Redis bằng hai dòng khai báo sinh trong `entrypoint.sh`:

```
session.save_handler = redis
session.save_path    = "tcp://redis01:6379?auth=...&database=0&prefix=de07:"
```

Redis chạy với `--requirepass`, `--maxmemory 128mb`, `--maxmemory-policy allkeys-lru` và `--save ""`, tức là dữ liệu phiên chỉ nằm trong bộ nhớ và không ghi đĩa. Đây là lựa chọn đúng cho đối tượng phiên: phiên có vòng đời ngắn, mất thì đăng nhập lại, đổi lại không phải chịu độ trễ ghi đĩa.

Các cờ cookie đặt tại node nên mọi node gửi về cùng một chính sách: `session.cookie_httponly`, `session.cookie_secure`, `session.cookie_samesite = Lax`, `session.use_strict_mode = 1` và `session.sid_length = 32`.

Redis nằm trong mạng backend và không có cổng công bố. Ai đọc được kho này thì giả được mọi phiên đang hoạt động, nên nó phải đứng sau cùng một hàng rào mạng với cơ sở dữ liệu.

#2 2.7 Lớp bảo mật của cụm

#3 2.7.1 Kết thúc TLS và header phản hồi

TLS kết thúc tại `lb01` với `ssl_protocols TLSv1.2 TLSv1.3` và chứng chỉ tự ký khai báo `subjectAltName` gồm cả địa chỉ 192.168.240.10. Toàn bộ cổng 80 chỉ làm một việc: chuyển hướng 301 sang HTTPS.

```
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header X-Content-Type-Options    "nosniff"  always;
add_header X-Frame-Options           "SAMEORIGIN" always;
add_header Content-Security-Policy   "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; script-src 'self'" always;
proxy_hide_header  Server;
proxy_hide_header  X-Powered-By;
```

`server_tokens off` đặt ở khối http để bản thân `lb01` cũng không lộ phiên bản. Đoạn từ bộ cân bằng tải về node chạy HTTP thuần trong mạng nội bộ; đây là đánh đổi của việc kết thúc TLS tập trung và được bàn ở mục 2.7.5.

[[FIG:anh-hinh-03|Một đáp ứng HTTPS đi qua cụm: header Server không kèm phiên bản, đủ bốn header an toàn, cookie phiên mang cả ba cờ|16]]

#3 2.7.2 Giới hạn tần suất

```
limit_req_zone $binary_remote_addr zone=auth:10m  rate=5r/s;
limit_req_zone $binary_remote_addr zone=probe:10m rate=5r/s;
limit_conn_zone $binary_remote_addr zone=perip:10m;

location ~ ^/(login|logout)\.php$ {
    limit_req zone=auth burst=5;
    limit_conn perip 20;
    ...
}
```

Giới hạn đặt riêng cho hai trang đăng nhập và đăng xuất, là nơi chịu tấn công dò mật khẩu, để không ảnh hưởng tới các phép đo phân phối tải.

Quá trình triển khai phát hiện một lỗi cấu hình. Location dùng để kiểm chứng giới hạn tần suất ban đầu chỉ có `return 200`, và kết quả là 40 request liên tiếp tất cả đều trả 200, nghĩa là giới hạn không hề chạy. Nguyên nhân: `return` thực thi ở giai đoạn rewrite, còn `limit_req` được xét ở giai đoạn preaccess muộn hơn, nên nginx trả lời luôn trước khi kịp kiểm tra. Phải chuyển location đó sang `proxy_pass` thì giới hạn mới có tác dụng. Đây là dạng lỗi cấu hình im lặng: tính năng trông như đang bật nhưng thực tế tắt.

Một lỗi khác ở ngay dòng khai báo, thuộc loại ngược lại vì nó khiến nginx từ chối khởi động: từ khóa `nodelay` được viết kèm `limit_req_zone`, trong khi `nodelay` là tham số của `limit_req`. nginx từ chối khởi động và chỉ rõ dòng sai. Hai dạng lỗi này cần phân biệt, vì lỗi thứ nhất mới là lỗi nguy hiểm: hệ thống vẫn chạy, vẫn trả lời đúng, chỉ có biện pháp bảo mật là không còn tác dụng.

#3 2.7.3 Cách ly và IP khách hàng

Hai lớp cách ly chồng lên nhau. Lớp thứ nhất là mạng backend `internal: true`: node không có đường ra Internet và không có cổng nào ở máy chủ, nên không thể bị gọi thẳng từ ngoài. Lớp thứ hai nằm ở chính node: `allow 172.20.0.10; deny all;` khiến node chỉ trả lời bộ cân bằng tải, kể cả khi người gọi đã nằm trong mạng backend. Không có lớp thứ hai thì chỉ cần một container khác trong cùng mạng là đọc được dữ liệu của node mà không đi qua bất kỳ kiểm soát nào ở tầng bảy.

Lớp thứ hai là quy tắc ở tầng ứng dụng, không phải quy tắc tường lửa ở tầng mạng: nó chặn sau khi kết nối TCP đã thiết lập nên vẫn để lộ việc cổng đang mở. Khi backend trải trên nhiều máy vật lý, cần thêm quy tắc tường lửa theo địa chỉ nguồn và mã hoá cả đoạn từ bộ cân bằng tải về node.

[[FIG:anh-hinh-15|Gọi thẳng vào node từ mạng phía ngoài: curl không thiết lập được kết nối|16]]

[[FIG:anh-hinh-16|Container khác trong cùng mạng backend gọi tới node bị trả về mã 403|16]]

[[FIG:anh-hinh-17|Đường dẫn vào thư viện riêng của ứng dụng bị node chặn bằng mã 403|16]]

#3 2.7.4 Đường kiểm tra sức khỏe và các đường dùng riêng cho phép đo

`/healthz` trả về đúng hai trường:

```
{"status":"ok","node":"web01"}
```

Đường này không mở session, không đọc cơ sở dữ liệu, không in phiên bản PHP hay đường dẫn tuyệt đối. Ở bộ cân bằng tải, `/healthz` đặt ở cả hai server block để giám sát gọi được qua HTTP lẫn HTTPS mà không bị chuyển hướng.

Riêng cho phép đo hiệu năng ở mục 3.1.3, cấu hình có thêm hai đường nữa.

`/lb-only` nằm ở bộ cân bằng tải và trả lời ngay tại chỗ, không mở kết nối tới node:

```
location = /lb-only {
    return 200 "lb\n";
}
```

`/dbping.php` nằm ở ứng dụng trên node, giống `/healthz` nhưng cộng thêm một truy vấn `SELECT COUNT(*)` thật tới MariaDB. Độ dài đáp ứng của cả hai đường này như nhau trên cả ba node vì tên node có cùng số ký tự; đây là điều kiện cần để ApacheBench không nhầm một đáp ứng khác độ dài thành một request thất bại.

Hai đường này tồn tại chỉ để đo, không thay thế `/healthz` làm đường giám sát.

#3 2.7.5 Đánh đổi của kết thúc TLS tập trung

Gom TLS về một chỗ làm chứng chỉ chỉ phải quản lý một nơi, giảm chi phí giải mã ở node và cho phép bộ cân bằng tải đọc nội dung HTTP để định tuyến. Đổi lại, đoạn trong mạng backend là HTTP thuần, cookie vẫn mang định danh phiên thật nhưng đi không mã hóa trên đoạn đó. Với đề tài này, đoạn trong mạng backend không thể bị nghe từ ngoài vì mạng là internal và không định tuyến, nên đánh đổi chấp nhận được. Khi backend đặt ở máy vật lý khác, phải mã hóa cả hai đầu.

#2 2.8 Hướng loại bỏ điểm hỏng đơn lẻ còn lại

Sau khi triển khai, cụm chịu được một node chết nhưng không chịu được `lb01` chết. Hướng xử lý là hai bộ cân bằng tải tranh nhau một địa chỉ ảo theo VRRP, dùng keepalived, kèm `vrrp_script` để node nào mất nginx thì tự hạ ưu tiên và nhả địa chỉ ảo.

Cấu hình mẫu để ở thư mục `keepalived/` nhưng không bật trong đề tài. Lý do: VRRP chạy trên giao thức 112 với địa chỉ multicast 224.0.0.18, còn Docker Desktop trên Windows không bảo đảm chuyển được multicast giữa các container. Đây là hướng phát triển ghi ở Kết luận.

#2 2.9 Kết chương

Chương này đã triển khai cụm ba máy chủ web với một bộ cân bằng tải nginx, kho phiên Redis dùng chung và một MariaDB dùng chung, tổ chức thành hai mạng trong đó node web không có cổng công bố và không có đường ra Internet. Thuật toán cân bằng tải, ngưỡng phát hiện lỗi và chế độ lưu phiên đều là tham số chạy, cho phép đổi mà không sửa cấu hình. Sáu yêu cầu đặt ra ở mục 2.1 được đưa sang Chương 3 để đo và kiểm chứng bằng số liệu.
