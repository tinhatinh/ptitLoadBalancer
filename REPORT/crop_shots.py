#!/usr/bin/env python3
"""Cat phan nen trang cua anh chup console va dua ve kich thuoc doc duoc.

Anh goc 1936x1048 nhung chi co vai dong chu o dinh, nen phia duoi la nen
tom xanh. De nguyen thi mot anh chiem ca trang ma van khong doc ra chu.

Dung:  python crop_shots.py
"""
import os

from PIL import Image, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'screenshots')
DST = os.path.join(HERE, 'figures')
PAD = 14
MIN_CONTRAST = 28
MIN_BRIGHT = 110
EDGE_BOTTOM = 28       # nhiem thanh taskbar lo ra duoi cua so chup
EDGE_RIGHT = 18        # thanh cuon cua Windows Terminal
# Mot dong chua chu thi co hang tram diem anh khac nen; mot dai lo ra o vien
# (bieu tuong man hinh, thanh cua so) chi vai chuc. Nguong dong ngan cac dai
# do git khung noi dung mo rong het chieu cao anh.
MIN_ROW_PIX = 40
# Hai gia tri duoi day phai khop build_docx.py (MAX_FIG_WIDTH_CM va
# MAX_FIG_HEIGHT_CM). Truoc day o day ghi 16 cm va 24 cm trong khi bai dung
# that cat ve 15 cm va canh cao 16 cm, nen chieu cao in ra o day luon lon hon
# chieu cao trong tai lieu va canh bao "hinh cao qua" khong bao gio bat duoc.
CONTENT_W_CM = 15.0
# Anh cao hon chieu cao van ban thi bi ep theo chieu cao, khong con theo ty le
# do rong; do la luc can xem lai anh.
MAX_HEIGHT_CM = 16.0


def background_color(img):
    """Mau nen la mau pho bien o 25% duoi anh, noi khong co chu.

    Khong lay mau goc: goc tren cua anh chup cua so Windows Terminal la thanh
    tieu de mau xam, khong phai nen xanh cua terminal.
    """
    band = img.crop((0, int(img.height * 0.75), img.width, img.height))
    counts = {}
    px = band.load()
    for y in range(0, band.height, 3):
        for x in range(0, band.width, 7):
            c = px[x, y]
            counts[c] = counts.get(c, 0) + 1
    return max(counts, key=counts.get)


def max_channel_diff(a, b):
    return max(abs(x - y) for x, y in zip(a, b))


def row_span(mask):
    """Khung noi dung dua theo mat do diem anh tung dong.

    getbbox() chi can MOT diem anh o goc duoi cung la mo khung ra het anh.
    Tren may nay thi luc nao cung co vai bieu tuong man hinh lo ra o vien
    trai, nen dung nguong: dong phai chua du nhieu diem noi dung thi moi
    duoc tinh la chu.
    """
    w, h = mask.size
    px = mask.load()
    rows = [y for y in range(h)
            if sum(1 for x in range(0, w, 2) if px[x, y]) * 2 >= MIN_ROW_PIX]
    if not rows:
        return None
    top, bottom = rows[0], rows[-1]
    cols = [x for x in range(w)
            if any(px[x, y] for y in range(top, bottom + 1, 2))]
    if not cols:
        return None
    return min(cols), top, max(cols), bottom


def crop(img):
    """Cat bo nen toi va vi trong suot cua cua so Windows.

    Vi trong suot duoc capture thanh dai mau den chay suot chieu cao anh, nen
    chi dem la noi dung nhung pixel vua lech khoi nen vua sang. Neu khong thi
    dai den do git bbox mo rong het anh va khong cat duoc gi.
    """
    img = img.convert('RGB')
    bg = Image.new('RGB', img.size, background_color(img))
    diff = ImageChops.difference(img, bg).convert('L')
    bright = img.convert('L')

    diff_mask = diff.point(lambda v: 255 if v > MIN_CONTRAST else 0)
    bright_mask = bright.point(lambda v: 255 if v > MIN_BRIGHT else 0)
    mask = ImageChops.darker(diff_mask, bright_mask)

    # Thanh taskbar lo ra duoi cua so va thanh cuon ben phai deu la "sang"
    # nen phai xoa khoi mask truoc khi tim khung noi dung.
    from PIL import ImageDraw
    ImageDraw.Draw(mask).rectangle(
        [0, max(0, img.height - EDGE_BOTTOM), img.width, img.height], fill=0)
    ImageDraw.Draw(mask).rectangle(
        [max(0, img.width - EDGE_RIGHT), 0, img.width, img.height], fill=0)

    box = row_span(mask)
    if not box:
        box = mask.getbbox()
    if not box:
        box = diff_mask.getbbox()
    if not box:
        return None
    left, top, right, bottom = box
    left = max(0, left - PAD)
    top = max(0, top - PAD)
    right = min(img.width, right + PAD)
    bottom = min(img.height, bottom + PAD)
    return img.crop((left, top, right, bottom))


def main():
    os.makedirs(DST, exist_ok=True)
    rows = []
    for name in sorted(os.listdir(SRC)):
        if not name.endswith('.png'):
            continue
        src = os.path.join(SRC, name)
        out = os.path.join(DST, 'anh-' + name)
        img = Image.open(src)
        cropped = crop(img)
        if cropped is None:
            print('BO QUA %s: khong co noi dung' % name)
            continue
        cropped.save(out)
        w, h = cropped.size
        # Ty le cao/rong quyet dinh anh chen vao bao cao chiem bao nhieu cm
        # khi gia nguyen do rong van ban.  Cung gia tri nay phai duoc luu vao
        # rows de canh ben duoi so voi nguong cm: truoc day no luu h/16 (mot
        # con so khac han) nen canh khong bao gio chay duoc.
        height_cm = round(h * CONTENT_W_CM / w, 1)
        rows.append((name, img.size, cropped.size, height_cm))
        print('  %-14s %sx%s -> %sx%s   cao khi chen o %scm: %s cm'
              % (name, img.size[0], img.size[1], w, h,
                 int(CONTENT_W_CM), height_cm))

    tall = [r for r in rows if r[3] > MAX_HEIGHT_CM]
    if tall:
        print('\nAnh cao hon %s cm khi chen o %s cm (se chiem het mot trang '
              'trong bao cao):' % (MAX_HEIGHT_CM, int(CONTENT_W_CM)))
        for name, _full, size, height_cm in tall:
            print('  %-14s %sx%s  cao %s cm' % (name, size[0], size[1],
                                                height_cm))


if __name__ == '__main__':
    main()
