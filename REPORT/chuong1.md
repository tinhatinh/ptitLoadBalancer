#1 CHƯƠNG 1. TỔNG QUAN VỀ CÂN BẰNG TẢI CÁC MÁY CHỦ WEB

#2 1.1 Khái niệm

Cân bằng tải (load balancing) là kỹ thuật phân chia khối lượng công việc của một hệ thống ra nhiều thành phần cùng đảm nhận, sao cho không thành phần nào phải chịu toàn bộ tải trong khi các thành phần khác còn nhàn rỗi, mô tả ở {fig:he-thong}. Khi áp dụng cho máy chủ web, cân bằng tải là việc phân phối các yêu cầu HTTP và HTTPS của người dùng tới nhiều máy chủ web cùng phục vụ một nội dung, thay vì dồn toàn bộ về một máy chủ duy nhất.

Một cụm máy chủ web (web server cluster) là tập hợp từ hai máy chủ web trở lên, cấu hình giống nhau, trả lời trên cùng một tên miền và cùng một nội dung. Bên ngoài, người dùng chỉ nhìn thấy một địa chỉ. Bên trong, yêu cầu được chia cho các thành viên của cụm.

Bộ cân bằng tải (load balancer) là phần mềm hoặc thiết bị đứng trước cụm máy chủ web, tiếp nhận yêu cầu từ người dùng, chọn ra một máy chủ trong cụm và chuyển yêu cầu đó tới máy chủ được chọn. Đáp ứng của máy chủ đi ngược trở lại người dùng thông qua bộ cân bằng tải, nên người dùng không biết và không cần biết máy chủ nào đã phục vụ mình.

Xét theo ba yêu cầu cơ bản của an toàn thông tin, cân bằng tải máy chủ web tác động trực tiếp vào tính sẵn dùng. Giáo trình của học phần xếp cân bằng tải cùng với nhân bản cơ sở dữ liệu thành hai biện pháp bảo đảm tính sẵn dùng, thể hiện ở Hình 5.12 của chương về an toàn cơ sở dữ liệu [1]. Đây là điểm khác biệt cần nhấn mạnh so với cách hiểu phổ biến coi cân bằng tải chỉ là giải pháp tăng tốc độ: tăng năng lực phục vụ là hệ quả, còn mục tiêu an toàn là giữ cho dịch vụ trả lời được khi một thành phần ngừng hoạt động.

[[FIG:he-thong|Hệ thống có bộ cân bằng tải đứng trước cụm máy chủ web]]

#2 1.2 Cân bằng tải trong bối cảnh bảo mật ứng dụng web

#3 1.2.1 Vị trí trong các lớp bảo mật

Giáo trình chia việc bảo mật ứng dụng web thành các lớp, trong đó lớp bảo mật máy chủ là lớp nằm ngay dưới lớp ứng dụng [1]. Bộ cân bằng tải tạo ra một điểm tập trung để đặt các biện pháp của lớp này: chỉ một chỗ phải cấu hình TLS, chỉ một chỗ khai báo header an toàn, chỉ một chỗ áp giới hạn tần suất. Ở mô hình một máy chủ đơn lẻ, các biện pháp đó nằm rải rác và dễ bị bỏ sót khi có máy chủ mới được thêm vào cụm.

#3 1.2.2 Quan hệ với các tấn công gây mất sẵn dùng

Tấn công từ chối dịch vụ nhắm vào tính sẵn dùng có hai dạng. Dạng khai thác lỗ hổng làm sập tiến trình phục vụ chỉ cần một yêu cầu độc hại. Dạng chiếm hết tài nguyên cần lưu lượng lớn hơn khả năng đáp ứng. Cân bằng tải chỉ xử lý được một phần của dạng thứ hai, bằng cách mở rộng số node tiếp nhận yêu cầu và bằng cách loại node đã chết ra khỏi vòng phục vụ. Nó không xử lý được dạng khai thác lỗ hổng, cũng không xử lý được tấn công làm nghẽn đường truyền trước bộ cân bằng tải. Giới hạn này cần nói rõ để không trình bày cân bằng tải như một biện pháp chống từ chối dịch vụ hoàn chỉnh.

#3 1.2.3 Bốn câu hỏi an toàn đặt ra cho mô hình

Đưa thêm một thành phần vào giữa người dùng và máy chủ làm xuất hiện các câu hỏi mà mô hình một máy chủ không có. Đoạn mã hóa từ bộ cân bằng tải về node có được bảo vệ không. Định danh phiên và cookie xử lý thế nào khi người dùng lần lượt gặp các node khác nhau. Nhật ký ở đâu phản ánh đúng địa chỉ của người gửi. Node có chấp nhận yêu cầu đi vòng qua bộ cân bằng tải hay không. Bốn câu hỏi này xuyên suốt đề tài và là nội dung của Chương 2 và Chương 3.

#2 1.3 Phân tầng của bộ cân bằng tải

Bộ cân bằng tải được phân loại theo tầng của mô hình OSI mà nó đọc được thông tin để ra quyết định định tuyến.

#3 1.3.1 Cân bằng tải tầng 4

Làm việc với địa chỉ IP và cổng TCP hoặc UDP. Bộ cân bằng tải nhận kết nối, chọn máy chủ đích theo bảng định tuyến hoặc theo thuật toán, rồi chuyển tiếp. Nội dung của giao thức ứng dụng không được giải mã, nên chi phí xử lý trên mỗi gói tin thấp và năng lực chuyển tiếp thường rất lớn.

Hệ quả là mọi quyết định chỉ dựa trên cặp địa chỉ và cổng. Hai yêu cầu tới /api và tới /images từ cùng một người dùng không thể đi tới hai cụm khác nhau.

#3 1.3.2 Cân bằng tải tầng 7

Làm việc ở tầng ứng dụng, đọc được yêu cầu HTTP đã giải mã: phương thức, đường dẫn, tiêu đề, cookie. Nhờ đó bộ cân bằng tải định tuyến theo nội dung, chẳng hạn chuyển đường dẫn /api sang cụm ứng dụng, chuyển thư mục ảnh sang cụm phục vụ nội dung tĩnh, và chọn node dựa trên giá trị cookie.

Cân bằng tải tầng 7 còn thường đảm nhận giải mã TLS, gọi là kết thúc TLS. Việc này gom chứng chỉ về một chỗ và dồn chi phí tính toán mã hóa vào bộ cân bằng tải, đổi lại đoạn từ bộ cân bằng tải về node web có thể đi dưới dạng HTTP thuần nếu không được bảo vệ bằng một lớp mã hóa riêng.

#3 1.3.3 Cân bằng tải tầng 3 và cân bằng tải bằng DNS

Ở tầng mạng, cân bằng tải dựa trên địa chỉ IP nguồn và IP đích, thường do thiết bị định tuyến đảm nhiệm, không liên quan tới nội dung web. Một cách tiếp cận khác phổ biến vì rẻ là DNS round robin: tên miền trả về nhiều bản ghi A, trình duyệt tự phân tán kết nối. Hạn chế là bộ định tên miền không biết máy chủ nào còn sống, thời gian khuếch tán bản ghi khiến việc loại một máy chủ hỏng mất nhiều phút, và trình duyệt thường ghi nhớ kết quả nên một người dùng có thể dính mãi một máy chủ.

[[TAB:so-sanh-tang|So sánh bộ cân bằng tải theo tầng làm việc]]
tbl:
| Tiêu chí | Tầng 3 | Tầng 4 | Tầng 7 |
| Thông tin dùng để quyết định | IP nguồn, IP đích | IP và cổng TCP/UDP | Nội dung HTTP: đường dẫn, tiêu đề, cookie |
| Có giải mã TLS tại bộ cân bằng tải | Không | Không bắt buộc | Có |
| Định tuyến theo đường dẫn URI | Không | Không | Có |
| Duy trì phiên theo cookie | Không | Không | Có |
| Chi phí xử lý mỗi yêu cầu | Thấp | Thấp | Trung bình đến cao |
| Phù hợp với ứng dụng web động | Kém | Tốt | Tốt nhất |
#tc

#2 1.4 Các thành phần của cụm máy chủ web cân bằng tải

[[FIG:thanh-phan|Các thành phần của một cụm máy chủ web cân bằng tải]]

Bộ cân bằng tải giữ danh sách thành viên của cụm, còn gọi là pool hoặc upstream. Mỗi thành viên có địa chỉ, cổng, trọng số và trạng thái.

Cơ chế kiểm tra sức khỏe xác định thành viên nào đang đáp ứng được. Có hai cách. Kiểm tra thụ động chỉ nhìn kết quả của các yêu cầu thật: sau một số lần lỗi liên tiếp, thành viên bị đánh dấu không đạt và bị loại trong một khoảng thời gian, hết thời gian thì được cho vào lại. Kiểm tra chủ động gửi thêm các yêu cầu thăm dò định kỳ tới một đường dẫn dành riêng, nên phát hiện máy chủ chết trước khi người dùng thật gặp lỗi.

Kho lưu phiên dùng chung giữ dữ liệu phiên của mọi node tại một chỗ, để bất kỳ node nào cũng đọc được phiên của bất kỳ người dùng nào.

Lưu trữ dùng chung và hệ quản trị cơ sở dữ liệu dùng chung bảo đảm mọi node đọc và ghi trên cùng một tập dữ liệu. Nếu mỗi node có một cơ sở dữ liệu riêng thì hai người dùng gặp hai node khác nhau sẽ thấy hai nội dung khác nhau.

Cụm cũng cần một cơ chế để nội dung do người dùng tải lên xuất hiện trên mọi node. Các thành phần của cụm được vẽ ở {fig:thanh-phan}. Với hệ thống nhỏ, dữ liệu tải lên nên đưa vào cơ sở dữ liệu hoặc một vùng lưu trữ đối tượng, không để trong thư mục cục bộ của node.

#2 1.5 Các thuật toán phân phối yêu cầu

#3 1.5.1 Round robin

Duyệt qua danh sách thành viên theo thứ tự vòng. Yêu cầu thứ nhất tới node thứ nhất, yêu cầu thứ hai tới node thứ hai, hết danh sách thì quay lại. Thuật toán không xét tới việc node nào đang bận hay nhanh chậm, chỉ cần danh sách còn thành viên là còn phân đều theo số lượng, mô tả ở {fig:round-robin}.

[[FIG:round-robin|Nguyên lý round robin]]

#3 1.5.2 Weighted round robin

Mỗi thành viên gắn một trọng số là số nguyên. Trong một vòng, thành viên có trọng số lớn được chọn nhiều lần hơn theo đúng tỉ lệ trọng số. Dùng khi các máy chủ trong cụm có cấu hình phần cứng khác nhau. Round robin thuần là trường hợp đặc biệt khi mọi trọng số bằng nhau, mô tả ở {fig:round-robin}.

#3 1.5.3 Least connection

Chọn thành viên đang có ít kết nối đang xử lý nhất, có tính trọng số. Khác với round robin, thuật toán này phản ánh tải thực tế tại thời điểm quyết định: một node trả lời chậm sẽ tích lũy nhiều kết nối mở và tự động nhận ít yêu cầu mới hơn. Ở chiều ngược lại, khi mọi node đồng chất và các request nhanh như nhau, số kết nối đang mở tại thời điểm chọn thường bằng nhau ở mọi node nên kết quả sát với round robin; khác biệt giữa hai thuật toán chỉ xuất hiện khi có node chậm hoặc khi nhiều request chồng lấn lên nhau, so sánh ở {fig:least-conn} và mục 3.2.3.

[[FIG:least-conn|Nguyên lý least connection]]

#3 1.5.4 Weighted least connection

Kết hợp hai ý trên: chọn tỉ lệ giữa số kết nối đang mở và trọng số, rồi lấy giá trị nhỏ nhất.

#3 1.5.5 IP hash

Tính hàm băm trên địa chỉ IP của người gửi, rồi ánh xạ kết quả vào danh sách thành viên. Cùng một địa chỉ IP luôn ra cùng một node, nên phiên để ở node vẫn được sử dụng lại.

Hai hạn chế. Người dùng trong một mạng công ty đi ra chung một địa chỉ sẽ đổ hết tải lên một node. Khi danh sách thành viên thay đổi, ánh xạ băm thay đổi theo và phần lớn người dùng bị chuyển sang node khác, mô tả ở {fig:ip-hash}.

[[FIG:ip-hash|Nguyên lý ip hash]]

#3 1.5.6 Hash theo URI và các thuật toán dựa trên nội dung

Băm đường dẫn yêu cầu để mọi yêu cầu tới cùng một tài nguyên đi về cùng một node, hoặc dùng một cookie riêng do bộ cân bằng tải gán để giữ người dùng ở lại node đã chọn. Nhóm này thuộc khả năng chỉ có ở cân bằng tải tầng 7.

[[TAB:so-sanh-thuat-toan|So sánh các thuật toán phân phối yêu cầu]]
tbl:
| Thuật toán | Căn cứ quyết định | Đều theo số request | Có tính tới tốc độ node | Giữ được phiên tại node | Nhạy khi thêm bớt node |
| Round robin | Thứ tự vòng | Có | Không | Không | Ít |
| Weighted round robin | Thứ tự vòng và trọng số | Theo trọng số | Một phần, qua trọng số | Không | Ít |
| Least connection | Số kết nối đang mở | Không tuyệt đối | Có | Không | Ít |
| Weighted least connection | Kết nối đang mở và trọng số | Không tuyệt đối | Có | Không | Ít |
| IP hash | Địa chỉ IP người gửi | Không | Không | Có | Nhiều |
| Hash theo URI | Đường dẫn yêu cầu | Không | Không | Một phần | Nhiều |
#tc

#2 1.6 Kiểm tra sức khỏe node

#3 1.6.1 Kiểm tra thụ động

Trong nginx mã nguồn mở, cấu hình gồm hai tham số đi cùng nhau. max_fails là số lần yêu cầu thất bại liên tiếp cần thiết để đánh dấu một thành viên không đạt. fail_timeout là khoảng thời gian thành viên bị loại, đồng thời là cửa sổ đếm lỗi. Sau khi hết hạn, nginx gửi thử một yêu cầu; nếu thành công, thành viên trở lại danh sách.

Các lỗi được tính gồm kết nối bị từ chối, hết thời gian kết nối, hết thời gian đọc, và một số mã trạng thái nếu được khai báo trong chỉ thị proxy_next_upstream.

#3 1.6.2 Kiểm tra chủ động

Kiểm tra chủ động cần một yêu cầu thăm dò riêng, gửi định kỳ tới một đường dẫn như /healthz, và coi là đạt khi nhận đúng mã trạng thái mong đợi. HAProxy hỗ trợ sẵn qua option httpchk. Nginx mã nguồn mở không có kiểm tra chủ động trong khối upstream; muốn có phải dùng nginx Plus hoặc một tiến trình ngoài ghi kết quả vào file mà nginx đọc lại.

Sự khác biệt này quyết định hình dạng của thời gian gián đoạn đo được ở Chương 3. Với kiểm tra thụ động, yêu cầu đầu tiên sau khi node chết chắc chắn thất bại hoặc phải chờ nginx chuyển sang node kế tiếp, vì nginx chỉ biết node hỏng sau khi thử phục vụ người dùng thật.

#3 1.6.3 Yêu cầu với đường dẫn kiểm tra sức khỏe

Đường dẫn kiểm tra phải trả lời nhanh, không tạo phiên, không ghi cơ sở dữ liệu và không tiết lộ thông tin hệ thống. Một trang hiển thị phiên bản PHP hoặc đường dẫn tuyệt đối sẽ biến cơ chế giám sát thành kênh cung cấp thông tin cho người tấn công.

#2 1.7 Duy trì phiên làm việc trong cụm

#3 1.7.1 Vấn đề

Ứng dụng web là ứng dụng có trạng thái: sau khi đăng nhập, máy chủ giữ thông tin người dùng và gắn nó với một định danh phiên gửi trong cookie. Giáo trình trình bày các yêu cầu với định danh phiên tại mục bảo mật phiên làm việc, trong đó có việc khởi tạo lại định danh sau khi người dùng đổi quyền [1].

Trong cụm máy chủ web, vấn đề phát sinh vì phiên được tạo ra trên một node cụ thể. Nếu dữ liệu phiên chỉ nằm trong bộ nhớ hoặc trên đĩa của node đó, yêu cầu tiếp theo của cùng người dùng mà rơi vào node khác sẽ không tìm thấy phiên, và người dùng bị coi là chưa đăng nhập.

#3 1.7.2 Hai cách giải quyết

Cách thứ nhất là giữ người dùng luôn quay về cùng một node, dùng ip hash, dùng cookie của bộ cân bằng tải, hoặc dùng phiên gắn với kết nối. Cách này không cần thay đổi ứng dụng nhưng làm giảm chất lượng cân bằng tải, và khi node bị giữ phiên ngừng hoạt động thì toàn bộ người dùng của node đó mất phiên cùng một lúc.

Cách thứ hai là đưa dữ liệu phiên ra ngoài node, vào một kho lưu trữ dùng chung như Redis hoặc vào chính cơ sở dữ liệu. Mọi node đọc được mọi phiên, nên bộ cân bằng tải tự do chọn node theo thuật toán nào cũng được, và một node chết không làm mất phiên.

Đề tài chọn cách thứ hai và dùng cách thứ nhất làm đối chứng trong phép đo ở Chương 3, so sánh ở {fig:phien-chung}.

[[FIG:phien-chung|Phiên để trên từng node so với phiên để ở kho dùng chung]]

#3 1.7.3 Hệ quả với bảo mật phiên

Khi phiên nằm ở kho dùng chung, một số biện pháp bảo vệ vẫn phải đặt đúng chỗ. Cookie phiên phải có cờ Secure để chỉ đi qua HTTPS, cờ HttpOnly để mã lệnh chèn vào trình duyệt không đọc được, và thuộc tính SameSite để chặn một phần tấn công giả mạo yêu cầu khác nguồn. Việc khởi tạo lại định danh phiên ngay sau khi đăng nhập thành công vẫn phải thực hiện, vì kho lưu trữ dùng chung không tự chống được tấn công cố định phiên.

Kho lưu phiên trở thành một điểm chứa dữ liệu nhạy cảm và phải nằm trong mạng nội bộ, không có cổng công bố ra ngoài. Ai lấy được định danh phiên hợp lệ thì còn nguy hiểm hơn trong mô hình một máy chủ, vì người đó có thể dùng phiên trên bất kỳ node nào.

#2 1.8 Các công cụ cân bằng tải phổ biến

[[TAB:cong-cu|So sánh các công cụ cân bằng tải thường dùng]]
tbl:
| Công cụ | Tầng làm việc | Kiểm tra sức khỏe chủ động | Duy trì phiên | Ghi chú |
| LVS | 4 | Có, qua daemon ngoài | Không | Chuyển tiếp gói tin ở tầng mạng, hiệu năng rất cao |
| HAProxy | 4 và 7 | Có, option httpchk | Có, qua cookie | Trang thống kê trực tiếp hiển thị trạng thái node |
| Nginx mã nguồn mở | 4 và 7 | Không, chỉ thụ động | Có, ip hash và sticky của bản thương mại | Phổ biến, tài liệu nhiều, tích hợp làm máy chủ web |
| keepalived | 3 và 4 | Có, qua vrrp_script | Không | Thường ghép với LVS hoặc HAProxy để chống điểm hỏng đơn lẻ |
| Cân bằng tải của nhà cung cấp đám mây | 4 và 7 | Có | Có | Cấu hình theo giao diện, chi phí theo lưu lượng |
#tc

Đề tài chọn nginx cho cả vai trò bộ cân bằng tải và máy chủ web ở mỗi node. Lý do là nginx phổ biến trong các hệ thống web, tài liệu cấu hình ngắn gọn và dễ trình bày trong báo cáo, và việc dùng cùng một phần mềm ở hai vai trò giúp tách rõ khác biệt giữa cấu hình định tuyến và cấu hình phục vụ nội dung. Điểm yếu của lựa chọn này là nginx mã nguồn mở không có kiểm tra sức khỏe chủ động, nên thời gian phát hiện node hỏng phụ thuộc vào yêu cầu của người dùng thật; đây là hạn chế được đo và bàn luận ở Chương 3.

#2 1.9 Kết chương

Chương này trình bày cân bằng tải máy chủ web như một biện pháp bảo đảm tính sẵn dùng trong mô hình an toàn ứng dụng web, xác định vị trí của bộ cân bằng tải trong kiến trúc nhiều lớp, phân biệt cân bằng tải ở tầng 4 và tầng 7, liệt kê các thành phần của một cụm máy chủ web gồm pool thành viên, cơ chế kiểm tra sức khỏe, kho phiên dùng chung và cơ sở dữ liệu dùng chung, so sánh các thuật toán phân phối yêu cầu và các công cụ thường dùng.

Bốn vấn đề được rút ra để làm mục tiêu cho phần triển khai. Thứ nhất, bộ cân bằng tải phải phân phối được yêu cầu đều trên các node theo một thuật toán chọn được. Thứ hai, khi một node ngừng trả lời, cụm phải tiếp tục phục vụ mà không cần can thiệp thủ công. Thứ ba, phiên làm việc của người dùng phải sống được qua sự cố của node, nên dữ liệu phiên không được nằm trong node. Thứ tư, node web không được phép tiếp nhận yêu cầu từ ngoài và không được tiết lộ thông tin qua đường kiểm tra sức khỏe. Chương 2 triển khai cụm đáp ứng bốn yêu cầu này, Chương 3 đo lại bằng số liệu.
