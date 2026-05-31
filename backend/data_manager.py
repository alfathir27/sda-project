# QM9Dataset - lazy load via hash map index
# startup cuma load index.json, parse xyz on-demand pas user buka detail
# hasil parse di-cache ke pickle biar akses kedua langsung dari memori

import pickle
import threading
from pathlib import Path
import numpy as np

from qm9_loader import (
    parse_xyz,
    PROPERTIES_NAMES,
    resolve_names_batch,
    _load_names_cache,
    hill_formula,
)
from graph_processor import infer_bonds, compute_2d_layout
from index_builder import load_index, INDEX_PATH

ROOT = Path(__file__).parent.parent
RAW_DIR = ROOT / "data" / "qm9_raw"
CACHE_PATH = ROOT / "data" / "qm9_processed" / "cache.pkl"


class QM9Dataset:
    def __init__(self):
        self._index = {}
        self._cache = {}
        self._lock = threading.Lock()
        self._load_index()
        self._load_cache()

    def _load_index(self):
        if not INDEX_PATH.exists():
            raise FileNotFoundError(
                f"index belum ada di {INDEX_PATH}. "
                f"jalanin `python setup.py` dulu"
            )
        self._index = load_index(INDEX_PATH)
        # merge nama dari PubChem cache ke meta
        names_cache = _load_names_cache()
        if names_cache:
            for mol_id, m in self._index["meta"].items():
                if not m.get("name") and m.get("smiles") and m["smiles"] in names_cache:
                    m["name"] = names_cache[m["smiles"]]

    def _load_cache(self):
        if CACHE_PATH.exists():
            try:
                with open(CACHE_PATH, 'rb') as f:
                    self._cache = pickle.load(f)
            except Exception as e:
                print(f"cache rusak ({e}), mulai dari kosong")
                self._cache = {}

    def _save_cache(self):
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_PATH, 'wb') as f:
            pickle.dump(self._cache, f)

    # ---------- core lookup ----------

    def get_molecule(self, mol_id):
        if mol_id in self._cache:
            return self._cache[mol_id]
        if mol_id not in self._index["meta"]:
            return None
        with self._lock:
            if mol_id in self._cache:
                return self._cache[mol_id]
            mol = self._build_molecule(mol_id)
            if mol is None:
                return None
            self._cache[mol_id] = mol
            self._save_cache()
            return mol

    def _build_molecule(self, mol_id):
        path = RAW_DIR / f"{mol_id}.xyz"
        if not path.exists():
            return None
        try:
            mol = parse_xyz(path)
        except Exception as e:
            print(f"parse error {mol_id}: {e}")
            return None

        bonds = infer_bonds(mol['atoms'], mol['coords'])
        layout = compute_2d_layout(mol['atoms'], bonds)

        nodes = []
        for i, atom in enumerate(mol['atoms']):
            x2d, y2d = layout[i]
            nodes.append({
                "id": i,
                "element": atom,
                "x": float(mol['coords'][i][0]),
                "y": float(mol['coords'][i][1]),
                "z": float(mol['coords'][i][2]),
                "x2d": x2d,
                "y2d": y2d,
            })

        edges = [
            {"source": i, "target": j, "length": round(dist, 4)}
            for i, j, dist in bonds
        ]

        meta = self._index["meta"].get(mol_id, {})
        return {
            "mol_id": mol_id,
            "n_atoms": mol['n_atoms'],
            "formula": hill_formula(mol['atoms']),
            "name": meta.get('name') or mol.get('name'),
            "smiles": mol.get('smiles'),
            "nodes": nodes,
            "edges": edges,
            "properties": mol['properties'],
        }

    # ---------- list / search / compare / stats ----------

    def list_molecules(self, limit=50, offset=0):
        meta = self._index["meta"]
        ids = list(meta.keys())
        total = len(ids)
        items = []
        for mol_id in ids[offset:offset + limit]:
            m = meta[mol_id]
            props = m.get("properties", {})
            items.append({
                "mol_id": mol_id,
                "n_atoms": m["n_atoms"],
                "formula": m["formula"],
                "name": m.get("name"),
                "smiles": m.get("smiles"),
                "mu": props.get("mu_Debye"),
                "gap": props.get("gap_Hartree"),
            })
        return {"total": total, "items": items}

    def search(self, query, limit=50):
        q = query.strip()
        if not q:
            return {"total": 0, "items": []}

        meta = self._index["meta"]
        formula_idx = self._index["formula_idx"]
        normalized = self._normalize_formula(q)
        if normalized in formula_idx:
            ids = formula_idx[normalized][:limit]
            return {
                "total": len(formula_idx[normalized]),
                "matched_by": "formula",
                "items": [self._summary(mol_id) for mol_id in ids],
            }

        smiles_idx = self._index["smiles_idx"]
        if q in smiles_idx:
            mol_id = smiles_idx[q]
            return {"total": 1, "matched_by": "smiles", "items": [self._summary(mol_id)]}

        # fallback: cocokin substring di mol_id atau name
        ql = q.lower()
        items = []
        for mol_id, m in meta.items():
            if ql in mol_id.lower() or (m.get("name") and ql in m["name"].lower()):
                items.append(self._summary(mol_id))
                if len(items) >= limit:
                    break
        return {"total": len(items), "matched_by": "substring", "items": items}

    def _normalize_formula(self, s):
        # terima h2o, H2O, atau h₂o, normalisasi ke notasi Hill
        sub = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")
        s = s.translate(sub).strip()
        import re
        atoms = []
        for el, cnt in re.findall(r"([A-Za-z][a-z]?)(\d*)", s):
            if not el:
                continue
            normalized = el[0].upper() + (el[1:].lower() if len(el) > 1 else "")
            n = int(cnt) if cnt else 1
            atoms.extend([normalized] * n)
        if not atoms:
            return s
        return hill_formula(atoms)

    def _summary(self, mol_id):
        m = self._index["meta"][mol_id]
        props = m.get("properties", {})
        return {
            "mol_id": mol_id,
            "n_atoms": m["n_atoms"],
            "formula": m["formula"],
            "name": m.get("name"),
            "smiles": m.get("smiles"),
            "mu": props.get("mu_Debye"),
            "gap": props.get("gap_Hartree"),
        }

    def compare(self, mol_ids):
        return [self.get_molecule(mid) for mid in mol_ids if mid in self._index["meta"]]

    def stats(self):
        if hasattr(self, "_stats_cached"):
            return self._stats_cached
        meta = self._index["meta"]
        out = {}
        for name in PROPERTIES_NAMES[2:]:
            values = [
                m["properties"][name]
                for m in meta.values()
                if "properties" in m and m["properties"].get(name) is not None
            ]
            if values:
                arr = np.array(values)
                out[name] = {
                    "min": round(float(np.min(arr)), 6),
                    "max": round(float(np.max(arr)), 6),
                    "mean": round(float(np.mean(arr)), 6),
                }
        self._stats_cached = out
        return out

    @property
    def molecules(self):
        return [
            {**m, "mol_id": mol_id}
            for mol_id, m in self._index["meta"].items()
        ]


dataset = QM9Dataset()
