# Vi tri cua Keepalived trong de tai

De bai yeu cau 2 den 3 may chu web phuc vu cung mot website va mot thanh phan
can bang tai, dong thoi kiem tra kha nang dap ung khi mot server gap su co. Lab
nay lam du yeu cau do.

Cau hoi con lai: chinh load balancer cung la mot diem hong don le. lb01 chet thi
ca cum mat duong vao. Keepalived dung VRRP cho hai load balancer tranh nhau mot
dia chi ao (VIP), node nao song sot hon nam VIP va chuyen no trong vong vai giay.

Cau hinh o `keepalived.conf.example`: hai container cung `vrrp_instance`, cung
`virtual_router_id`, khac nhau o `priority`. Can them
`cap_add: [NET_ADMIN, NET_BROADCAST]` cho container.

Mac dinh VRRP gui bao dieu khien theo multicast 224.0.0.18, nhung Docker
Desktop khong bao dam chuyen duoc multicast giua hai container, nen file cau hinh
huong dan dung `unicast_src_ip` va `unicast_peer` (dan dang nam trong file, bo
dau `!` khi dung). Vi khong kiem chung duoc tren may ao hoa nay, phan nay de o
huong phat trien trong bao cao chu khong bat lam ket qua nghiem thu.
