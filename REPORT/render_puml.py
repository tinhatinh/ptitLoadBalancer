#!/usr/bin/env python3
"""Render cac file .puml trong figures/ thanh PNG qua PlantUML server.

In ra figures/manifest.json ghi bam sha256 cua tung cap (.puml, .png) de
nha build docx kiem tra hinh khong bi cu so voi nguon.

Dung:  python render_puml.py [ten_khong_duoi_mi] ...
"""
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
import zlib

SERVER = os.environ.get('PLANTUML_SERVER', 'http://www.plantuml.com/plantuml')
HERE = os.path.dirname(os.path.abspath(__file__))
FIGDIR = os.path.join(HERE, 'figures')

B64 = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_'


def encode(text: str) -> str:
    data = zlib.compressobj(9, zlib.DEFLATED, -15)
    comp = data.compress(text.encode('utf-8')) + data.flush()
    out = []
    for i in range(0, len(comp), 3):
        chunk = comp[i:i + 3]
        n = chunk[0] << 16
        if len(chunk) > 1:
            n |= chunk[1] << 8
        if len(chunk) > 2:
            n |= chunk[2]
        pad = 3 - len(chunk)
        for j in range(4 - pad):
            out.append(B64[(n >> (18 - 6 * j)) & 0x3F])
    return ''.join(out)


def fetch(kind: str, code: str) -> bytes:
    url = f'{SERVER}/{kind}/{code}'
    # Server plantuml.com tra ve 403 cho User-Agent mac dinh cua urllib.
    req = urllib.request.Request(
        url, headers={'User-Agent': 'Mozilla/5.0 (report-builder)'})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read()


def local_render(puml_path, png_path):
    """Fallback: dung plantuml.jar neu may co."""
    jar = os.environ.get('PLANTUML_JAR')
    if not jar or not os.path.exists(jar):
        return False
    subprocess.run(['java', '-jar', jar, '-tpng', '-o', FIGDIR, puml_path],
                   check=True, shell=False)
    return os.path.exists(png_path)


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for blk in iter(lambda: f.read(1 << 20), b''):
            h.update(blk)
    return h.hexdigest()


def main(argv):
    names = argv or sorted(
        f[:-5] for f in os.listdir(FIGDIR) if f.endswith('.puml'))
    manifest_path = os.path.join(FIGDIR, 'manifest.json')
    manifest = {}
    if os.path.exists(manifest_path):
        manifest = json.load(open(manifest_path, encoding='utf-8'))

    failed = []
    for name in names:
        puml = os.path.join(FIGDIR, name + '.puml')
        png = os.path.join(FIGDIR, name + '.png')
        if not os.path.exists(puml):
            print(f'BO QUA  {name}: khong co file nguon')
            failed.append(name)
            continue

        src = open(puml, encoding='utf-8').read()
        code = encode(src)
        try:
            svg = fetch('svg', code)
        except (urllib.error.URLError, TimeoutError) as exc:
            print(f'MANG LOI {name}: {exc}, thu render cuc bo')
            if not local_render(puml, png):
                failed.append(name)
                continue
            svg = b''

        text = svg.decode('utf-8', 'ignore')
        err = re.search(r'(Syntax Error|Error line (\d+)|cannot find)', text)
        if err:
            print(f'LOI     {name}: {err.group(0)}')
            for line in re.findall(r'<text[^>]*>([^<]*)</text>', text)[:12]:
                print('         ', line)
            failed.append(name)
            continue

        blob = fetch('png', code)
        if blob[:8] != b'\x89PNG\r\n\x1a\n':
            print(f'LOI     {name}: phoi ve khong phai PNG')
            failed.append(name)
            continue
        with open(png, 'wb') as f:
            f.write(blob)

        manifest[name] = {'puml': sha(puml), 'png': sha(png),
                          'bytes': len(blob)}
        print(f'OK      {name}.png  {len(blob) // 1024} KB')

    json.dump(manifest, open(manifest_path, 'w', encoding='utf-8'),
              indent=1, ensure_ascii=False, sort_keys=True)
    print(f'\nmanifest: {manifest_path}')
    if failed:
        print('KHONG DAT:', ', '.join(failed))
        sys.exit(1)


if __name__ == '__main__':
    main(sys.argv[1:])
