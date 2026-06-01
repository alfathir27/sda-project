from pathlib import Path
import re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from data_manager import dataset
from qm9_loader import hill_formula
from smiles_parser import parse_smiles
from graph_processor import compute_2d_layout

app = FastAPI(title="QM9 Graph API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/molecules")
def list_molecules(limit: int = 50, offset: int = 0):
    return dataset.list_molecules(limit, offset)


@app.get("/molecules/{mol_id}")
def get_molecule(mol_id: str):
    mol = dataset.get_molecule(mol_id)
    if not mol:
        raise HTTPException(status_code=404, detail="molekul tidak ditemukan")
    return mol


@app.get("/search")
def search(q: str, limit: int = 50):
    return dataset.search(q, limit)


class RenderRequest(BaseModel):
    smiles: str


class RenderFormulaRequest(BaseModel):
    formula: str


@app.post("/render-smiles")
def render_smiles(req: RenderRequest):
    try:
        parsed = parse_smiles(req.smiles)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"smiles invalid: {e}")

    atoms = parsed["atoms"]
    raw_bonds = parsed["bonds"]
    layout_bonds = [(i, j, 1.0) for i, j, _order in raw_bonds]
    layout = compute_2d_layout(atoms, layout_bonds)

    nodes = [
        {"id": i, "element": el, "x": 0.0, "y": 0.0, "z": 0.0,
         "x2d": layout[i][0], "y2d": layout[i][1]}
        for i, el in enumerate(atoms)
    ]
    edges = [
        {"source": i, "target": j, "length": 1.0, "order": order}
        for i, j, order in raw_bonds
    ]
    return {
        "mol_id": None,
        "n_atoms": len(atoms),
        "formula": hill_formula(atoms),
        "name": None,
        "smiles": req.smiles,
        "nodes": nodes,
        "edges": edges,
        "properties": {},
        "synthetic": True,
    }


@app.post("/render-formula")
def render_formula(req: RenderFormulaRequest):
    sub = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")
    s = req.formula.translate(sub).strip()
    atoms_list = []
    for el, cnt in re.findall(r"([A-Za-z][a-z]?)(\d*)", s):
        if not el:
            continue
        normalized = el[0].upper() + (el[1:].lower() if len(el) > 1 else "")
        atoms_list.extend([normalized] * (int(cnt) if cnt else 1))
    if not atoms_list:
        raise HTTPException(status_code=400, detail="formula tidak valid")

    heavy = [(i, el) for i, el in enumerate(atoms_list) if el != "H"]
    hydrogens = [i for i, el in enumerate(atoms_list) if el == "H"]
    bonds = []
    if len(heavy) >= 2:
        for k in range(len(heavy) - 1):
            bonds.append((heavy[k][0], heavy[k + 1][0], 1.0))
    if heavy:
        for k, h_idx in enumerate(hydrogens):
            target = heavy[k % len(heavy)][0]
            bonds.append((target, h_idx, 1.0))
    elif len(hydrogens) >= 2:
        for k in range(len(hydrogens) - 1):
            bonds.append((hydrogens[k], hydrogens[k + 1], 1.0))

    layout = compute_2d_layout(atoms_list, bonds)
    nodes = [
        {"id": i, "element": el, "x": 0.0, "y": 0.0, "z": 0.0,
         "x2d": layout[i][0], "y2d": layout[i][1]}
        for i, el in enumerate(atoms_list)
    ]
    edges = [
        {"source": i, "target": j, "length": 1.0, "order": 1}
        for i, j, _ in bonds
    ]
    return {
        "mol_id": None,
        "n_atoms": len(atoms_list),
        "formula": hill_formula(atoms_list),
        "name": None,
        "smiles": None,
        "nodes": nodes,
        "edges": edges,
        "properties": {},
        "synthetic": True,
        "warning": "struktur ikatan tidak bisa ditentukan dari formula. ini cuma gambaran kasar.",
    }


class CompareRequest(BaseModel):
    ids: list[str]


@app.post("/compare")
def compare_molecules(req: CompareRequest):
    return dataset.compare(req.ids)


@app.get("/properties/stats")
def get_stats():
    return dataset.stats()


app.mount("/", StaticFiles(directory=Path(__file__).parent / "static", html=True), name="static")
