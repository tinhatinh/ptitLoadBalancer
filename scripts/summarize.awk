#!/usr/bin/env awk -f
# Tong hop file CSV cua loadloop.sh (cot: unix_ms, http_code, node, time_total).
# Cho ra so lieu day vao Bang 3.2 trong bao cao.
BEGIN { FS = "," }
NR == 1 { next }
{
    n++
    ms[n]   = $1 + 0
    code[n] = $2
    node[n] = $3
    t[n]    = $4 + 0
    sum += t[n]
    if (t[n] > maxt) maxt = t[n]

    if (code[n] != "200") {
        err++
        if (first_err_idx == 0) first_err_idx = n
    } else if (first_err_idx && recovered_idx == 0) {
        recovered_idx = n
    }

    cnt[node[n]]++
}
END {
    printf "== KET QUA DO FAILOVER ==\n"
    printf "Tong so mau                  : %d\n", n
    printf "So mau co HTTP != 200        : %d\n", err + 0
    printf "Thoi gian dap ung trung binh : %.4f s\n", sum / (n ? n : 1)
    printf "Thoi gian dap ung lon nhat   : %.4f s\n", maxt + 0

    if (first_err_idx && recovered_idx) {
        printf "\n-- Khoang gian doan nhin thay tu phia nguoi dung --\n"
        printf "Mau loi dau tien           : #%d tai %d\n", first_err_idx, ms[first_err_idx]
        printf "Mau thanh cong dau sau loi : #%d tai %d\n", recovered_idx, ms[recovered_idx]
        printf "Thoi gian gian doan        : %d ms\n", ms[recovered_idx] - ms[first_err_idx]
    } else if (first_err_idx) {
        # Ky do ket thuc luc van con loi: khong co mau thanh cong nao sau
        # loi nen khong the tinh khoang gian do. De trong thi ms[0] rong,
        # hieu hai so se in ra mot con so vo nghia hang ngan ty ms.
        printf "\n-- Khoang gian doan --\n"
        printf "Mau loi dau tien           : #%d, ky do ket thuc truoc khi he thong phuc hoi\n", first_err_idx
        printf "Thoi gian gian doan        : khong do duoc (chua phuc hoi trong ky do)\n"
    } else {
        printf "\nNguoi dung khong nhan ma loi nao trong suot ky do.\n"
    }

    # Khi khong co loi, bang chung cua failover nam o phat gia thoi gian:
    # moi request ma nginx con thu goto node da chet phai chong day
    # proxy_connect_timeout.
    penalized = 0
    for (i = 1; i <= n; i++) if (t[i] > 1.0) penalized++
    printf "Mau phai chiu thoi gian cho vuot 1 s (nginx thu lai node da chet) : %d\n", penalized

    printf "\n-- Phan phoi node trong ky do --\n"
    for (k in cnt) printf "  %-10s %d\n", k, cnt[k]
}
