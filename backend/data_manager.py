import pickle
from pathlib import Path
from typing import List, Dict, Optional
import numpy as np

from qm9_loader import parse_xyz, PROPERTIES_NAMES
from graph_processor import infer_bonds, compute_2d_layout

RAW_DIR = Path(__file__).parent.parent / "data" / "qm9_raw"
CACHE_PATH = Path(__file__).parent.parent / "data" / "qm9_processed" / "cache.pkl"
MAX_MOLECULES = 2000


class QM9Dataset:
    def __init__(self):
        self.molecules: List[Dict] = []
        self._id_to_idx: Dict[str, int] = {}
        self._load()

    def _load(self):
        if CACHE_PATH.exists():
            with open(CACHE_PATH, 'rb') as f:
                self.molecules = pickle.load(f)
            for idx, mol in enumerate(self.molecules):
                self._id_to_idx[mol['mol_id']] = idx
            return

        files = sorted(RAW_DIR.glob("*.xyz"))[:MAX_MOLECULES]
        for f in files:
            try:
                mol = parse_xyz(f)
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

                edges = []
                for i, j, dist in bonds:
                    edges.append({
                        "source": i,
                        "target": j,
                        "length": round(dist, 4),
                    })

                self.molecules.append({
                    "mol_id": mol['mol_id'],
                    "n_atoms": mol['n_atoms'],
                    "formula": self._formula(mol['atoms']),
                    "nodes": nodes,
                    "edges": edges,
                    "properties": mol['properties'],
                })
                self._id_to_idx[mol['mol_id']] = len(self.molecules) - 1
            except Exception as e:
                print(f"Error parsing {f}: {e}")
                continue

        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_PATH, 'wb') as f:
            pickle.dump(self.molecules, f)

    def _formula(self, atoms: List[str]) -> str:
        counts = {}
        for a in atoms:
            counts[a] = counts.get(a, 0) + 1
        return ''.join(f"{k}{counts[k] if counts[k] > 1 else ''}" for k in sorted(counts.keys()))

    def list_molecules(self, limit: int = 50, offset: int = 0):
        total = len(self.molecules)
        items = []
        for mol in self.molecules[offset:offset + limit]:
            items.append({
                "mol_id": mol['mol_id'],
                "n_atoms": mol['n_atoms'],
                "formula": mol['formula'],
                "mu": mol['properties'].get('mu_Debye'),
                "gap": mol['properties'].get('gap_Hartree'),
            })
        return {"total": total, "items": items}

    def get_molecule(self, mol_id: str) -> Optional[Dict]:
        idx = self._id_to_idx.get(mol_id)
        if idx is None:
            return None
        return self.molecules[idx]

    def compare(self, mol_ids: List[str]):
        return [self.get_molecule(mid) for mid in mol_ids if mid in self._id_to_idx]

    def stats(self):
        props = {}
        for name in PROPERTIES_NAMES[2:]:
            values = [m['properties'][name] for m in self.molecules if name in m['properties']]
            if values:
                arr = np.array(values)
                props[name] = {
                    "min": round(float(np.min(arr)), 6),
                    "max": round(float(np.max(arr)), 6),
                    "mean": round(float(np.mean(arr)), 6),
                }
        return props


dataset = QM9Dataset()
