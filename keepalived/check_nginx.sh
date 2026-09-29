#!/bin/sh
# Suc khoe nginx cho keepalived. Chay trong container load balancer, duoc
# vrrp_script goi lai moi 2 giay. Ket qua 0 giu quyen MASTER, khong zero thi
# keepalived tru priority (weight -20) va ban dia chi ao cho node khac.
#
# kiem tra bang mot lan goi that, khong chi "pidof nginx": nginx con song
# ma loi cau hinh hoac full worker thi van khong phuc vu duoc.
curl -fsS -m 2 -o /dev/null http://127.0.0.1/healthz || exit 1
exit 0
