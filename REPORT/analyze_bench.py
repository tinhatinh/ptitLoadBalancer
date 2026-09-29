#!/usr/bin/env python3
"""Tong hop ba loai ket do thanh so lieu cho Chuong 3.

Ba view:
  matrix   thong qua cua ba thuat toan tren ba tang phan hoi, hai che do
           keep-alive, moi o 20 luong doc lap.
  skew     do lech phan phối node, cung 20 luong, dem tu access log.
  degrade  mot kich thuoc ba node va mot kich thuoc hai node.

Mot con so o thang laptop nay khong co y nghia: hai luong cua cung mot cau
hinh da lech nhau toi 34 phan tram. O day moi o tong hop thanh mean ± 95% CI
va thu Welch de xem khac biet co y nghia thong ke khong.

Lenh nay cung la nguon in ra cua cac anh chup bang so lieu, nen bang trong
bao cao va hinh trong bao cao cung mot tri so, khong the lech nhau.

Dung:  python analyze_bench.py [matrix|skew|degrade|all]
"""
import csv
import glob
import json
import math
import os
import statistics as st
import sys

from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(os.path.dirname(HERE), 'results')
BENCH = os.path.join(RESULTS, 'bench')
DIST = os.path.join(RESULTS, 'distribute')
CONC = 20                      # so ket noi song song da dung khi do
ALGS = ('round_robin', 'least_conn', 'ip_hash')
EPS = ('lb-only', 'healthz', 'dbping.php')
TIER = {'lb-only': 'rieng can bang tai',
        'healthz': '+ nginx va php-fpm tren node',
        'dbping.php': '+ mot truy van MariaDB'}


def newest(pattern):
    hits = sorted(glob.glob(os.path.join(pattern)), key=os.path.getmtime)
    if not hits:
        sys.exit('khong thay file: ' + pattern)
    return hits[-1]


def rows(path):
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def describe(values, n_expected=None):
    """mean, do lech chuan, khoang tin cay 95% theo Student va CV."""
    vals = [v for v in values if v is not None]
    n = len(vals)
    if not n:
        return None
    mean = st.mean(vals)
    sd = st.stdev(vals) if n > 1 else 0.0
    half = stats.t.ppf(0.975, n - 1) * sd / math.sqrt(n) if n > 1 and sd else 0.0
    warn = ''
    if n_expected and n != n_expected:
        warn = '  !! CHI CO %d/%d LUONG' % (n, n_expected)
    return dict(n=n, mean=round(mean, 1), sd=round(sd, 1),
                ci=round(half, 1), lo=round(mean - half, 1),
                hi=round(mean + half, 1),
                cv=round(100 * sd / mean, 1) if mean else None,
                warn=warn)


def med(values):
    vals = sorted(v for v in values if v is not None)
    return round(st.median(vals)) if vals else None


def welch(a, b):
    """Khac biet hai mau doc lap, khong gia phuong sai bang nhau."""
    va = [v for v in a if v is not None]
    vb = [v for v in b if v is not None]
    if len(va) < 2 or len(vb) < 2:
        return None
    t, p = stats.ttest_ind(va, vb, equal_var=False)
    pooled = math.sqrt((st.variance(va) + st.variance(vb)) / 2)
    return dict(t=round(float(t), 2), p=round(float(p), 4),
                d=round((st.mean(vb) - st.mean(va)) / pooled, 2) if pooled else None,
                diff_pct=round(100 * (st.mean(vb) - st.mean(va)) / st.mean(va), 1))


def dash(v):
    return '-' if v is None else v


def vc(x, nd=1):
    """So thap phan dau phay, giong het quy uoc trong bao cao.

    Anp chup bang so lieu va bang trong bao cao phai doc ra cung mot kieu;
    neu in dau cham thi nguoi doi chieu nghi hai so khac nhau.
    """
    return ('%%.%df' % nd) % x


def vcc(x, nd=1):
    return vc(x, nd).replace('.', ',')


def pct(x, nd=1):
    return '-' if x is None else vcc(x, nd) + '%'


def sgn(x, nd=1):
    """Chenh lech luon in dau, de anp chup khong doc ra '1,4%' khi thuc te la
    tang 1,4%."""
    return ('+' if x >= 0 else '') + vcc(x, nd)


def num(row, key):
    v = (row.get(key) or '').strip()
    return float(v) if v else None


def load_matrix():
    path = newest(os.path.join(BENCH, 'matrix-*.csv'))
    cells = {}
    hdr = rows(path)
    if hdr and 'p100' not in hdr[0]:
        # Luong chay truoc khi bench_matrix.sh do phan vi 100%. P100 khi do
        # in ra dau '-' vi khong do duoc, khong phai vi request nao cham.
        print('LUU Y: %s khong co cot p100, phep do nay chua ghi nhan phan vi'
              % os.path.basename(path))
    for r in hdr:
        if int(r['rep']) == 0:
            continue
        cells.setdefault((r['algorithm'], r['endpoint'], r['keepalive']),
                         []).append(r)
    return path, cells


def view_matrix(show):
    path, cells = load_matrix()
    summary, tests = {}, {}
    print('nguon: %s   (%d luong do, %d o)'
          % (os.path.basename(path), sum(len(v) for v in cells.values()),
             len(cells)))
    print('=' * 96)
    # In dung tam cot voi bang trong bao cao. Dong dai hon be ngang cua so
    # chup se tu gay thanh hai dong va pha huong dan chup.
    print('%-12s %-11s %-10s %10s %8s %6s %5s %5s'
          % ('thuat toan', 'endpoint', 'ket noi', 'req/s', '± CI',
             'CV %', 'P50', 'P99'))
    for key in sorted(cells, key=lambda k: (EPS.index(k[1]), k[2],
                                            ALGS.index(k[0]))):
        alg, ep, ka = key
        rs = cells[key]
        d = describe([num(r, 'rps') for r in rs], 20)
        if not d:
            continue
        p50, p95, p99, p100 = (med([num(r, f) for r in rs])
                               for f in ('p50', 'p95', 'p99', 'p100'))
        bad = sum(int(num(r, f) or 0) for r in rs for f in ('failed', 'non2xx'))
        summary.setdefault(alg, {}).setdefault(ep, {})[ka] = dict(
            d, p50=p50, p95=p95, p99=p99, p100=p100,
            lat_ms=round(CONC * 1000 / d['mean'], 1) if d['mean'] else None,
            bad=bad)
        if show:
            print('%-12s %-11s %-10s %10s %8s %6s %5s %5s%s'
                  % (alg, ep, ka, vcc(d['mean']), vcc(d['ci']), vcc(d['cv']),
                     dash(p50), dash(p99), d['warn']))

    if show:
        print()
        print('== SO SANH VOI round_robin cung endpoint va che do ket noi ==')
    for ep in EPS:
        for ka in ('cold', 'keepalive'):
            base = cells.get(('round_robin', ep, ka))
            if not base:
                continue
            for alg in ('least_conn', 'ip_hash'):
                other = cells.get((alg, ep, ka))
                if not other:
                    continue
                r = welch([num(x, 'rps') for x in base],
                          [num(x, 'rps') for x in other])
                if not r:
                    continue
                tests['%s|%s|%s' % (ep, ka, alg)] = r
                if show:
                    print('  %-11s %-10s round_robin -> %-11s %s%%  p=%s  %s'
                          % (ep, ka, alg, sgn(r['diff_pct']), vcc(r['p'], 4),
                             'co y nghia thong ke' if r['p'] < 0.05
                             else 'khong co y nghia thong ke'))

    ladder = {}
    if show:
        print()
        print('== BAC THANG CHI PHI PHAN HOI (least_conn) ==')
    for ka in ('cold', 'keepalive'):
        steps = []
        for ep in EPS:
            c = summary.get('least_conn', {}).get(ep, {}).get(ka)
            if c:
                steps.append((ep, c))
        if len(steps) != 3:
            continue
        base = dict(req_s=steps[0][1]['mean'], lat_ms=steps[0][1]['lat_ms'])
        prev_ep, prev = steps[0]
        for (ep, c) in steps[1:]:
            base[ep] = dict(req_s=c['mean'], lat_ms=c['lat_ms'],
                            them_ms=round(c['lat_ms'] - prev['lat_ms'], 1))
            prev_ep, prev = ep, c
        ladder[ka] = base
        if show:
            print('  che do %s:' % ka)
            print('    %-30s %10s req/s  %7s ms'
                  % (TIER[steps[0][0]], vcc(steps[0][1]['mean'], 0),
                     vcc(steps[0][1]['lat_ms'])))
            for (ep, c) in steps[1:]:
                before = summary['least_conn'][prev_step(ep)][ka]
                print('    %-30s %10s req/s  %7s ms  (%s ms)'
                      % (TIER[ep], vcc(c['mean'], 0), vcc(c['lat_ms']),
                         sgn(c['lat_ms'] - before['lat_ms'])))
    return summary, tests, ladder


def prev_step(ep):
    return {'healthz': 'lb-only', 'dbping.php': 'healthz'}[ep]


def load_skew():
    path = newest(os.path.join(DIST, 'skew-*.csv'))
    per = {}
    for r in rows(path):
        if int(r['rep']) == 0:
            continue
        per.setdefault(r['algorithm'], []).append(r)
    return path, per


def view_skew(show):
    path, per = load_skew()
    out = {}
    if show:
        print()
        print('== DO LECH PHAN PHOI, %d LUONG MOI THUT TOAN =='
              % max(len(v) for v in per.values()))
        print('%-12s %3s %-13s %-13s %-13s %-9s %-8s'
              % ('thuat toan', 'n', 'web01 (± CI)', 'web02 (± CI)',
                 'web03 (± CI)', 'lech max', 'thu lai'))
    for alg in ALGS:
        rs = per.get(alg, [])
        if not rs:
            continue
        cols = {}
        for i, node in enumerate(('web01', 'web02', 'web03'), start=3):
            d = describe([num(r, 'w%d' % (i - 2)) for r in rs], 20)
            cols[node] = d
        skew = describe([max(int(r['w1']), int(r['w2']), int(r['w3']))
                         - min(int(r['w1']), int(r['w2']), int(r['w3']))
                         for r in rs], 20)
        retr = sum(int(num(r, 'retries') or 0) for r in rs)
        unacc = sum(int(num(r, 'unaccounted') or 0) for r in rs)
        tot = sum(int(num(r, 'w1') or 0) + int(num(r, 'w2') or 0)
                  + int(num(r, 'w3') or 0) for r in rs)
        out[alg] = dict(nodes=cols, skew=skew, retries=retr,
                        unaccounted=unacc, total=tot, n=len(rs))
        if show:
            print('%-12s %3d %-13s %-13s %-13s %-9s %-8d%s'
                  % (alg, len(rs),
                     '%s ± %s' % (vcc(cols['web01']['mean']), vcc(cols['web01']['ci'])),
                     '%s ± %s' % (vcc(cols['web02']['mean']), vcc(cols['web02']['ci'])),
                     '%s ± %s' % (vcc(cols['web03']['mean']), vcc(cols['web03']['ci'])),
                     vcc(skew['mean']), retr,
                     cols['web01']['warn'] or skew['warn']))
    return out


def load_degrade():
    # degrade-nodes-*.csv cung khop pattern degrade-*.csv, nen loc theo ten:
    # do la bang chung node nao phuc vu, khong phai so lieu thong qua.
    path = newest(os.path.join(BENCH, 'degrade-[0-9]*.csv'))
    per = {}
    for r in rows(path):
        if int(r['rep']) == 0:
            continue
        per.setdefault((r['state'], r['keepalive']), []).append(r)
    return path, per


def view_degrade(show):
    path, per = load_degrade()
    out = {}
    if show:
        print()
        print('== SUY GIAM KHI MAT MOT NODE ==')
        print('%-8s %-10s %4s %10s %8s %7s %6s %6s %6s %6s %6s'
              % ('node', 'ket noi', 'n', 'req/s', '± CI', 'CV %',
                 'P50', 'P95', 'P99', 'P100', 'loi'))
    for (state, ka), rs in sorted(per.items()):
        d = describe([num(r, 'rps') for r in rs], 20)
        if not d:
            continue
        p = {f: med([num(r, f) for r in rs])
             for f in ('p50', 'p95', 'p99', 'p100')}
        bad = sum(int(num(r, f) or 0) for r in rs for f in ('failed', 'non2xx'))
        out['%s|%s' % (state, ka)] = dict(d, **p, bad=bad)
        if show:
            print('%-8s %-10s %4d %10s %8s %7s %6s %6s %6s %6s %6d%s'
                  % (state, ka, d['n'], vcc(d['mean']), vcc(d['ci']),
                     vcc(d['cv']), dash(p['p50']), dash(p['p95']),
                     dash(p['p99']), dash(p['p100']), bad, d['warn']))
    for ka in ('cold', 'keepalive'):
        a = out.get('3-node|%s' % ka)
        b = out.get('2-node|%s' % ka)
        if not (a and b):
            continue
        w = welch([num(r, 'rps') for r in per[('3-node', ka)]],
                  [num(r, 'rps') for r in per[('2-node', ka)]])
        out['loss|%s' % ka] = dict(pct=round(100 * (b['mean'] - a['mean'])
                                             / a['mean'], 1), **(w or {}))
        if show:
            print('  mat 1/3 node (%s): %s%% req/s, p=%s'
                  % (ka, sgn(out['loss|%s' % ka]['pct']),
                     vcc((w or {}).get('p') or 0, 4)))
    nhits = sorted(glob.glob(os.path.join(BENCH, 'degrade-nodes-*.csv')),
                   key=os.path.getmtime)
    if nhits:
        if show:
            print()
            print('  node phuc vu trong hai kich thuoc (bang chung cua phep do):')
        for r in rows(nhits[-1]):
            out.setdefault('served', {})[r['state']] = {
                'web01': int(r['web01']), 'web02': int(r['web02']),
                'web03': int(r['web03']), 'retries': int(r['retries']),
                'lines': int(r['lines'])}
            if show:
                print('    %-8s web01=%s web02=%s web03=%s  thu lai=%s  dong log=%s'
                      % (r['state'], r['web01'], r['web02'], r['web03'],
                         r['retries'], r['lines']))
    return out


def load_failover():
    path = newest(os.path.join(RESULTS, 'failover', 'repeat-[0-9]*.csv'))
    return path, rows(path)


def view_failover(show):
    """Failover do lap lai: so mau cham co that su on dinh khi chay lai?"""
    path, all_rows = load_failover()
    rs = [r for r in all_rows if r['samples']]
    # Mot vong bi loai la bang 3.2 thua mot dong ma khong ai biet. Ghi ro si
    # so bi loai va dem so luong, de verify_numbers.bat duoc.
    dropped = len(all_rows) - len(rs)
    out = {'n': len(rs), 'dropped': dropped, 'source': os.path.basename(path)}
    if show:
        print()
        print('== FAILOVER LAP LAI, %d vong ==   (%s)' % (len(rs), out['source']))
        if dropped:
            print('  !! %d DONG THIEU DU LIEU DA BI LOAI (tong %d dong trong file)'
                  % (dropped, len(all_rows)))
        print('%-12s %4s %10s %8s %8s %10s' % ('chi tieu', 'n', 'TB', '± CI',
                                               'CV', 'min..max'))
    # retry_lines lo ra khoi tong hop: 9 vong dau chay bang failover.sh ban
    # chua gioi han theo moc dong log nen cot nay cong gộp ca nhung vong
    # truoc do. Chi so lieu tu vong do sach (muc 3.3.2) duoc dung.
    for key, label in (('samples', 'Số mẫu'), ('errors', 'Mẫu lỗi HTTP'),
                       ('slow', 'Mẫu chờ quá 1 s'), ('avg_ms', 'TB ms/mẫu'),
                       ('max_ms', 'Chậm nhất ms')):
        d = describe([float(r[key]) for r in rs if r[key]], len(rs))
        if not d:
            continue
        vals = [float(r[key]) for r in rs if r[key]]
        out[key] = dict(d, lo_val=min(vals), hi_val=max(vals))
        if show:
            print('%-12s %4d %10s %8s %8s %6s..%s'
                  % (label, d['n'], vcc(d['mean']), vcc(d['ci']),
                     pct(d['cv']), vcc(min(vals), 0),
                     vcc(max(vals), 0)))
    for node in ('w1', 'w2', 'w3'):
        vals = [float(r[node]) for r in rs if r[node]]
        d = describe(vals, len(rs))
        out['node' + node[-1]] = d
        if show and d:
            print('%-12s %4d %10s %8s %8s %6s..%s'
                  % ('web0' + node[-1], d['n'], vcc(d['mean']), vcc(d['ci']),
                     pct(d['cv']), vcc(min(vals), 0),
                     vcc(max(vals), 0)))
    if show:
        print('  chi tiet tung vong: %s' % path)
    return out


def main():
    what = (sys.argv[1] if len(sys.argv) > 1 else 'all').lower()
    show = what != 'json'
    agg_path = os.path.join(HERE, 'bench_summary.json')
    data = {}
    if os.path.exists(agg_path):
        # Doc lai file cu de giu nguyen cac phan khong chay lan nay. truoc day
        # file chi bi ghi khi goi 'all', nen `analyze_bench.py skew` in ra so
        # moi trong khi bench_summary.json van la so cu, va make_charts.py ve
        # bieu do tu so cu do con bang trong bao cao doc so moi.
        try:
            with open(agg_path, encoding='utf-8') as f:
                data.update(json.load(f))
        except (ValueError, OSError) as exc:
            print('bench_summary.json doc khong duoc (%s), viet lai tu dau' % exc)
    if what in ('all', 'matrix', 'json'):
        m, t, l = view_matrix(show)
        data['matrix'] = m
        data['tests'] = t
        data['ladder'] = l
    if what in ('all', 'skew', 'json'):
        data['skew'] = view_skew(show)
    if what in ('all', 'degrade', 'json'):
        data['degrade'] = view_degrade(show)
    if what in ('all', 'failover', 'json'):
        data['failover'] = view_failover(show)
    json.dump(data, open(agg_path, 'w', encoding='utf-8'), indent=1,
              ensure_ascii=False)
    if show:
        print('\nda cap nhat bench_summary.json: %s' % ', '.join(sorted(data)))


if __name__ == '__main__':
    main()
