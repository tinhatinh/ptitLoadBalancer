# Hướng dẫn làm tiếp: phần tấn công

Dành cho người nhận repo này và muốn đi sâu vào phía thử nghiệm xâm nhập
(penetration test) thay vì phía triển khai cụm. Phần cân bằng tải, chịu lỗi,
phiên làm việc và bảng kiểm cấu hình đã xong và có số liệu; xem
`REPORT/BaoCao_BTL_INT14105_Nhom15.pdf` để biết hệ thống đang ở đâu.

## 0. Phạm vi và an toàn

- Chỉ tấn công vào cụm do chính bạn dựng bằng `docker compose up` trên máy bạn.
  Không quét, không brute-force vào hệ thống của trường hay của bên thứ ba.
- Toàn bộ mật khẩu, tài khoản và chứng chỉ trong repo này là **fixture của lab**.
  Không dùng lại chúng ở bất cứ đâu khác.
- `results/` đang được git theo dõi vì báo cáo cần đối chiếu từng con số. Trước
  khi đẩy lên một repo công khai, kiểm tra lại lần cuối:

  ```bash
  grep -rEn "BEGIN [A-Z ]*PRIVATE KEY|\b[a-z0-9]{32}\b|DE07SID=[A-Za-z0-9]{8,}" \
      results/ nginx/ web/ scripts/ | grep -v "_archived\|_run1_stale"
  ```

  Định dạng 32 ký tự là độ dài SID của PHP trong lab này (`sid_length=32`), nên
  mọi token khớp mẫu đều phải bị che. `results/session/jar` đã nằm ngoài git vì
  nó là cookie jar đang sinh, không phải bằng chứng. Nếu bạn sinh log mới thì
  chạy lại bước che ở mục 6.

## 1. Dựng lab từ bản clone sạch

```bash
cp .env.example .env          # du gia tri dev, khong can sua
./scripts/lab.sh up           # sinh chung chi tu, build, khoi dong, do san sang
./scripts/lab.sh ps           # chi lb01 co cong ngoai
```

Cổng trên máy của bạn: `http://localhost:8080` (chuyển hướng cưỡng bức sang
HTTPS) và `https://localhost:8443`. Chứng chỉ tự ký, trình duyệt sẽ cảnh báo.

Hai cổng đó **chỉ bind `127.0.0.1`**, nên từ máy khác trong cùng mạng bạn gọi
không tới được. Đó là chủ ý (lab này dựng trên laptop cá nhân). Muốn mở cho cả
mạng để demo, sửa `docker-compose.yml` bỏ tiền tố `127.0.0.1:` rồi
`docker compose up -d --force-recreate lb01`.

Cụm giờ đây tự xếp thứ tự khởi động: node chỉ lên sau khi Redis và MariaDB
healthy, load balancer chỉ lên sau khi cả ba node healthy. Nếu một container
kẹt `starting`, xem `docker compose ps` rồi `docker compose logs <tên>`.

Tài khoản demo đã seed trong `mysql/init/01_schema.sql`. Cả ba dùng chung một
mật khẩu lab, `Lab@De07`, không phải mật khẩu của ai và không dùng được ở đâu
khác; cột `password_hash` chỉ chứa bcrypt.

| Tài khoản | Mật khẩu | Phân quyền |
|---|---|---|
| `danhpt` | `Lab@De07` | admin, xem được `/audit.php` |
| `hoangtung` | `Lab@De07` | user |
| `tungtt` | `Lab@De07` | user |

Đăng nhập bằng `POST /login.php` với ba trường `csrf`, `username`, `password`;
`scripts/session_client.sh login` làm đúng việc đó và in ra node nhận phiên.

## 2. Địa hình thực tế, đọc trước khi nổ súng

```
client01 192.168.240.20  --frontend-->  lb01 192.168.240.10 / 172.20.0.10
                                            |
                                     --backend (internal: true)-->
                             web01 .11   web02 .12   web03 .13
                             redis01 .20            mysql01 .30
```

Ba điểm làm thay đổi cách tấn công so với một web app thông thường:

1. **Mạng backend là `internal`**, không có đường ra Internet và không định
   tuyến từ ngoài. Node web không pull được package, không gọi được công cụ
   quét từ xa. Muốn dùng công cụ mới thì cài vào `client/Dockerfile` (client01
   nằm ở mạng frontend nên có đường ra), rồi `docker compose --profile tools
   build client01`.
2. **Node chỉ trả lời đúng địa chỉ của load balancer** (`allow 172.20.0.10;
   deny all;` trong `web/nginx.conf`). Gọi thẳng `http://172.20.0.12/healthz`
   từ một container khác trong cùng mạng backend nhận 403. Muốn đi vòng qua
   load balancer thì phải có mặt trong mạng backend trước đã, tức là phải
   chiếm được một container.
3. **Node không còn dùng `set_real_ip_from`**. `$remote_addr` ở node là địa chỉ
   của load balancer; IP khách hàng đi qua tiêu đề `X-Real-IP` do load balancer
   ghi, và được chuyển cho PHP qua `fastcgi_param REMOTE_ADDR`. Xem mục 3.4.

## 3. Những thứ nên thử, xếp theo giá trị

### 3.1 Giả mạo IP trong nhật ký truy vết (nhiều khả năng thành công)

`index.php` in ra `client_ip()` và `login_audit.client_ip` lưu lại chính giá trị
đó, trong khi node lấy nó từ `X-Real-IP` của load balancer. Từ vị trí của một
container trong mạng backend, gọi thẳng node và tự đặt tiêu đề này:

```bash
docker compose exec -T web02 sh -c \
  "curl -s -H 'X-Real-IP: 1.2.3.4' http://127.0.0.1/index.php | grep -i 'IP khách'"
```

Nếu trang trả về `1.2.3.4` thì mọi dòng truy vết đều có thể bị đầu độc bởi bất
kỳ ai đã nằm trong mạng nội bộ. **Đã chạy cả hai chiều**: lệnh trên in ra
`1.2.3.4`, còn cũng tiêu đề đó gửi từ client01 xuyên qua load balancer thì trang
vẫn báo đúng `192.168.240.20`, vì load balancer ghi đè `X-Real-IP` bằng
`$remote_addr` của chính kết nối TCP. Đừng mất thời gian thử giả mạo từ phía
khách hàng, cửa đó đã đóng; cửa còn lại nằm sau bước chiếm một container.

Hướng sửa: chỉ tin `X-Real-IP` khi `$remote_addr` là đúng địa chỉ load balancer
(dùng `map` + `geo`), hoặc chấp nhận rằng nhật ký chỉ đáng tin tới tầng cân bằng
tải.

### 3.2 Đọc toàn bộ phiên từ Redis sau khi chiếm một container backend

Redis bật `requirepass` nhưng **không bật TLS**, và mật khẩu nằm trong biến môi
trường của mọi node. Từ một node đã bị chiếm:

```bash
docker compose exec -T web01 sh -c \
  'redis-cli -a "$REDIS_PASSWORD" --no-auth-warning KEYS "*" | head'
```

Định danh phiên của người dùng đang hoạt động nằm ở đó, đọc được nguyên văn.
Đây là bước leo thang điển hình: node web không còn là biên giới. Kiểm chứng
xem `session.use_strict_mode` có cứu được gì không (không, vì token là thật).

### 3.3 SQL injection

Tất cả truy vấn đều đi qua `prepare`/`bind_param`. Điểm cần thử không phải form
đăng nhập mà là những nơi tham số đi vào `ORDER BY`, tên cột, hoặc giới hạn
`LIMIT` - những chỗ không tham số hoá được. Hiện tại mã nguồn chưa có chỗ nào
như vậy, nên muốn có đất diễn thì phải thêm một tính năng (ví dụ sắp xếp bài
viết theo từ khoá URL) rồi tấn công vào đó. Ghi rõ trong kết luận rằng lỗ hổng
nằm ở tính năng bạn thêm, không phải ở mã gốc.

```bash
docker compose exec -T client01 sh -c \
  "sqlmap -u 'https://192.168.240.10/login.php' --data='username=*&password=*&csrf=*' \
   --cookie='DE07SID=*' --csrf-token=csrf --batch --level 5"
```

### 3.4 Bỏ qua giới hạn tần suất ở trang đăng nhập

`location ~ ^/(login|logout)\.php$` đặt `limit_req zone=auth burst=5` (5 req/s,
**không có `nodelay`**), nên request vượt ngưỡng bị xếp hàng chờ chứ không bị
từ chối. Đây là điểm cần kiểm tra kỹ: một công cụ brute-force sẽ chạy chậm đi
chứ không nhận 429, và người dùng thật cũng bị ảnh hưởng khi hệ thống bị bắn.
Các hướng thử:

- Tăng `burst` hoặc đổi chỗ đặt giới hạn rồi đo lại tác động.
- Bỏ giới hạn cho `logout.php` (không cần chống dò mật khẩu ở đó).
- Thử duy trì keep-alive để một kết nối mang nhiều request: bộ đếm tính theo
  IP nguồn, không theo kết nối, nên cách này nhiều khả năng không vượt được.
- Gửi `X-Forwarded-For` giả: load balancer dùng `$binary_remote_addr` (địa chỉ
  TCP thật) làm khoá, nên tiêu đề này không đổi được bucket. Kiểm chứng lại.

### 3.5 CSRF và cờ cookie

`login.php` có token chống CSRF và cookie mang `HttpOnly; Secure; SameSite=Lax`.
Cần một kịch bản thật: dựng một trang ở nguồn khác, POST có kèm cookie. Vì
`Secure` và `SameSite=Lax` chặn phần lớn đường gửi, bài kiểm chứng giá trị nhất
thường là **chứng minh nó chặn được**, kèm giải thích vì sao.

Một điểm đã đo và cần khai thác tiếp: token **không dùng một lần**.
`csrf_token()` sinh một giá trị rồi giữ nguyên trong suốt phiên, `csrf_ok()` chỉ
so mà không xoay vòng token, và `session_regenerate_id(true)` khi đăng nhập thành
công giữ nguyên toàn bộ `$_SESSION`. Thực nghiệm: lấy một token rồi gửi ba lần
đăng nhập sai liên tiếp, cả ba lần đều nhận "Sai tên đăng nhập" chứ không nhận
"Mã bảo vệ không hợp lệ". Token pre-login vì thế vẫn dùng được sau login. Đây là
khoảng cách thật so với khuyến nghị thông thường, dù bản thân nó chưa phải lỗ hổng
CSRF (kẻ tấn công vẫn không đọc được token của nạn nhân). Nếu bịt, sửa
`csrf_ok()` để xoay vòng token ngay sau khi so khớp, rồi kiểm tra lại luồng
`session_client.sh login` (một lần GET rồi một lần POST) vẫn chạy.

### 3.6 Session fixation và cố định quyền

`session_regenerate_id(true)` được gọi sau khi đăng nhập. Kịch bản cần dựng:
lấy một SID hợp lệ (đăng nhập bằng tài khoản của chính mình), đưa nạn nhân dùng
SID đó với CSRF token đã có sẵn, rồi đăng nhập. Vì `use_strict_mode=1` và
`sid_length=32`, SID không do PHP sinh ra sẽ bị bỏ. Cần kiểm chứng cả hai
chiều: fixation thất bại, và **đổi quyền trong session từ phía client** cũng
không được (thử sửa `role` trong Redis rồi tải lại `/audit.php`).

### 3.7 Điều hướng sai phân quyền

`audit.php` trả 403 khi không phải admin. Thử: xoá cookie, đổi user thường,
thêm `?user=` (không có tham số nào được đọc), và gọi qua HTTP thay vì HTTPS.

### 3.8 HTTP request smuggling

Cả hai đầu của chuỗi proxy đều là nginx, và load balancer nói chuyện với node
bằng HTTP/1.1 có keep-alive. Đây là nơi đáng thử nhất của mô hình này:

- Hai dòng `Content-Length`, hoặc `Content-Length` kèm `Transfer-Encoding`.
- Thân request có độ dài không khớp khai báo.
- Tiêu đề chứa ký tự điều khiển hoặc khoảng trắng bất thường.
- `proxy_next_upstream` đang bật cho `error timeout http_500..504`: một request
  POST bị chậm ở node thứ nhất có được thử lại ở node thứ hai không? Nếu có,
  người dùng nhận hai hiệu ứng từ một lần bấm.

### 3.9 TLS và header

```bash
docker compose exec -T client01 sh -c \
  "echo | openssl s_client -connect 192.168.240.10:443 -tls1_1 2>&1 | head -3"
```

Cấu hình chỉ nhận TLS 1.2/1.3 với danh sách mã hoá tường minh; chứng chỉ tự ký
và chưa có chuỗi. Các hướng: thử hạ phiên bản, kiểm tra HSTS có `includeSubDomains`
nhưng chưa có `preload`, và kiểm tra CSP có cho `'unsafe-inline'` trong `style-src`.

### 3.10 Bề mặt của chính container

Node chạy nginx (master root) và php-fpm trong cùng một container. Đáng kiểm
tra: `docker compose exec -T web01 id`, `capsh --print` nếu có, và việc
`./scripts` được mount vào client01 dưới dạng chỉ đọc còn các dịch vụ khác thì
không mount gì.

### 3.11 Làm cho ứng dụng không phục vụ được nữa

MariaDB và Redis là hai điểm hỏng đơn lẻ còn lại, và mỗi đường dẫn xử lý một
trong hai thứ đó khác nhau. Trạng thái hiện tại đã đo lúc `docker compose stop
mysql01`:

| Đường | Kết quả khi DB chết | Thời gian |
|---|---|---|
| `/index.php` | 200, kèm dòng "không kết nối được cơ sở dữ liệu" | ~5 s |
| `/dbping.php` | 200, `{"rows":0,"ok":0}` | ~5 s |
| `POST /login.php` | 503 kèm thông báo mời thử lại | ~5 s |
| `/healthz` | 200, không chạm DB | 8 ms |

Ba đường đầu từng là **lỗi thật**: `login.php` gọi `db()` mà không bọc
`try/catch` nên PHP bắn exception trần (500, thân rỗng, kèm đường dẫn tuyệt đối
trong stack trace ở log của node), còn `index.php` treo tới hạn 10 s của load
balancer nên trả 504. Nguyên nhân sâu là `new mysqli()` không có thời hạn chờ
khi phân giải tên `mysql01` thất bại. `db()` bây giờ đặt
`MYSQLI_OPT_CONNECT_TIMEOUT` 2 giây và nhớ lần thất bại trong cùng request.

Còn đất diễn: ~5 s chờ đó là `getaddrinfo` của Docker DNS, không phải connect
timeout, nên một kẻ làm được việc chặn DNS hoặc làm php-fpm hết worker vẫn hạ
được dịch vụ. Mỗi node chạy `pm.max_children = 16` (đặt bằng `sed` trong
`web/Dockerfile`), tức toàn cụm có 48 worker; kết hợp với 5 s treo ở mỗi request
chạm DB thì con số request đồng thời cần để bão hoà là bao nhiêu, đó là một bài
đo có bằng chứng rõ ràng.

## 4. Những gì ĐÃ được kiểm chứng, đừng làm lại

Bảng kiểm 19 hạng mục trong `scripts/sec_check.sh` đã phủ: ẩn phiên bản server,
ẩn `X-Powered-By`, HSTS, `X-Content-Type-Options`, CSP, chuyển hướng cưỡng bức
ở cổng 80, TLS 1.2 trở lên, ba cờ cookie, chặn `/lib/`, chặn `/config.php`,
giới hạn tần suất trên đường thăm dò, node không gọi được từ mạng ngoài, node
từ chối container không phải load balancer, node không có đường ra Internet,
node ghi đúng IP khách hàng, `/healthz` không lộ thông tin, và mọi node trả về
cùng nội dung. Kết quả lưu trong `results/security/`.

Đó là **kiểm tra cấu hình**, không phải thử nghiệm xâm nhập. Phần việc của bạn
là biến một số dòng trong mục 3 ở trên thành bài kiểm tra có bằng chứng.

### 4.1 Những cửa vừa đóng trong lượt soát cuối

Đừng mất thời gian thử lại, nhưng hãy kiểm chứng rằng chúng đóng thật:

- **Biến thể hoa/thường của tên đăng nhập.** Cột `users.username` mang
  `COLLATE utf8mb4_bin` và `login.php` `trim()` trước khi truy vấn, nên
  `DANHPT`, `dànhpt` và `danhpt ` không còn khớp với `danhpt`. Kiểm chứng:
  `POST /login.php` với `username=DANHPT` và mật khẩu đúng phải trả 200
  (từ chối), còn `danhpt` trả 302. Lưu ý `utf8mb4_bin` vẫn là kiểu PAD SPACE
  trong MariaDB, nên cửa trailing-space đóng được là nhờ `trim()` ở tầng ứng
  dụng, không phải nhờ collation.
- **Mất dấu vết khi dò tài khoản.** `login_audit` chạy dưới
  `STRICT_TRANS_TABLES`: username dài hơn 64 ký từng khiến INSERT báo lỗi
  1406 và `record_login_attempt()` nuốt luôn, nghĩa là một chuỗi brute-force
  với tên dài để lại **không có dòng nào**. Nay giá trị được cắt về đúng
  chiều dài cột trước khi ghi. Kiểm chứng: gửi username 200 ký tự rồi
  `SELECT id, CHAR_LENGTH(username) FROM login_audit ORDER BY id DESC LIMIT 1`.
- **Đặc quyền của tài khoản ứng dụng.** `webapp` chỉ còn `SELECT, INSERT`
  trên `de07_web` (xem `mysql/init/02_grants.sql`), nên một lỗi SQL injection
  không còn DROP/ALTER được nữa. `SHOW GRANTS FOR 'webapp'@'%'` để đối chiếu.
  Trên máy đã chạy từ trước, file này không tự chạy: phải áp thủ công.
- **Phục hồi phiên TLS.** `ssl_session_tickets off`, và danh sách mật mã không
  còn các bộ `ECDHE-ECDSA` vô dụng với chứng chỉ RSA.
- **Redis** dùng `noeviction` thay vì `allkeys-lru`: đầy bộ nhớ sẽ báo lỗi ghi
  chứ không âm thầm đá phiên đang sống.

## 5. Cách thêm một kiểm tra vào bộ hiện có

Mở `scripts/sec_check.sh`, dùng hàm `check` có sẵn:

```bash
check "Ten hang muc ngan gon" "ma hoac gia tri mong doi" \
    "$(cli_sh "lenh chay trong client01")" "chu thit ngan"
```

Chạy lại bằng `./scripts/lab.sh sec`. Kết quả ghi vào `results/security/`.
Nếu thêm hạng mục, nhớ cập nhật số lượng trong `REPORT/chuong3.md` (bảng
`an-toan`) và `REPORT/ket-luan.md`, rồi chạy `python REPORT/check_md.py` và
`python REPORT/verify_numbers.py` ở `REPORT/`.

Với kịch bản tấn công dài (sqlmap, smuggler), đừng nhét vào `sec_check.sh`.
Tạo `scripts/attacks/<ten>.sh` trả về 0 khi phòng vệ đứng vững, và một thư mục
kết quả riêng `results/attacks/`.

## 6. Che dữ liệu nhạy cảm trước khi commit log mới

```bash
python - <<'PY'
import io, glob, re
pat = re.compile(r'(DE07SID[\t=]|password=)[^&\s"\'|]+')
for p in glob.glob('results/**/*', recursive=True):
    try:
        s = io.open(p, encoding='utf-8', errors='ignore').read()
    except Exception:
        continue
    t = pat.sub(lambda m: m.group(1) + '<da-che>', s)
    if t != s:
        io.open(p, 'w', encoding='utf-8', newline='').write(t)
PY
```

Mẫu `DE07SID[\t=]` bắt cả hai nơi định danh phiên xuất hiện: header
`Set-Cookie: DE07SID=...` và cột tab của cookie jar. Sau khi chạy, dùng lại lệnh
kiểm tra ở mục 0 để xác nhận không còn token nào.

## 7. Chạy lại các phép đo cũ

```bash
./scripts/lab.sh dist-all       # 300 request tuan tu, ba thuat toan
./scripts/lab.sh dist-skew      # do lech phan phoi, 20 luong moi thuat toan
./scripts/lab.sh bench-matrix   # 18 o thong qua, 20 luong moi o  (~45 phut)
./scripts/lab.sh bench-degrade  # cum 3 node doi voi cum 2 node    (~10 phut)
./scripts/lab.sh failover web02 # mot vong failover
./scripts/failover_matrix.sh 12 # 12 vong, co so lieu cho bang 3.2 (~12 phut)
./scripts/lab.sh report         # in lai dung cac so trong bang bao cao
```

Ba điều đã làm hỏng số liệu ở lượt trước, đừng lặp lại:

1. **Không để script đổi cấu hình rồi bỏ đó.** `session_test.sh` từng để lại
   `ip_hash` trên load balancer, và phép đo chạy sau đó kéo 126.000 request về
   đúng một node mà không báo lỗi. Mọi script đo bây giờ tự đặt cấu hình của nó.
2. **Không sửa file script trong lúc nó đang chạy.** Bash đọc file theo con trỏ;
   ghi đè giữa chừng làm lượt đo hỏng im lặng và dụng cụ tổng hợp lấy lại tệp
   của lượt trước, tạo một dòng trùng trong bảng.
3. **Không đếm từ log của container mà không có mốc.** `healthz.log` của `lb01`
   chỉ mất khi container khởi động lại, nên chạy nhiều vòng liên tiếp mà grep cả
   file thì vòng sau cộng luôn số liệu của vòng trước.

Trước khi sửa số liệu failover, đọc `results/failover/NOTA.md`: thư mục đó có một
vòng bị loại khỏi bảng, một cột đã hỏng và ba vòng đo độc lập dễ nhầm với nhau.

## 8. Công cụ

`client/Dockerfile` hiện chỉ có `curl`, `jq`, `openssl` và ApacheBench. Thêm công
cụ vào file đó rồi build lại image `client01` là cách sạch nhất: mọi lệnh chạy từ
một địa chỉ IP thật trong mạng frontend, giống hệt cách các phép đo hiện tại đang
chạy. sqlmap chưa có; muốn dùng thì `apk add --no-cache sqlmap` trong Dockerfile
đó (image Alpine) và cân nhắc chạy nó trong một container tách rời rồi gắn vào
mạng `backend`, vì tấn công từ client01 chỉ đi được qua load balancer.

## 9. Dựng lại báo cáo (nếu cần)

Phần này chỉ cần khi sửa `REPORT/*.md`. Ba bước:

```bash
cd REPORT
export BTL_TEMPLATE="/duong/dan/toi/ATTT-Mau-bao-cao-bai-thuc-hanh-TTCS.docx"
python check_md.py                    # cau truc markdown
python analyze_bench.py all           # dung bench_summary.json tu results/
python make_charts.py                 # ve ba bieu do tu bench_summary.json
python verify_numbers.py              # doi chieu so TRONG BANG va tinh anh
                                      # khong cu hon du lieu no the hien
python build_docx.py mo-dau.md chuong1.md chuong2.md chuong3.md ket-luan.md tai-lieu.md --out out.docx
python finalize_word.py out.docx      # mo Word, thay marker danh muc, xuat PDF
```

Thu tu tren la bat buoc: `verify_numbers.py` so thoi gian cua moi file trong
`figures/` voi nguon cua no (`.puml`, `screenshots/`, `bench_summary.json`),
nen chay `analyze_bench.py` roi mới chạy `make_charts.py`, neu khong bao cao se
bi bao la bieu do cu. So in trong bang du doi chieu tung o; con so nam ben
trong file PNG thi khong the doi chieu truc tiep, day la cach duy nhat phat
hien chung bi cu.

`BTL_TEMPLATE` là bắt buộc với hai bước cuối: mẫu báo cáo của học phần là file
của trường, không đi kèm repo, và `build_docx.py` cần các style `BTL-H1`,
`BTL-Hinh`, `BTL-Bang` định nghĩa trong đó. Nếu không có mẫu, đặt tên file là
`REPORT/mau-bao-cao.docx` thì script tự tìm. `check_md.py` và
`verify_numbers.py` không cần mẫu.

`finalize_word.py` và `take_shots.py` chạy trên Windows (dùng Word COM và Win32
API); trên Linux chỉ dựng được tới `out.docx` và danh mục hình/bảng sẽ còn
placeholder. `take_shots.py` tự tìm `bash.exe`, ghi đè được bằng
`SHOTS_BASH`.

Sau khi đổi số liệu hoặc thêm hạng mục bảo mật, chạy lại `verify_numbers.py`: nó
so từng ô của bảng trong báo cáo với tệp thô trong `results/` và báo lỗi nếu một
con số không đọc lại được.
