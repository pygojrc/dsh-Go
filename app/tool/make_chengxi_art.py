#!/usr/bin/env -S uv run
"""从澄汐定稿路径生成应用图标、聊天状态图集和原创装饰。"""
import json
import math
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory

APP = Path(__file__).resolve().parents[1]
BRAND = APP / "assets/brand"
RES = APP / "android/app/src/main/res"
MOON = ("M 59 30 C 56 30 53 31 50 33 C 40 39 39 53 50 60 "
        "C 57 64 65 63 71 57 C 69 63 64 67 57 69 "
        "C 44 73 31 65 31 51 C 31 38 44 27 59 30 Z")
WAVES = ("M 29 75 C 38 69 47 70 55 73 C 65 77 72 76 81 71 "
         "C 74 81 63 82 53 78 C 44 74 37 73 29 75 Z "
         "M 33 82 C 40 77 46 78 52 81 C 57 84 61 85 65 84 "
         "C 59 89 54 87 49 85 C 43 82 38 81 33 82 Z")
NIGHT = "#061844"
LIGHT = ("#173568", "#007684")
DARK = ("#FFF5DB", "#8EF1F3")
TILE = ("M 32 18 C 23 18 18 23 18 32 C 18 40 18 68 18 76 "
        "C 18 85 23 90 32 90 C 40 90 68 90 76 90 "
        "C 85 90 90 85 90 76 C 90 68 90 40 90 32 "
        "C 90 23 85 18 76 18 C 68 18 40 18 32 18 Z")
VARIANTS = {
    "": (NIGHT, NIGHT, DARK),
    "_night": ("#2C3D6C", "#0C122D", DARK),
    "_frost": ("#FCFDFF", "#DDE5F8", LIGHT),
    "_ink": ("#292B30", "#0D0E11", ("#F5F7FB", "#F5F7FB")),
}


def centered(data):
    """压进 Android 遮罩安全区，按墨迹质心校正非对称标识。"""
    offsets = iter((5, -4) * 100)
    return re.sub(r"-?\d+(?:\.\d+)?", lambda number: f"{54 + (float(number[0]) - 54) * 0.82 + next(offsets):.2f}", data)


MOON = centered(MOON)
WAVES = centered(WAVES)


def path(identifier, data, fill):
    return f'<path id="{identifier}" fill="{fill}" d="{data}"/>'


def gradient(identifier, start, end):
    return (f'<linearGradient id="{identifier}" gradientUnits="userSpaceOnUse" x1="7.57" y1="-5.87" '
            f'x2="100.43" y2="113.87"><stop offset="0" stop-color="{start}"/>'
            f'<stop offset="1" stop-color="{end}"/></linearGradient>')


def svg(box, body):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{box}">\n{body}\n</svg>\n'


def glyph(colors, generated_ids=False):
    if not generated_ids:
        return path("moon", MOON, colors[0]) + path("waves", WAVES, colors[1])
    # 沿用品牌代码生成器的图层接口，让单色和彩色轮廓完全一致。
    definitions = "".join(gradient(name, color, color) for name, color in
                          zip(("tail", "fin", "belly", "bubble"), (colors[0], colors[0], colors[0], colors[1])))
    shapes = "".join(path(name, MOON, f"url(#{fill})") for name, fill in
                     (("body", "tail"), ("fin-layer", "fin"), ("belly-layer", "belly")))
    return f"<defs>{definitions}</defs>" + shapes + path("bubble-layer", WAVES, "url(#bubble)")


def launcher():
    ink_box = "37 29 46 50"
    (BRAND / "glyph-light.svg").write_text(svg(ink_box, glyph(LIGHT, True)))
    (BRAND / "glyph-dark.svg").write_text(svg(ink_box, glyph(DARK, True)))
    (BRAND / "glyph-mono.svg").write_text(svg(ink_box, glyph(("#FFFFFF", "#FFFFFF"))))
    tile = f'<defs>{gradient("tile-bg", NIGHT, NIGHT)}</defs>' + path("tile", TILE, "url(#tile-bg)")
    (BRAND / "tile.svg").write_text(svg("18 18 72 72", tile + glyph(DARK, True)))

    background = RES / "drawable/ic_launcher_background.xml"
    background.write_text(background.read_text().replace("#FF9AB0E8", "#FF061844").replace("#FF405AAD", "#FF061844"))
    mono = RES / "drawable/ic_launcher_monochrome.xml"
    mono.write_text(f'''<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp" android:height="108dp"
    android:viewportWidth="108" android:viewportHeight="108">
    <path android:fillColor="#FFFFFFFF" android:pathData="{MOON}" />
    <path android:fillColor="#FFFFFFFF" android:pathData="{WAVES}" />
</vector>
''')
    # 通知只使用 Alpha，缩放后将同一轮廓放进 24dp 状态栏图标。
    (RES / "drawable/ic_stat_dsh.xml").write_text(f'''<?xml version="1.0" encoding="utf-8"?>
<!-- 澄汐通知图标，由 app/tool/make_chengxi_art.py 生成。 -->
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="24dp"
    android:height="24dp"
    android:viewportWidth="24"
    android:viewportHeight="24">
    <group android:pivotX="54" android:pivotY="54" android:scaleX="0.44" android:scaleY="0.44"
        android:translateX="-42" android:translateY="-42">
        <path android:fillColor="#FFFFFFFF" android:pathData="{MOON}" />
        <path android:fillColor="#FFFFFFFF" android:pathData="{WAVES}" />
    </group>
</vector>
''')
    with TemporaryDirectory() as directory:
        master = Path(directory) / "icon.svg"
        for suffix, (start, end, colors) in VARIANTS.items():
            prefix = f"ic_launcher{suffix}"
            for density, size in (("mdpi", 48), ("hdpi", 72), ("xhdpi", 96), ("xxhdpi", 144), ("xxxhdpi", 192)):
                dest = RES / f"mipmap-{density}"
                for name, shape, extent, width in (
                    (prefix, '<rect x="18" y="18" width="72" height="72" rx="12"', "18 18 72 72", size),
                    (prefix + "_round", '<circle cx="54" cy="54" r="36"', "18 18 72 72", size),
                    (prefix + "_foreground", "", "0 0 108 108", size * 108 // 48),
                ):
                    fill = f'<defs>{gradient("bg", start, end)}</defs>{shape} fill="url(#bg)"/>' if shape else ""
                    master.write_text(svg(extent, fill + glyph(colors)))
                    subprocess.run(["rsvg-convert", "-w", str(width), "-h", str(width), "-o",
                                    dest / (name + ".png"), master], check=True)


def activity():
    # 保留状态档位和时间契约，帧只绘制三个由慢到快依次高亮的圆点。
    target = APP / "assets/whale"
    manifest = target / "whale.json"
    data = json.loads(manifest.read_text())
    with TemporaryDirectory() as directory:
        work = Path(directory)
        for level in data["levels"]:
            level.pop("source", None)
            frames = []
            for i in range(level["frames"]):
                phase = i / level["frames"] * math.tau
                shapes = []
                for j, x in enumerate((32, 60, 88)):
                    wave = (1 + math.cos(phase - j * math.tau / 3)) / 2
                    radius = 6 + round(2 * wave)
                    alpha = 1 if level["frames"] == 1 else 0.35 + 0.65 * wave
                    shapes.extend(["-fill", f"rgba(255,255,255,{alpha:.3f})", "-draw", f"circle {x},48 {x + radius},48"])
                frame = work / f"{i:02}.png"
                subprocess.run(["magick", "-size", "120x96", "xc:none", *shapes, frame], check=True)
                frames.append(frame)
            subprocess.run(["magick", "montage", *frames, "-tile", "6x", "-geometry", "+0+0",
                            "-background", "none", f"PNG32:{target / level['image']}"], check=True)
    manifest.write_text(json.dumps(data, indent=2) + "\n")


def main():
    launcher()
    activity()
    subprocess.run(["magick", RES / "drawable-nodpi/companion_widget_happy.png", "-resize", "576x576",
                    APP / "assets/star/star_whale.webp"], check=True)


if __name__ == "__main__":
    main()
