#!/usr/bin/env python3
"""Ve do thi cho Chuong 3, doc truc tiep tu file ket qua trong results/.

Khong nhap tay con so nao: bieu do sai thi do lieu sai se lo ra ngay.

Dung:  python make_charts.py
"""
import csv
import glob
import os
import re
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RESULTS = os.path.join(ROOT, 'results')
FIGDIR = os.path.join(HERE, 'figures')
os.makedirs(FIGDIR, exist_ok=True)

plt.rcParams.update({
    'font.family': 'DejaVu Sans',
    'font.size': 10,
    'axes.grid': True,
    'axes.grid.axis': 'y',
    'grid.color': '#DDDDDD',
    'axes.edgecolor': '#666666',
    'figure.dpi': 150,
})

COLOR = {'web01': '#2F6FA8', 'web02': '#3E8E5A', 'web03': '#C08A2E',
         'none': '#B03030'}
ALGOS = ('round_robin', 'least_conn', 'ip_hash')


def newest(pattern):
    files = sorted(glob.glob(os.path.join(RESULTS, pattern)))
    if not files:
        sys.exit('khong thay file: ' + pattern)
    return files[-1]


def chart_failover():
    path = newest('failover/load-*.csv')
    rows = list(csv.DictReader(open(path, encoding='utf-8')))
    if not rows:
        sys.exit('file failover rong: ' + path)

    t0 = int(rows[0]['unix_ms'])
    sec = [(int(r['unix_ms']) - t0) / 1000.0 for r in rows]
    ms = [float(r['time_total']) * 1000 for r in rows]
    node = [r['node'] for r in rows]
    code = [r['http_code'] for r in rows]

    slow = [s for s, m in zip(sec, ms) if m > 1000]
    stop_at = min(slow) - 1 if slow else None

    fig, ax = plt.subplots(figsize=(8.6, 3.6))
    for n in ('web01', 'web02', 'web03', 'none'):
        xs = [s for s, m, k in zip(sec, ms, node) if k == n]
        ys = [m for m, k in zip(ms, node) if k == n]
        if xs:
            ax.scatter(xs, ys, s=14, label=n, color=COLOR[n], alpha=.85)
    bad = [i for i, c in enumerate(code) if c != '200']
    if bad:
        ax.scatter([sec[i] for i in bad], [ms[i] for i in bad], s=46,
                   facecolors='none', edgecolors='#B03030', linewidths=1.4,
                   label='HTTP != 200')
    if stop_at is not None:
        ax.axvline(stop_at, color='#B03030', linestyle='--', linewidth=1.2)
        ax.annotate('tắt web02', xy=(stop_at, 900),
                    xytext=(stop_at + 1.5, 1150),
                    color='#B03030', fontsize=9)
        # Diem bat lai node lay tu chinh du lieu: mau web02 som nhat xuat hien
        # SAU mau cham cuoi cung, khong phai con so 40 s viet tay.
        after = max(slow)
        back = [s for s, k in zip(sec, node) if k == 'web02' and s > after]
        if back:
            rt = min(back)
            ax.axvline(rt, color='#3E8E5A', linestyle='--', linewidth=1.2)
            ax.annotate('bật lại web02', xy=(rt, 900),
                        xytext=(rt + 1.0, 1150),
                        color='#3E8E5A', fontsize=9)
    ax.set_ylim(0, 2150)
    ax.set_xlabel('Giây kể từ bắt đầu vòng đo')
    ax.set_ylabel('Thời gian đáp ứng (ms)')
    ax.legend(loc='upper right', ncol=4, fontsize=8, framealpha=.9)
    fig.tight_layout()
    out = os.path.join(FIGDIR, 'do-thai-failover.png')
    fig.savefig(out)
    plt.close(fig)
    print('ok', os.path.basename(out),
          '| mau=%d| cham=%d| loi=%d' % (len(rows), len(slow), len(bad)))
    return out


IP2NODE = {'172.20.0.11': 'web01', '172.20.0.12': 'web02', '172.20.0.13': 'web03'}


def chart_distribution():
    """Do lech phan phối, 20 luong moi thuat toan, co thanh sai so.

    Thanh sai so la phan quan trong nhat cua bieu do: no cho biet khac biet
    nao dang tin. Du lieu lay tu bench_summary.json do analyze_bench.py sinh
    ra, cung la nguon in ra bang trong bao cao.
    """
    import json
    agg_path = os.path.join(HERE, 'bench_summary.json')
    if not os.path.exists(agg_path):
        sys.exit('chay analyze_bench.py truoc de co bench_summary.json')
    skew = json.load(open(agg_path, encoding='utf-8'))['skew']
    algos = [a for a in ALGOS if a in skew]
    nodes = ('web01', 'web02', 'web03')

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.6, 3.4))
    width = 0.24
    xs = range(len(algos))
    for i, n in enumerate(nodes):
        vals = [skew[a]['nodes'][n]['mean'] for a in algos]
        errs = [skew[a]['nodes'][n]['ci'] for a in algos]
        ax1.bar([x + (i - 1) * width for x in xs], vals, width, yerr=errs,
                capsize=2, label=n, color=COLOR[n], ecolor='#444444')
        for j, v in enumerate(vals):
            # Chen so thap phan dau phay nhu bang trong bao cao, va dong dem
            # de ba nhan canh nhau khong de len nhau.
            ax1.text(xs[j] + (i - 1) * width, v + errs[j] + 14 + i * 26,
                     ('%.1f' % v).replace('.', ','), ha='center', fontsize=7)
    ax1.set_xticks(list(xs))
    ax1.set_xticklabels(algos, fontsize=9)
    ax1.set_ylabel('Request phục vụ, trung bình 20 lượt')
    ax1.set_ylim(0, 700)
    ax1.legend(ncol=3, fontsize=8)
    ax1.set_title('Độ đều của phân phối', fontsize=10)

    means = [skew[a]['skew']['mean'] for a in algos]
    errs = [skew[a]['skew']['ci'] for a in algos]
    bars = ax2.bar(range(len(algos)), means, 0.55, yerr=errs, capsize=6,
                   color='#2F6FA8', ecolor='#B03030')
    for x, (m, e) in enumerate(zip(means, errs)):
        ax2.text(x, m + e + 12, '%.1f ± %.1f' % (m, e), ha='center', fontsize=8)
    ax2.set_xticks(range(len(algos)))
    ax2.set_xticklabels(algos, fontsize=9)
    ax2.set_ylabel('Chênh lệch lớn nhất giữa hai node')
    ax2.set_yscale('symlog', linthresh=1)
    ax2.set_ylim(0, 1500)
    ax2.set_title('Một lượt đo, sai số là nửa khoảng tin cậy 95%', fontsize=9)
    fig.tight_layout()
    out = os.path.join(FIGDIR, 'phoi-canh-dong-thoi.png')
    fig.savefig(out)
    plt.close(fig)
    print('ok phoi-canh-dong-thoi.png',
          {a: (skew[a]['nodes']['web01']['mean'], skew[a]['skew']['mean'])
           for a in algos})
    return out


def chart_throughput():
    """Bac thang chi phi va so sanh thuat toan o tang ung dung.

    Doi truc log vi rieng bo can bang tai phuc vu gap 39 lan ca cum khi
    phai proxy sang node; tren truc tuyen thi hai tang sau deo thang nhau.
    """
    import json
    agg_path = os.path.join(HERE, 'bench_summary.json')
    if not os.path.exists(agg_path):
        sys.exit('chay analyze_bench.py truoc de co bench_summary.json')
    m = json.load(open(agg_path, encoding='utf-8'))['matrix']

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.6, 3.6))
    eps = ('lb-only', 'healthz', 'dbping.php')
    vals = [m['least_conn'][ep]['keepalive']['mean'] for ep in eps]
    errs = [m['least_conn'][ep]['keepalive']['ci'] for ep in eps]
    ax1.bar(range(len(eps)), vals, 0.55, yerr=errs, capsize=6,
            color=['#C08A2E', '#2F6FA8', '#3E8E5A'], ecolor='#B03030')
    for x, (v, e) in enumerate(zip(vals, errs)):
        ax1.text(x, v * 1.3, '%.0f' % v, ha='center', fontsize=8)
    ax1.set_yscale('log')
    ax1.set_ylim(300, 120000)
    ax1.set_xticks(range(len(eps)))
    ax1.set_xticklabels(('/lb-only', '/healthz', '/dbping.php'), fontsize=9)
    ax1.set_ylabel('req/s (thang log)')
    ax1.set_title('Chi phí tăng thêm theo tầng, least_conn, keep-alive', fontsize=9)

    algos = [a for a in ALGOS if a in m]
    vals = [m[a]['dbping.php']['keepalive']['mean'] for a in algos]
    errs = [m[a]['dbping.php']['keepalive']['ci'] for a in algos]
    ax2.bar(range(len(algos)), vals, 0.55, yerr=errs, capsize=6,
            color='#2F6FA8', ecolor='#B03030')
    for x, (v, e) in enumerate(zip(vals, errs)):
        ax2.text(x, v + e + 12, '%.0f ± %.0f' % (v, e), ha='center', fontsize=8)
    ax2.set_xticks(range(len(algos)))
    ax2.set_xticklabels(algos, fontsize=9)
    ax2.set_ylim(0, 900)
    ax2.set_ylabel('req/s')
    ax2.set_title('Tầng ứng dụng /dbping.php, 20 lượt', fontsize=9)
    fig.tight_layout()
    out = os.path.join(FIGDIR, 'do-thi-thong-qua.png')
    fig.savefig(out)
    plt.close(fig)
    print('ok do-thi-thong-qua.png', vals)
    return out


if __name__ == '__main__':
    chart_failover()
    chart_distribution()
    chart_throughput()
