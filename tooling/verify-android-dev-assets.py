#!/usr/bin/env python3
"""核对签名 APK 中的品牌素材和 GitHub 源码归档。"""

import argparse
from pathlib import Path
import re
import subprocess
import tarfile
import xml.etree.ElementTree as ET
from zipfile import ZipFile, is_zipfile

ROOT = Path(__file__).resolve().parents[1]
ANDROID = ROOT / 'app/android/app/src/main/res/drawable'
ANDROID_NS = '{http://schemas.android.com/apk/res/android}'


def verify_apk(apk, aapt2):
    """核对实际编译的通知和主题图标，以及桌宠和聊天资源。"""
    resources = subprocess.check_output([aapt2, 'dump', 'resources', apk], text=True)
    for resource in ('ic_stat_dsh', 'ic_launcher_monochrome'):
        match = re.search(rf'drawable/{resource}\n\s+\(\) \(file\) (\S+)', resources)
        if match is None:
            raise SystemExit(f'APK 缺少 drawable/{resource}')
        compiled = subprocess.check_output([aapt2, 'dump', 'xmltree', apk, '--file', match[1]], text=True)
        expected = [p.attrib[ANDROID_NS + 'pathData'] for p in ET.parse(ANDROID / f'{resource}.xml').iter('path')]
        if re.findall(r'android:pathData\([^)]*\)="([^"]+)"', compiled) != expected:
            raise SystemExit(f'APK 的 {resource} 路径与澄汐源码不一致')

    with ZipFile(apk) as archive:
        names = set(archive.namelist())
        for folder in ('pets', 'whale', 'star'):
            prefix = f'assets/flutter_assets/assets/{folder}/'
            base = ROOT / 'app/assets' / folder
            source = base / 'xiaoxi' if folder == 'pets' else base
            expected = {prefix + path.relative_to(base).as_posix(): path for path in source.rglob('*') if path.is_file()}
            included = {name for name in names if name.startswith(prefix) and not name.endswith('/')}
            if not expected or included != expected.keys():
                raise SystemExit(f'APK 的 {folder} 资源清单不一致')
            for name, path in expected.items():
                if archive.read(name) != path.read_bytes():
                    raise SystemExit(f'APK 的 {name} 资源内容不一致')
        if any(name.startswith('assets/flutter_assets/assets/companion/') and name.endswith('.zip') for name in names):
            raise SystemExit('APK 仍含预装的 Live2D 素材包')


def verify_source(path):
    """比较 GitHub 归档内容清单与发布提交的 git archive。"""
    if is_zipfile(path):
        with ZipFile(path) as archive:
            hosted = {name.split('/', 1)[1] for name in archive.namelist() if not name.endswith('/')}
    else:
        with tarfile.open(path) as archive:
            hosted = {member.name.split('/', 1)[1] for member in archive if not member.isdir()}
    with subprocess.Popen(['git', 'archive', 'HEAD'], cwd=ROOT, stdout=subprocess.PIPE) as git:
        with tarfile.open(fileobj=git.stdout, mode='r|') as archive:
            expected = {member.name for member in archive if not member.isdir()}
        if git.wait():
            raise SystemExit('本地 git archive 失败')
    if hosted != expected:
        raise SystemExit(f'{path} 与 git archive 不一致：多出 {sorted(hosted - expected)[:10]}，缺少 {sorted(expected - hosted)[:10]}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='kind', required=True)
    apk = sub.add_parser('apk')
    apk.add_argument('path', type=Path)
    apk.add_argument('aapt2', type=Path)
    source = sub.add_parser('source')
    source.add_argument('paths', type=Path, nargs='+')
    args = parser.parse_args()
    if args.kind == 'apk':
        verify_apk(args.path, args.aapt2)
        print(f'APK 素材核对通过：{args.path}')
    else:
        for path in args.paths:
            verify_source(path)
            print(f'源码归档核对通过：{path}')


if __name__ == '__main__':
    main()
