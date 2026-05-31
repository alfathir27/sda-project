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


def step(msg: str) -> None:
    print(f"\n==> {msg}")


def info(msg: str) -> None:
    print(f"    {msg}")


def venv_python() -> Path:
    if os.name == "nt":
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


def check_python() -> None:
    step("Cek Python version")
    if sys.version_info < MIN_PYTHON:
        sys.exit(
            f"Butuh Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+, "
            f"kamu pakai {sys.version.split()[0]}"
        )
    info(f"Python {sys.version.split()[0]} OK")


def create_venv() -> None:
    step("Setup virtual environment")
    if VENV.exists():
        info(f"Venv sudah ada di {VENV.relative_to(ROOT)}, skip")
        return
    info(f"Buat venv di {VENV.relative_to(ROOT)}")
    subprocess.check_call([sys.executable, "-m", "venv", str(VENV)])


def install_deps() -> None:
    step("Install dependencies")
    py = venv_python()
    req = BACKEND / "requirements.txt"
    if not req.exists():
        sys.exit(f"requirements.txt tidak ditemukan: {req}")
    subprocess.check_call(
        [str(py), "-m", "pip", "install", "--upgrade", "pip", "--quiet"]
    )
    subprocess.check_call([str(py), "-m", "pip", "install", "-r", str(req)])


def download_dataset(force: bool = False) -> None:
    step("Download QM9 dataset")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if ARCHIVE.exists() and not force:
        size_mb = ARCHIVE.stat().st_size // (1024 * 1024)
        info(f"Archive sudah ada ({size_mb} MB), skip download")
        return
    info(f"Unduh dari {QM9_URL}")
    info("Ukuran ~83 MB, ini bisa beberapa menit...")

    def progress(block_num: int, block_size: int, total_size: int) -> None:
        # progress bar sederhana
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
        sys.exit(f"Download gagal: {e}")


def extract_dataset(force: bool = False) -> None:
    step("Extract dataset")
    if RAW_DIR.exists() and any(RAW_DIR.glob("*.xyz")) and not force:
        n = sum(1 for _ in RAW_DIR.glob("*.xyz"))
        info(f"Sudah ada {n} file .xyz di {RAW_DIR.relative_to(ROOT)}, skip")
        return
    if not ARCHIVE.exists():
        sys.exit(f"Archive tidak ditemukan: {ARCHIVE}")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    info(f"Extract ke {RAW_DIR.relative_to(ROOT)} (~134K file, butuh ~1-2 menit)")
    with tarfile.open(ARCHIVE, "r:bz2") as tar:
        try:
            # py 3.12+ butuh filter
            tar.extractall(RAW_DIR, filter="data")
        except TypeError:
            tar.extractall(RAW_DIR)
    n = sum(1 for _ in RAW_DIR.glob("*.xyz"))
    info(f"Extracted {n} file .xyz")


def build_index() -> None:
    step("Build index hash map (scan semua .xyz)")
    info("~134K file, butuh ~3 detik. Hasil disimpan ke data/qm9_processed/index.json")
    py = venv_python()
    subprocess.check_call(
        [str(py), "index_builder.py"],
        cwd=str(BACKEND),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--skip-index",
        action="store_true",
        help="Skip build index (kalau index.json sudah ada dan valid)",
    )
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="Re-download archive walau sudah ada",
    )
    parser.add_argument(
        "--force-extract",
        action="store_true",
        help="Re-extract walau .xyz sudah ada",
    )
    parser.add_argument(
        "--skip-deps",
        action="store_true",
        help="Skip pip install (kalau dependencies sudah terpasang)",
    )
    parser.add_argument(
        "--skip-data",
        action="store_true",
        help="Skip download dan extract dataset",
    )
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
            info(f"Index sudah ada di {index_path.relative_to(ROOT)}, skip (pakai --force-index untuk rebuild)")
        else:
            build_index()

    step("Setup selesai")
    venv_rel = VENV.relative_to(ROOT)
    print(f"\n  jalankan: {venv_rel}/bin/uvicorn main:app --app-dir backend --port 8000")
    print(f"  lalu buka: http://localhost:8000\n")


if __name__ == "__main__":
    main()
