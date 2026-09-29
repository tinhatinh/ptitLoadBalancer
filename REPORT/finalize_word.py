#!/usr/bin/env python3
"""Mo bao cao bang Word: thay cho dat cho bang danh muc hinh/bang, cap nhat
truong, luu lai va xuat PDF de kiem tra bang mat.

Dung:  python finalize_word.py out.docx
"""
import os
import sys

from win32com.client.dynamic import Dispatch as DynDispatch

TOF = {
    '@@TOF_HINH@@': ('BTL-Hinh', 'DANH MỤC CÁC HÌNH VẼ'),
    '@@TOF_BANG@@': ('BTL-Bang', 'DANH MỤC CÁC BẢNG BIỂU'),
}

# Thu tu tham so cua TablesOfContents.Add trong Word 16. Khong co tham so
# Style; cach dua mot style khong phai heading vao danh muc la AddedStyles,
# dinh dang "TenStyle,cap".
def tof_args(style_name):
    return [
        False,               # UseHeadingStyles
        1,                   # UpperHeadingLevel
        3,                   # LowerHeadingLevel
        False,               # UseFields
        '',                  # TableID
        True,                # RightAlignPageNumbers
        True,                # IncludePageNumbers
        '%s,1' % style_name,  # AddedStyles
        True,                # UseHyperlinks
        False,               # HidePageNumbersInWeb
        False,               # UseOutlineLevels
    ]


def add_tof(doc, marker, style_name):
    """Dat TablesOfContents vung cua doan van chua marker, lay theo ten style."""
    for para in list(doc.Paragraphs):
        if marker in para.Range.Text:
            toc = doc.TablesOfContents.Add(para.Range, *tof_args(style_name))
            toc.Update()
            return True
    return False


def drop_leftover(doc):
    """Xoa moi doan van van con giu marker sau khi danh muc da xen vao.

    Marker la doan van that trong tai lieu, khong phai field. Ne no lai thi
    nguoi dung doc thay "@@TOF_HINH@@" in ngay tren trang, va do la mot file
    hong. Xoa tu cuoi len de khong lam hong chi muc dang duyet.
    """
    hits = [p for p in doc.Paragraphs if '@@TOF_' in p.Range.Text]
    for p in reversed(hits):
        p.Range.Delete()
    return len(hits)


def main(path):
    path = os.path.abspath(path)
    word = DynDispatch('Word.Application')
    word.Visible = False
    word.DisplayAlerts = 0
    try:
        doc = word.Documents.Open(path)

        # Ba danh muc (muc luc, hinh, bang) deu la truong TOC do build_docx.py
        # viet thang ma lenh, khong can Word them danh muc nua. O day chi cap
        # nhat va kiem tra khong con cho dat cho nao sot lai.
        n_toc = doc.TablesOfContents.Count
        if n_toc < 3:
            raise SystemExit('chi thay %d danh muc, mong doi 3 '
                             '(muc luc + hinh + bang)' % n_toc)
        print('%d danh muc duoc tim thay' % n_toc)

        for i in range(doc.TablesOfContents.Count):
            doc.TablesOfContents.Item(i + 1).Update()
        doc.Fields.Update()
        doc.Repaginate()
        for i in range(doc.TablesOfContents.Count):
            doc.TablesOfContents.Item(i + 1).Update()

        removed = drop_leftover(doc)
        still = [p.Range.Text.strip() for p in doc.Paragraphs
                 if '@@TOF_' in p.Range.Text]
        if still:
            raise SystemExit('marker van con trong tai lieu sau khi xoa: %r'
                             % still[:3])
        print('da xoa %d doan marker' % removed)

        pages = doc.ComputeStatistics(2)          # wdStatisticPages
        words = doc.ComputeStatistics(0)          # wdStatisticWords
        print('so trang: %d | so tu: %d' % (pages, words))

        doc.Save()
        pdf = os.path.splitext(path)[0] + '.pdf'
        doc.ExportAsFixedFormat(pdf, 17)           # wdExportDocumentPDF
        doc.Close(False)
        print('pdf:', pdf)
        return pages
    finally:
        word.Quit()


if __name__ == '__main__':
    if not os.path.exists(sys.argv[1]):
        sys.exit('khong thay file: ' + sys.argv[1])
    main(sys.argv[1])
