#0 KẾT LUẬN

!b Các kết quả đạt được

Nhóm đã hoàn thành việc tìm hiểu và triển khai cụm máy chủ web cân bằng tải theo đề tài số 7, đối chiếu với từng yêu cầu của đề bài như sau.

Về tìm hiểu lý thuyết, báo cáo đã trình bày được khái niệm cân bằng tải máy chủ web, vị trí của nó trong yêu cầu bảo đảm tính sẵn dùng theo giáo trình, phân biệt cân bằng tải tầng ba, tầng bốn và tầng bảy, liệt kê các thành phần của một cụm gồm pool thành viên, cơ chế kiểm tra sức khỏe, kho phiên dùng chung và cơ sở dữ liệu dùng chung, so sánh sáu thuật toán phân phối và năm nhóm công cụ.

Về triển khai cụm hai đến ba máy chủ web phục vụ cùng một website, hệ thống gồm ba node nginx kết hợp php-fpm 8.3, cùng dựng từ một bản ảnh, cùng đọc một MariaDB và cùng dùng một kho phiên Redis. Toàn bộ khai báo trong một tệp Docker Compose, khởi động lại được bằng một lệnh.

Về thành phần cân bằng tải, bộ cân bằng tải nginx 1.27 đặt ở vị trí duy nhất nhận lưu lượng từ ngoài, có khối upstream khai báo ba thành viên, chọn thuật toán qua tham số chạy mà không phải sửa cấu hình.

Về kiểm tra phân phối request, hai phép đo đã thực hiện. Với 300 request gửi tuần tự, phân phối là 104 / 98 / 98 và chuỗi phân phối của round robin trùng khớp least_conn ở từng vị trí. Với 600 request gửi qua 20 kết nối song song, chạy 20 lượt độc lập cho mỗi thuật toán, round robin cho 199,9 / 200,1 / 200,0 với độ lệch lớn nhất giữa hai node trong một lượt là 1,0 request; least_conn cho 199,9 / 200,5 / 199,6 với độ lệch 10,2 request; ip_hash dồn 600 về một node ở cả hai mươi lượt. Phép đo thứ hai được bổ sung sau khi phát hiện phép đo thứ nhất không phân biệt được round robin với least_conn, và chính chỗ này cho kết luận rằng least connection chỉ khác round robin khi có request chồng lấn hoặc khi các node không đồng chất.

Về hiệu năng, một ma trận 18 ô với 20 lượt đo cho mỗi ô tách được ba thứ vẫn hay bị gộp làm một. Bộ cân bằng tải tự nó đạt 31360 req/s; con số rơi xuống 805 req/s khi mỗi yêu cầu phải chuyển tiếp sang node và 707 req/s khi node còn phải truy vấn cơ sở dữ liệu. Tính theo thời gian cho một request ở 20 kết nối song song, 24,2 ms trong tổng số 28,3 ms thuộc về tầng ứng dụng, chỉ 0,6 ms thuộc về việc cân bằng tải, và một truy vấn MariaDB cộng thêm 3,5 ms. Ba thuật toán không hơn kém nhau ổn định về thông qua: độ lớn chênh lệch không quá 5% ở tầng ứng dụng và dấu của nó đổi chiều giữa hai chế độ kết nối. Mất một trong ba node làm thông qua trung bình giảm 7,7%, nhưng làm hệ số biến thiên tăng từ 4,2% lên 14,7% và đẩy request chậm nhất trong lượt đo từ 54 ms lên 1048 ms.

Về khả năng đáp ứng khi một server gặp sự cố, vòng đo 70 giây được lặp lại 12 lần độc lập, mỗi lần khoảng 219 mẫu, với lệnh tắt hẳn web02 ở giây thứ 10. Không có request nào nhận mã lỗi ở cả 12 vòng. Trung bình 8,8 ± 0,4 mẫu phải chờ thêm khoảng hai giây do nginx thử lại node đã chết, và hành vi này khớp với cơ chế kiểm tra sức khỏe thụ động đã phân tích ở Chương 1. Bằng chứng là chín dòng log có hai địa chỉ upstream kèm cặp mã trạng thái 504 rồi 200. Cùng kịch bản tắt đúng node vừa phục vụ đăng nhập, phiên của người dùng chỉ sống được khi nó không nằm trong node: phương án kho Redis dùng chung giữ được 10 trên 10 phiên, phương án lưu trên đĩa của chính node giữ được 0 trên 10.

Ngoài ba yêu cầu của đề bài, đề tài còn làm thêm hai việc phục vụ trực tiếp cho tính sẵn dùng và cho môn học. Thứ nhất, xây dựng bảng kiểm cấu hình và thuộc tính an toàn gồm mười chín hạng mục tự động, phủ ẩn phiên bản máy chủ, kết thúc TLS tại cân bằng tải, HSTS và các header an toàn, cờ bảo vệ cookie phiên, giới hạn tần suất cho đường thăm dò, chặn đọc file cấu hình, cách ly node khỏi mạng phía ngoài, node chỉ nhận yêu cầu từ đúng bộ cân bằng tải, đường kiểm tra sức khỏe không lộ thông tin và việc mọi node trả về cùng một nội dung. Cả mười chín hạng mục đều xác nhận cấu hình có hiệu lực. Bảng kiểm đánh giá hiệu lực của cấu hình, không đánh giá khả năng chống tấn công. Thứ hai, toàn bộ log thô của mọi phép đo được lưu trong thư mục results, nên từng con số trong báo cáo đều kiểm tra lại được.

Trong quá trình làm, năm chỗ sai đã phát hiện và sửa. Ba chỗ sai ở cấu hình im lặng, không báo lỗi mà chỉ làm tính năng mất tác dụng: location chỉ có `return` khiến `limit_req` không bao giờ được xét; `location ~ ^/(config\.php|\.env)` đặt sau `location ~ \.php$` nên không bao giờ chạy vì nginx xét regex theo thứ tự xuất hiện; php-fpm với `clear_env = yes` mặc định xóa hết biến môi trường của container khiến ứng dụng không đọc được địa chỉ cơ sở dữ liệu. Một chỗ sai làm nginx không khởi động được: khai báo `nodelay` đặt nhầm ở `limit_req_zone` thay vì `limit_req`. Chỗ sai cuối cùng nằm ở chính công cụ đo: kiểm tra giới hạn tần suất đếm dòng "Non-2xx" của ApacheBench trong khi gọi tới cổng 80, nơi mọi request đều nhận 301 chuyển hướng, nên nó báo đạt ngay cả khi giới hạn đang tắt.

!b Hướng phát triển

Bốn hướng mở rộng được xác định nhưng chưa thực hiện trong đề tài.

Loại bỏ điểm hỏng đơn lẻ còn lại của chính bộ cân bằng tải bằng hai instance và giao thức VRRP qua keepalived, kèm kiểm tra nginx định kỳ để tự hạ ưu tiên. Cấu hình mẫu đã chuẩn bị, nhưng Docker Desktop trên Windows không bảo đảm chuyển được multicast của VRRP, nên cần làm trên mạng ảo hóa kiểu VirtualBox hoặc VMware hoặc trên nhiều máy vật lý.

Chuyển từ kiểm tra sức khỏe thụ động sang chủ động. HAProxy với `option httpchk` phát hiện node chết mà không cần request thật, dự kiến loại được các request phải chờ hai giây ở mục 3.3, trung bình 8,8 mẫu trên mỗi vòng đo. Cần một phép đo so sánh trực tiếp hai cơ chế trên cùng một tải.

Mã hóa đoạn từ bộ cân bằng tải về node và thêm ràng buộc để node chỉ nhận yêu cầu từ đúng cân bằng tải, chẳng hạn TLS hai chiều với chứng chỉ client hoặc quy tắc tường lửa theo địa chỉ nguồn. Hiện tại việc cách ly chỉ dựa ở tầng mạng.

Đưa cơ sở dữ liệu và kho phiên ra mô hình có dự phòng, gồm nhân bản MariaDB và Redis Sentinel, để hai thành phần này không còn là điểm hỏng đơn lẻ. Khi đó mới đo được hành vi của cụm khi mất cả node web lẫn node dữ liệu cùng lúc.
