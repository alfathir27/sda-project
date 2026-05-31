#!/usr/bin/env python3
# setup awal: bikin venv, install deps, download + extract QM9, opsional build cache
# pakai: python setup.py

import argparse
import os
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
VENV = BACKEND / ".venv"
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "qm9_raw"
PROCESSED_DIR = DATA_DIR / "qm9_processed"
ARCHIVE = DATA_DIR / "dsgdb9nsd.xyz.tar.bz2"

# url QM9 dari figshare
QM9_URL = "https://ndownloader.figshare.com/files/3195389"

MIN_PYTHON = (3, 9)


def step(msg):
    print(f"\n==> {msg}")


def info(msg):
    print(f"    {msg}")


def venv_python():
    if os.name == "nt":
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


def check_python():
    step("cek versi python")
    if sys.version_info < MIN_PYTHON:
        sys.exit(
            f"butuh python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+, "
            f"kamu pakai {sys.version.split()[0]}"
        )
    info(f"python {sys.version.split()[0]} ok")


def create_venv():
    step("setup venv")
    if VENV.exists():
        info(f"venv udah ada di {VENV.relative_to(ROOT)}, skip")
        return
    info(f"bikin venv di {VENV.relative_to(ROOT)}")
    subprocess.check_call([sys.executable, "-m", "venv", str(VENV)])


def install_deps():
    step("install deps")
    py = venv_python()
    req = BACKEND / "requirements.txt"
    if not req.exists():
        sys.exit(f"requirements.txt gak ada: {req}")
    subprocess.check_call(
        [str(py), "-m", "pip", "install", "--upgrade", "pip", "--quiet"]
    )
    subprocess.check_call([str(py), "-m", "pip", "install", "-r", str(req)])


def download_dataset(force=False):
    step("download dataset QM9")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if ARCHIVE.exists() and not force:
        size_mb = ARCHIVE.stat().st_size // (1024 * 1024)
        info(f"archive udah ada ({size_mb} MB), skip")
        return
    info(f"download dari {QM9_URL}")
    info("size ~83 MB, butuh beberapa menit...")

    def progress(block_num, block_size, total_size):
        downloaded = block_num * block_size
        if total_size > 0:
            pct = min(100, downloaded * 100 // total_size)
            mb = downloaded // (1024 * 1024)
            total_mb = total_size // (1024 * 1024)
            print(f"\r    {pct}% ({mb}/{total_mb} MB)", end="", flush=True)

    try:
        urllib.request.urlretrieve(QM9_URL, ARCHIVE, reporthook=progress)
        print()
    except Exception as e:
        if ARCHIVE.exists():
            ARCHIVE.unlink()
        sys.exit(f"download gagal: {e}")


def extract_dataset(force=False):
    step("extract dataset")
    if RAW_DIR.exists() and any(RAW_DIR.glob("*.xyz")) and not force:
        n = sum(1 for _ in RAW_DIR.glob("*.xyz"))
        info(f"udah ada {n} file xyz di {RAW_DIR.relative_to(ROOT)}, skip")
        return
    if not ARCHIVE.exists():
        sys.exit(f"archive gak ada: {ARCHIVE}")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    info(f"extract ke {RAW_DIR.relative_to(ROOT)}, butuh ~1-2 menit")
    with tarfile.open(ARCHIVE, "r:bz2") as tar:
        try:
            tar.extractall(RAW_DIR, filter="data")
        except TypeError:
            tar.extractall(RAW_DIR)
    n = sum(1 for _ in RAW_DIR.glob("*.xyz"))
    info(f"selesai, {n} file xyz")


def build_index():
    step("build index")
    info("scan ~134K file, sekitar 3 detik")
    py = venv_python()
    subprocess.check_call(
        [str(py), "index_builder.py"],
        cwd=str(BACKEND),
    )


def main():
    parser = argparse.ArgumentParser(description="setup awal QM9 graph explorer")
    parser.add_argument("--skip-index", action="store_true", help="skip build index")
    parser.add_argument("--force-download", action="store_true", help="download ulang archive")
    parser.add_argument("--force-extract", action="store_true", help="extract ulang xyz")
    parser.add_argument("--skip-deps", action="store_true", help="skip pip install")
    parser.add_argument("--skip-data", action="store_true", help="skip download dan extract")
    args = parser.parse_args()

    check_python()
    create_venv()
    if not args.skip_deps:
        install_deps()
    if not args.skip_data:
        download_dataset(force=args.force_download)
        extract_dataset(force=args.force_extract)
    if not args.skip_index:
        index_path = PROCESSED_DIR / "index.json"
        if index_path.exists():
            info(f"index udah ada di {index_path.relative_to(ROOT)}, skip")
        else:
            build_index()

    step("selesai")
    venv_rel = VENV.relative_to(ROOT)
    print(f"\n  jalankan: {venv_rel}/bin/uvicorn main:app --app-dir backend --port 8000")
    print(f"  buka: http://localhost:8000\n")


if __name__ == "__main__":
    main()
