# Ảnh chụp màn hình của từng phép đo

Hai mươi ảnh trong `screenshots/` do `take_shots.py` chụp tự động. Mỗi ảnh là
một cửa sổ console thật: script mở cửa sổ, chạy đúng một lệnh, chờ lệnh kết
thúc rồi lấy vùng pixel của cửa sổ đó. Không có ảnh nào dựng lại.

Chụp lại toàn bộ: `python take_shots.py`. Chụp lẻ: `python take_shots.py 08 09`.

Ảnh chỉ được chấp nhận nếu `looks_like_terminal()` xác nhận vùng pixel lấy về
đúng là cửa sổ terminal; ba lần thử không đạt thì ảnh bị xoá và mã số được báo
lại để chụp tiếp. Kiểm tra này có từ một sự cố thật: một ảnh từng chụp trúng
cửa sổ trình duyệt của người dùng.

| # | Ảnh | Nội dung trên ảnh | Lệnh đã chạy | Dẫn tới |
|---|---|---|---|---|
| 01 | `hinh-01.png` | bảy container, chỉ `lb01` có cổng công bố | `bash scripts/lab.sh ps` | mục 2.2 |
| 02 | `hinh-02.png` | mạng backend khai báo `internal`, kèm các thành viên và subnet | `docker network inspect de07-web-lb-cluster_backend \| grep -Ei "Name\|Internal\|Subnet"` | mục 2.2.1 |
| 03 | `hinh-03.png` | đủ header an toàn, cookie phiên có ba cờ, giá trị SID đã che | `curl -sk -D - login.php \| sed` che giá trị cookie | mục 2.7.1, bảng `an-toan` |
| 04 | `hinh-04.png` | phân phối tuần tự round robin | `distribute.sh 300 round_robin` sau khi đặt round robin | mục 3.2.1, bảng `phoi-tuan-tu` |
| 05 | `hinh-05.png` | phân phối tuần tự least_conn, cùng một chuỗi | `distribute.sh 300 least_conn` | mục 3.2.1, bảng `phoi-tuan-tu` |
| 06 | `hinh-06.png` | ip_hash dồn toàn bộ về một node | `distribute.sh 300 ip_hash` | mục 3.2.1, bảng `phoi-tuan-tu` |
| 07 | `hinh-07.png` | bảng phân phối 20 lượt của ba thuật toán | `python REPORT/analyze_bench.py skew` | mục 3.2.2, bảng `phoi-dong-thoi` |
| 08 | `hinh-08.png` | tắt web02 giữa vòng đo, kèm bảng tổng hợp | `bash scripts/failover.sh web02 70 30` | mục 3.3.1, bảng `failover` |
| 09 | `hinh-09.png` | log nginx cho thấy chuyển node sau mã 504 | `grep "upstream=172.20.0.12:80, " results/failover/retries-*.log` | mục 3.3.2 |
| 10 | `hinh-10.png` | redis giữ phiên sau khi tắt node đã đăng nhập | `bash scripts/session_test.sh redis` | mục 3.4, bảng `phien` |
| 11 | `hinh-11.png` | file mất phiên sau khi tắt đúng node đó | `bash scripts/session_test.sh file` | mục 3.4, bảng `phien` |
| 12 | `hinh-12.png` | bảng kiểm 19 hạng mục, `PASS=19 FAIL=0 GHI_NHAN=0` | `bash scripts/sec_check.sh` | mục 3.6, bảng `an-toan` |
| 13 | `hinh-13.png` | ma trận 18 ô thông qua, mỗi ô 20 lượt | `python REPORT/analyze_bench.py matrix` | mục 3.5.1, bảng `thong-qua` |
| 14 | `hinh-14.png` | suy giảm khi mất một node, kèm dòng đếm node phục vụ | `python REPORT/analyze_bench.py degrade` | mục 3.5.4, bảng `hieu-nang` |
| 20 | `hinh-20.png` | mười hai phép kiểm định Welch và bậc thang chi phí | `python REPORT/analyze_bench.py matrix` (phần cuối) | mục 3.5.2 và 3.5.3, bảng `thang-chi-phi`, `welch` |
| 15 | `hinh-15.png` | gọi thẳng node từ mạng phía ngoài không được | `curl http://172.20.0.12/healthz` từ client01 | mục 2.7.3, bảng `an-toan` |
| 16 | `hinh-16.png` | container khác trong cùng mạng backend bị node trả về 403 | `curl http://172.20.0.12/healthz` từ web03 | mục 2.7.3, bảng `an-toan` |
| 17 | `hinh-17.png` | thư viện riêng của ứng dụng bị chặn bằng mã 403 | `curl -i https://.../lib/bootstrap.php` | mục 2.7.3, bảng `an-toan` |
| 18 | `hinh-18.png` | giới hạn tần suất chặn request gửi dồn dập | `ab -n 200 -c 20 https://.../ratelimit-probe` rồi đếm `status=429` trong `probe.log` | mục 3.6, bảng `an-toan` |
| 19 | `hinh-19.png` | các tệp kết quả được giữ lại trong `results/` | `find results -type f -not -path 'results/_*'` | mục 3.1.2 |

## Điểm cần biết khi đối chiếu

Ảnh 07, 13, 14 và 20 là đầu ra của `analyze_bench.py`, cũng chính là chương
trình sinh ra các ô trong bảng của mục 3.2 và 3.5. Vì vậy số trong ảnh và số
trong bảng không thể lệch nhau: cả hai đều đọc từ một tệp đo duy nhất trong
`results/`.

Ảnh 08 và 09 chụp lượt chạy được giữ lại trong `results/failover/`, gồm file
CSV mẫu đo, bảng tổng hợp và các dòng log có hai địa chỉ upstream. Ba file này
trùng khớp nhau về số mẫu và số lần chuyển node.

Access log của nginx nằm trong container và mất khi container khởi động lại.
Vì `lab.sh`, `session_test.sh` và `bench_matrix.sh` đều khởi động lại `lb01`,
các dòng log của phép failover được lưu ra `results/failover/retries-*.log`
ngay trong lúc chạy, trước khi bị xóa.

Nhãn in ra của `summarize.awk`, `distribute.sh` và `sec_check.sh` viết không
dấu. Lý do không phải thẩm mỹ: cửa sổ console trên Windows giải mã UTF-8 theo
bảng mã của phiên, nên một số ký tự có dấu hiện ra thành ký tự rác ngay trong
ảnh chụp. Ảnh là bằng chứng thì phải đọc được.

Riêng ảnh 03, giá trị cookie phiên bị che bằng `sed` trước khi chụp. Cờ của
cookie là nội dung cần chứng minh; bản thân định danh phiên thì không.

Mọi con số trong Chương 3 kiểm tra lại được bằng `python verify_numbers.py`,
đối chiếu từng ô bảng với tệp trong `results/`.
