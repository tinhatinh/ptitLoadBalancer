#!/usr/bin/env python3
"""Chup anh man hinh that cua tung phep do trong lab de 07.

Moi anh la mot cua so console that, chay mot lenh that, chup luc lenh da chay
xong. Khong co anh gia lap: moi pixel lay tren man hinh.

Lenh duoc ghi ra file .sh roi moi goi bash chay file do. Ly do: truyen lenh
nam trong chuoi cua PowerShell se bi PowerShell bao lai dau nhay khi chuyen
cho bash.exe, lam hong nhung lenh co dang VAR="gia tri" cmd.

Dung:  python take_shots.py             # chup het
       python take_shots.py 03 09 12    # chup mot so thu
"""
import os
import re
import shutil
import subprocess
import sys
import time

import ctypes
import win32con
import win32gui
from PIL import Image, ImageGrab

user32 = ctypes.windll.user32


def raise_window(hwnd, tries=6):
    """Windows bloock SetForegroundWindow khi goi tu tien trinh nen.

    M mo khoa bang phim Alt gia lap, sau do kiem tra that su cua so dang
    o truoc moi cho phep chup.
    """
    for _ in range(tries):
        user32.keybd_event(0x12, 0, 0, 0)          # ALT down
        user32.keybd_event(0x12, 0, 2, 0)          # ALT up
        win32gui.SetForegroundWindow(hwnd)
        win32gui.BringWindowToTop(hwnd)
        time.sleep(0.5)
        if win32gui.GetForegroundWindow() == hwnd:
            return True
        win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
        time.sleep(0.3)
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        time.sleep(0.5)
    return win32gui.GetForegroundWindow() == hwnd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, 'screenshots')
TMP = os.path.join(HERE, '_shot_tmp')


def msys_path(win_path):
    """Doi duong dan Windows thanh duong dan Git Bash (/c/...)."""
    d = re.match(r'([A-Za-z]):\\?(.*)', win_path)
    if not d:
        return win_path
    return '/' + d.group(1).lower() + '/' + d.group(2).replace('\\', '/')


SH_DIR = msys_path(TMP)


def find_bash():
    """bash.exe co the nam o cho khac tuy may. Thu bien moi truong, roi cac
    vi tri mac dinh cua Git for Windows, roi moi tim trong PATH."""
    for cand in (os.environ.get('SHOTS_BASH'),
                 r'C:\Program Files\Git\bin\bash.exe',
                 r'C:\Program Files (x86)\Git\bin\bash.exe',
                 os.path.expandvars(r'%LOCALAPPDATA%\Programs\Git\bin\bash.exe')):
        if cand and os.path.exists(cand):
            return cand
    found = shutil.which('bash')
    if found:
        return found
    sys.exit('Khong tim thay bash.exe. Dat bien moi truong SHOTS_BASH tro toi '
             'no (thuong la C:\\Program Files\\Git\\bin\\bash.exe).')


BASH = find_bash()
DOCKER_BIN = '/c/Program Files/Docker/Docker/resources/bin'
HOLD = 30

RESET_LB = ('LB_ALGO_DIRECTIVE="least_conn;" docker compose up -d '
            '--force-recreate --no-deps lb01 > /dev/null 2>&1; sleep 5')
RR_LB = ('LB_ALGO_DIRECTIVE="# round_robin: khong khai bao directive" '
         'docker compose up -d --force-recreate --no-deps lb01 > /dev/null 2>&1')

# (so, mo ta, lenh, giay cho toi da)
SHOTS = [
    ('01', 'bay container, chi lb01 co cong ngoai',
     'bash scripts/lab.sh ps', 90),
    ('02', 'mang backend la internal',
     'docker network inspect de07-web-lb-cluster_backend '
     '| grep -Ei "Name|Internal|Subnet"', 90),
    ('03', 'du header an toan va cookie phien',
     'docker compose exec -T client01 curl -sk -D - -o /dev/null '
     'https://192.168.240.10/login.php '
     '| sed -E "s/(SID=)[A-Za-z0-9]+/\\1<da-che>/g"', 120),
    ('04', 'phan phoi tuan tu round robin',
     '%s; sleep 6; docker compose exec -T client01 bash '
     '/scripts/distribute.sh 300 round_robin' % RR_LB, 300),
    ('05', 'phan phoi tuan tu least_conn, cung mot chuoi',
     'LB_ALGO_DIRECTIVE="least_conn;" docker compose up -d --force-recreate '
     '--no-deps lb01 > /dev/null 2>&1; sleep 6; docker compose exec -T client01 bash '
     '/scripts/distribute.sh 300 least_conn; %s' % RESET_LB, 300),
    ('06', 'ip_hash don toan bo ve mot node',
     'LB_ALGO_DIRECTIVE="ip_hash;" docker compose up -d --force-recreate '
     '--no-deps lb01 > /dev/null 2>&1; sleep 6; docker compose exec -T client01 bash '
     '/scripts/distribute.sh 300 ip_hash; %s' % RESET_LB, 300),
    ('07', 'do lech phan phoi 20 luong',
     'PYTHONUTF8=1 python REPORT/analyze_bench.py skew', 120),
    ('08', 'tat web02 giua vong do',
     'bash scripts/failover.sh web02 70 30', 400),
    ('09', 'log nginx cho thay chuyen node sau 504',
     'ls -la results/failover/; echo ""; '
     'grep "upstream=172.20.0.12:80, " $(ls -t results/failover/retries-*.log | head -1)',
     120),
    ('10', 'redis giu duoc phien sau khi tat node',
     'bash scripts/session_test.sh redis', 300),
    ('11', 'file mat phien sau khi tat cung node do',
     'bash scripts/session_test.sh file; %s' % RESET_LB, 300),
    ('12', 'bang kiem tra an toan 19 hang muc',
     'bash scripts/sec_check.sh', 300),
    ('13', 'ma tran 18 o thong qua',
     'PYTHONUTF8=1 python REPORT/analyze_bench.py matrix | sed -n "1,21p"', 180),
    ('14', 'suy giam khi mat mot node',
     'PYTHONUTF8=1 python REPORT/analyze_bench.py degrade', 180),
    ('20', 'welch va bac thang chi phi',
     'PYTHONUTF8=1 python REPORT/analyze_bench.py matrix | sed -n "23,45p"', 180),
    ('15', 'goi thang node tu mang ngoai khong duoc',
     'docker compose exec -T client01 curl -s -m 4 -o /dev/null '
     '-w "http_code=%{http_code}\\n" http://172.20.0.12/healthz 2>&1 '
     '| grep -v -e "What.s next" -e Gordon -e "docker ai"; '
     'echo "curl khong noi duoc den node, dung nhu thiet ke"', 120),
    ('16', 'node tu choi container khong phai load balancer',
     'docker compose exec -T web03 curl -s -m 4 -o /dev/null '
     '-w "http_code=%{http_code}\\n" http://172.20.0.12/healthz', 120),
    ('17', 'khong goi truc tiep duoc thu vien rieng',
     'docker compose exec -T client01 curl -sk -i '
     'https://192.168.240.10/lib/bootstrap.php | head -3', 120),
    ('18', 'gioi han tan suat chan request gui qua nhanh',
     'b=$(docker compose exec -T lb01 sh -c "wc -l < /var/log/nginx/probe.log" '
     '| tr -dc 0-9); docker compose exec -T client01 ab -n 200 -c 20 -q '
     'https://192.168.240.10/ratelimit-probe | grep -E "Complete requests|'
     'Failed requests|Non-2xx"; echo -n "so request nhan ma 429 trong log '
     'tham do: "; docker compose exec -T lb01 sh -c '
     '"tail -n +$((b+1)) /var/log/nginx/probe.log | grep -c status=429"', 180),
    ('19', 'ket qua tho luu trong results',
     "find results -type f -not -path 'results/_*' | sed 's|/[^/]*$||' "
     '| sort | uniq -c; echo; ls -l results/bench results/security | tail -16',
     90),
]

def sq(text):
    """Thoat mot chuoi cho vao trong dau nhay don cua bash.

    Dong echo truoc do viet kieu echo "$ cmd" nen mo mot dau nhay kep trong
    lenh (curl -w "...", grep -E "a|b") la bash dong chuoi som, an luon dong
    lenh ben duoi va chay no nhu mot lenh. Sau nay anh 15 chi con mot dong
    loi shell, anh 11 chay nham ca thuat toan.
    """
    return text.replace("'", "'\\''")


SH_TEMPLATE = """#!/usr/bin/env bash
cd '%(root)s' || exit 1
export PATH="$PATH:%(dockerbin)s"
export MSYS_NO_PATHCONV=1
export MSYS2_ARG_CONV_EXCL='*'
echo "=== %(root)s ==="
echo '%(shown)s'
echo ""
%(cmd)s
rc=$?
echo ""
echo "exit code: $rc"
"""

PS_TEMPLATE = """
$ErrorActionPreference = 'Continue'
$Host.UI.RawUI.WindowTitle = 'lb-lab-%(num)s %(desc)s'
& '%(bash)s' -lc '%(sh)s'
'DONE' | Out-File -Encoding ascii -LiteralPath '%(done)s'
Start-Sleep -Seconds %(hold)s
"""


def find_window(title, timeout=45):
    end = time.time() + timeout
    while time.time() < end:
        hwnd = win32gui.FindWindow(None, title)
        if hwnd and win32gui.IsWindowVisible(hwnd):
            return hwnd
        time.sleep(0.4)
    return None


SHOT_W = 1000          # px; khong phong to de chur chiem phan lon be ngang
SHOT_H = 1048
TERMINAL_BG = (1, 36, 86)
BG_TOL = 26


def looks_like_terminal(path):
    """Kiem anh chup dung la cua so terminal, khong phai cua so khac.

    That bai nay co that: GetForegroundWindow tra ve dung handle luc kiem tra
    nhung den luc lay pixel thi cua so khac da nam chen vao vung do, va anh
    cho ra lai la trinh duyet cua nguoi dung. Khong kiem thi anh rieng tu
    chay vao bao cao va vao both thu muc giao nop.
    """
    img = Image.open(path).convert('RGB')
    band = img.crop((0, int(img.height * 0.75), img.width, img.height))
    counts = {}
    px = band.load()
    for y in range(0, band.height, 3):
        for x in range(0, band.width, 7):
            c = px[x, y]
            counts[c] = counts.get(c, 0) + 1
    if not counts:
        return False
    bg = max(counts, key=counts.get)
    return all(abs(a - b) <= BG_TOL for a, b in zip(bg, TERMINAL_BG))


def grab_verified(hwnd, path, tries=3):
    for attempt in range(tries):
        size = grab(hwnd, path)
        if looks_like_terminal(path):
            return size, True
        print('     lan %d khong phai cua so terminal, chup lai' % (attempt + 1))
        time.sleep(1.5)
    if os.path.exists(path):
        os.remove(path)
    return None, False


def grab(hwnd, path):
    """Do cua so rong 1000 px roi chup.

    Phong to het man hinh (1936 px) khien khi chen vao 16 cm chu chi con
    khoang 4 point, in ra khong doc duoc. Hep be ngang lai giup chu to gan
    hai lan; dong dai se tu goang, do la hanh vi binh thuong cua terminal.
    """
    if not win32gui.IsWindow(hwnd):
        raise RuntimeError('cua so dong som')
    screen_h = user32.GetSystemMetrics(1)
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    time.sleep(0.4)
    win32gui.MoveWindow(hwnd, 0, 0, SHOT_W, min(SHOT_H, screen_h), True)
    time.sleep(0.8)
    if not raise_window(hwnd):
        raise RuntimeError('khong dua duoc cua so len truoc, bo qua de tranh '
                           'chup nham cua so khac')
    try:
        win32gui.SetLayeredWindowAttributes(hwnd, 0, 255, win32con.LWA_ALPHA)
    except Exception:
        pass
    time.sleep(0.5)
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    img = ImageGrab.grab(bbox=(left, top, right, bottom), all_screens=True)
    img.save(path)
    return img.size


def take(shot):
    num, desc, cmd, limit = shot
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(TMP, exist_ok=True)

    sh_path = os.path.join(TMP, 'shot-%s.sh' % num)
    done = os.path.join(TMP, 'shot-%s.done' % num)
    script = os.path.join(TMP, 'shot-%s.ps1' % num)
    for stale in (done, sh_path):
        if os.path.exists(stale):
            os.remove(stale)

    short = cmd if len(cmd) < 130 else cmd[:127] + '...'
    with open(sh_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(SH_TEMPLATE % dict(root=ROOT.replace('\\', '/'),
                                   dockerbin=DOCKER_BIN,
                                   shown=sq('$ ' + short),
                                   cmd=cmd))
    with open(script, 'w', encoding='utf-8-sig') as f:
        f.write(PS_TEMPLATE % dict(num=num, desc=desc[:40], bash=BASH,
                                   sh='%s/shot-%s.sh' % (SH_DIR, num),
                                   done=done, hold=HOLD))

    title = 'lb-lab-%s %s' % (num, desc[:40])
    subprocess.Popen(['powershell.exe', '-NoProfile', '-ExecutionPolicy',
                      'Bypass', '-File', script],
                     creationflags=subprocess.CREATE_NEW_CONSOLE)

    hwnd = find_window(title)
    if not hwnd:
        print('  LOI: mo cua so khong thanh cong (%s)' % num)
        return False

    start = time.time()
    while not os.path.exists(done) and time.time() - start < limit:
        time.sleep(1.0)
    timed_out = not os.path.exists(done)
    time.sleep(2.0)

    path = os.path.join(OUT, 'hinh-%s.png' % num)
    try:
        size, ok = grab_verified(hwnd, path)
    except Exception as exc:
        print('  LOI chup:', exc)
        ok = False
    try:
        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
    except Exception:
        pass
    time.sleep(1.2)

    if not ok:
        return False
    print('  %s %6.0f KB  %dx%d  %s%s'
          % (num, os.path.getsize(path) / 1024, size[0], size[1], desc,
             '   (QUA THOI GIAN CHO)' if timed_out else ''))
    return not timed_out


if __name__ == '__main__':
    wanted = sys.argv[1:]
    todo = [s for s in SHOTS if not wanted or s[0] in wanted]
    print('Chup %d anh. Man hinh se bi choang phia truoc tung lan, xin khong '
          'lam viec khac trong luc nay.\n' % len(todo))
    bad = []
    for i, s in enumerate(todo, 1):
        print('[%d/%d] %s' % (i, len(todo), s[1]))
        if not take(s):
            bad.append(s[0])
    print('\nxong: %d/%d' % (len(todo) - len(bad), len(todo)))
    if bad:
        print('can kiem tra lai:', ', '.join(bad))
