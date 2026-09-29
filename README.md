# Đề 07. Chuỗi cân bằng tải các máy chủ web (web server load balancing cluster)

Học phần INT14105. An toàn ứng dụng web và cơ sở dữ liệu. Nhóm 15, lớp 04.

Lab này dựng một cụm ba máy chủ web đứng sau một load balancer nginx, dùng
chung kho phiên Redis và một MariaDB, rồi đo ba việc mà đề bài yêu cầu: phân
phối request, khả năng chịu lỗi khi một node gặp sự cố, và tính liên tục của
phiên làm việc qua sự cố đó.

## Chạy

Yêu cầu Docker Engine và Docker Compose plugin. Chạy trong Git Bash trên Windows
hoặc trong terminal Linux.

```bash
cp .env.example .env
./scripts/lab.sh up        # sinh chứng chỉ, build, khởi động, kiểm tra sẵn sàng
./scripts/lab.sh ps        # chỉ có lb01 có cổng ngoài
curl -sk https://localhost:8443/healthz
```

Mở `https://localhost:8443/` trên trình duyệt. Chứng chỉ tự ký nên trình duyệt
sẽ cảnh báo.

`.env` và `nginx/lb/certs/` không được đưa vào git; `.env.example` là bản giá
trị dev đủ để chạy. Chứng chỉ do `scripts/gen_certs.sh` sinh ra khi `lab.sh up`
chạy lần đầu trên máy của bạn.

Hai cổng của load balancer chỉ bind `127.0.0.1`, nên gọi từ máy khác trong cùng
mạng sẽ không tới được. Muốn mở cho cả mạng khi demo, bỏ tiền tố `127.0.0.1:`
trong `docker-compose.yml` rồi chạy lại `docker compose up -d --force-recreate
lb01`.

## Đo đạc

Ba nội dung đề bài yêu cầu và các phép đo bổ sung:

```bash
./scripts/lab.sh dist-all       # 3.2.1: ba thuat toan, 300 request tuan tu
./scripts/lab.sh dist-skew      # 3.2.2: do lech phan phoi, 20 luong moi thuat toan
./scripts/lab.sh failover       # 3.3: tat web02 giua chung vong do
./scripts/lab.sh session redis  # 3.4: con phien sau khi tat node, kho Redis
./scripts/lab.sh session file   # 3.4: mat phien, luu trong node, dinh kem ip_hash
./scripts/lab.sh sec            # 3.6: bang kiem 19 hang muc cau hinh an toan
./scripts/lab.sh bench-matrix   # 3.5.1: 18 o thong qua, 20 luong moi o
./scripts/lab.sh bench-degrade  # 3.5.4: cum 3 node doi voi cum 2 node
./scripts/lab.sh all            # chay het theo thu tu tren
```

Mỗi lệnh đo tự đặt thuật toán và tự làm nóng trước khi lấy số; không lệnh nào
dựa vào trạng thái do lệnh trước để lại. Sau khi chạy, dùng lệnh này để in lại
đúng các con số xuất hiện trong bảng của báo cáo:

```bash
./scripts/lab.sh report          # matrix + skew + degrade, doc truc tiep results/
```

Mọi kết quả lưu vào `results/`, giữ nguyên log thô để làm phụ lục báo cáo. Mỗi
thư mục chỉ giữ lượt chạy mới nhất; các lượt đã bị thay thế nằm trong
`results/_archived/` và `results/_run1_stale/`, không được bất kỳ công cụ tổng
hợp nào đọc tới. `results/failover/NOTA.md` giải thích một vòng đo đã bị loại và
một cột số liệu đã hỏng trong thư mục đó.

## Báo cáo

Bản nộp ở `REPORT/BaoCao_BTL_INT14105_Nhom15.docx` (kèm `.pdf` để đọc nhanh).
Nguồn là các file `REPORT/*.md`, số liệu lấy trực tiếp từ `results/`.

Hai lệnh kiểm tra không cần gì thêm và nên chạy sau mỗi lần sửa:

```bash
python REPORT/check_md.py && python REPORT/verify_numbers.py
```

Quy trình dựng lại `.docx` (cần mẫu báo cáo của học phần, không đi kèm repo) ở
mục 9 của `docs/HUONG-DAN-TIEP-TUC.md`.

## Cấu trúc

| Đường dẫn | Nội dung |
|---|---|
| `docker-compose.yml` | khai báo bảy dịch vụ và hai mạng |
| `nginx/lb/` | cấu hình load balancer (template envsubst) |
| `web/` | Dockerfile, nginx, php-fpm và mã nguồn PHP của node |
| `mysql/init/` | schema và dữ liệu seed |
| `scripts/` | điều khiển lab và toàn bộ script đo |
| `results/` | log thô và CSV của mọi lượt đo, là nguồn số liệu cho báo cáo |
| `REPORT/` | markdown báo cáo, công cụ sinh `.docx`, hình vẽ, ảnh chụp |
| `docs/HUONG-DAN-TIEP-TUC.md` | dẫn nhập cho người làm tiếp phần tấn công |

## Trạng thái hiện tại

Đề bài yêu cầu ba việc, và mỗi việc tương ứng một phép đo đã chạy xong:

| Yêu cầu của đề bài | Phép đo | Kết quả đo được |
|---|---|---|
| Kiểm tra phân phối request | 600 request gửi đồng thời qua 20 kết nối song song, lặp lại 20 lượt độc lập cho mỗi thuật toán | round robin chia 199,9 / 200,1 / 200,0 giữa ba node, độ lệch lớn nhất giữa hai node trong một lượt là 1,0 request; least_conn chia 199,9 / 200,5 / 199,6 với độ lệch 10,2; ip_hash dồn cả 600 về một node ở cả hai mươi lượt |
| Khả năng đáp ứng khi một server gặp sự cố | vòng đo 70 giây gửi request liên tục, lặp lại 12 lần độc lập, tắt hẳn `web02` ở giây thứ 10 | không có request nào nhận mã lỗi ở cả 12 vòng; trung bình 8,8 ± 0,4 request mỗi vòng phải chờ thêm khoảng hai giây vì nginx thử lại node đã chết |
| Tính liên tục của phiên làm việc qua sự cố | đăng nhập, tắt đúng node vừa phục vụ đăng nhập, gọi lại `/member.php` mười lần | kho phiên Redis dùng chung giữ được 10/10 phiên; lưu phiên trên đĩa của chính node giữ được 0/10 |

Ký hiệu `±` ở trên là nửa khoảng tin cậy 95% của giá trị trung bình, tính từ số
lượt đo lặp lại, không phải độ chính xác của thiết bị.

Ba nội dung đo thêm ngoài phạm vi đề bài, để trả lời câu hỏi "hệ thống chậm là
chậm ở đâu":

- Ma trận 18 ô, tức ba thuật toán nhân ba tầng phản hồi nhân hai chế độ giữ kết
  nối, mỗi ô 20 lượt. Nó tách thông qua của bộ cân bằng tải ra khỏi thông qua
  của ứng dụng: 31.360 req/s khi nginx tự trả lời, giảm còn 805 req/s khi mỗi
  yêu cầu phải chuyển tiếp sang node.
- So sánh cụm ba node với cụm hai node: mất một node chỉ làm thông qua trung
  bình giảm 7,7%, nhưng làm hệ số biến thiên tăng từ 4,2% lên 14,7% và đẩy
  request chậm nhất trong lượt đo từ 54 ms lên 1048 ms.
- Bảng kiểm 19 hạng mục cấu hình an toàn.

Mọi con số in trong báo cáo đều đọc lại được từ tệp thô:
`python REPORT/verify_numbers.py` lần lượt mở từng bảng trong `REPORT/*.md`,
truy ngược mỗi ô về đúng tệp trong `results/`, và báo lỗi nêu rõ ô nào nếu một
giá trị không tái lập được. Đây là chốt chặn để không ai trích lại một con số
đã bị lượt đo sau thay thế.

Bảng kiểm an toàn 19 hạng mục (`./scripts/lab.sh sec`) mới chứng minh **cấu hình
đang chạy đúng**, chưa phải thử nghiệm xâm nhập. Phần tấn công để ngỏ và được
hướng dẫn ở mục "Làm tiếp: phần tấn công".

## Địa chỉ trong lab

| Thành phần | Container | Địa chỉ | Mạng |
|---|---|---|---|
| Load balancer | lb01 | 192.168.240.10 / 172.20.0.10 | frontend + backend |
| Node web 1 | web01 | 172.20.0.11 | backend |
| Node web 2 | web02 | 172.20.0.12 | backend |
| Node web 3 | web03 | 172.20.0.13 | backend |
| Kho phiên | redis01 | 172.20.0.20 | backend |
| Cơ sở dữ liệu | mysql01 | 172.20.0.30 | backend |
| Máy đo | client01 | 192.168.240.20 | frontend |

Mạng `backend` khai báo `internal: true`, nên node web không có đường ra
Internet và không nghe cổng nào trên máy chủ. Chỉ `lb01` có cổng công bố.

## Vì sao có container client01

Gọi từ máy Windows thì Docker Desktop NAT ghi đè mất địa chỉ nguồn, nên không
đo được `ip_hash` và cũng không chứng minh được chuỗi IP khách hàng trong nhật
ký. client01 nằm cùng mạng frontend với load balancer nên địa chỉ nguồn là thật.

## Làm tiếp: phần tấn công

Người nhận repo muốn đi sâu phía thử nghiệm xâm nhập đọc
[`docs/HUONG-DAN-TIEP-TUC.md`](docs/HUONG-DAN-TIEP-TUC.md). Tài liệu đó mô tả
địa hình mạng, những phòng vệ đang bật, danh sách mục tiêu xếp theo giá trị, và
cách thêm một kiểm tra vào bộ `sec_check.sh` hiện có mà không phá số liệu đã
trông cậy được.

## Ghi chú về Keepalived

Đề bài chỉ yêu cầu cân bằng tải cho máy chủ web nên phần này không bật. Thư mục
`keepalived/` giữ sẵn cấu hình VRRP để nói về điểm hỏng đơn lẻ còn lại: chính
load balancer. Hướng dẫn ở trong đó.
