# Đọc trước khi dùng số liệu trong thư mục này

Thư mục có hai loại bằng chứng, và một cột đã hỏng.

## 1. `repeat-20260929-144558.csv` — nguồn của Bảng 3.2

Mười hai vòng lặp của phép đo failover. Đánh số dòng là `1..9, 11, 12, 13`;
**không có dòng 10**. Dòng đó bị loại vì nó trùng im lặng với dòng 9:
`scripts/failover.sh` bị sửa trong lúc `failover_matrix.sh` đang chạy, Bash đọc
file theo con trỏ nên vòng đó không sinh được bảng tổng hợp mới và dụng cụ gom
dữ liệu lấy lại tệp của vòng trước. Vòng sạch thay thế mang số 13. Các tệp của
vòng 10 vẫn nằm trong `repeat-20260929-144558/` để giữ dấu vết, nhưng **không**
được tính vào bất kỳ con số nào.

Từng dòng vẫn đối chiếu được với tệp thô của nó:

```bash
tail -n +2 repeat-20260929-144558/load-11.csv | wc -l   # 229 = cot samples
grep 'vuot 1 s' repeat-20260929-144558/summary-11.txt    # : 9 = cot slow
```

## 2. Cột `retry_lines` của vòng 1 đến 9: không dùng được

Tám, 18, 27, 36, 46, 54, 63, 73, 82 tăng đơn điệu qua các vòng. Đó là dấu hiệu
của lỗi đếm, không phải của hệ thống: `retries-*.log` cắt từ access log đang
chạy của container `lb01`, mà log này chỉ mất khi container khởi động lại, nên
vòng sau cộng luôn số lần thử lại của vòng trước. `scripts/failover.sh` sau đó
được sửa để ghi lại mốc dòng của log trước khi mở vòng đo; vòng 11, 12, 13
(9, 8, 9) là số liệu sau khi sửa.

**Báo cáo không trích dẫn cột này.** Các con số ở Bảng 3.2 lấy từ cột `slow`,
đo từ phía khách hàng, không liên quan tới log của load balancer, nên không bị
lỗi đếm ảnh hưởng.

## 3. `retries-*.log` có nhiều dòng hơn cột `retry_lines`

Ví dụ vòng 13: tệp 22 dòng, cột `retry_lines` là 9. Hai con số đo hai thứ khác
nhau. Cột `retry_lines` chỉ đếm dòng có `upstream=` (request thực sự được chuyển
node); phần còn lại là dòng nginx tự ghi vào tệp lỗi. Muốn tái dựng con số của
báo cáo thì lọc theo `upstream=`, đừng đếm cả tệp.

## 4. Ba bộ tệp top-level là ba vòng đo độc lập

`load-web02-20260929-150308`, `-150848`, `-152350` kèm `summary-*` và
`retries-*` tương ứng. Vòng **15:23:50** là vòng được trích dẫn cho các dòng log
ở mục 3.3 của báo cáo (25 dòng ghi, 10 dòng có hai địa chỉ upstream), vì nó là
vòng cuối chạy bằng `failover.sh` đã có mốc log. Hai vòng trước giữ lại để chứng
minh kết quả lặp lại được, không trích số từ đó.
