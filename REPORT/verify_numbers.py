#!/usr/bin/env python3
"""Doi chieu moi con so trong bao cao voi file ket qua trong results/.

Chay that cong khi: bao cao ke mot so khong co trong results; mot so cua luong
chay cu con sot lai trong bao cao; va mot o bang lech khoi gia tri ma
analyze_bench.py da tinh tu chinh log tho.

Ba chuong duoc doi chieu bang ba cach khac nhau:
  - Bang phan phoi tuan tu, failover, phien, an toan: doc thang log tho.
  - Bang thong qua, do lech, bac thang chi phi, suy giam: doi chieu voi
    bench_summary.json do analyze_bench.py sinh ra, tung o mot.
  - Phat so cua luong chay cu: quet moi chu so trong moi bang.

Dung:  python verify_numbers.py
"""
import glob
import io
import json
import os
import re
import sys
from collections import Counter

# Windows dinh nghia stdout la cp1252; in ra mot chuoi co dau giua chung luc
# bao cao loi se nanh UnicodeEncodeError va an mat chinh loi can doc.
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace', line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(os.path.dirname(HERE), 'results')
SOURCES = ('mo-dau.md', 'chuong1.md', 'chuong2.md', 'chuong3.md',
           'ket-luan.md')
IP2NODE = {'172.20.0.11': 'web01', '172.20.0.12': 'web02', '172.20.0.13': 'web03'}
ALGS = ('round_robin', 'least_conn', 'ip_hash')
EPS = ('lb-only', 'healthz', 'dbping.php')


def newest(pattern):
    """Luong chay duoc doi chieu la luong MOI NHAT, khong phai mot luong duy
    nhat: moi lan lay lai bang an toan hay do lai phien deu sinh file moi, va
    that bai muon phat hien o day hon la dung lai so lieu cu."""
    hits = sorted(glob.glob(os.path.join(RESULTS, pattern)),
                  key=os.path.getmtime)
    if not hits:
        sys.exit('khong co file nao khop: ' + pattern)
    if len(hits) > 1:
        print('  luu y: "%s" khop %d file, dung %s'
              % (pattern, len(hits), os.path.basename(hits[-1])))
    return hits[-1]


def read(path):
    return open(path, encoding='utf-8', errors='ignore').read().replace('\r\n', '\n')


def fold(text):
    """Bo dau cua chu Viet. summarize.awk in nhan khong dau de cong so don
    gian, nhung cac luong chay cu van con nhan co dau; doi chieu tren ban
    khong dau gi cho ca hai kieu doc duoc."""
    import unicodedata
    out = []
    for ch in text:
        if ord(ch) < 128:
            out.append(ch)
        elif ch in ('đ', 'Đ'):
            out.append(ch.lower())
        else:
            base = ''.join(c for c in unicodedata.normalize('NFD', ch)
                           if not unicodedata.combining(c))
            out.append(base or ch)
    return ''.join(out)


def vn(x, nd=1):
    return ('%%.%df' % nd) % x


def vnc(x, nd=1):
    return vn(x, nd).replace('.', ',')


def vns(x, nd=1):
    # Cot chenh lech trong bao cao luon in dau, ke ca khi duong, de nguoi doc
    # khong phai doan xem 0,5% la tang hay giam.
    return (('+' if x >= 0 else '') + vn(x, nd)).replace('.', ',')


def collect():
    facts = {}

    for alg in ALGS:
        t = read(newest('distribute/summary-%s-*.txt' % alg))
        d = {v: int(k) for k, v in re.findall(r'^\s*(\d+) (web0\d)$', t, re.M)}
        seq = [d.get('web0%d' % i, 0) for i in (1, 2, 3)]
        # Script chi in ra node co request, nen ip_hash chi mot dong la dung.
        # Thu doat that la tong phai bang so request da gui.
        sent = int(re.search(r'requests=(\d+)', t).group(1))
        if sum(seq) != sent:
            sys.exit('summary-%s: tong %d khac %d request da gui'
                     % (alg, sum(seq), sent))
        facts['seq-' + alg] = seq
        facts['seq-missing-' + alg] = int(
            re.search(r'missing_node_header=(\d+)', t).group(1))

    t = fold(read(newest('failover/summary-load-web02-*.txt')))
    facts['fo-samples'] = int(re.search(r'Tong so mau\s*:\s*(\d+)', t).group(1))
    facts['fo-errors'] = int(re.search(r'HTTP != 200\s*:\s*(\d+)', t).group(1))
    facts['fo-slow'] = int(re.search(r'vuot 1 s[^:]*:\s*(\d+)', t).group(1))
    facts['fo-max'] = round(float(re.search(r'lon nhat\s*:\s*([\d.]+)', t).group(1)) * 1000, 1)
    facts['fo-avg'] = round(float(re.search(r'trung binh\s*:\s*([\d.]+)', t).group(1)) * 1000, 1)
    dist = {k: int(v) for k, v in re.findall(r'^\s+(web0\d)\s+(\d+)$', t, re.M)}
    facts['fo-dist'] = [dist.get('web0%d' % i, 0) for i in (1, 2, 3)]

    log = newest('failover/retries-web02-*.log')
    log_lines = read(log).splitlines()
    acc = [l for l in log_lines if 'upstream=' in l]
    facts['fo-retry-lines'] = len([l for l in acc
                                   if re.search(r'upstream=[^ ]*172\.20\.0\.12:80,', l)])
    # So dong va dau thoi gian cua VONG DO DUU GIU o results/failover. Chup
    # lai anh 08 tuc la co vong moi; hai gia tri nay bat bao cao phai theo.
    facts['fo-log-lines'] = len(log_lines)
    facts['fo-log-acc'] = len(acc)
    facts['fo-log-ts'] = (re.search(r'\[(\d+/\w+/\d+:\d+:\d+:\d+)',
                                    acc[0]).group(1) if acc else '')
    facts['fo-slow-retries'] = len([l for l in acc
                                    if re.search(r'upstream_time=2\.', l)])

    for mode in ('redis', 'file'):
        t = read(newest('session/session-%s-*.txt' % mode))
        facts['sess-' + mode] = (int(re.search(r'200_giu_duoc_phien=(\d+)', t).group(1)),
                                 int(re.search(r'302_mat_phien=(\d+)', t).group(1)))
        algo = re.search(r'load_balancer_algorithm=(\S+)', t)
        facts['sess-algo-' + mode] = algo.group(1) if algo else ''
        # Dem node o giai doan GOI LAI (sau khi tat node), khong tinh dong
        # dang nhap: bao cao neu noi "chia 7/3" thi phai doc duoc 7/3.
        tail = t.split('Buoc 3')[-1]
        nodes = Counter(re.findall(r'node=(web0\d)', tail))
        facts['sess-nodes-' + mode] = [nodes.get('web0%d' % i, 0)
                                       for i in (2, 3)]

    t = read(newest('security/seccheck-*.txt'))
    m = re.search(r'PASS=(\d+)\s+FAIL=(\d+)\s+SKIP=(\d+)\s+GHI_NHAN=(\d+)', t)
    facts['sec'] = tuple(int(x) for x in m.groups())
    facts['sec-rows'] = len(re.findall(r'\[(PASS|FAIL|SKIP|GHI_NHAN)\]', t))
    facts['sec-429'] = int(re.search(r'(\d+)/200 (?:request )?nhan 429', t).group(1))

    npath = newest('bench/degrade-nodes-[0-9]*.csv')
    for r in csv_rows(npath):
        facts['served-' + r['state']] = {
            k: int(r[k]) for k in ('web01', 'web02', 'web03', 'retries', 'lines')}
    return facts


def csv_rows(path):
    import csv
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def table(report, slug):
    """Tra ve danh sach dong cua bang co slug cho truoc, moi dong la danh sach
    o da cat bo rong hai dau."""
    m = re.search(r'\[\[TAB:%s\|[^\]]*\]\]\ntbl:\n(.*?)\n#tc' % re.escape(slug),
                  report, re.S)
    if not m:
        return None
    out = []
    for line in m.group(1).splitlines():
        if line.strip().startswith('|'):
            out.append([c.strip() for c in line.strip().strip('|').split('|')])
    return out


def main():
    texts = {name: read(os.path.join(HERE, name)) for name in SOURCES}
    report = '\n'.join(texts.values())
    f = collect()
    spath = os.path.join(HERE, 'bench_summary.json')
    if not os.path.exists(spath):
        sys.exit('thieu bench_summary.json: chay analyze_bench.py truoc')
    S = json.load(open(spath, encoding='utf-8'))
    problems = []

    def expect(name, *renderings, where='report'):
        hay = texts.get(where, report) if where != 'report' else report
        for r in renderings:
            if r in hay:
                return
        problems.append('%s: gia tri %r khong xuat hien trong %s'
                        % (name, renderings[0],
                           where if where != 'report' else 'toan bao cao'))

    # ---- bang phan phoi tuan tu: doc thang log tho ----
    for alg in ALGS:
        expect('seq-' + alg, ' | '.join(str(x) for x in f['seq-' + alg]))

    # ---- bang thong qua ma tran: tung o so voi bench_summary ----
    mt = table(report, 'thong-qua')
    if not mt:
        problems.append('khong tim thay bang thong-qua')
    else:
        seen = set()
        for row in mt[1:]:
            ep, ka, alg, rps, cv, p50, p99 = row[:7]
            ep_slug = {'`/lb-only`': 'lb-only', '`/healthz`': 'healthz',
                       '`/dbping.php`': 'dbping.php'}[ep]
            ka_slug = {'không giữ kết nối': 'cold', 'keep-alive': 'keepalive'}[ka]
            alg_slug = {'round robin': 'round_robin', 'least_conn': 'least_conn',
                        'ip_hash': 'ip_hash'}[alg]
            c = S['matrix'][alg_slug][ep_slug][ka_slug]
            mean, ci = rps.split(' ± ')
            want = (vnc(c['mean']), vnc(c['ci']), vnc(c['cv']),
                    str(c['p50']) + ' ms', str(c['p99']) + ' ms')
            got = (mean, ci, cv.replace('%', ''), p50, p99)
            if got != want:
                problems.append('bang thong-qua %s/%s/%s: bao cao %s, do luong %s'
                                % (ep_slug, ka_slug, alg_slug, got, want))
            seen.add((ep_slug, ka_slug, alg_slug))
        if len(seen) != 18:
            problems.append('bang thong-qua co %d o, khong phai 18' % len(seen))

    # ---- bang do lech phan phoi ----
    sk = table(report, 'phoi-dong-thoi')
    if not sk:
        problems.append('khong tim thay bang phoi-dong-thoi')
    else:
        for row in sk[1:]:
            alg = {'round robin': 'round_robin', 'least_conn': 'least_conn',
                   'ip_hash': 'ip_hash'}[row[0]]
            d = S['skew'][alg]
            want = tuple('%s ± %s' % (vnc(d['nodes'][n]['mean']),
                                      vnc(d['nodes'][n]['ci']))
                         for n in ('web01', 'web02', 'web03'))
            want += ('%s ± %s' % (vnc(d['skew']['mean']), vnc(d['skew']['ci'])),
                     str(d['retries']))
            got = tuple(row[1:6])
            if got != want:
                problems.append('bang phoi-dong-thoi %s: bao cao %s, do luong %s'
                                % (alg, got, want))
            for cell in want[:4]:
                expect('skew-' + cell, cell)

    # ---- bac thang chi phi ----
    lad = table(report, 'thang-chi-phi')
    if not lad:
        problems.append('khong tim thay bang thang-chi-phi')
    else:
        for row in lad[1:]:
            ka = 'cold' if row[0] == 'không giữ kết nối' else 'keepalive'
            ep = {0: 'lb-only', 1: 'healthz', 2: 'dbping.php'}[(int(row[1].startswith('thêm'))
                                                               + (int('truy vấn' in row[1])))]
            c = S['matrix']['least_conn'][ep][ka]
            if row[2] != vnc(c['mean']):
                problems.append('bac thang %s/%s: bao cao %s, do luong %s'
                                % (ep, ka, row[2], vnc(c['mean'])))

    # ---- bang Welch ----
    wt = table(report, 'welch')
    if not wt:
        problems.append('khong tim thay bang welch')
    else:
        for row in wt[1:]:
            ep = {'`/lb-only`': 'lb-only', '`/healthz`': 'healthz',
                  '`/dbping.php`': 'dbping.php'}[row[0]]
            ka = 'cold' if row[1] == 'không giữ kết nối' else 'keepalive'
            alg = row[2]
            t = S['tests']['%s|%s|%s' % (ep, ka, alg)]
            if row[3] != vns(t['diff_pct']) + '%':
                problems.append('welch %s/%s/%s: bao cao %s, do luong %s'
                                % (ep, ka, alg, row[3], vns(t['diff_pct']) + '%'))
            if row[4] != vnc(t['p'], 4):
                problems.append('welch %s/%s/%s: p bao cao %s, do luong %s'
                                % (ep, ka, alg, row[4], vnc(t['p'], 4)))

    # ---- suy giam khi mat node ----
    dg = table(report, 'hieu-nang')
    if not dg:
        problems.append('khong tim thay bang hieu-nang')
    else:
        for row in dg[1:]:
            state = '3-node' if row[0] == 'ba node' else '2-node'
            ka = 'cold' if row[1] == 'không giữ kết nối' else 'keepalive'
            c = S['degrade']['%s|%s' % (state, ka)]
            want = ('%s ± %s' % (vnc(c['mean']), vnc(c['ci'])), vnc(c['cv']) + '%',
                    str(c['p50']) + ' ms', str(c['p95']) + ' ms',
                    str(c['p100']) + ' ms')
            if tuple(row[2:7]) != want:
                problems.append('bang hieu-nang %s/%s: bao cao %s, do luong %s'
                                % (state, ka, tuple(row[2:7]), want))
    for ka in ('cold', 'keepalive'):
        L = S['degrade'].get('loss|%s' % ka)
        if not L:
            continue
        magnitude = vnc(abs(L['pct'])) + '%'
        expect('degrade-loss-' + ka, magnitude, vns(L['pct']) + '%')
        expect('degrade-p-' + ka, 'p = ' + vnc(L['p'], 4))
    for k in ('3-node', '2-node'):
        s = S['degrade']['served'][k]
        expect('served-' + k,
               'phân phối là %d / %d / %d' % (s['web01'], s['web02'], s['web03']),
               '%d / %d / %d' % (s['web01'], s['web02'], s['web03']),
               'web01=%d web02=%d web03=%d' % (s['web01'], s['web02'], s['web03']))

    # ---- failover, phien, an toan ----
    # Bang 3.2 tong hop tu nhieu vong lap nen doi chieu voi bench_summary,
    # khong doi chieu voi rieng mot file summary nua.
    F = S['failover']

    def fci(key):
        d = F[key]
        return '%s ± %s' % (vnc(d['mean']), vnc(d['ci']))

    expect('fo-samples', '| Số mẫu trong vòng đo | %s |' % fci('samples'))
    expect('fo-errors', '| Số mẫu có mã HTTP khác 200 | %s |' % fci('errors'))
    expect('fo-slow', '| Số mẫu phải chờ quá 1 giây | %s |' % fci('slow'))
    expect('fo-max', '| Thời gian đáp ứng lớn nhất | %s ms |' % fci('max_ms'))
    expect('fo-avg', '| Thời gian đáp ứng trung bình | %s ms |' % fci('avg_ms'))
    expect('fo-dist', 'web01: %s, web02: %s, web03: %s'
           % (fci('node1'), fci('node2'), fci('node3')))
    if F['errors']['hi_val'] != 0:
        problems.append('co vong failover khong tra ve 0 mau loi')
    if F['n'] < 10:
        problems.append('failover moi co %d vong lap trong khi bao cao noi 12'
                        % F['n'])
    expect('fo-log-lines', '%d dòng log ghi' % f['fo-log-lines'],
           'lưu %d dòng log' % f['fo-log-lines'])
    expect('fo-log-acc', '%d dòng access log' % f['fo-log-acc'],
           '%d dòng nhiều hơn' % f['fo-log-acc'])
    expect('fo-log-err', '%d dòng do nginx'
           % (f['fo-log-lines'] - f['fo-log-acc']))
    if f['fo-log-ts']:
        expect('fo-log-ts', f['fo-log-ts'])
    # So duoc thu lai nhieu hon so mau cham: mot request bi tu choi bang RST
    # thi chuyen node trong 1 ms, khong vuot nguong 1 s. Tam = so dong retry
    # co upstream_time bat dau bang 2.
    if f['fo-slow-retries'] != f['fo-slow']:
        problems.append('so dong retry cho hai giay (%d) khac so mau cham (%d)'
                        % (f['fo-slow-retries'], f['fo-slow']))
    if f['fo-retry-lines'] <= f['fo-slow']:
        problems.append('bao cao noi so dong retry (%d) nhieu hon so mau cham '
                        '(%d), duong nhu vong do duu giu da thay'
                        % (f['fo-retry-lines'], f['fo-slow']))

    if f['sess-redis'] != (10, 0):
        problems.append('session redis bat thuong: %s' % (f['sess-redis'],))
    if f['sess-file'] != (0, 10):
        problems.append('session file bat thuong: %s' % (f['sess-file'],))
    if f['sess-algo-file'] != 'ip_hash;':
        problems.append('phuong an file chay voi thuat toan %r, bao cao lai noi '
                        'la ip_hash' % f['sess-algo-file'])
    if f['sess-algo-redis'] != 'least_conn;':
        problems.append('phuong an redis chay voi thuat toan %r'
                        % f['sess-algo-redis'])
    r2, r3 = f['sess-nodes-redis']
    expect('sess-nodes-redis', 'theo tỉ lệ %d/%d' % (r2, r3))
    f2, f3 = f['sess-nodes-file']
    if f2 + f3 != 10 or min(f2, f3) != 0:
        problems.append('phuong an file khong dinh kem vung mot node: '
                        'web02=%d web03=%d' % (f2, f3))

    n_dat = len(re.findall(r'\| Đạt \|', report))
    n_ghi = len(re.findall(r'\| Ghi nhận \|', report))
    if n_dat + n_ghi != f['sec'][0] + f['sec'][3]:
        problems.append('bang an toan co %d dong, results co %d hang muc dat/ghi nhan'
                        % (n_dat + n_ghi, f['sec'][0] + f['sec'][3]))
    if f['sec'][1] or f['sec'][2]:
        problems.append('con kiem tra FAIL/SKIP trong results: %s' % (f['sec'],))
    if n_ghi:
        problems.append('bao cao con %d dong "Ghi nhận" trong khi results khong'
                        ' con hang muc nao thu loai nay' % n_ghi)
    if f['sec-rows'] != n_dat + n_ghi:
        problems.append('so dong kiem tra trong results = %d, bao cao = %d'
                        % (f['sec-rows'], n_dat + n_ghi))
    expect('sec-429', '%d trên 200 request nhận 429' % f['sec-429'],
           'chặn %d trong 200 request' % f['sec-429'])

    # ---- so cua luong chay cu con sot lai ----
    # Bat ky so nao xuat hien trong bang cung phai la gia tri ma do luong sinh
    # ra. Danh sach duoc lay tu bench_summary, khong phai go tay.
    allowed = set()
    for alg in ALGS:
        allowed |= {str(x) for x in f['seq-' + alg]}
        allowed |= {str(x) for x in f['fo-dist']}
    for k in ('3-node', '2-node'):
        allowed |= {str(x) for x in S['degrade']['served'][k].values()}
    for per_alg in S['matrix'].values():
        for per_ep in per_alg.values():
            for cell in per_ep.values():
                allowed |= {str(cell[k]) for k in ('p50', 'p95', 'p99', 'p100')
                            if cell.get(k) is not None}
    for cell in S['degrade'].values():
        if isinstance(cell, dict) and 'p100' in cell:
            allowed |= {str(cell[k]) for k in ('p50', 'p95', 'p99', 'p100')
                        if cell.get(k) is not None}
    allowed |= {str(f[k]) for k in ('fo-samples', 'fo-errors', 'fo-slow')}
    allowed |= {'600', '300', '3000', '1500', '20', '30', '70', '10', '50',
                '126000', '12000', '360', '18', '19', '17'}
    stale = []
    for slug in ('thong-qua', 'phoi-dong-thoi', 'hieu-nang', 'bac-thang',
                 'thang-chi-phi', 'welch', 'phoi-tuan-tu', 'failover'):
        for row in (table(report, slug) or [])[1:]:
            for cell in row:
                head = cell.split()[0] if cell.split() else ''
                if re.fullmatch(r'\d{3,4}', head) and head not in allowed:
                    stale.append('%s:%s' % (slug, head))
    if stale:
        problems.append('gia tri khong co trong do luong: %s' % sorted(set(stale)))

    # ---- ket luan tong hop lai so lieu ----
    kl = texts['ket-luan.md']
    for alg in ('round_robin', 'least_conn'):
        d = S['skew'][alg]['nodes']
        expect('kl-skew-' + alg,
               ' / '.join(vnc(d[n]['mean']) for n in ('web01', 'web02', 'web03')),
               where='ket-luan.md')
    expect('kl-fo-samples', '12 lần độc lập', '8,8 ± 0,4',
           where='ket-luan.md')
    expect('kl-sec-wording', 'bảng kiểm cấu hình và thuộc tính an toàn',
           where='ket-luan.md')
    expect('kl-noscope', 'không đánh giá khả năng chống tấn công',
           where='ket-luan.md')

    print('so lieu doi chieu:')
    for k in sorted(f):
        print('  %-22s %s' % (k, f[k]))
    print()
    if problems:
        print('LOI (%d):' % len(problems))
        for x in problems:
            print('  ' + x)
        sys.exit(1)
    print('KHOP: moi con so trong bao cao deu doc lai duoc tu results/')


if __name__ == '__main__':
    main()
