#!/usr/bin/env -S uv run
"""用 ImageMagick 装配小汐关键帧、状态图集及小组件静态图。"""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import json
import math
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

APP = Path(__file__).resolve().parents[1]
SOURCE = APP / "tool/pet_src/xiaoxi"
DEST = APP / "assets/pets/xiaoxi"
WIDGETS = APP / "android/app/src/main/res/drawable-nodpi"
SIDE = 128
COLS = 6
FRAMES = 12
BASELINE = 114


@dataclass(frozen=True)
class Motion:
    pose: str
    ms: int
    rise: int = 4
    sway: int = 2
    tilt: int = 3
    breathe: float = 0.03
    loop: bool = True
    effect: str = ""
    flip: bool = False


MOTIONS = {
    "idle": Motion("idle", 150, rise=5),
    "thinking": Motion("thinking", 125, tilt=6, effect="dots"),
    "working": Motion("working", 85, rise=9, sway=5, effect="ticks"),
    "juggling": Motion("working", 100, rise=8, sway=7, tilt=8, effect="orbit"),
    "sweeping": Motion("working", 115, rise=3, sway=9, tilt=7, effect="sweep"),
    "notification": Motion("notification", 110, rise=8, effect="alert"),
    "attention": Motion("attention", 100, rise=13, tilt=5, loop=False, effect="spark"),
    "error": Motion("error", 110, rise=2, sway=5, tilt=5, loop=False, effect="alert"),
    "carrying": Motion("carrying", 125, rise=4, sway=4, loop=False),
    "sleeping": Motion("sleeping", 170, rise=2, sway=0, tilt=1, effect="dots"),
    "waking": Motion("notification", 90, rise=12, tilt=4, loop=False),
    "roam": Motion("idle", 105, rise=9, sway=3, tilt=7),
    "tap-left": Motion("notification", 70, rise=7, tilt=12, loop=False),
    "tap-right": Motion("notification", 70, rise=7, tilt=12, loop=False, flip=True),
    "tickle": Motion("attention", 75, rise=11, sway=6, tilt=9, loop=False, effect="spark"),
    "drag": Motion("drag", 115, rise=2, sway=4, tilt=9),
}


def magick(*args, capture=False):
    command = ["magick"]
    if args[0] in {"identify", "montage"}:
        command.append(args[0])
        args = args[1:]
    return subprocess.run(
        [*command, "-limit", "thread", "1", *map(str, args)],
        check=True, text=True, capture_output=capture,
    ).stdout


def prepare_poses(work):
    crops = {"idle": (SOURCE / "idle.png", [])}
    for file, names in (
        ("poses-a.png", ("thinking", "working", "attention", "sleeping")),
        ("poses-b.png", ("notification", "error", "carrying", "drag")),
    ):
        sheet = SOURCE / file
        width, height = map(int, magick("identify", "-format", "%w %h", sheet, capture=True).split())
        for i, name in enumerate(names):
            w, h = width // 2, height // 2
            crops[name] = sheet, ["-crop", f"{w}x{h}+{i % 2 * w}+{i // 2 * h}", "+repage"]
    for name, (image, crop) in crops.items():
        # 清除生成图边缘的低透明噪点，再统一身体的基准高度。
        magick(image, *crop, "-channel", "A", "-level", "10%,100%", "+channel",
               "-trim", "+repage", "-resize", "98x96", work / f"pose-{name}.png")


def frame_effect(name, index):
    # 道具用简单几何图形，在小尺寸下也能区分不同状态。
    phase = index / FRAMES
    if name in {"dots", "ticks"}:
        step = 6 if name == "dots" else 8
        return " ".join(
            f"circle {84 + j * step},{12 + (index // 3 + j) % 3} {86 + j * step},{12 + (index // 3 + j) % 3}"
            for j in range(1 + index // 4)
        )
    if name == "sweep":
        x = 14 + index * 8
        return f"roundrectangle {x},114 {x + 11},117 1,1"
    if name:
        x = 101 + round(6 * math.sin(phase * math.tau)) if name == "orbit" else 101
        y = 19 + round(3 * math.sin(phase * math.tau))
        if name == "alert":
            return f"roundrectangle {x},8 {x + 3},17 1,1 circle {x + 1},21 {x + 3},21"
        return f"polygon {x},{y - 5} {x + 2},{y - 1} {x + 6},{y} {x + 2},{y + 1} {x},{y + 5} {x - 2},{y + 1} {x - 6},{y} {x - 2},{y - 1}"
    return ""


def render(name, motion, work):
    frames = []
    for index in range(FRAMES):
        phase = index / FRAMES * math.tau
        # 循环的首尾相位相邻。一次性动作回落到静止位置再交还状态机。
        impulse = (1 - math.cos(phase)) / 2
        x = round(motion.sway * math.sin(phase))
        y = round(motion.rise * impulse)
        angle = round(motion.tilt * math.sin(phase)) * (-1 if motion.flip else 1)
        resize = 100 + round(motion.breathe * 100 * impulse)
        output = work / f"{name}-{index:02}.png"
        decorate = frame_effect(motion.effect, index)
        color = "#F7BC81" if name == "error" else "#86ECF6"
        magick("-size", f"{SIDE}x{SIDE}", "xc:none", "(",
               work / f"pose-{motion.pose}.png", *(["-flop"] if motion.flip else []),
               "-resize", f"{resize}%", "-background", "none", "-rotate", angle, ")", "-gravity", "South",
               "-geometry", f"{x:+d}+{SIDE - BASELINE + y}", "-composite", "-gravity", "NorthWest",
               *(["-fill", color, "-draw", decorate] if decorate else []), output)
        frames.append(output)
    magick("montage", *frames, "-tile", f"{COLS}x", "-geometry", "+0+0", "-background", "none",
           "-define", "png:exclude-chunk=date,time", f"PNG32:{DEST / (name + '.png')}")
    return name, {
        "sheet": f"{name}.png", "frameW": SIDE, "frameH": SIDE, "cols": COLS,
        "box": {"x": 0, "y": 0, "w": SIDE, "h": SIDE}, "loop": motion.loop,
        "frames": [{"i": i, "ms": motion.ms} for i in range(FRAMES)],
    }


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory() as directory:
        work = Path(directory)
        prepare_poses(work)
        with ThreadPoolExecutor(max_workers=6) as pool:
            animations = dict(pool.map(lambda item: render(*item, work), MOTIONS.items()))
        for state, pose in (("idle", "idle"), ("happy", "attention"), ("sleeping", "sleeping")):
            magick(work / f"pose-{pose}.png", "-gravity", "center", "-background", "none", "-extent", "112x112",
                   "-define", "png:exclude-chunk=date,time", f"PNG32:{WIDGETS / ('companion_widget_' + state + '.png')}")
    states = {name: [name] for name in list(MOTIONS)[:12]}
    body = {"x": 16, "y": 16, "w": 96, "h": 98}
    pack = {
        "schema": 1, "id": "xiaoxi", "name": "小汐", "author": "澄汐项目",
        "license": "澄汐项目原创桌宠素材，随澄汐分发",
        "source": "按用户授权参考图的夜海配色生成原创关键帧，并装配为状态动画",
        "pixelArt": False, "scale": 1, "canvas": {"w": SIDE, "h": SIDE},
        "anchor": {"x": SIDE // 2, "baseline": BASELINE}, "contentBox": body,
        "hitBoxes": {"default": {"x": 12, "y": 10, "w": 104, "h": 104}},
        "animations": animations, "states": states,
        "timings": {"minDisplay": {"attention": 1200, "error": 1320, "notification": 1320, "carrying": 1500},
                    "autoReturn": {"attention": 1200, "error": 1320, "carrying": 1500}, "wakeMs": 1080},
        "roam": {"anim": "roam", "faces": "left"},
        "sleep": {"afterMs": 60000},
        "reactions": {"tapLeft": "tap-left", "tapRight": "tap-right", "tickle": "tickle", "drag": "drag"},
    }
    (DEST / "pack.json").write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
