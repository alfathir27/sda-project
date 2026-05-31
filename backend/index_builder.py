# build index hash map dari semua xyz, simpan ke data/qm9_processed/index.json
# 3 hash map: formula_idx, smiles_idx, meta
# build sekali aja, lalu tinggal load dari disk

import json
import time
from pathlib import Path

from qm9_loader import parse_xyz_meta

ROOT = Path(__file__).parent.parent
RAW_DIR = ROOT / "data" / "qm9_raw"
INDEX_PATH = ROOT / "data" / "qm9_processed" / "index.json"


def build_index(verbose=True):
    if not RAW_DIR.exists():
        raise FileNotFoundError(f"data mentah tidak ada: {RAW_DIR}")

    files = sorted(RAW_DIR.glob("*.xyz"))
    total = len(files)
    if verbose:
        print(f"scan {total} file xyz...")

    formula_idx = {}
    smiles_idx = {}
    meta = {}

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
        if m["smiles"] and m["smiles"] not in smiles_idx:
            smiles_idx[m["smiles"]] = mol_id

        if verbose and (i + 1) % 10000 == 0:
            elapsed = time.time() - start
            print(f"  {i + 1}/{total} ({elapsed:.1f}s)")

    if verbose:
        elapsed = time.time() - start
        print(f"selesai {elapsed:.1f}s. formula unik: {len(formula_idx)}, "
              f"smiles unik: {len(smiles_idx)}, skip: {skipped}")

    return {
        "formula_idx": formula_idx,
        "smiles_idx": smiles_idx,
        "meta": meta,
    }


def save_index(index, path=INDEX_PATH):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(index, f, separators=(",", ":"))
    size_mb = path.stat().st_size / (1024 * 1024)
    print(f"index disimpan ke {path.relative_to(ROOT)} ({size_mb:.1f} MB)")


def load_index(path=INDEX_PATH):
    with open(path, "r") as f:
        return json.load(f)


if __name__ == "__main__":
    idx = build_index()
    save_index(idx)
