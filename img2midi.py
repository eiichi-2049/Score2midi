# -*- coding: utf-8 -*-
"""批量：乐谱图片 → MusicXML + MIDI

用法:
  python img2midi.py 图片1.png [图片2.jpg ...]
  python img2midi.py 乐谱图片\
  python img2midi.py 图片.png --out-dir "E:/乐谱转MIDI/MIDI输出"
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
import traceback
import uuid
from pathlib import Path

# 保证能 import 到同目录下的 homr 包
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "homr_gui"))

from music21 import converter  # noqa: E402
from homr.main import ProcessingConfig, process_image  # noqa: E402
from homr.music_xml_generator import XmlGeneratorArguments  # noqa: E402

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}
DEFAULT_OUT = ROOT / "MIDI输出"


def collect_images(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for p in paths:
        path = Path(p)
        if path.is_dir():
            files.extend(
                sorted(f for f in path.iterdir() if f.suffix.lower() in IMAGE_EXTS)
            )
        elif path.is_file() and path.suffix.lower() in IMAGE_EXTS:
            files.append(path)
        else:
            print(f"[跳过] 不是图片: {p}")
    # 去重
    seen = set()
    unique = []
    for f in files:
        key = str(f.resolve())
        if key not in seen:
            seen.add(key)
            unique.append(f)
    return unique


def stage_ascii(image_path: Path) -> Path:
    """OpenCV on Windows cannot open non-ASCII paths; copy to %TEMP%/score2midi first."""
    work = Path(tempfile.gettempdir()) / "score2midi"
    work.mkdir(parents=True, exist_ok=True)
    dest = work / f"{uuid.uuid4().hex[:10]}{image_path.suffix.lower() or '.png'}"
    shutil.copy2(image_path, dest)
    return dest


def convert_one(image_path: Path, out_dir: Path) -> Path | None:
    out_dir.mkdir(parents=True, exist_ok=True)
    config = ProcessingConfig(
        enable_debug=False,
        enable_cache=False,
        write_staff_positions=False,
        read_staff_positions=False,
        selected_staff=-1,
        use_gpu_inference=False,
    )
    xml_args = XmlGeneratorArguments(False, None, None)

    print(f"\n=== 识别: {image_path.name} ===")
    staged = stage_ascii(image_path)
    try:
        process_image(str(staged), config, xml_args)
        xml_path = staged.with_suffix(".musicxml")
    finally:
        staged.unlink(missing_ok=True)

    if not xml_path.exists():
        print(f"[失败] 未生成 MusicXML: {xml_path}")
        return None

    midi_path = out_dir / (image_path.stem + ".mid")
    xml_out = out_dir / (image_path.stem + ".musicxml")

    score = converter.parse(str(xml_path))
    score.write("midi", fp=str(midi_path))

    xml_out.write_bytes(xml_path.read_bytes())
    xml_path.unlink(missing_ok=True)

    # 识别谱面左侧乐器名，写回 MusicXML（名称 + GM 音色）
    try:
        from instrument_tagger import apply_instruments

        tag = apply_instruments(image_path, xml_out)
        if tag.get("updated"):
            names = ", ".join(tag.get("detected") or [])
            print(f"[乐器] 已标注 {tag['updated']} 轨: {names}")
            # MusicXML 更新后重新导出 MIDI，音色才会带过去
            score2 = converter.parse(str(xml_out))
            score2.write("midi", fp=str(midi_path))
        elif tag.get("error"):
            print(f"[乐器] 跳过标注: {tag['error']}")
        else:
            print("[乐器] 未识别到左侧乐器文字，保持默认 Piano")
    except Exception as e:  # noqa: BLE001
        print(f"[乐器] 标注失败（不影响 MIDI）: {e}")

    print(f"[成功] MIDI  → {midi_path}")
    print(f"[成功] MusicXML → {xml_out}")
    return midi_path


def main() -> int:
    parser = argparse.ArgumentParser(description="乐谱图片批量转 MIDI")
    parser.add_argument("paths", nargs="+", help="图片文件或文件夹")
    parser.add_argument(
        "--out-dir",
        default=str(DEFAULT_OUT),
        help=f"输出目录（默认: {DEFAULT_OUT}）",
    )
    args = parser.parse_args()

    images = collect_images(args.paths)
    if not images:
        print("没有找到可处理的图片。支持: " + ", ".join(sorted(IMAGE_EXTS)))
        return 1

    out_dir = Path(args.out_dir)
    print(f"共 {len(images)} 张图片，输出到: {out_dir}")

    ok = 0
    for img in images:
        try:
            if convert_one(img, out_dir):
                ok += 1
        except Exception:
            print(f"[异常] {img.name}")
            traceback.print_exc()

    print(f"\n完成: {ok}/{len(images)}")
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
