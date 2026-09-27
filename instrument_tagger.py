# -*- coding: utf-8 -*-
"""从谱面左侧文字识别乐器名，并写回 MusicXML（名称 + GM 音色）。

HOMR 默认把所有声部标成 Piano；本模块在生成 MusicXML 后打补丁。
OpenCV 在 Windows 中文路径下不可靠，OCR 前先把图拷到临时英文目录。
"""

from __future__ import annotations

import re
import shutil
import tempfile
import uuid
from pathlib import Path

# MusicXML <midi-program> 为 1-based（1 = GM Piano）
# 键为识别到的规范化名字
GM = {
    "piano": (1, "keyboard.piano"),
    "harpsichord": (7, "keyboard.harpsichord"),
    "celesta": (9, "keyboard.celesta"),
    "glockenspiel": (10, "metal.glockenspiel"),
    "vibraphone": (12, "metal.vibraphone"),
    "marimba": (13, "wood.marimba"),
    "tubular bells": (15, "metal.tubular-bells"),
    "accordion": (22, "wind.reed-accordion"),
    "harmonica": (23, "wind.reed-harmonica"),
    "nylon guitar": (25, "pluck.guitar-nylon"),
    "acoustic guitar": (26, "pluck.guitar-steel"),
    "electric guitar": (28, "pluck.guitar-jazz"),
    "jazz guitar": (27, "pluck.guitar-jazz"),
    "clean guitar": (28, "pluck.guitar-clean"),
    "muted guitar": (29, "pluck.guitar-muted"),
    "overdriven guitar": (30, "pluck.guitar-overdriven"),
    "distortion guitar": (31, "pluck.guitar-distortion"),
    "acoustic bass": (33, "pluck.acoustic-bass"),
    "electric bass": (34, "pluck.electric-bass"),
    "fingered bass": (34, "pluck.electric-bass"),
    "picked bass": (35, "pluck.electric-bass-picked"),
    "fretless bass": (36, "pluck.bass-fretless"),
    "slap bass": (37, "pluck.bass-slap"),
    "synth bass": (39, "synth-bass.synth-bass-1"),
    "violin": (41, "strings.violin"),
    "viola": (42, "strings.viola"),
    "cello": (43, "strings.cello"),
    "contrabass": (44, "strings.contrabass"),
    "double bass": (44, "strings.contrabass"),
    "string ensemble": (49, "ensemble.string-ensemble-1"),
    "strings": (49, "ensemble.string-ensemble-1"),
    "string orchestra": (49, "ensemble.string-ensemble-1"),
    "slow strings": (50, "ensemble.string-ensemble-2"),
    "synth strings": (51, "ensemble.synth-strings-1"),
    "choir aahs": (53, "voice.choir-aahs"),
    "voice oohs": (54, "voice.voice-oohs"),
    "synth voice": (55, "voice.synth-voice"),
    "orchestra hit": (56, "ensemble.orchestra-hit"),
    "trumpet": (57, "brass.trumpet"),
    "trombone": (58, "brass.trombone"),
    "bass trombone": (58, "brass.trombone"),
    "alto trombone": (58, "brass.trombone"),
    "contrabass trombone": (58, "brass.trombone"),
    "tuba": (59, "brass.tuba"),
    "muted trumpet": (60, "brass.muted-trumpet"),
    "french horn": (61, "brass.french-horn"),
    "horn": (61, "brass.french-horn"),
    "brass section": (62, "brass.brass-section"),
    "brass": (62, "brass.brass-section"),
    "synth brass": (63, "brass.synth-brass-1"),
    "soprano sax": (65, "reed.soprano-sax"),
    "alto sax": (66, "reed.alto-sax"),
    "tenor sax": (67, "reed.tenor-sax"),
    "baritone sax": (68, "reed.baritone-sax"),
    "sax": (66, "reed.alto-sax"),
    "saxophone": (66, "reed.alto-sax"),
    "oboe": (69, "reed.oboe"),
    "english horn": (70, "reed.english-horn"),
    "bassoon": (71, "reed.bassoon"),
    "clarinet": (72, "reed.clarinet"),
    "piccolo": (73, "flute.piccolo"),
    "flute": (74, "flute.flute"),
    "recorder": (75, "flute.recorder"),
    "pan flute": (76, "flute.pan-flute"),
    "bottle blow": (77, "flute.bottle-blow"),
    "shakuhachi": (78, "flute.shakuhachi"),
    "whistle": (79, "flute.whistle"),
    "ocarina": (80, "flute.ocarina"),
    "square lead": (81, "lead.square"),
    "saw lead": (82, "lead.sawtooth"),
    "calliope lead": (83, "lead.calliope"),
    "chiff lead": (84, "lead.chiff"),
    "charang lead": (85, "lead.charang"),
    "voice lead": (86, "lead.voice"),
    "fifths lead": (87, "lead.fifths"),
    "bass and lead": (88, "lead.bass-and-lead"),
    "pad new age": (89, "pad.new-age"),
    "pad warm": (90, "pad.warm"),
    "pad polysynth": (91, "pad.polysynth"),
    "pad choir": (92, "pad.choir"),
    "pad bowed": (93, "pad.bowed"),
    "pad metallic": (94, "pad.metallic"),
    "pad halo": (95, "pad.halo"),
    "pad sweep": (96, "pad.sweep"),
    "rain": (97, "fx.rain"),
    "soundtrack": (98, "fx.soundtrack"),
    "crystal": (99, "fx.crystal"),
    "atmosphere": (100, "fx.atmosphere"),
    "brightness": (101, "fx.brightness"),
    "goblins": (102, "fx.goblins"),
    "echoes": (103, "fx.echoes"),
    "sci-fi": (104, "fx.sci-fi"),
    "sitar": (105, "pluck.sitar"),
    "banjo": (106, "pluck.banjo"),
    "shamisen": (107, "pluck.shamisen"),
    "koto": (108, "pluck.koto"),
    "kalimba": (109, "pluck.kalimba"),
    "bagpipe": (110, "pipe.bagpipe"),
    "fiddle": (111, "strings.fiddle"),
    "shanai": (112, "reed.shanai"),
    "tinkle bell": (113, "metal.tinkle-bell"),
    "agogo": (114, "percussion.agogo"),
    "steel drums": (115, "percussion.steel-drums"),
    "woodblock": (116, "wood.woodblock"),
    "taiko drum": (117, "percussion.taiko-drum"),
    "melodic tom": (118, "percussion.melodic-tom"),
    "synth drum": (119, "percussion.synth-drum"),
    "reverse cymbal": (120, "percussion.reverse-cymbal"),
    "guitar fret noise": (121, "seashore.guitar-fret-noise"),
    "breath noise": (122, "seashore.breath-noise"),
    "seashore": (123, "seashore.seashore"),
    "bird tweet": (124, "bird.bird-tweet"),
    "telephone ring": (125, "telephone.telephone-ring"),
    "helicopter": (126, "helicopter.helicopter"),
    "applause": (127, "applause.applause"),
    "gunshot": (128, "gunshot.gunshot"),
    "timpani": (48, "percussion.timpani"),
    "kettledrums": (48, "percussion.timpani"),
    "timp": (48, "percussion.timpani"),
    "drum": (1, "percussion.drums"),
    "drums": (1, "percussion.drums"),
    "percussion": (1, "percussion.drums"),
}

# 常见缩写 / 别名 → 规范名
ALIASES = {
    "hn": "horn",
    "hrn": "horn",
    "f horn": "french horn",
    "french hn": "french horn",
    "tpt": "trumpet",
    "tpt.": "trumpet",
    "tbn": "trombone",
    "tbn.": "trombone",
    "b tbn": "bass trombone",
    "btb": "bass trombone",
    "bass tbn": "bass trombone",
    "tba": "tuba",
    "tba.": "tuba",
    "tb": "tuba",
    "timp": "timpani",
    "timp.": "timpani",
    "kettledrums": "timpani",
    "pno": "piano",
    "pno.": "piano",
    "pf": "piano",
    "pianoforte": "piano",
    "acc": "accordion",
    "ob": "oboe",
    "bcl": "bass clarinet",
    "cl": "clarinet",
    "fl": "flute",
    "picc": "piccolo",
    "vn": "violin",
    "vln": "violin",
    "va": "viola",
    "vc": "cello",
    "cb": "contrabass",
    "db": "double bass",
    "el gtr": "electric guitar",
    "e gtr": "electric guitar",
    "gtr": "acoustic guitar",
    "e bass": "electric bass",
    "el bass": "electric bass",
    "bass trombone": "bass trombone",
}

# 进一步把长名归并到 GM 键
for _k in list(ALIASES.values()):
    if _k not in GM:
        # 尝试去掉修饰词
        for _cand in (_k, _k.split()[-1]):
            if _cand in GM:
                ALIASES[_k] = _cand
                break


def _norm_instrument(raw: str) -> str | None:
    s = re.sub(r"[^a-zA-Z0-9]+", " ", raw).strip().lower()
    s = re.sub(r"\s+", " ", s)
    if not s or len(s) < 2:
        return None
    # 去掉前导编号 1 2 I II
    s = re.sub(r"^(i{1,3}|iv|v|[1-9])\s+", "", s)
    if s in GM:
        return s
    if s in ALIASES:
        return ALIASES[s]
    # 含关键词
    for key in sorted(GM.keys(), key=len, reverse=True):
        if key in s or s in key:
            return key
    for a, canon in ALIASES.items():
        if a in s:
            return canon
    return None


def _stage_ascii(image_path: Path) -> Path:
    work = Path(tempfile.gettempdir()) / "score2midi"
    work.mkdir(parents=True, exist_ok=True)
    dest = work / f"{uuid.uuid4().hex[:10]}_ocr{image_path.suffix.lower() or '.png'}"
    shutil.copy2(image_path, dest)
    return dest


def detect_instruments(image_path: Path) -> list[dict]:
    """OCR 谱面左侧，按上→下返回 [{raw, name, program, sound, y}]。"""
    try:
        import cv2
        from rapidocr import RapidOCR
    except Exception:
        return []

    staged = _stage_ascii(image_path)
    try:
        img = cv2.imread(str(staged))
        if img is None:
            return []
        h, w = img.shape[:2]
        # 左侧约 22% 宽度（乐器名区域）
        left = img[:, : max(80, int(w * 0.22))].copy()
        # 轻度放大提高 OCR 稳定度
        left = cv2.resize(left, None, fx=1.3, fy=1.3, interpolation=cv2.INTER_CUBIC)

        ocr = RapidOCR()
        result = ocr(left)

        # 兼容 RapidOCR 3.x (RapidOCROutput) 与旧版 tuple
        boxes = txts = scores = None
        if hasattr(result, "txts"):
            boxes, txts, scores = result.boxes, result.txts, result.scores
        elif isinstance(result, (tuple, list)) and result:
            first = result[0]
            if first is None:
                return []
            if isinstance(first, (tuple, list)) and len(first) >= 3:
                boxes, txts, scores = first[0], first[1], first[2]
            elif hasattr(first, "txts"):
                boxes, txts, scores = first.boxes, first.txts, first.scores

        if not txts:
            return []

        items = []
        for box, txt, score in zip(boxes, txts, scores):
            if score is not None and float(score) < 0.4:
                continue
            name = _norm_instrument(str(txt))
            if not name:
                continue
            pts = box if hasattr(box, "__len__") else []
            ys = [float(p[1]) for p in pts] if len(pts) else [0.0]
            xs = [float(p[0]) for p in pts] if len(pts) else [0.0]
            y = sum(ys) / len(ys) / 1.3  # 还原缩放
            x = sum(xs) / len(xs) / 1.3
            program, sound = GM.get(name, (1, "keyboard.piano"))
            items.append(
                {
                    "raw": str(txt).strip(),
                    "name": name,
                    "program": program,
                    "sound": sound,
                    "y": y,
                    "x": x,
                    "score": float(score or 0),
                }
            )

        # 按 y 排序；同一水平线去重（保留更高分）
        items.sort(key=lambda d: (d["y"], d["x"]))
        dedup: list[dict] = []
        for it in items:
            if dedup and abs(dedup[-1]["y"] - it["y"]) < 28:
                if it["score"] > dedup[-1]["score"]:
                    dedup[-1] = it
                continue
            dedup.append(it)
        return dedup
    finally:
        staged.unlink(missing_ok=True)


def patch_musicxml_instruments(xml_path: Path, instruments: list[dict]) -> dict:
    """把识别到的乐器写进 part-list（按 part 顺序自上而下对齐）。"""
    import xml.etree.ElementTree as ET

    tree = ET.parse(str(xml_path))
    root = tree.getroot()

    # MusicXML 无命名空间（homr 输出为无 ns 的 score-partwise）
    score_parts = root.findall("./part-list/score-part")
    if not score_parts:
        return {"updated": 0, "instruments": instruments}

    n = min(len(score_parts), len(instruments)) if instruments else 0
    updated = 0
    for i, sp in enumerate(score_parts):
        if i < n:
            inst = instruments[i]
            # 显示名优先用谱面原文，否则用规范化名
            raw = (inst.get("raw") or "").strip()
            pretty = raw if raw else inst["name"]
            pretty = pretty if raw else " ".join(
                w.capitalize() if w != "and" else w for w in inst["name"].split()
            )
            program, sound = inst["program"], inst["sound"]
        else:
            pretty = "Piano"
            program, sound = 1, "keyboard.piano"

        pn = sp.find("part-name")
        if pn is None:
            pn = ET.SubElement(sp, "part-name")
        pn.text = pretty

        # 清掉旧 instrument 块
        for tag in ("score-instrument", "midi-instrument"):
            for old in sp.findall(tag):
                sp.remove(old)

        si_id = f"{sp.get('id')}-I1"
        si = ET.SubElement(sp, "score-instrument", {"id": si_id})
        ET.SubElement(si, "instrument-name").text = pretty
        ET.SubElement(si, "instrument-sound").text = sound

        mi = ET.SubElement(sp, "midi-instrument", {"id": si_id})
        ET.SubElement(mi, "midi-channel").text = str(i + 1)
        ET.SubElement(mi, "midi-program").text = str(program)
        ET.SubElement(mi, "volume").text = "100"
        ET.SubElement(mi, "pan").text = "0"
        updated += 1

    tree.write(str(xml_path), encoding="utf-8", xml_declaration=True)
    return {"updated": updated, "instruments": instruments[:n]}


def apply_instruments(image_path: Path, xml_path: Path) -> dict:
    """识别乐器并打补丁；失败时保持 Piano 不阻断主流程。"""
    try:
        instruments = detect_instruments(image_path)
        info = patch_musicxml_instruments(xml_path, instruments)
        info["detected"] = [i["raw"] + "→" + i["name"] for i in instruments]
        return info
    except Exception as e:  # noqa: BLE001
        return {"updated": 0, "instruments": [], "error": str(e)}
