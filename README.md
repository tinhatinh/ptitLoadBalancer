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

## Đo đạc

Ba phép đo của đề bài và hai phép đo bổ sung:

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

Ba nội dung đề bài yêu cầu đã triển khai và có số liệu: phân phối request qua
ba thuật toán, chịu lỗi khi tắt một node giữa vòng đo, tính liên tục của phiên
qua sự cố đó. Ma trận hiệu năng 18 ô, phép đo cụm suy giảm và phép đo failover
lặp lại 12 vòng đều đã chạy xong; `python REPORT/verify_numbers.py` đối chiếu
từng con số trong báo cáo với `results/`.

Bảng kiểm an toàn 19 hạng mục (`./scripts/lab.sh sec`) mới chứng minh **cấu hình
đang chạy đúng**, chưa phải thử nghiệm xâm nhập. Phần tấn công để ngỏ và được
hướng dẫn ở mục "Làm tiếp: phần tấn công".

## Dia chi trong lab

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

## Vi sao co container client01

Goi tu Windows thi Docker Desktop NAT ghi de mat IP nguon, khong the do duoc
ip_hash va cung khong chung minh duoc chuoi IP khach hang trong log. client01
nam cung mang frontend voi load balancer nen IP nguon la that.

## Làm tiếp: phần tấn công

Người nhận repo muốn đi sâu phía thử nghiệm xâm nhập đọc
[`docs/HUONG-DAN-TIEP-TUC.md`](docs/HUONG-DAN-TIEP-TUC.md). Tài liệu đó mô tả
địa hình mạng, những phòng vệ đang bật, danh sách mục tiêu xếp theo giá trị, và
cách thêm một kiểm tra vào bộ `sec_check.sh` hiện có mà không phá số liệu đã
trông cậy được.

## Ghi chu ve Keepalived

Đề bài chỉ yêu cầu cân bằng tải cho máy chủ web nên phần này không bật. Thư mục
`keepalived/` giữ sẵn cấu hình VRRP để nói về điểm hỏng đơn lẻ còn lại: chính
load balancer. Hướng dẫn ở trong đó.
