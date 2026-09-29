#1 CHƯƠNG 3. THỬ NGHIỆM VÀ ĐÁNH GIÁ

#2 3.1 Môi trường và cách tiến hành

#3 3.1.1 Môi trường phần cứng và phần mềm

[[TAB:moi-truong|Môi trường thử nghiệm]]
tbl:
| Mục | Giá trị |
| Máy | MSI Thin GF63 12UC, Intel Core i7-12650H, 16 logical processor |
| Bộ nhớ | 16.085 MB |
| Hệ điều hành | Windows 11 Pro, bản 10.0.26200 |
| Lớp ảo hóa | WSL 2.7.14, kernel 6.18.33.2, giới hạn 4 GB và 6 CPU qua .wslconfig |
| Engine container | Docker 29.8.1, Docker Compose v5.5.1 |
| Bộ cân bằng tải | nginx 1.27.5 |
| Node web | Alpine 3.20, nginx và PHP 8.3.15 |
| Kho phiên | Redis 7 |
| Cơ sở dữ liệu | MariaDB 11.4 |
| Máy đo | container client01, curl và ApacheBench 2.3 |
#tc

#3 3.1.2 Cách tiến hành

Mọi phép đo đều chạy từ container `client01`, không phát từ Windows, vì lý do đã nêu ở mục 2.2.3. Mỗi phép đo lưu hai thứ: bảng tổng hợp và log thô, nằm trong thư mục `results/`. Các con số trong chương này đọc lại từ chính log thô, không nhập tay.

Tập lệnh tổng hợp `summarize.awk` đã được đối chiếu trước bằng một file dữ liệu giả có đáp án biết trước: mười mẫu, hai mẫu lỗi nằm ở vị trí 6 và 7, khoảng gián đoạn khai báo 400 ms. Chương trình trả về đúng từng con số, kể cả bảng phân phối node trong đó hai mẫu không đọc được tên node bị đẩy vào ô riêng thay vì bị tính nhầm vào một node thật. Bộ phân tích header cũng thử riêng trên một khối header có sẵn ký tự xuống dòng kiểu CR LF. Nhờ đó các con số trong chương là kết quả đo của hệ thống, không phải sản phẩm của công đoạn tổng hợp.

[[FIG:anh-hinh-19|Danh sách file kết quả của lượt chạy được giữ lại làm nguồn cho mọi số liệu trong chương|16]]

#3 3.1.3 Lệnh đo và cách đọc kết quả

Toàn bộ phép đo hiệu năng dùng ApacheBench. Một lệnh đầy đủ có dạng:

```
ab -k -n 3000 -c 20 -q https://192.168.240.10/healthz
```

[[TAB:ab-flags|Ý nghĩa từng tham số của lệnh đo]]
tbl:
| Tham số | Ý nghĩa | Lý do chọn giá trị này |
| `-n 3000` | Tổng số yêu cầu gửi đi | Đủ dài để một vài yêu cầu chậm không làm lệch trung bình, nhưng vẫn kết thúc trong vài giây để chạy được nhiều lượt |
| `-c 20` | Số kết nối giữ đồng thời lúc nào cũng mở | Tạo ra trạng thái có nhiều kết nối đang mở, tức điều kiện cần để least connection khác round robin |
| `-k` | Bật keep-alive, nhiều yêu cầu dùng lại một kết nối TCP | Khi bật thì đo được tốc độ phục vụ yêu cầu; khi tắt thì phần lớn thời gian là bắt tay TLS, đo được tốc độ dựng kết nối |
| `-q` | Không in tiến trình | Để kết quả ghi thẳng vào file |
| đường dẫn | Endpoint bị đo | Chọn ba endpoint khác nhau để tách chi phí từng tầng, giải thích ở dưới |
#tc

Tham số `-c 20` là số kết nối luôn mở đồng thời, không phải số người dùng. Con số "Time per request" mà `ab` in ra là độ trễ trung bình của một yêu cầu trong điều kiện có 20 yêu cầu khác đang bay, không phải độ trễ của một yêu cầu đơn lẻ.

Ba yếu tố phương pháp được áp dụng cho toàn bộ phép đo, đưa vào sau khi các phép thử đầu tiên cho kết quả không ổn định.

Thứ nhất, mỗi ô của ma trận đo chạy 20 lượt độc lập, giữa các lượt nghỉ một giây. Một lượt duy nhất không đủ: hai lượt của cùng một cấu hình least_conn trong các phép thử thăm dò đã lệch nhau tới 34 phần trăm. Mỗi lượt cũng đặt giới hạn 240 giây; chế độ keep-alive đôi khi khiến `ab` không tự thoát trên WSL 2, và một lượt treo như vậy nếu không bị cắt sẽ làm hỏng toàn bộ các lượt sau vì chiếm tài nguyên của máy.

Thứ hai, trước 20 lượt đo là một lượt làm nóng không tính vào kết quả. Lượt này để bộ đệm của nginx, kho kết nối giữ lại tới node và cache của MariaDB đi vào trạng thái ổn định, tránh việc lượt đầu tiên luôn chậm hơn các lượt sau một cách hệ thống.

Thứ ba, kết quả trình bày dưới dạng trung bình kèm khoảng tin cậy 95% tính theo phân phối Student, và có phép kiểm Welch khi so sánh hai thuật toán. Trung bình một mình không nói được gì; phải so độ rộng khoảng tin cậy với độ lớn của hiệu ứng thì mới kết luận được hai cấu hình khác nhau hay chỉ khác nhau do nhiễu.

Ký hiệu dùng chung trong các bảng của mục 3.2 và 3.5: dấu "±" sau giá trị trung bình là nửa khoảng tin cậy 95% (CI) của trung bình đó; CV là hệ số biến thiên, tức độ lệch chuẩn chia cho trung bình, đo độ nhiễu của chính phép đo; P50, P95, P99 và P100 là các phân vị thời gian đáp ứng tính trên từng request trong một lượt đo, trong đó P50 mô tả request ở giữa, P99 mô tả 1% request chậm nhất và P100 là request chậm nhất của lượt đo.

Keep-alive được đưa vào làm một chiều của ma trận thay vì chọn một giá trị cố định, vì hai chế độ này đo hai đại lượng khác nhau.

Để tách chi phí của bộ cân bằng tải khỏi chi phí của ứng dụng, mỗi lượt đo trên một endpoint khác nhau:

[[TAB:bac-thang|Ba endpoint dùng để tách chi phí theo tầng]]
tbl:
| Endpoint | Đường đi của yêu cầu | Tầng được thêm vào |
| `/lb-only` | `ab` tới `lb01`, nginx trả lời tại chỗ | chỉ bộ cân bằng tải |
| `/healthz` | `lb01` sang node, node gọi php-fpm | thêm nginx và php-fpm trên node |
| `/dbping.php` | như trên, cộng một truy vấn `SELECT COUNT` | thêm MariaDB |
#tc

Hiệu số thời gian giữa hai dòng liên tiếp chính là chi phí của tầng vừa thêm vào, với điều kiện các yếu tố khác không đổi.

Ba thuật toán nhân ba endpoint nhân hai chế độ kết nối thành 18 ô. Mỗi ô 20 lượt đo cùng một lượt làm nóng, tổng cộng 360 lượt đo và 18 lượt làm nóng, ghi vào `results/bench/matrix-<Thời gian>.csv`. Hai phép đo khác dùng cùng giao thức nhưng trả lời câu hỏi khác: `results/distribute/skew-<Thời gian>.csv` chứa 60 lượt đo phân phối cho mục 3.2.2, còn `results/bench/degrade-<Thời gian>.csv` chứa 80 lượt đo (kèm 4 lượt làm nóng) so sánh cụm ba node với cụm hai node ở mục 3.5.4, kèm `degrade-nodes-<Thời gian>.csv` ghi số request mà từng node thực sự phục vụ trong mỗi kích thước. Chương trình tổng hợp của cả ba tệp là `analyze_bench.py`; mọi con số hiệu năng trong mục 3.2 và mục 3.5 chép từ đầu ra của đúng chương trình đó, và cũng đầu ra ấy được chụp lại thành hình.

#2 3.2 Khả năng phân phối yêu cầu

#3 3.2.1 Phép đo tuần tự

Gửi 300 request lần lượt tới `/healthz`, mỗi request một tiến trình curl riêng, đếm giá trị header `X-Node` ở đáp ứng.

[[TAB:phoi-tuan-tu|Phân phối 300 request gửi tuần tự]]
tbl:
| Thuật toán | web01 | web02 | web03 | Request thiếu header |
| round robin | 104 | 98 | 98 | 0 |
| least_conn | 104 | 98 | 98 | 0 |
| ip_hash | 300 | 0 | 0 | 0 |
#tc

Kết quả xác nhận cụm có phân phối được yêu cầu và `ip_hash` dồn toàn bộ về một node khi chỉ có một địa chỉ nguồn. Nhưng hai dòng đầu gây nghi ngờ: không những cùng tổng số, hai phép chạy còn cho **chuỗi 300 phần tử giống hệt nhau từng vị trí**.

Nghi vấn đầu tiên là thuật toán chưa thực sự đổi. Để loại trừ, mỗi lần chạy đã lưu lại đúng khối `upstream` mà nginx đang dùng. Ba file cấu hình khác nhau thật: vòng round robin có dòng comment thay cho directive, vòng least_conn có `least_conn;`, vòng ip_hash có `ip_hash;`.

Vậy đây là hành vi đúng của hệ thống, và nó chỉ ra một hạn chế của cách đo. least connection chọn node có ít kết nối đang mở nhất. Khi request gửi tuần tự, tại thời điểm chọn luôn không có kết nối nào đang mở, mọi node đều hòa nhau, và nginx phân xử theo đúng thứ tự vòng. Nói cách khác, với tải tuần tự thì least connection suy biến thành round robin, phép đo này không phân biệt được hai thuật toán.

[[FIG:anh-hinh-04|Phép đo tuần tự với round robin|16]]

[[FIG:anh-hinh-05|Phép đo tuần tự với least_conn, cho cùng chuỗi phân phối như round robin|16]]

[[FIG:anh-hinh-06|Phép đo tuần tự với ip_hash, toàn bộ request đi về một node|16]]

#3 3.2.2 Phép đo đồng thời hai mươi lượt

Để tạo ra trạng thái có nhiều kết nối mở cùng lúc, dùng ApacheBench gửi 600 request qua 20 kết nối song song và đếm node phục vụ từ chính access log của bộ cân bằng tải. Trường `$upstream_addr` trong log ghi lại địa chỉ node đã trả lời, nên phép đếm này không phụ thuộc vào việc node có gửi header đo hay không. Mỗi thuật toán chạy 20 lượt độc lập, sau một lượt làm nóng không tính vào kết quả, theo đúng giao thức đã nêu ở mục 3.1.3.

[[TAB:phoi-dong-thoi|Phân phối 600 request gửi đồng thời qua 20 kết nối, tổng hợp từ 20 lượt độc lập cho mỗi thuật toán]]
tbl:
| Thuật toán | web01 | web02 | web03 | Độ lệch lớn nhất giữa hai node trong một lượt | Request phải thử lại ở node khác |
| round robin | 199,9 ± 0,3 | 200,1 ± 0,3 | 200,0 ± 0,3 | 1,0 ± 0,5 | 0 |
| least_conn | 199,9 ± 1,9 | 200,5 ± 2,9 | 199,6 ± 2,3 | 10,2 ± 2,5 | 0 |
| ip_hash | 600,0 ± 0,0 | 0,0 ± 0,0 | 0,0 ± 0,0 | 600,0 ± 0,0 | 0 |
#tc

Mỗi ô là trung bình của 20 lượt kèm theo nửa khoảng tin cậy 95%. Cột cuối đếm số dòng log có hai địa chỉ upstream, tức những request bị chuyển sang node khác sau khi thử thất bại; mỗi thuật toán gồm 20 lượt, tức 12000 request; cả ba thuật toán là 36000 request, và không có request nào thuộc loại đó.

[[FIG:phoi-canh-dong-thoi|Trái: số request trung bình mỗi node theo thuật toán, sai số là nửa khoảng tin cậy 95%. Phải: độ lệch lớn nhất giữa hai node đo trong cùng một lượt]]

[[FIG:anh-hinh-07|Bảng phân phối hai mươi lượt in ra từ analyze_bench.py, đúng nguồn của các con số trong bảng trên|16]]

#3 3.2.3 Nhận xét

Độ đều của phân phối xếp hạng được. round robin chia 600 request thành 199,9 / 200,1 / 200,0, và độ lệch lớn nhất giữa hai node trong một lượt đo là 1,0 ± 0,5 request. least_conn cho 199,9 / 200,5 / 199,6 với độ lệch 10,2 ± 2,5 request. ip_hash dồn toàn bộ 600 request về một node ở cả hai mươi lượt. Ba khoảng 0,5 đến 1,5; 7,7 đến 12,7 và 600 không chồng lên nhau, nên thứ tự round robin đều nhất, least_conn kém hơn, ip_hash không phân phối là kết luận có cơ sở.

Việc least_conn cho cùng một chuỗi phân phối như round robin ở phép đo tuần tự (mục 3.2.1) nhưng kém đều hơn ở phép đo này không phải hai kết quả mâu thuẫn nhau. least connection chọn node có ít kết nối đang mở nhất. Ba node trong cụm chạy cùng một bản ảnh, cùng cấu hình php-fpm và trả về một đáp ứng 30 byte như nhau, nên tại thời điểm chọn, khác biệt giữa các node thường chỉ là không hoặc một kết nối. Thuật toán vì thế quyết định trên một mẫu nhiễu rất nhỏ và tích luỹ sai số đó thành độ lệch mười request, trong khi round robin đi theo một vòng đã định sẵn. Đúng như phân tích ở mục 1.5.3, least connection là thuật toán thích nghi và chỉ có lợi thế khi các node không đồng chất hoặc khi tồn tại request chậm; cấu hình của đề tài không có cả hai điều kiện đó.

Số request mỗi node nhận được và tốc độ phục vụ là hai đại lượng khác nhau. Tốc độ của ba thuật toán được đo riêng ở mục 3.5 bằng một ma trận 20 lượt cho mỗi cấu hình.

Với ip_hash, toàn bộ lưu lượng của một địa chỉ nguồn đi về đúng một node, nên node đó vừa là điểm nghẽn vừa là điểm hỏng đơn lẻ. Mục 3.4 sẽ cho thấy dính theo địa chỉ IP cũng không giữ được phiên khi node đó chết, còn mục 3.5 đo xem việc chỉ dùng một node làm giảm thông qua bao nhiêu khi ứng dụng thật sự phải tính toán.

Yêu cầu thứ nhất của đề bài được thỏa: cụm phân phối được yêu cầu đều trên ba node, và chọn được thuật toán bằng tham số chạy.

#2 3.3 Khả năng đáp ứng khi một máy chủ gặp sự cố

#3 3.3.1 Diễn biến

Vòng đo gửi một request, chờ kết quả, nghỉ 0,2 giây rồi gửi tiếp, lặp trong 70 giây, ghi lại thời điểm, mã HTTP, node phục vụ và thời gian đáp ứng của từng mẫu. Chu kỳ thực tế bằng 0,2 giây cộng thời gian đáp ứng, nên nhịp đạt được xấp xỉ 3,2 request mỗi giây và một vòng thu được khoảng 219 mẫu. Ở giây thứ 10, lệnh `docker compose stop web02` tắt hẳn node này. Ở giây thứ 40, `docker compose start web02` bật lại. Toàn bộ vòng đo được lặp lại 12 lần độc lập; mỗi lần lặp giữ lại cả tệp mẫu, bảng tổng hợp và log của lần đó trong `results/failover/repeat-<Thời gian>/`.

[[TAB:failover|Kết quả vòng đo khi tắt web02, trung bình 12 vòng lặp độc lập kèm nửa khoảng tin cậy 95%]]
tbl:
| Chỉ tiêu | Giá trị |
| Số mẫu trong vòng đo | 218,9 ± 13,1 |
| Số mẫu có mã HTTP khác 200 | 0,0 ± 0,0 |
| Thời gian đáp ứng trung bình | 90,2 ± 9,6 ms |
| Thời gian đáp ứng lớn nhất | 2026,4 ± 23,6 ms |
| Số mẫu phải chờ quá 1 giây | 8,8 ± 0,4 |
| Phân phối trong kỳ đo | web01: 84,6 ± 4,6, web02: 49,6 ± 4,3, web03: 84,8 ± 4,6 |
#tc

Số mẫu phải chờ quá một giây là đại lượng ổn định nhất của phép đo: 12 vòng cho lần lượt 9, 9, 9, 9, 10, 8, 9, 8, 8, 8, 9, 9 mẫu, trung bình 8,8 với nửa khoảng tin cậy 0,4, tức chạy lại thì kết quả dao động trong khoảng 8 đến 10. Chênh lệch giữa hai vòng lặp xa nhất chỉ là hai mẫu. Số mẫu lỗi HTTP bằng 0 ở cả 12 vòng, không có vòng nào ngoại lệ.

Hai đại lượng khác dao động mạnh hơn, và mỗi giá trị trung bình chỉ có nghĩa khi đi kèm khoảng của nó. Số mẫu của một vòng rơi trong dải 174 đến 232 vì vòng đo dừng theo thời gian chứ không theo số request, nên vòng nào gặp nhiều request chậm thì thu ít mẫu hơn. Thời gian đáp ứng trung bình dao động 77 đến 130 ms, hệ số biến thiên 16,7%, chủ yếu do tỉ lệ request trúng lượt thử node chết thay đổi giữa các vòng. Ngược lại, request chậm nhất của mỗi vòng rất ổn định: 2011 đến 2139 ms, tức đúng hai giây chờ của `proxy_connect_timeout` cộng phần dao động nhỏ.

[[FIG:do-thai-failover|Mỗi chấm là một request trong vòng đo, tô theo node phục vụ. Đường đỏ là thời điểm tắt web02; đường xanh là request đầu tiên web02 phục vụ trở lại sau sự cố, trễ hơn lệnh bật node vài giây]]

Đồ thị của một vòng đo điển hình cho thấy hai điểm. Không có mẫu nào rơi khỏi mức 200, kể cả ngay sau thời điểm tắt. Chín mẫu bị đẩy lên hơn 2000 ms, nằm rải suốt khoảng thời gian web02 chết. Sau khi web02 bật lại, tất cả trở về nền dưới 20 ms.

[[FIG:anh-hinh-08|Vòng đo failover: tắt web02 ở giây thứ 10, bật lại ở giây thứ 40, kèm bảng tổng hợp|16]]

#3 3.3.2 Bằng chứng trong log của bộ cân bằng tải

Một vòng đo điển hình lưu 25 dòng log ghi trong khoảng thời gian diễn ra sự cố, gồm 15 dòng do nginx ghi vào tệp lỗi và 10 dòng access log có hai địa chỉ upstream. Mười dòng nhiều hơn một dòng so với số mẫu chậm: chín dòng có `upstream_time=2.00x` tức là chờ trọn hai giây, dòng còn lại có `upstream_time=0.001, 0.001` vì node chết từ chối kết nối ngay bằng RST, request được chuyển node trong một phần nghìn giây nên không vượt ngưỡng một giây. Chín dòng chờ hai giây đúng bằng chín mẫu chậm, và mỗi dòng có dạng:

```
192.168.240.20 - [29/Sep/2026:08:24:02 +0000] "GET /healthz HTTP/2.0"
  status=200 upstream=172.20.0.12:80, 172.20.0.13:80
  upstream_status=504, 200 upstream_time=2.002, 0.001 req_time=2.004
```

Ba trường này kể lại toàn bộ sự việc. nginx thử node 172.20.0.12, nhận 504 sau 2,002 giây, tức là hết `proxy_connect_timeout`. Sau đó nó chuyển sang 172.20.0.13, node này trả lời trong 0,001 giây. Người dùng cuối nhận một đáp ứng 200 và chỉ phải chờ thêm hai giây.

[[FIG:anh-hinh-09|Các dòng access log tương ứng các mẫu chậm, mỗi dòng có hai địa chỉ upstream và cặp mã 504 rồi 200|16]]

#3 3.3.3 Vì sao không có request nào lỗi

Ba cấu hình phối hợp tạo ra kết quả đó. `proxy_connect_timeout 2s` chặn thời gian chờ một node chết, thay vì để mặc định 60 giây. `proxy_next_upstream error timeout http_502 http_503 http_504` cho phép chuyển node khi thử thất bại. `proxy_next_upstream_tries 2` giới hạn số lần thử để một request không đi vòng hết cả cụm.

Chi phí phải trả là hai giây chờ ở những request trúng lượt thử lại. Chín request chậm nằm trải trong 29 giây, cách nhau trung bình 3,6 giây, ngắn nhất 2 giây và dài nhất 5 giây. Khoảng cách này ngắn hơn nhiều chu kỳ `fail_timeout=10s` đã khai trong cấu hình. Lý do là mỗi request trúng lượt thử đều được tính là một lần thất bại, và vì máy đo gửi liên tục nên ngưỡng `max_fails=2` được tích lại nhanh hơn một chu kỳ hết hạn. Quy luật tương tác giữa ba tham số `max_fails`, `fail_timeout` và `proxy_next_upstream` cần một phép đo riêng; con số ghi ở đây là quan sát trực tiếp trên log của vòng đo.

Đây chính là đặc trưng của kiểm tra sức khỏe thụ động đã nêu ở mục 1.6. nginx bản mã nguồn mở không gửi yêu cầu thăm dò nền, nên nó chỉ biết node hỏng sau khi một người dùng thật phải chịu hậu quả. Nếu dùng HAProxy với `option httpchk`, node chết bị phát hiện mà không cần request thật, và khoảng chín mẫu chậm đó sẽ không tồn tại. Đổi lại phải thêm một thành phần và một lớp cấu hình.

Yêu cầu thứ hai của đề bài được thỏa: khi một máy chủ gặp sự cố, cụm vẫn đáp ứng, không cần can thiệp thủ công.

#2 3.4 Tính liên tục của phiên làm việc

Phép đo này trả lời câu hỏi: nếu node đã phục vụ đăng nhập chết thì người dùng có mất phiên không. Cách làm: đăng nhập, ghi lại node đã phục vụ, tắt đúng node đó, rồi gọi `/member.php` mười lần bằng cookie cũ.

Hai phương án chạy với hai cấu hình khác nhau, và sự khác nhau đó là nội dung của phép đo chứ không phải thiếu sót. Phương án redis dùng least_conn vì phiên nằm ngoài node nên được phép chọn tự do. Phương án file buộc phải dùng ip_hash, vì nếu không thì phiên đã mất ngay từ bước đăng nhập do token chống CSRF nằm ở node khác.

[[TAB:phien|Giữ phiên sau khi tắt node đã phục vụ đăng nhập]]
tbl:
| Phương án | Thuật toán | Node đăng nhập | Node bị tắt | Lần gọi giữ được phiên | Lần gọi bị đá về đăng nhập |
| redis | least_conn | web01 | web01 | 10 / 10 | 0 / 10 |
| file | ip_hash | web01 | web01 | 0 / 10 | 10 / 10 |
#tc

Ở phương án redis, mười lần gọi sau đó chia cho hai node còn lại theo tỉ lệ 7/3, tất cả đều trả 200 và vẫn hiển thị đúng tên người dùng. Ở phương án file, ip_hash dồn cả mười lần gọi về cùng một node vì chỉ còn node đó sống, và cả mười lần đều nhận 302 chuyển về trang đăng nhập.

Kết quả này khẳng định nhận định ở mục 1.7: ngay cả khi dùng ip hash để dính người dùng vào một node, việc mất node vẫn làm mất phiên. Sticky session chỉ giải quyết được vấn đề khi mọi node còn sống; nó không phải là cơ chế chịu lỗi. Chỉ đưa dữ liệu phiên ra ngoài node mới giải quyết được.

Yêu cầu thứ ba của đề bài được thỏa.

[[FIG:anh-hinh-10|Phương án redis: tắt đúng node vừa phục vụ đăng nhập, mười lần gọi sau vẫn giữ phiên|16]]

[[FIG:anh-hinh-11|Phương án file: cùng kịch bản, cả mười lần gọi bị trả về trang đăng nhập|16]]

#2 3.5 Hiệu năng

Mục này tách ba chuyện thường bị gộp làm một: bộ cân bằng tải tự nó phục vụ được bao nhiêu yêu cầu, chi phí của từng tầng nằm ở đâu, và ba thuật toán có khác nhau về thông qua hay không. Nguồn số liệu là `results/bench/matrix-20260929-103024.csv`: 18 ô, mỗi ô 20 lượt đo 3000 request với 20 kết nối song song, đã loại một lượt làm nóng.

#3 3.5.1 Thông qua theo thuật toán và theo tầng phản hồi

[[TAB:thong-qua|Thông qua trung bình của 20 lượt đo cho mỗi cặp thuật toán và endpoint. Cột CV là hệ số biến thiên, P50 và P99 tính trên từng request]]
tbl:
| Tầng phản hồi | Kết nối | Thuật toán | req/s ± 95% CI | CV | P50 | P99 |
| `/lb-only` | không giữ kết nối | round robin | 914,3 ± 23,0 | 5,4% | 22 ms | 36 ms |
| `/lb-only` | không giữ kết nối | least_conn | 918,9 ± 14,8 | 3,4% | 21 ms | 35 ms |
| `/lb-only` | không giữ kết nối | ip_hash | 909,4 ± 18,0 | 4,2% | 22 ms | 36 ms |
| `/lb-only` | keep-alive | round robin | 28869,2 ± 3048,1 | 22,6% | 0 ms | 2 ms |
| `/lb-only` | keep-alive | least_conn | 31360,0 ± 1922,1 | 13,1% | 0 ms | 2 ms |
| `/lb-only` | keep-alive | ip_hash | 30496,1 ± 2262,6 | 15,9% | 0 ms | 2 ms |
| `/healthz` | không giữ kết nối | round robin | 759,0 ± 24,4 | 6,9% | 25 ms | 44 ms |
| `/healthz` | không giữ kết nối | least_conn | 791,4 ± 24,1 | 6,5% | 24 ms | 42 ms |
| `/healthz` | không giữ kết nối | ip_hash | 854,7 ± 22,3 | 5,6% | 23 ms | 37 ms |
| `/healthz` | keep-alive | round robin | 848,0 ± 12,7 | 3,2% | 23 ms | 38 ms |
| `/healthz` | keep-alive | least_conn | 805,0 ± 8,3 | 2,2% | 24 ms | 40 ms |
| `/healthz` | keep-alive | ip_hash | 817,2 ± 15,3 | 4,0% | 24 ms | 41 ms |
| `/dbping.php` | không giữ kết nối | round robin | 693,4 ± 6,3 | 1,9% | 28 ms | 46 ms |
| `/dbping.php` | không giữ kết nối | least_conn | 702,9 ± 13,1 | 4,0% | 28 ms | 44 ms |
| `/dbping.php` | không giữ kết nối | ip_hash | 621,5 ± 6,6 | 2,3% | 31 ms | 52 ms |
| `/dbping.php` | keep-alive | round robin | 683,5 ± 8,4 | 2,6% | 29 ms | 46 ms |
| `/dbping.php` | keep-alive | least_conn | 707,4 ± 6,4 | 1,9% | 28 ms | 45 ms |
| `/dbping.php` | keep-alive | ip_hash | 619,4 ± 6,5 | 2,2% | 32 ms | 52 ms |
#tc

[[FIG:do-thi-thong-qua|Trái: thông qua theo tầng trên thang logarit, sai số là nửa khoảng tin cậy 95%. Phải: cùng phép đo ở tầng ứng dụng, nơi công việc thật của node xuất hiện]]

[[FIG:anh-hinh-13|Bảng ma trận 18 ô in ra từ chương trình tổng hợp, đúng nguồn của các con số trong mục này|16]]

Kết quả của bảng cho thấy ba điểm.

Thứ nhất, ở đường `/lb-only`, bật keep-alive đổi thông qua từ 914 lên 28869 req/s, gấp 31,6 lần. Cùng một bộ cân bằng tải, cùng một phần cứng, chỉ khác việc có dựng lại kết nối TCP và bắt tay TLS cho mỗi yêu cầu hay không. Khi tắt keep-alive thì phép đo đang đo tốc độ dựng kết nối, không phải tốc độ phục vụ yêu cầu, và cả ba thuật toán cho kết quả không phân biệt được (mục 3.5.3).

Thứ hai, thông qua của bản thân bộ cân bằng tải cao hơn thông qua của cả cụm khi có một node tham gia khoảng 39 lần: 31360 req/s cho riêng `lb01` so với 805 req/s khi mỗi yêu cầu phải đi tiếp sang node. Nói cách khác, ở cấu hình này cổ chai không nằm ở việc chọn node mà nằm ở đoạn từ bộ cân bằng tải tới ứng dụng. Con số 800 req/s là giới hạn của ba node nginx cộng php-fpm trên một máy tính, không phải giới hạn của nginx với vai trò cân bằng tải.

Thứ ba, hệ số biến thiên nội bộ mỗi thuật toán nhỏ hơn nhiều so với các phép đo bốn lượt trước đây: từ 1,9% đến 6,9% ở hai tầng có proxy, riêng tầng `/lb-only` keep-alive vẫn còn 13% đến 23% vì ở tốc độ 30000 req/s, độ nhiễu của lịch trình tiến trình chiếm tỷ lệ lớn.

#3 3.5.2 Bậc thang chi phí giữa các tầng

Bảng dưới lấy cùng số liệu trên nhưng đổi đơn vị thành thời gian cho một request, tính bằng cách nhân số kết nối song song với 1000 rồi chia cho thông qua, đúng như cách ApacheBench in dòng "Time per request (mean)". Đây là độ trễ trung bình khi đang có 20 yêu cầu bay đồng thời, không phải độ trễ của một người dùng đơn lẻ; độ trễ từng request là các cột P50 và P99 ở bảng trên.

[[TAB:thang-chi-phi|Chi phí cộng thêm của từng tầng, đo với least_conn]]
tbl:
| Chế độ kết nối | Tầng | req/s | ms cho một request | Cộng thêm so với tầng trước |
| không giữ kết nối | riêng bộ cân bằng tải | 918,9 | 21,8 | - |
| không giữ kết nối | thêm nginx và php-fpm trên node | 791,4 | 25,3 | 3,5 ms |
| không giữ kết nối | thêm một truy vấn MariaDB | 702,9 | 28,5 | 3,2 ms |
| keep-alive | riêng bộ cân bằng tải | 31360,0 | 0,6 | - |
| keep-alive | thêm nginx và php-fpm trên node | 805,0 | 24,8 | 24,2 ms |
| keep-alive | thêm một truy vấn MariaDB | 707,4 | 28,3 | 3,5 ms |
#tc

Hai dòng keep-alive cho thấy rõ nhất vị trí của chi phí: 24,2 ms trong tổng số 28,3 ms của một yêu cầu ứng dụng thật là chi phí của việc chuyển yêu cầu sang node và chờ php-fpm trả lời, gấp bảy lần chi phí của một truy vấn cơ sở dữ liệu và gấp bốn mươi lần chi phí tự thân của bộ cân bằng tải ở cùng chế độ kết nối. Một truy vấn `SELECT COUNT` chỉ cộng thêm 3,5 ms. Do đó điểm cần tối ưu nằm ở đoạn từ bộ cân bằng tải tới ứng dụng, không nằm ở thuật toán chọn node.

Ở chế độ không giữ kết nối thì bức tranh ngược lại: 21,8 ms trong 28,5 ms thuộc về việc dựng kết nối và bắt tay TLS, phần proxy chỉ còn 3,5 ms và phần cơ sở dữ liệu 3,2 ms. Cũng một hệ thống, hai câu trả lời khác nhau, tùy ở chỗ người đo có bật keep-alive hay không.

#3 3.5.3 Ba thuật toán có khác nhau về thông qua không

[[TAB:welch|Kiểm định Welch so với round robin trên cùng endpoint và cùng chế độ kết nối, mỗi bên 20 mẫu]]
tbl:
| Endpoint | Kết nối | So sánh | Chênh lệch | p | Kết luận ở mức 5% |
| `/lb-only` | không giữ kết nối | least_conn | +0,5% | 0,7271 | không có ý nghĩa thống kê |
| `/lb-only` | không giữ kết nối | ip_hash | -0,5% | 0,7228 | không có ý nghĩa thống kê |
| `/lb-only` | keep-alive | least_conn | +8,6% | 0,1577 | không có ý nghĩa thống kê |
| `/lb-only` | keep-alive | ip_hash | +5,6% | 0,3758 | không có ý nghĩa thống kê |
| `/healthz` | không giữ kết nối | least_conn | +4,3% | 0,0551 | không có ý nghĩa thống kê |
| `/healthz` | không giữ kết nối | ip_hash | +12,6% | 0,0000 | có ý nghĩa thống kê |
| `/healthz` | keep-alive | least_conn | -5,1% | 0,0000 | có ý nghĩa thống kê |
| `/healthz` | keep-alive | ip_hash | -3,6% | 0,0025 | có ý nghĩa thống kê |
| `/dbping.php` | không giữ kết nối | least_conn | +1,4% | 0,1859 | không có ý nghĩa thống kê |
| `/dbping.php` | không giữ kết nối | ip_hash | -10,4% | 0,0000 | có ý nghĩa thống kê |
| `/dbping.php` | keep-alive | least_conn | +3,5% | 0,0000 | có ý nghĩa thống kê |
| `/dbping.php` | keep-alive | ip_hash | -9,4% | 0,0000 | có ý nghĩa thống kê |
#tc

[[FIG:anh-hinh-20|Đoạn in ra của cùng chương trình chứa mười hai phép kiểm định Welch và bậc thang chi phí ở mục 3.5.2|16]]

round robin và least_conn không hơn kém nhau ổn định. Sáu ô so sánh giữa hai thuật toán này cho +0,5%, +8,6%, +4,3%, -5,1%, +1,4% và +3,5%; dấu của hiệu ứng đổi chiều giữa hai chế độ kết nối trên cùng một endpoint, nên không thể nói thuật toán nào nhanh hơn. Hai ô có p nhỏ hơn 0,05 chỉ đạt độ lớn 3,5% và 5,1%, nằm trong vùng mà một thay đổi nhỏ của môi trường đo cũng tạo ra được, nên chưa đủ để xếp hạng hai thuật toán này.

ip_hash thì khác, và chiều đổi ngược của nó là chi tiết đáng chú ý nhất. Ở `/healthz` không giữ kết nối, ip_hash nhanh hơn round robin 12,6% với p nhỏ hơn 0,0001. Ở `/dbping.php` nó chậm hơn 10,4%, cũng với p nhỏ hơn 0,0001. Nguyên nhân là `/healthz` chỉ đủ cho php-fpm trả lời một xâu 30 byte, nên một node gánh toàn bộ lưu lượng vẫn theo kịp và còn lợi hơn vì không phải chia kết nối; khi ứng dụng thật sự phải truy vấn cơ sở dữ liệu thì một node không theo kịp hai node kia. Đây chính là lý do phải đo riêng thông qua của bộ cân bằng tải và thông qua của ứng dụng: chọn thuật toán chỉ vì một con số ở đường kiểm tra sức khỏe sẽ dẫn tới quyết định sai ngay khi ứng dụng bắt đầu làm việc.

#3 3.5.4 Hiệu năng khi mất một node

Hai kích thước được đo bằng cùng một giao thức: 20 lượt, mỗi lượt 3000 request với 20 kết nối song song trên đường `/healthz`, thuật toán least_conn. Giữa hai lượt đo có một giây nghỉ, và trước đó là một lượt làm nóng. Kích thước hai node lấy bằng cách tắt hẳn `web03` và chờ quá một chu kỳ `fail_timeout` để nginx loại node đó khỏi danh sách.

[[TAB:hieu-nang|So sánh hai kích thước cụm, mỗi con số tổng hợp từ 20 lượt đo]]
tbl:
| Kích thước | Kết nối | req/s ± 95% CI | CV | P50 | P95 | P100 |
| ba node | không giữ kết nối | 779,3 ± 15,4 | 4,2% | 25 ms | 37 ms | 54 ms |
| hai node | không giữ kết nối | 719,4 ± 49,6 | 14,7% | 23 ms | 35 ms | 1048 ms |
| ba node | keep-alive | 771,4 ± 16,6 | 4,6% | 26 ms | 37 ms | 52 ms |
| hai node | keep-alive | 848,3 ± 76,8 | 19,4% | 20 ms | 28 ms | 2016 ms |
#tc

Bằng chứng rằng phép đo đúng như tên gọi: trong 126000 request của kích thước ba node, phân phối là 42156 / 41962 / 41882 cho web01, web02, web03; trong 126000 request của kích thước hai node, phân phối là 63058 / 62942 / 0, tức `web03` phục vụ chính xác không request nào.

Không có request nào trả về mã lỗi ở cả hai kích thước. Thông qua trung bình của hai node thấp hơn ba node 7,7% ở chế độ không giữ kết nối, kiểm định Welch cho p = 0,0243. Ở chế độ keep-alive, trung bình của hai node thậm chí cao hơn 10,0% với p = 0,0536, tức chưa loại được khả năng hai cấu hình như nhau.

Ba đại lượng sau phản ánh việc mất node, và cả ba đều nằm ngoài giá trị trung bình.

Thứ nhất, độ biến động. Hệ số biến thiên nhảy từ 4,2% lên 14,7% và từ 4,6% lên 19,4%, tức khoảng tin cậy của chính phép đo rộng gấp ba đến năm lần. Một cụm mất node không chậm đi đều đặn; nó trở nên khó đoán.

Thứ hai, đuôi phân phối. P100, tức request chậm nhất trong lượt đo, đi từ 54 ms lên 1048 ms ở chế độ không giữ kết nối và từ 52 ms lên 2016 ms ở chế độ keep-alive. Con số 2016 ms đúng bằng `proxy_connect_timeout 2s` đã cấu hình: mỗi chu kỳ `fail_timeout`, nginx cho một request thử lại node đã chết và request đó nằm chờ trọn hai giây trước khi được chuyển sang node khác.

Thứ ba, số request phải thử lại ở node khác: 126 trên 126000 request của kích thước hai node, chiếm 0,1%, trong khi kích thước ba node là 0. Tỷ lệ nhỏ nhưng tập trung hết vào một nhóm người dùng cụ thể, và đó là nhóm cảm thấy hệ thống có vấn đề.

P50 và P100 của cùng một lượt đo cách nhau hàng trăm lần. Nếu chỉ báo cáo trung bình thì kết luận rút ra là mất một node gần như không ảnh hưởng; nếu chỉ nhìn P95 thì hai dòng 35 ms và 28 ms của kích thước hai node lại thấp hơn 37 ms của kích thước ba node, tức mất node làm hệ thống nhanh lên. Mỗi kết luận trên đều lấy một thống kê duy nhất để đại diện cho cả phép đo. Đối với hệ thống cân bằng tải, tác động của việc mất node thể hiện ở phương sai và ở đuôi phân phối nhiều hơn ở giá trị trung bình.

Lý do thông qua trung bình không giảm tương ứng với việc mất 1/3 số node đã giải thích ở mục 3.5.1: trên đường `/healthz`, giới hạn nằm ở đoạn máy đo tới bộ cân bằng tải chứ không ở node, nên hai node vẫn thừa khả năng đáp ứng. Tổn thất chỉ hiện ra khi node phải làm việc thật, và ma trận ở mục 3.5.1 đã chỉ ra điều đó ở một phía khác: thuật toán dồn toàn bộ lưu lượng vào một node như ip_hash mất 10,4% thông qua khi endpoint phải truy vấn cơ sở dữ liệu.

[[FIG:anh-hinh-14|Bảng tổng hợp hai kích thước cụm in ra từ cùng chương trình sinh ra bảng trên, kèm dòng đếm node phục vụ|16]]

#2 3.6 Kiểm tra cấu hình và một số thuộc tính an toàn

Mục này trả lời một câu hỏi hẹp: những biện pháp bảo mật đã khai báo ở Chương 2 có thực sự có hiệu lực khi có người truy cập từ ngoài hay không. Hình thức là bảng kiểm cấu hình: mỗi hạng mục là một phát biểu chỉ có thể đúng hoặc sai, kiểm bằng một lệnh đọc mã trạng thái hoặc đọc header trả về, chạy tự động từ container máy đo và ghi kết quả vào `results/security/`. Phạm vi của mục này là kiểm tra cấu hình, không phải thử nghiệm xâm nhập.

[[TAB:an-toan|Kết quả kiểm tra cấu hình và thuộc tính an toàn của cụm, theo đúng thứ tự mà sec_check.sh in ra]]
tbl:
| Nhóm | Kiểm tra | Kết quả |
| Lộ thông tin | Header Server không kèm phiên bản | Đạt |
| Lộ thông tin | Không còn X-Powered-By của PHP | Đạt |
| Header | Strict-Transport-Security có mặt | Đạt |
| Header | X-Content-Type-Options nosniff | Đạt |
| Header | Content-Security-Policy | Đạt |
| Giao thức | Cổng 80 chuyển cưỡng bức sang HTTPS | Đạt |
| Giao thức | Thương lượng được TLS 1.2 trở lên, thực tế là TLS 1.3 | Đạt |
| Cookie | Phiên có cờ HttpOnly | Đạt |
| Cookie | Phiên có cờ Secure | Đạt |
| Cookie | Phiên có SameSite | Đạt |
| Kiểm soát truy cập | Không gọi trực tiếp được thư mục lib của ứng dụng | Đạt |
| Lộ thông tin | /healthz chỉ trả về trạng thái và tên node | Đạt |
| Chống lạm dụng | Giới hạn tần suất chặn request gửi dồn dập | Đạt |
| Kiểm soát truy cập | Không đọc được file cấu hình của ứng dụng | Đạt |
| Cách ly | Không gọi được node web từ mạng phía ngoài | Đạt |
| Cách ly | Node từ chối container khác trong cùng mạng backend | Đạt |
| Cách ly | Node không có đường ra Internet | Đạt |
| Log | Node ghi đúng địa chỉ khách hàng sau cân bằng tải | Đạt |
| Nội dung | Mọi node trả về cùng một nội dung | Đạt |
#tc

Mười chín hạng mục đều cho kết quả đúng như cấu hình đã khai báo; không có hạng mục thất bại và không còn hạng mục nào phải ghi nhận. Ba kết quả cụ thể như sau.

Hạng mục giới hạn tần suất từng báo đạt một cách sai lệch. Bản đầu của kiểm tra này gọi tới cổng 80 rồi đếm dòng "Non-2xx" mà ApacheBench in ra. Cổng 80 chỉ làm một việc là chuyển cưỡng bức sang HTTPS, nên toàn bộ 200 request đều nhận mã 301, và 301 cũng là non-2xx. Kiểm tra vì thế luôn đạt cho dù giới hạn có tắt. Bản hiện tại gọi thẳng sang HTTPS và đếm mã 429 trong tệp log riêng của đường thăm dò, do chính nginx ghi lại. Kết quả là 193 trên 200 request nhận 429; bảy request còn lại lọt qua, sát với `burst=5` cộng một request đang được xét, phần lệch nằm ở tốc độ bù của vùng trong lúc máy đo gửi hết 200 request.

Hạng mục đọc file cấu hình cũng từng là một kiểm tra chết. Vị trí khai báo `location ~ ^/(config\.php|\.env)` nằm sau `location ~ \.php$`, mà nginx xét các regex theo thứ tự xuất hiện, nên mọi request tới `/config.php` đã bị khối xử lý `.php` nhận trước và rule chặn không bao giờ chạy. Sửa thành `location = /config.php` thì đúng, vì match tuyệt đối có ưu tiên cao hơn mọi regex.

Hạng mục "Node từ chối container khác trong cùng mạng backend" trước đây cho kết quả ngược lại và được xếp loại ghi nhận: node vẫn trả lời 200 cho bất kỳ ai nằm trong mạng backend, nên hàng rào duy nhất là tầng mạng. Sau khi thêm `allow 172.20.0.10; deny all;` ở node, đúng cuộc gọi đó nhận 403 và hạng mục chuyển thành đạt. Hạng mục log đi kèm chứng minh việc chặn nguồn không làm hỏng truy vết: node vẫn ghi đúng địa chỉ khách hàng vào dòng log của mình.

[[FIG:anh-hinh-12|Bảng kiểm cấu hình mười chín hạng mục in ra từ sec_check.sh|16]]

[[FIG:anh-hinh-18|Giới hạn tần suất chặn 194 trong 200 request gửi dồn dập vào đường thăm dò|16]]

#2 3.7 Nhận xét và hạn chế

Sáu yêu cầu đặt ra ở mục 2.1 đều được kiểm chứng bằng số liệu: chọn node theo thuật toán khai báo ở mục 3.2, dịch vụ vẫn trả lời khi tắt hẳn một node ở mục 3.3, phiên không nằm trong node ở mục 3.4, mọi node trả về cùng một nội dung và node không tiết lộ thông tin hệ thống ở bảng kiểm 3.6, mọi phép đo chạy lại được bằng một lệnh kèm log thô ở mục 3.1.3. Riêng yêu cầu thứ năm, node không tiếp nhận kết nối từ ngoài, nay đạt ở cả hai lớp: từ mạng phía ngoài không thiết lập được kết nối, và từ một container khác trong cùng mạng backend thì node trả về 403.

Ba hạn chế còn lại của mô hình.

Thứ nhất, bộ cân bằng tải là điểm hỏng đơn lẻ. Mất `lb01` thì cả cụm mất cửa vào. Hướng xử lý bằng hai instance và VRRP được nêu ở phần định hướng phát triển của Kết luận.

Thứ hai, nginx mã nguồn mở chỉ phát hiện node chết một cách thụ động, nên luôn có request phải chịu hai giây chờ. Các request chậm trong phép đo failover ở mục 3.3 và 126 request phải thử lại trong phép đo ở mục 3.5.4 là biểu hiện của cơ chế này.

Thứ ba, toàn bộ cụm chạy trên một máy vật lý. Các phép đo về giao thức và định tuyến vì thế vẫn phản ánh đúng hành vi của hệ thống, còn độ trễ mạng thật giữa các node và hiện tượng nghẽn ở cổng lên thì chưa nằm trong phạm vi đo.

#2 3.8 Kết chương

Chương này đã đo đủ ba nội dung đề bài yêu cầu. Về phân phối tải, 600 request gửi đồng thời qua 20 kết nối, tổng hợp từ 20 lượt độc lập cho mỗi thuật toán: round robin chia 199,9 / 200,1 / 200,0 với độ lệch lớn nhất giữa hai node trong một lượt là 1,0 request, least_conn chia 199,9 / 200,5 / 199,6 với độ lệch 10,2 request, còn ip_hash dồn 600 request về một node ở cả hai mươi lượt. Về khả năng chịu lỗi, tắt hẳn một node trong 30 giây không làm hỏng request nào ở cả 12 vòng đo lặp lại; cái giá phải trả là 8,8 ± 0,4 request mỗi vòng phải chờ thêm hai giây, đúng như phân tích về kiểm tra sức khỏe thụ động ở Chương 1. Về phiên làm việc, kho dùng chung giữ được 10 trên 10 phiên sau khi tắt node phục vụ đăng nhập, cách lưu trong node giữ được 0 trên 10.

Ngoài ba yêu cầu đó, ma trận 18 ô với 20 lượt cho mỗi ô trả lời thêm câu hỏi nên nhìn vào đâu khi hệ thống chậm. Bộ cân bằng tải tự nó phục vụ 31360 req/s; khi mỗi yêu cầu phải chuyển tiếp sang node, con số còn 805 req/s. Thuật toán chọn node không tạo ra khoảng cách đó: ở tầng ứng dụng, round robin và least_conn chênh nhau không quá 5,1% và dấu của chênh lệch đổi chiều giữa hai chế độ kết nối; chỉ có ip_hash, thuật toán dồn mọi lưu lượng vào một node, tách khỏi hai thuật toán kia với mức -10,4%. Mất một trong ba node cũng không làm thông qua trung bình giảm bao nhiêu, chỉ -7,7%, nhưng làm hệ số biến thiên tăng từ 4,2% lên 14,7% và đẩy request chậm nhất từ 54 ms lên 1048 ms. Mười chín hạng mục kiểm tra cấu hình đều cho kết quả đạt.
