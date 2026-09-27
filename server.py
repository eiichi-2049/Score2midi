# -*- coding: utf-8 -*-
"""乐谱转 MIDI · 本地服务（可携带版）

提供网页 GUI：拖拽图片 → 生成 MusicXML + MIDI。
仅监听 127.0.0.1，不对外网开放。
"""
from __future__ import annotations

import json
import mimetypes
import os
import queue
import re
import shutil
import sys
import tempfile
import threading
import time
import traceback
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

ROOT = Path(__file__).resolve().parent
HOMR_DIR = ROOT / "homr_gui"
WEB_DIR = ROOT / "web"
UPLOAD_DIR = ROOT / "上传"
OUTPUT_DIR = ROOT / "输出"
CLI_PY = ROOT / "img2midi.py"

sys_path_set = False


def setup_sys_path() -> None:
    global sys_path_set
    if not sys_path_set:
        import sys

        sys.path.insert(0, str(HOMR_DIR))
        sys_path_set = True


# 任务队列（串行识别，避免显存/内存打满）
JOB_LOCK = threading.Lock()
JOBS: dict[str, dict] = {}
JOB_ORDER: list[str] = []
WORKER_BUSY = threading.Event()


def new_job(filename: str, saved_path: Path) -> str:
    job_id = uuid.uuid4().hex[:12]
    with JOB_LOCK:
        JOBS[job_id] = {
            "id": job_id,
            "filename": filename,
            "status": "queued",  # queued | running | done | error
            "message": "排队中",
            "image": saved_path.name,
            "image_path": str(saved_path),
            "midi": None,
            "musicxml": None,
            "error": None,
            "created": time.time(),
        }
        JOB_ORDER.append(job_id)
    return job_id


def set_job(job_id: str, **kwargs) -> None:
    with JOB_LOCK:
        JOBS[job_id].update(kwargs)


def get_job(job_id: str) -> dict | None:
    with JOB_LOCK:
        return JOBS.get(job_id)


def list_jobs() -> list[dict]:
    with JOB_LOCK:
        return [JOBS[j] for j in JOB_ORDER]


def stage_ascii(image_path: Path) -> Path:
    """OpenCV on Windows cannot open non-ASCII paths; copy to %TEMP%/score2midi first."""
    work = Path(tempfile.gettempdir()) / "score2midi"
    work.mkdir(parents=True, exist_ok=True)
    dest = work / f"{uuid.uuid4().hex[:10]}{image_path.suffix.lower() or '.png'}"
    shutil.copy2(image_path, dest)
    return dest


def convert_image(image_path: Path, out_dir: Path) -> tuple[Path, Path]:
    setup_sys_path()
    from homr.main import ProcessingConfig, process_image
    from homr.music_xml_generator import XmlGeneratorArguments
    from music21 import converter

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

    staged = stage_ascii(image_path)
    try:
        process_image(str(staged), config, xml_args)
        xml_beside = staged.with_suffix(".musicxml")
    finally:
        staged.unlink(missing_ok=True)

    if not xml_beside.exists():
        raise RuntimeError("识别完成但未生成 MusicXML")

    xml_out = out_dir / (image_path.stem + ".musicxml")
    midi_out = out_dir / (image_path.stem + ".mid")
    shutil.copy2(xml_beside, xml_out)
    xml_beside.unlink(missing_ok=True)

    score = converter.parse(str(xml_out))
    score.write("midi", fp=str(midi_out))

    try:
        root = Path(__file__).resolve().parent
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        from instrument_tagger import apply_instruments

        tag = apply_instruments(image_path, xml_out)
        if tag.get("updated"):
            score = converter.parse(str(xml_out))
            score.write("midi", fp=str(midi_out))
    except Exception:  # noqa: BLE001
        traceback.print_exc()

    return midi_out, xml_out


def worker_loop() -> None:
    while True:
        job_id = None
        with JOB_LOCK:
            for jid in JOB_ORDER:
                if JOBS[jid]["status"] == "queued":
                    job_id = jid
                    break
        if not job_id:
            time.sleep(0.4)
            continue

        set_job(job_id, status="running", message="AI 识别中…")
        WORKER_BUSY.set()
        try:
            job = get_job(job_id)
            img = Path(job["image_path"])
            midi_out, xml_out = convert_image(img, OUTPUT_DIR)
            set_job(
                job_id,
                status="done",
                message="转换成功",
                midi=midi_out.name,
                musicxml=xml_out.name,
            )
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            set_job(job_id, status="error", message="识别失败", error=str(e))
        finally:
            WORKER_BUSY.clear()


def models_status() -> dict:
    setup_sys_path()
    from homr.segmentation.config import segnet_path_onnx
    from homr.transformer.configs import default_config

    paths = {
        "segnet": segnet_path_onnx,
        "encoder": default_config.filepaths.encoder_path,
        "decoder": default_config.filepaths.decoder_path,
    }
    items = []
    ready = True
    for name, p in paths.items():
        exists = Path(p).exists() and Path(p).stat().st_size > 1024 * 100
        size = Path(p).stat().st_size if Path(p).exists() else 0
        items.append(
            {
                "name": name,
                "file": Path(p).name,
                "ready": exists,
                "size_mb": round(size / 1024 / 1024, 1),
            }
        )
        ready = ready and exists
    return {"ready": ready, "items": items}


class Handler(BaseHTTPRequestHandler):
    server_version = "Score2MIDI/1.0"

    def log_message(self, fmt: str, *args) -> None:
        print(f"[http] {self.address_string()} {fmt % args}")

    def _json(self, code: int, data: dict) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path: Path, download_name: str | None = None) -> None:
        if not path.exists() or not path.is_file():
            self._json(404, {"error": "文件不存在"})
            return
        ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        if download_name:
            self.send_header(
                "Content-Disposition",
                f"attachment; filename*=UTF-8''{download_name}",
            )
        self.end_headers()
        self.wfile.write(data)

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length", "0"))
        return self.rfile.read(length) if length else b""

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        qs = parse_qs(parsed.query)

        if path in ("/", "/index.html"):
            self._file(WEB_DIR / "index.html")
            return
        if path.startswith("/static/"):
            rel = path[len("/static/") :]
            target = (WEB_DIR / rel).resolve()
            if not str(target).startswith(str(WEB_DIR.resolve())):
                self._json(403, {"error": "forbidden"})
                return
            self._file(target)
            return
        if path == "/api/health":
            self._json(200, {"ok": True, "root": str(ROOT)})
            return
        if path == "/api/models":
            self._json(200, models_status())
            return
        if path == "/api/jobs":
            self._json(200, {"jobs": list_jobs()})
            return
        if path.startswith("/api/download/"):
            name = Path(path[len("/api/download/") :]).name
            folder = qs.get("type", ["midi"])[0]
            base = OUTPUT_DIR if folder in ("midi", "musicxml") else UPLOAD_DIR
            self._file(base / name, download_name=name)
            return
        if path.startswith("/preview/"):
            name = Path(path[len("/preview/") :]).name
            # 先看输出，再看上传
            for folder in (OUTPUT_DIR, UPLOAD_DIR):
                p = folder / name
                if p.exists():
                    self._file(p)
                    return
            self._json(404, {"error": "not found"})
            return

        self._json(404, {"error": "not found", "path": path})

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        if path == "/api/upload":
            body = self._read_body()
            fname = self.headers.get("X-Filename") or self.headers.get("X-File-Name")
            if not fname:
                # multipart 简单解析（可选）
                ctype = self.headers.get("Content-Type", "")
                if "multipart/form-data" in ctype:
                    fname, body = _parse_multipart(body, ctype)
                else:
                    fname = "paste.png"
            fname = Path(unquote(fname)).name
            UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
            safe = re.sub(r"[^\w.\-]+", "_", fname)
            saved = UPLOAD_DIR / f"{int(time.time()*1000)}_{safe}"
            saved.write_bytes(body)
            job_id = new_job(saved.name, saved)
            self._json(200, {"job_id": job_id, "filename": saved.name})
            return

        if path == "/api/convert-path":
            data = json.loads(self._read_body() or b"{}")
            src = Path(data.get("path", ""))
            if not src.exists() or src.suffix.lower() not in {
                ".png",
                ".jpg",
                ".jpeg",
                ".bmp",
                ".tif",
                ".tiff",
                ".webp",
            }:
                self._json(400, {"error": "无效图片路径"})
                return
            UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
            dest = UPLOAD_DIR / f"{int(time.time()*1000)}_{src.name}"
            shutil.copy2(src, dest)
            job_id = new_job(dest.name, dest)
            self._json(200, {"job_id": job_id, "filename": dest.name})
            return

        self._json(404, {"error": "not found"})


def _parse_multipart(body: bytes, ctype: str) -> tuple[str, bytes]:
    m = re.search(r'boundary="?([^";]+)"?', ctype)
    if not m:
        return "upload.bin", body
    boundary = b"--" + m.group(1).encode()
    parts = body.split(boundary)
    for part in parts:
        if b"Content-Disposition" not in part:
            continue
        header, _, data = part.partition(b"\r\n\r\n")
        data = data.rstrip(b"\r\n")
        fm = re.search(r'filename="([^"]+)"', header.decode("utf-8", "ignore"))
        if fm:
            return fm.group(1), data
    return "upload.bin", body


def main() -> int:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    t = threading.Thread(target=worker_loop, daemon=True)
    t.start()

    host, port = "127.0.0.1", 8765
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"乐谱转 MIDI 服务已启动: http://{host}:{port}")
    print(f"上传目录: {UPLOAD_DIR}")
    print(f"输出目录: {OUTPUT_DIR}")
    print("按 Ctrl+C 停止")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
