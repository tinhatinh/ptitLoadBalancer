#!/usr/bin/env python3
"""Dung bao cao .docx tu markdown nguon, dua tren mau chinh thuc cua khoa.

Mau duoc giu nguyen bo style BTL-* va dinh so tu dong:
  BTL-H1 -> "CHƯƠNG n."      BTL-H2 -> "n.m"      BTL-H3 -> "n.m.k"
  BTL-Bang -> "Bảng n"       BTL-Hinh -> "Hình n"   (đánh số toàn cục)

Vi the markdown nguon KHONG duoc chua so thu cong o dong heading, va
`{fig:slug}` / `{tab:slug}` trong van ban se duoc thay bang so that ma
Word se hien khi cap nhat truong.

Dung:
    python build_docx.py --out ../REPORT/out.docx chuong1.md [chuong2.md ...]
    python build_docx.py --draft-only ...        # khong chay Word
"""
import argparse
import copy
import json
import os
import re
import sys

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

HERE = os.path.dirname(os.path.abspath(__file__))


def find_template():
    """Mau bao cao cua hoc phan la file cua truong, khong di kem repo. Tim
    theo hai thu tu: bien moi truong BTL_TEMPLATE, roi ban copy dat ngay trong
    REPORT/. Khong ghi duong dan tuyet doi cua may nguoi soan vao day."""
    for cand in (os.environ.get('BTL_TEMPLATE'),
                 os.path.join(HERE, 'mau-bao-cao.docx')):
        if cand and os.path.exists(cand):
            return cand
    return None


TEMPLATE = find_template()
FIGDIR = os.path.join(HERE, 'figures')

# Hai cho dat cho do finalize_word.py tim va thay bang danh muc hinh/bang
# that.  Neu mot marker bi mat hoac lap lai, Word in thoang qua va bao cao
# bi hong van duoc giao, nen build_docx kiem tra truoc khi ghi file.
TOF_HINH = '@@TOF_HINH@@'
TOF_BANG = '@@TOF_BANG@@'
TOF_MARKERS = (TOF_HINH, TOF_BANG)

# Chieu dai mac dinh cua mot hinh khi marker khong ghi ro (cm).
DEFAULT_FIG_WIDTH_CM = 15.0
# Cot van ban A4 cua mau, tinh theo do le trang. Anh be hon thi giu nguyen
# kich thuoc markdown yeu cau; anh lon hon bi ep ve dung cot.
MAX_FIG_WIDTH_CM = 15.0
# Mot anh chen vao khong duoc cao qua 60% chieu cao van ban, neu khong no
# day chu thich sang trang sau va de lai mot trang trong.
MAX_FIG_HEIGHT_CM = 16.0


def image_size(path):
    from PIL import Image
    with Image.open(path) as im:
        return im.size

META = {
    'hoc_vien': 'HỌC VIỆN CÔNG NGHỆ BƯU CHÍNH VIỄN THÔNG',
    'khoa': 'KHOA AN TOÀN THÔNG TIN',
    'loai_bao_cao': 'BÁO CÁO BÀI TẬP LỚN',
    'hoc_phan': 'AN TOÀN ỨNG DỤNG WEB VÀ CƠ SỞ DỮ LIỆU',
    'ma_hoc_phan': 'INT14105',
    'de_tai': 'Tìm hiểu và triển khai chuỗi cân bằng tải các máy chủ web '
              '(web server load balancing cluster)',
    'nhom': '15',
    'lop': '04',
    'gvhd': 'ThS Vũ Minh Mạnh',
    'nam': 'HÀ NỘI 2026',
    # Bìa mẫu của khoa kết bằng dòng học ky, khong phai "Ha Noi 2026".
    'hoc_ky': 'HỌC KỲ 1 NĂM HỌC 2026-2027',
    'logo': os.path.join(HERE, 'logo-ptit.jpeg'),
    'thanh_vien': [
        ('B23DCAT040', 'Phan Thành Danh'),
        ('B23DCAT326', 'Nghiêm Xuân Hoàng Tùng'),
        ('B23DCAT329', 'Trịnh Thanh Tùng'),
    ],
    'tu_viet_tat': [
        ('CSRF', 'Cross-Site Request Forgery', 'Giả mạo yêu cầu từ một site khác'),
        ('CI', 'Confidence Interval', 'Khoảng tin cậy của giá trị trung bình'),
        ('CV', 'Coefficient of Variation', 'Hệ số biến thiên, bằng độ lệch chuẩn chia trung bình'),
        ('DNS', 'Domain Name System', 'Hệ thống tên miền'),
        ('HSTS', 'HTTP Strict Transport Security', 'Chính sách buộc trình duyệt chỉ dùng HTTPS'),
        ('HTTP', 'HyperText Transfer Protocol', 'Giao thức truyền tải siêu văn bản'),
        ('HTTPS', 'HTTP Secure', 'HTTP chạy trên TLS'),
        ('IP', 'Internet Protocol', 'Giao thức liên mạng'),
        ('LVS', 'Linux Virtual Server', 'Dự án cân bằng tải tầng 4 của Linux'),
        ('NAT', 'Network Address Translation', 'Phép chuyển đổi địa chỉ mạng'),
        ('IETF', 'Internet Engineering Task Force', 'Tổ chức tiêu chuẩn hóa kỹ thuật Internet'),
        ('OSI', 'Open Systems Interconnection', 'Mô hình tham chiếu kết nối mở'),
        ('OWASP', 'Open Worldwide Application Security Project', 'Dự án mở về an toàn ứng dụng'),
        ('PHP', 'Hypertext Preprocessor', 'Ngôn ngữ lập trình phía máy chủ'),
        ('RST', 'Reset', 'Cờ TCP báo hủy kết nối đột ngột'),
        ('RFC', 'Request for Comments', 'Văn bản chuẩn của IETF'),
        ('TLS', 'Transport Layer Security', 'Giao thức bảo vệ kênh truyền'),
        ('TCP', 'Transmission Control Protocol', 'Giao thức điều khiển truyền'),
        ('UDP', 'User Datagram Protocol', 'Giao thức dữ liệu người dùng'),
        ('URI', 'Uniform Resource Identifier', 'Bộ nhận dạng tài nguyên'),
        ('WSL', 'Windows Subsystem for Linux', 'Hệ con Linux của Windows'),
        ('VRRP', 'Virtual Router Redundancy Protocol', 'Giao thức dự phòng bộ định tuyến ảo'),
    ],
    'phan_cong': [
        ('1', 'Tìm hiểu lý thuyết về cân bằng tải và các thuật toán phân phối',
         'Nghiêm Xuân Hoàng Tùng'),
        ('2', 'Thiết kế và triển khai cụm ba máy chủ web với nginx load balancer',
         'Phan Thành Danh'),
        ('3', 'Triển khai kho phiên dùng chung và lớp bảo mật tại cân bằng tải',
         'Trịnh Thanh Tùng'),
        ('4', 'Thử nghiệm, thu số liệu phân phối tải, failover và đánh giá',
         'Phan Thành Danh'),
    ],
}

SELF_TALK = re.compile(r'\b(phần này giúp|có thể thấy|như đã phân tích)\b', re.I)


def set_style(par, name):
    par.style = name


def run_of(par, text, bold=False, italic=False, size=None, font='Times New Roman'):
    r = par.add_run(text)
    r.bold = bold
    r.italic = italic
    r.font.name = font
    r._element.rPr.rFonts.set(qn('w:eastAsia'), font)
    if size:
        r.font.size = Pt(size)
    return r


def clear_body(doc):
    body = doc.element.body
    sectpr = body.find(qn('w:sectPr'))
    for child in list(body):
        if child is not sectpr:
            body.remove(child)
    return sectpr


def add_field(par, instr):
    """Chen truong Word dang phuc tap (begin / instrText / separate / end)."""
    from docx.oxml import OxmlElement
    begin = OxmlElement('w:fldChar'); begin.set(qn('w:fldCharType'), 'begin')
    code = OxmlElement('w:instrText'); code.set(qn('xml:space'), 'preserve')
    code.text = ' %s ' % instr
    sep = OxmlElement('w:fldChar'); sep.set(qn('w:fldCharType'), 'separate')
    run = par.add_run()
    run._element.append(begin); run._element.append(code); run._element.append(sep)
    tail = OxmlElement('w:fldChar'); tail.set(qn('w:fldCharType'), 'end')
    par._p.append(tail)


# Thu tu con bat buoc cua CT_PPr theo schema (ECMA-376): w:pBdr dung sau
# numPr va truoc toan bo nhom con lien sau no.  code_block tao spacing/ind
# truoc khi chen vien trai, nen pBdr phai chen vao vi tri nay chu khong
# duoc append: Word hoi dung duoc file sai thu tu, do la nguy co hong file
# lon nhat cua bao cao nay.
PPR_AFTER_PBDR = (
    'w:shd', 'w:tabs', 'w:suppressAutoHyphens', 'w:kinsoku', 'w:wordWrap',
    'w:overflowPunct', 'w:topLinePunct', 'w:autoSpaceDE', 'w:autoSpaceDN',
    'w:bidi', 'w:adjustRightInd', 'w:snapToGrid', 'w:spacing', 'w:ind',
    'w:contextualSpacing', 'w:mirrorIndents', 'w:suppressOverlap', 'w:jc',
    'w:textDirection', 'w:textAlignment', 'w:textboxTightWrap',
    'w:outlineLvl', 'w:divId', 'w:cnfStyle', 'w:rPr', 'w:sectPr',
    'w:pPrChange',
)


TOKEN = re.compile(r'(\*\*.+?\*\*|`[^`]+`)')


ZERO_SP = '\ufeff'      # ZWNBSP: cho Word thay mot diem cat, khong in ra ly tu


def soft_breaks(text):
    """Them diem cat vo hinh sau cac ky tu cau duong dan va ten tep.

    Doan van bang kieu `results/bench/matrix-20260929-103024.csv` la mot tu
    dai khong cat duoc. Van ban can deu hai ben (justify) khi do se gian ca
    dong lenh de lua chon, de lai khoang trong lu lon giua cac tu.
    """
    out = []
    for ch in text:
        out.append(ch)
        if ch in '_/.-':
            out.append(ZERO_SP)
    return ''.join(out)


def add_rich(par, text, base_bold=False, size=None):
    """Viet van ban co **in dam** va `ma nguon` vao mot doan van."""
    for piece in TOKEN.split(text):
        if not piece:
            continue
        bold, mono, body = base_bold, False, piece
        if piece.startswith('**') and piece.endswith('**') and len(piece) > 4:
            bold, body = True, piece[2:-2]
        elif piece.startswith('`') and piece.endswith('`') and len(piece) > 2:
            mono, body = True, soft_breaks(piece[1:-1])
        r = par.add_run(body)
        r.bold = bold
        r.font.name = 'Consolas' if mono else 'Times New Roman'
        r._element.rPr.rFonts.set(qn('w:eastAsia'), r.font.name)
        if mono:
            r.font.size = Pt((size or 13) - 1.5)
        elif size:
            r.font.size = Pt(size)
    return par


class Builder:
    def __init__(self, doc):
        self.doc = doc
        self.fig_num = {}
        self.tab_num = {}
        self.counters = {'fig': 0, 'tab': 0}
        self.pending_caption = None
        # Ghi lai file va slug cua bang dang viet de loi bang lech cot ke duoc
        # dung o dau: file nao, slug nao, dong nao.
        self.src = None
        self.tab_slug = None

    # -- tham chieu ------------------------------------------------
    def register(self, kind, slug):
        # Idempotent: feed_markdown dem so o luot doc thu nhat, luot viet
        # thu hai goi lai cung slug thi phai giu nguyen so da cap.
        table = getattr(self, kind + '_num')
        if slug in table:
            return table[slug]
        self.counters[kind] += 1
        table[slug] = self.counters[kind]
        return self.counters[kind]

    def resolve(self, text):
        def sub(m):
            kind, slug = m.group(1), m.group(2)
            table = self.fig_num if kind == 'fig' else self.tab_num
            if slug not in table:
                raise KeyError('tham chieu {%s:%s} khong co muc tieu' % (kind, slug))
            word = 'Hình' if kind == 'fig' else 'Bảng'
            return '%s %d' % (word, table[slug])
        return re.sub(r'\{(fig|tab):([a-z0-9\-]+)\}', sub, text)

    # -- khoi goi --------------------------------------------------
    def para(self, text, style='BTL-Text', align=None, keep_with_next=False):
        p = self.doc.add_paragraph(style=style)
        add_rich(p, self.resolve(text))
        if align:
            p.alignment = align
        if keep_with_next:
            p.paragraph_format.keep_with_next = True
        return p

    def heading(self, level, text, new_page=False):
        style = {0: 'BTL-H0', 1: 'BTL-H1', 2: 'BTL-H2', 3: 'BTL-H3'}[level]
        text = re.sub(r'^(CHƯƠNG|Chương)\s+\d+[\.\s]*', '', text)
        text = re.sub(r'^\d+(\.\d+)*[\.\s]+', '', text)
        p = self.para(text, style=style)
        if new_page:
            # Thuoc tinh "page break before" cua chinh doan van, khong phai
            # doan cat trang rieng: doan rieng se de lai mot trang trong khi
            # trang truoc do vua ky lan.
            p.paragraph_format.page_break_before = True
        return p

    def figure(self, slug, caption, width_cm=DEFAULT_FIG_WIDTH_CM):
        png = os.path.join(FIGDIR, slug + '.png')
        if not os.path.exists(png):
            raise FileNotFoundError('thieu hinh %s' % png)
        n = self.register('fig', slug)
        w, h = image_size(png)
        # Chen theo ty le cua anh, khong theo mot be rong an dinh: anh 16 cm
        # ma cot van ban chi 15 cm thi mat bi cat nghen ben phai.
        width_cm = min(width_cm, MAX_FIG_WIDTH_CM,
                       MAX_FIG_HEIGHT_CM * w / float(h))
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        # Doan anh phai di kem chu thich: khong co keep_with_next thi Word day
        # chu thich sang trang sau va anh dung khong ten.
        p.paragraph_format.keep_with_next = True
        p.add_run().add_picture(png, width=Cm(width_cm))
        self.para(caption, style='BTL-Hinh', align=WD_ALIGN_PARAGRAPH.CENTER)
        return n

    def table_caption(self, slug, caption):
        self.register('tab', slug)
        self.tab_slug = slug
        # Chu thich bang nam tren bang, nen no phai di theo bang.
        self.para(caption, style='BTL-Bang', align=WD_ALIGN_PARAGRAPH.CENTER,
                  keep_with_next=True)

    def table(self, rows):
        # Dong dau la hang dau bang va quyet dinh so cot.  Van giu chen o trong
        # cho dong thieu o, nhung dong le so cot thi phai bao ra: mot dau | lac
        # trong mot o day ca cac o con lai cua dong ay sang ben phai, va bang
        # lech cot thi khong ai phat hien bang mat.
        if not rows:
            raise ValueError('bang %s trong %s khong co dong du lieu nao'
                             % (self.tab_slug, self.src))
        expected = len(rows[0])
        ragged = [(j, len(r)) for j, r in enumerate(rows) if len(r) != expected]
        if ragged:
            raise ValueError('bang "%s" trong %s le so cot: %s'
                             % (self.tab_slug, self.src,
                                '; '.join('dong %d co %d cot (mong %d)'
                                          % (j + 1, n, expected)
                                          for j, n in ragged)))
        ncols = max(len(r) for r in rows)
        t = self.doc.add_table(rows=0, cols=ncols)
        t.style = 'Table Grid'
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        for i, row in enumerate(rows):
            cells = t.add_row().cells
            for j in range(ncols):
                txt = row[j] if j < len(row) else ''
                cell = cells[j]
                cell.text = ''
                p = cell.paragraphs[0]
                add_rich(p, txt, base_bold=(i == 0), size=11)
                # O bang rat hep, can deu hai ben se gian chu giua dong.
                # Lech duy nhat can giu la hang dau de giua.
                p.alignment = (WD_ALIGN_PARAGRAPH.CENTER if i == 0
                               else WD_ALIGN_PARAGRAPH.LEFT)
        # Bang dai hon mot trang thi hang dau phai lap lai o trang tiep theo,
        # neu khong so trong cot khong con biet thuoc cot nao. Dat sau khi
        # dong dau tien da ton tai.
        from docx.oxml import OxmlElement
        t.rows[0]._tr.get_or_add_trPr().append(OxmlElement('w:tblHeader'))
        return t

    def code_block(self, rows):
        """Khoi ma nguon: font don rong, khong thut dau dong, co vien trai."""
        for text in rows:
            p = self.doc.add_paragraph()
            pf = p.paragraph_format
            pf.left_indent = Cm(0.8)
            pf.space_before = Pt(0)
            pf.space_after = Pt(0)
            pf.line_spacing = 1.0
            r = p.add_run(text if text else ' ')
            r.font.name = 'Consolas'
            r._element.rPr.rFonts.set(qn('w:eastAsia'), 'Consolas')
            r.font.size = Pt(9.5)
            pPr = p._p.get_or_add_pPr()
            borders = pPr.makeelement(qn('w:pBdr'), {})
            left = pPr.makeelement(qn('w:left'), {
                qn('w:val'): 'single', qn('w:sz'): '6',
                qn('w:space'): '4', qn('w:color'): '808080'})
            borders.append(left)
            # pPr da co spacing va ind do paragraph_format tao o tren, nen
            # pBdr phai chen truoc chung theo thu tu schema.
            pPr.insert_element_before(borders, *PPR_AFTER_PBDR)

    def page_break(self):
        self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def build_cover(b):
    """Bìa theo đúng mẫu 111.docx của khoa: cỡ chữ, khoảng cách và logo.

    Cac kich thuoc o day la do lai truc tiep tu file mau (EMU doi ra pt),
    khong phai phat bieu: bao cao nop theo bìa cua truong thi lech mot diem
    tu cung lo.
    """
    d = b.doc

    def line(text='', size=None, bold=False, after=0, before=0,
             spacing=1.15, align=WD_ALIGN_PARAGRAPH.CENTER):
        par = d.add_paragraph()
        par.alignment = align
        pf = par.paragraph_format
        pf.space_before = Pt(before)
        pf.space_after = Pt(after)
        pf.line_spacing = spacing
        if text:
            run_of(par, text, bold=bold, size=size)
        return par

    line(META['hoc_vien'], 14, True, before=12)
    line(META['khoa'], 14, True)
    logo = d.add_paragraph()
    logo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    logo.paragraph_format.space_before = Pt(8)
    logo.paragraph_format.space_after = Pt(6)
    if os.path.exists(META['logo']):
        logo.add_run().add_picture(META['logo'], width=Cm(3.6))
    line(before=28, after=36)
    line(META['loai_bao_cao'], 16, True)
    line('HỌC PHẦN: ' + META['hoc_phan'], 16, True)
    line('MÃ HỌC PHẦN: ' + META['ma_hoc_phan'], 16, True, after=6)
    line('ĐỀ TÀI: ' + META['de_tai'], 14, False, after=28, spacing=1.2)
    line('Sinh viên thực hiện:', 14, False, after=2, spacing=1.3)
    for msv, name in META['thanh_vien']:
        line('%s   %s' % (msv, name), 14, False, after=10, spacing=1.3)
    line('Nhóm: ' + META['nhom'], 14, False, after=2, spacing=1.3)
    line('Lớp: ' + META['lop'], 14, False, after=2, spacing=1.3)
    line('Giảng viên hướng dẫn: ' + META['gvhd'], 14, False, after=48,
         spacing=1.3)
    line(META['hoc_ky'], 14, True, before=24)
    b.page_break()


def build_front_matter(b):
    h = b.doc.add_paragraph('PHÂN CÔNG NHIỆM VỤ NHÓM THỰC HIỆN', style='BTL-H0')
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER

    t = b.doc.add_table(rows=1, cols=4)
    t.style = 'Table Grid'
    for i, head in enumerate(('TT', 'Công việc / Nhiệm vụ', 'SV thực hiện',
                              'Tỉ lệ phần trăm đóng góp')):
        r = t.rows[0].cells[i].paragraphs[0].add_run(head)
        r.bold = True
        r.font.name = 'Times New Roman'
        r.font.size = Pt(11)
    for num, task, who in META['phan_cong']:
        cells = t.add_row().cells
        for i, val in enumerate((num, task, who, '')):
            rr = cells[i].paragraphs[0].add_run(val)
            rr.font.name = 'Times New Roman'
            rr.font.size = Pt(11)

    b.doc.add_paragraph()
    h = b.doc.add_paragraph('NHÓM THỰC HIỆN TỰ ĐÁNH GIÁ', style='BTL-H0')
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t = b.doc.add_table(rows=1, cols=7)
    t.style = 'Table Grid'
    for i, head in enumerate(('TT', 'SV thực hiện', 'Thái độ tham gia',
                              'Mức hoàn thành CV', 'Kỹ năng giao tiếp',
                              'Kỹ năng hợp tác', 'Kỹ năng lãnh đạo')):
        r = t.rows[0].cells[i].paragraphs[0].add_run(head)
        r.bold = True
        r.font.name = 'Times New Roman'
        r.font.size = Pt(11)
    for idx, (msv, name) in enumerate(META['thanh_vien'], 1):
        cells = t.add_row().cells
        for i, val in enumerate((str(idx), name, '', '', '', '', '')):
            rr = cells[i].paragraphs[0].add_run(val)
            rr.font.name = 'Times New Roman'
            rr.font.size = Pt(11)
    b.page_break()

    def heading_line(text):
        p = b.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(text)
        r.bold = True
        r.font.name = 'Times New Roman'
        r.font.size = Pt(13)
        return p

    heading_line('MỤC LỤC')
    add_field(b.doc.add_paragraph(),
              # Khong dung \u: style BTL-Bang va BTL-Hinh cua mang co outline
              # level, nen \u keo ca 49 chu thich vao muc luc va no dai gap
              # ba lan. Chi lay theo ten style ghi ro o \t.
              r'TOC \h \z \t "BTL-H1,1,BTL-H2,2,BTL-H3,3,'
              r'BTL-H0,1,BTL-H3.1,3,BTL-H3.0,3"')
    b.page_break()

    # Danh muc hinh va danh muc bang la truong TOC chi lay theo DUNG ten
    # style chu thich. Truoc day dung TablesOfContents.Add cua Word COM thi
    # tham so so thu bi dich nghia khac, danh muc keo ca cac muc cua muc luc
    # vao va dai gap doi. Viet truc tiep bang ma lenh tu \.
    heading_line('DANH MỤC CÁC HÌNH VẼ')
    add_field(b.doc.add_paragraph(), r'TOC \h \z \t "BTL-Hinh,1"')
    b.page_break()
    heading_line('DANH MỤC CÁC BẢNG BIỂU')
    add_field(b.doc.add_paragraph(), r'TOC \h \z \t "BTL-Bang,1"')
    b.page_break()

    heading_line('DANH MỤC CÁC TỪ VIẾT TẮT')
    t = b.doc.add_table(rows=1, cols=3)
    t.style = 'Table Grid'
    for i, head in enumerate(('Từ viết tắt', 'Thuật ngữ tiếng Anh',
                              'Thuật ngữ tiếng Việt')):
        r = t.rows[0].cells[i].paragraphs[0].add_run(head)
        r.bold = True
        r.font.name = 'Times New Roman'
        r.font.size = Pt(11)
    for abbr, en, vi in META['tu_viet_tat']:
        cells = t.add_row().cells
        for i, val in enumerate((abbr, en, vi)):
            rr = cells[i].paragraphs[0].add_run(val)
            rr.font.name = 'Times New Roman'
            rr.font.size = Pt(11)
    b.page_break()


# Do dai trong marker hinh viet theo kieu Viet (dau phay thap phan), nen regex
# phai chap nhan ca '.' va ','.  Chi nhan dau '.' khien '|15,5' khong duoc doc
# la chieu dai: nhom caption ham luon '|15,5' vao doan ghi chu, con chieu dai
# thi quay ve mac dinh.
FIG_RE = re.compile(
    r'^\[\[FIG:([a-z0-9\-]+)\|(.+?)(?:\|(\d+(?:[.,]\d+)?))?\]\]$')
TAB_RE = re.compile(r'^\[\[TAB:([a-z0-9\-]+)\|(.+)\]\]$')
# Dong mo khoi ma nguon co the kem info string (```bash).  Token do chi giup
# nhan ra dong mo khoi de loai bo, khong bao gio in ra bao cao.
FENCE_RE = re.compile(r"^```\s*([A-Za-z0-9_+.\-]*)\s*$")


def cm_value(text):
    """Chieu dai hinh bang cm, doi duoc '16', '15.5' lan '15,5'."""
    if not text:
        return DEFAULT_FIG_WIDTH_CM
    return float(text.replace(',', '.'))


def feed_markdown(b, path, page_break_before=True):
    lines = open(path, encoding='utf-8').read().splitlines()
    b.src = path
    # Lan 1: dang ky so thu tu hinh va bang theo thu tu xuat hien.
    for line in lines:
        m = FIG_RE.match(line.strip())
        if m and m.group(1) not in b.fig_num:
            b.register('fig', m.group(1))
        m = TAB_RE.match(line.strip())
        if m and m.group(1) not in b.tab_num:
            b.register('tab', m.group(1))

    # Lan 2: viet.
    i = 0
    first_heading_done = False
    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip()
        i += 1
        if not line.strip():
            continue
        s = line.strip()

        if s.startswith('#0 '):
            # Moi nguon vao bao cao (mo-dau, ket-luan, tai-lieu) bat dau bang
            # mot `#0` va phai nam dau trang rieng.
            b.heading(0, s[3:], new_page=page_break_before or first_heading_done)
            first_heading_done = True
            continue
        if s.startswith('#1 '):
            b.heading(1, s[3:], new_page=True)
            first_heading_done = True
            continue
        if s.startswith('#2 '):
            b.heading(2, s[3:]); continue
        if s.startswith('#3 '):
            b.heading(3, s[3:]); continue

        m = FIG_RE.match(s)
        if m:
            b.figure(m.group(1), m.group(2),
                     width_cm=cm_value(m.group(3))); continue

        m = TAB_RE.match(s)
        if m:
            b.table_caption(m.group(1), m.group(2)); continue

        if FENCE_RE.match(s):
            # Info string (bash, ini, ...) duoc loai bo, khong in ra bao cao.
            rows = []
            while i < len(lines) and not FENCE_RE.match(lines[i].strip()):
                rows.append(lines[i].rstrip())
                i += 1
            i += 1
            b.code_block(rows)
            continue

        if s == 'tbl:':
            rows = []
            while i < len(lines) and lines[i].strip() != '#tc':
                row = lines[i].strip()
                i += 1
                if row.startswith('|') and not re.match(r'^\|[\s\-|:]+\|$', row):
                    rows.append([c.strip() for c in row.strip('|').split('|')])
            i += 1                      # bo dong dong #tc
            b.table(rows)
            continue

        if s.startswith('!b '):
            # Doan dan y in dam: van phai qua add_rich de **dau** va `ma nguon`
            # trong no duoc dich, neu run_of thi dau sao in ra nguyen van.
            p = b.doc.add_paragraph(style='BTL-Text')
            add_rich(p, b.resolve(s[3:]), base_bold=True)
            continue

        if s.startswith('- '):
            b.para(s[2:], style='BTL-Bullet1'); continue

        b.para(s)


def check_placeholders(doc):
    """That build neu mot cho dat cho danh muc khong con dung mot lan.

    finalize_word.py tim hai chu @@...@@ de thay bang danh muc hinh va danh
    muc bang that.  Marker bi mat hoac bi lap thi Word khong in ra bao loi,
    bao cao van duoc giao ma thieu mot danh muc, nen kiem tra som mot buoc.
    """
    xml = doc.element.xml
    for name, code in (('danh muc hinh', 'BTL-Hinh,1'),
                       ('danh muc bang', 'BTL-Bang,1')):
        n = xml.count(code)
        if n != 1:
            sys.exit('truong %s xuat hien %d lan, can dung mot lan'
                     % (name, n))
    for marker in TOF_MARKERS:
        if marker in xml:
            sys.exit('con cho dat cho %s trong tai lieu' % marker)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('sources', nargs='+')
    ap.add_argument('--out', default=os.path.join(HERE, 'BaoCao_BTL_INT14105.docx'))
    ap.add_argument('--draft-only', action='store_true')
    args = ap.parse_args()

    if not TEMPLATE:
        sys.exit(
            'Khong tim thay mau bao cao. Lay file "ATTT-Mau bao cao bai thuc '
            'hanh TTCS.docx" tu portal cua truong, dat ten la '
            'REPORT/mau-bao-cao.docx hoac tro vao no bang bien moi truong '
            'BTL_TEMPLATE.\n'
            'Cac buoc trung gian khong can mau: check_md.py va '
            'verify_numbers.py van chay duoc.')

    doc = Document(TEMPLATE)
    clear_body(doc)
    b = Builder(doc)
    build_cover(b)
    build_front_matter(b)
    for k, src in enumerate(args.sources):
        # File dau tien da nam sau trang bi, khong can cat trang truoc no.
        feed_markdown(b, src, page_break_before=(k > 0))

    out = os.path.abspath(args.out)
    check_placeholders(doc)
    doc.save(out)
    print('da ghi', out)

    # Thong ke kiem tra
    print('hinh: %d, bang: %d' % (len(b.fig_num), len(b.tab_num)))
    json.dump({'figures': b.fig_num, 'tables': b.tab_num},
              open(os.path.join(HERE, 'numbering.json'), 'w', encoding='utf-8'),
              indent=1, ensure_ascii=False, sort_keys=True)
    return out


if __name__ == '__main__':
    main()
