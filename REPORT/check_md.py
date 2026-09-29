#!/usr/bin/env python3
"""Kiem tra tinh cua file markdown bao cao.

Dung:  python check_md.py chuong1.md [chuong2.md ...]
Thoat ma khac 0 neu phat hien loi.

Ly do co file nay: cac loi ma thay kiem bang mat bat nhat o bao cao truoc
(danh muc hinh trong, so hinh khong lien tuc, tu viet tat sao nguyen mau
chua sua) deu co the may phat hien duoc.
"""
import os
import re
import sys
import unicodedata

CJK = re.compile(r'[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af]')
DASH = re.compile(r'[\u2013\u2014]')
# Chieu dai hinh duoc viet theo kieu Viet (dau phay thap phan).  Regex phai
# khop voi FIG_RE trong build_docx.py, neu khong dong marker bi doc la caption.
FIG = re.compile(r'^\[\[FIG:([a-z0-9\-]+)\|(.+?)(?:\|(\d+(?:[.,]\d+)?))?\]\]$')
TAB = re.compile(r'^\[\[TAB:([a-z0-9\-]+)\|(.*)\]\]$')
REF = re.compile(r'\{(fig|tab):([a-z0-9\-]+)\}')
SELF_TALK = re.compile(
    r'(phần này giúp|có thể thấy|như đã phân tích|cho thấy rằng|'
    r'chúng tôi nhận thấy|đáng khuyến nghị|tốt hơn nhiều|hoàn hảo|'
    r'nổi bật|chính xác tuyệt đối|rất quan trọng)', re.IGNORECASE)
# Dong phan cach trong bang markdown, khong phai dong du lieu.
SEPARATOR = re.compile(r'^\|[\s\-|:]+\|$')
# Bao cao danh so hinh va bang tu dong, nen mot chu "Bảng 13" viet tay trong
# van ban se sai ngay khi them hay bo mot bang.  So cua giao trinh la ngoai le
# duoc phep go ten thang: "hình 5.12" o chuong 1 tro toi tai lieu [1], khong
# phai tro mot doi tuong cua bao cao.
OWN_NUMBER = re.compile(r'\b(?:[Bb]ảng|[Hh]ình)\s+\d+(?:[.,]\d+)?')
TEXTBOOK_EXEMPT = {
    'chuong1.md': re.compile(r'^[Hh]ình\s+5\.12$'),
}
# Nguoi dung viet bao cao tieng Viet khong dau o mot so nhan de, nen nhung
# tu hoa nay khong phai la tu viet tat.
NOT_AN_ABBREV = {
    'QUAN', 'WEB', 'CHUONG', 'KET', 'LUAN', 'MO', 'DAU', 'TAB', 'FIG',
    'BANG', 'BIEU', 'HINH', 'MUC', 'LUC', 'TAT', 'NGU', 'VIET', 'DANH',
    'MUC', 'AP', 'INT', 'SAMEORIGIN', 'NOSNIFF', 'STRICT', 'ORIGIN',
    'CROSS', 'EMBED', 'GET', 'POST', 'TCPDUMP', 'LAMP', 'LNMP',
    'CPU', 'GB', 'MB', 'MSI', 'GF63', 'CR', 'LF', 'P50', 'P95',
    'P99', 'P75', 'P90', 'P100', 'SQL', 'PAGEREF', 'TOC', 'SELECT', 'COUNT', 'TLSV',
}


def strip_markers(text):
    """Bo cac dong danh nghia va the tham chieu tru khi quet tu viet tat."""
    out = []
    for line in text.splitlines():
        if FIG.match(line.strip()) or TAB.match(line.strip()):
            continue
        if line.strip().startswith(('#1 ', '#0 ')):  # nhan de viet hoa toan bo
            continue
        out.append(REF.sub(' ', line))
    return '\n'.join(out)


def khong_dau(text):
    """Bo dau tieng Viet.

    Man hinh Windows cua may nay la cp1252 nen in nguyen chu co dau ra loi
    se lam check_md chep thay vi bao loi.
    """
    nfd = unicodedata.normalize('NFD', text)
    nfd = ''.join(c for c in nfd if not unicodedata.combining(c))
    return nfd.replace('\u0111', 'd').replace('\u0110', 'D')


def check(path, seen_figs, seen_tabs):
    """Kiem tra mot file markdown, bo loi vao seen_figs/seen_tabs tich luy.

    build_docx.py danh so hinh va bang toan cuc qua tat ca cac chuong, nen
    slug bi trung phai do tren tap tich luy cua moi file chu khong phai tung
    file mot: slug dung lai o chuong khac van duoc cap so ma khong tham
    chieu nao giai duoc.
    """
    problems = []
    lines = open(path, encoding='utf-8').read().splitlines()
    exempt = TEXTBOOK_EXEMPT.get(os.path.basename(path))

    for n, line in enumerate(lines, 1):
        if DASH.search(line):
            problems.append('%s:%d: dau gach ngang dai' % (path, n))
        if CJK.search(line):
            problems.append('%s:%d: ky tu CJK lac: %s' % (path, n, line[:60]))
        m = SELF_TALK.search(line)
        if m:
            problems.append('%s:%d: loi van tu ping gia: %s'
                            % (path, n, khong_dau(m.group(0))))
        for m in OWN_NUMBER.finditer(line):
            if exempt and exempt.match(m.group(0)):
                continue          # so cua giao trinh, khong phai cua bao cao
            problems.append('%s:%d: so thu tu viet tay "%s" -> de Word tu danh'
                            % (path, n, khong_dau(m.group(0))))
        if len(line) > 1200:
            problems.append('%s:%d: hai doan co the bi din vao nhau (%d ky tu)'
                            % (path, n, len(line)))

    opens = sum(1 for l in lines if l.strip() == 'tbl:')
    closes = sum(1 for l in lines if l.strip() == '#tc')
    if opens != closes:
        problems.append('%s: mo tbl: = %d, dong #tc = %d' % (path, opens, closes))

    # Moi khoi tbl: phai co cung so cot o moi dong.  build_docx.py xu ly bang
    # lech cot bang cach chen o trong, ma mot dau | lac trong mot o se day cac
    # o con lai cua dong ay sang ben phai, nen phai bao ra day.
    i = 0
    while i < len(lines):
        if lines[i].strip() != 'tbl:':
            i += 1
            continue
        start = i + 1
        rows = []
        i += 1
        while i < len(lines) and lines[i].strip() != '#tc':
            row = lines[i].strip()
            if row.startswith('|') and not SEPARATOR.match(row):
                rows.append((i + 1, len(row.strip('|').split('|'))))
            i += 1
        if not rows:
            problems.append('%s:%d: khoi tbl: khong co dong du lieu nao'
                            % (path, start))
        else:
            want = rows[0][1]
            for n, found in rows[1:]:
                if found != want:
                    problems.append('%s:%d: bang co %d cot o dong dau, dong nay'
                                    ' co %d cot' % (path, n, want, found))

    figs, tabs = {}, {}
    for n, line in enumerate(lines, 1):
        for rx, local, glob_tbl, word in ((FIG, figs, seen_figs, 'FIG'),
                                          (TAB, tabs, seen_tabs, 'TAB')):
            m = rx.match(line.strip())
            if not m:
                continue
            slug, cap = m.group(1), m.group(2).strip()
            if not cap:
                problems.append('%s:%d: %s %s khong co caption'
                                % (path, n, word, slug))
            # Slug lap lai vuot sang file khac moi gay hai: build_docx.py cap
            # so theo thu tu toan bo bao cao, nen lan gap sau bi gan cho mot
            # so ma khong tham chieu nao tro duoc.
            if slug in glob_tbl and glob_tbl[slug] != path:
                problems.append('%s:%d: %s %s da dung o %s, slug phai duy nhat'
                                ' toan bao cao' % (path, n, word, slug,
                                                   glob_tbl[slug]))
            elif slug in local:
                problems.append('%s:%d: %s %s bi trung trong cung file'
                                % (path, n, word, slug))
            local[slug] = cap
            glob_tbl.setdefault(slug, path)

    # Moi doan van phai bat dau bang mot doan co caption, khong phai bang
    for i, line in enumerate(lines):
        if line.strip() == 'tbl:':
            prev = next((lines[j].strip() for j in range(i - 1, -1, -1)
                         if lines[j].strip()), '')
            if not TAB.match(prev):
                problems.append('%s:%d: bang khong co dong caption ngay truoc'
                                % (path, i + 1))

    # Heading phai co so khop voi thu tu, va khong duoc dua so vao van ban
    # vi Word tu danh so theo style.
    h2 = 0
    prev_lvl = None
    for n, line in enumerate(lines, 1):
        s = line.strip()
        lvl = re.match(r'^#([0-3]) ', s)
        if lvl:
            # Khong duoc bo qua cap muc: #3 ngay sau #1 ma khong co #2 thi
            # muc luc cua Word thieu mot tang va so "1.1.1" nhay thang.
            lvl = int(lvl.group(1))
            if prev_lvl is not None and lvl > prev_lvl + 1:
                problems.append('%s:%d: nhay tu muc #%d len muc #%d, thieu muc'
                                ' #%d' % (path, n, prev_lvl, lvl, lvl - 1))
            prev_lvl = lvl
        if s.startswith('#1 '):
            if re.match(r'^(CHƯƠNG|Chương)\s*\d', s[3:]):
                pass                      # builder lo, van cho phep viet tay
        elif s.startswith('#2 '):
            h2 += 1
            m = re.match(r'^(\d+)\.(\d+)\s', s[3:])
            if m and int(m.group(2)) != h2:
                problems.append('%s:%d: muc %s khong khop thu tu %d'
                                % (path, n, m.group(0).strip(), h2))

    print('%s: %d dong, %d hinh, %d bang, %d loi'
          % (path, len(lines), len(figs), len(tabs), len(problems)))
    for p in problems:
        print('   ', p)
    return len(problems)


def check_abbrev(paths):
    import build_docx
    body = '\n'.join(strip_markers(open(p, encoding='utf-8').read())
                     for p in paths)
    listed = {a for a, _e, _v in build_docx.META['tu_viet_tat']}
    used = {t for t in re.findall(r'\b[A-Z][A-Z0-9]{1,9}\b', body)
            if t not in NOT_AN_ABBREV and not re.match(r'^B\d', t)}
    problems = []
    for a in sorted(listed - used):
        problems.append('danh muc co "%s" nhung cac chuong da viet khong dung' % a)
    for u in sorted(used - listed):
        problems.append('bai dung "%s" nhung thieu trong danh muc' % u)
    print('tu viet tat: %d khai bao, %d gap trong bai, %d loi'
          % (len(listed), len(used & listed), len(problems)))
    for p in problems:
        print('   ', p)
    return len(problems)


def check_refs(paths, all_figs, all_tabs):
    problems = []
    for p in paths:
        text = open(p, encoding='utf-8').read()
        for kind, slug in REF.findall(text):
            store = all_figs if kind == 'fig' else all_tabs
            if slug not in store:
                problems.append('%s: tham chieu {%s:%s} khong co muc tieu' % (p, kind, slug))
    print('tham chieu cross: %d loi' % len(problems))
    for x in problems:
        print('   ', x)
    return len(problems)


if __name__ == '__main__':
    # Mac dinh kiem TRA TOAN BO nguon vao bao cao, ke ca tai-lieu.md. Danh muc
    # tu viet tat phai doi chieu voi ca sach tham khao: RFC 5798 va OWASP Top 10
    # xuat hien o do chu khong xuat hien trong ba chuong, nen chi quet chuong
    # thi ba muc bi bao la "khong dung" trong khi chung van nam trong file.
    paths = sys.argv[1:] or ['mo-dau.md', 'chuong1.md', 'chuong2.md',
                             'chuong3.md', 'ket-luan.md', 'tai-lieu.md']
    total = 0
    # slug duoc tich luy qua tung file theo thu tu dung tren lenh, vi
    # build_docx.py cung doc theo thu tu do va danh so toan cuc.
    all_figs, all_tabs = {}, {}
    for f in paths:
        total += check(f, all_figs, all_tabs)
    total += check_refs(paths, all_figs, all_tabs)
    total += check_abbrev(paths)
    sys.exit(1 if total else 0)
