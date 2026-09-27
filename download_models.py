# -*- coding: utf-8 -*-
"""预下载 HOMR 全部模型（断点续传 + 多镜像重试）。"""
from __future__ import annotations

import sys
import time
import zipfile
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
HOMR = ROOT / "homr_gui"
sys.path.insert(0, str(HOMR))

from homr.segmentation.config import segnet_path_onnx, segnet_path_onnx_fp16  # noqa: E402
from homr.transformer.configs import default_config  # noqa: E402

BASE_RELEASE = "https://github.com/liebharc/homr/releases/download/onnx_checkpoints"
MIRRORS = [
    BASE_RELEASE,
    "https://ghproxy.net/https://github.com/liebharc/homr/releases/download/onnx_checkpoints",
    "https://ghfast.top/https://github.com/liebharc/homr/releases/download/onnx_checkpoints",
    "https://gh-proxy.com/https://github.com/liebharc/homr/releases/download/onnx_checkpoints",
    "https://cdn.ghproxy.cc/https://github.com/liebharc/homr/releases/download/onnx_checkpoints",
]

CPU_MODELS = [
    segnet_path_onnx,
    default_config.filepaths.encoder_path,
    default_config.filepaths.decoder_path,
]
GPU_MODELS = [
    segnet_path_onnx_fp16,
    default_config.filepaths.encoder_path_fp16,
    default_config.filepaths.decoder_path_fp16,
]

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 Score2MIDI-Portable"})


def zip_name_for(model_path: str) -> str:
    return Path(model_path).name.split(".")[0] + ".zip"


def download_resumable(url: str, dest: Path, rounds: int = 8) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")

    for attempt in range(1, rounds + 1):
        existing = part.stat().st_size if part.exists() else 0
        headers = {}
        if existing:
            headers["Range"] = f"bytes={existing}-"
        try:
            with SESSION.get(url, stream=True, timeout=(30, 180), headers=headers) as r:
                if r.status_code == 416:
                    # 已下完
                    part.rename(dest)
                    return dest
                if r.status_code not in (200, 206):
                    print(f"  [{attempt}/{rounds}] HTTP {r.status_code}")
                    time.sleep(2)
                    continue

                # 服务器不支持 Range 时从头下
                mode = "ab" if r.status_code == 206 and existing else "wb"
                if mode == "wb":
                    existing = 0

                total = int(r.headers.get("content-length", 0))
                if r.status_code == 206 and total:
                    total += existing
                elif r.status_code == 200:
                    total = int(r.headers.get("content-length", 0))

                done = existing
                last_print = 0
                with open(part, mode) as f:
                    for chunk in r.iter_content(1024 * 256):
                        if not chunk:
                            continue
                        f.write(chunk)
                        done += len(chunk)
                        if done - last_print >= 1024 * 1024 * 4:
                            last_print = done
                            if total:
                                print(f"  {done // (1024*1024)}/{total // (1024*1024)} MB ({100*done//total}%)")
                            else:
                                print(f"  {done // (1024*1024)} MB")

                if total and done < total - 1024:
                    print(f"  [{attempt}/{rounds}] 不完整 {done}/{total}，续传…")
                    time.sleep(1)
                    continue

                part.replace(dest)
                print(f"[完成] {dest.name} {dest.stat().st_size // (1024*1024)} MB")
                return dest
        except Exception as e:  # noqa: BLE001
            print(f"  [{attempt}/{rounds}] {type(e).__name__}: {e}")
            time.sleep(1.5)

    raise RuntimeError(f"下载失败: {url}")


def download_one(zip_name: str, dest_dir: Path) -> Path:
    out = dest_dir / zip_name
    if out.exists() and out.stat().st_size > 1024 * 100:
        print(f"[跳过] {out.name} 已存在")
        return out

    last_err = None
    for base in MIRRORS:
        url = f"{base}/{zip_name}"
        print(f"[下载] {url}")
        try:
            return download_resumable(url, out)
        except Exception as e:  # noqa: BLE001
            last_err = e
            print(f"  镜像失败: {e}")
            time.sleep(1)
    raise RuntimeError(f"所有镜像失败 {zip_name}: {last_err}")


def unzip_model(zip_path: Path, model_path: str) -> None:
    dest_dir = Path(model_path).parent
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = [n for n in zf.namelist() if not n.endswith("/")]
        print(f"  zip 内容: {names}")
        onnx_members = [n for n in names if n.lower().endswith(".onnx")]
        if onnx_members:
            # 优先精确同名，否则第一个 onnx
            target_name = Path(model_path).name
            member = next((n for n in onnx_members if Path(n).name == target_name), onnx_members[0])
            data = zf.read(member)
            Path(model_path).write_bytes(data)
            print(f"  解压 → {Path(model_path).name} ({len(data) // (1024*1024)} MB)")
        else:
            zf.extractall(dest_dir)
            print(f"  整包解压到 {dest_dir}")


def ensure_models(models: list[str]) -> None:
    for model in models:
        model_path = Path(model)
        if model_path.exists() and model_path.stat().st_size > 1024 * 100:
            print(f"[就绪] {model_path.name}")
            continue
        zname = zip_name_for(str(model))
        candidates = [zname]
        if zname.endswith("_fp16.zip"):
            candidates.append(zname.replace("_fp16.zip", ".zip"))
        dest_dir = model_path.parent
        zip_path = None
        err = None
        for cand in candidates:
            try:
                zip_path = download_one(cand, dest_dir)
                break
            except Exception as e:  # noqa: BLE001
                err = e
                print(f"  尝试 {cand} 失败: {e}")
        if zip_path is None:
            raise RuntimeError(f"无法下载 {zname}: {err}")
        unzip_model(zip_path, str(model))
        try:
            zip_path.unlink()
        except OSError:
            pass


def ensure_ocr() -> None:
    print("[OCR] 初始化 RapidOCR 权重…")
    from homr.title_detection import download_ocr_weights

    download_ocr_weights(False)
    print("[OCR] CPU 完成")


def main() -> int:
    print("=== CPU 模型 ===")
    ensure_models(CPU_MODELS)
    print("=== GPU(fP16) 模型（可选） ===")
    try:
        ensure_models(GPU_MODELS)
    except Exception as e:  # noqa: BLE001
        print(f"GPU 模型失败可忽略: {e}")
    print("=== OCR ===")
    try:
        ensure_ocr()
    except Exception as e:  # noqa: BLE001
        print(f"OCR 失败可稍后再试: {e}")
    print("\nALL_MODELS_READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
