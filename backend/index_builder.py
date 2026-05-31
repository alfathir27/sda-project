"""
Build index hash map dari semua file QM9 .xyz.

Index disimpan di data/qm9_processed/index.json:
  - formula_idx: formula (Hill) -> list mol_id   (banyak molekul bisa share formula)
  - smiles_idx: smiles -> mol_id                  (asumsi unique untuk QM9)
  - meta: mol_id -> {n_atoms, formula, smiles, name}

Lookup runtime: O(1) hash map. Build sekali (~1 menit untuk 134K file), lalu
disimpan ke disk.
"""

import json
import time
from pathlib import Path
from typing import Dict, List

from qm9_loader import parse_xyz_meta

ROOT = Path(__file__).parent.parent
RAW_DIR = ROOT / "data" / "qm9_raw"
INDEX_PATH = ROOT / "data" / "qm9_processed" / "index.json"


def build_index(verbose: bool = True) -> Dict:
    """Scan semua .xyz, bangun 3 hash map. Returns dict yang siap di-serialize."""
    if not RAW_DIR.exists():
        raise FileNotFoundError(f"Raw data tidak ada: {RAW_DIR}")

    files = sorted(RAW_DIR.glob("*.xyz"))
    total = len(files)
    if verbose:
        print(f"Scan {total} file .xyz...")

    formula_idx: Dict[str, List[str]] = {}
    smiles_idx: Dict[str, str] = {}
    meta: Dict[str, Dict] = {}

    start = time.time()
    skipped = 0
    for i, path in enumerate(files):
        try:
            m = parse_xyz_meta(path)
        except Exception:
            skipped += 1
            continue

        mol_id = m["mol_id"]
        meta[mol_id] = {
            "n_atoms": m["n_atoms"],
            "formula": m["formula"],
            "smiles": m["smiles"],
            "name": m["name"],
            "properties": m["properties"],
        }
        formula_idx.setdefault(m["formula"], []).append(mol_id)
        # smiles bisa None (rare); skip kalau gada
        if m["smiles"] and m["smiles"] not in smiles_idx:
            smiles_idx[m["smiles"]] = mol_id

        if verbose and (i + 1) % 10000 == 0:
            elapsed = time.time() - start
            print(f"  {i + 1}/{total} ({elapsed:.1f}s)")

    if verbose:
        elapsed = time.time() - start
        print(f"Selesai dalam {elapsed:.1f}s. Unique formula: {len(formula_idx)}, "
              f"unique smiles: {len(smiles_idx)}, skipped: {skipped}")

    return {
        "formula_idx": formula_idx,
        "smiles_idx": smiles_idx,
        "meta": meta,
    }


def save_index(index: Dict, path: Path = INDEX_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(index, f, separators=(",", ":"))  # compact
    size_mb = path.stat().st_size / (1024 * 1024)
    print(f"Index ditulis ke {path.relative_to(ROOT)} ({size_mb:.1f} MB)")


def load_index(path: Path = INDEX_PATH) -> Dict:
    with open(path, "r") as f:
        return json.load(f)


if __name__ == "__main__":
    idx = build_index()
    save_index(idx)
