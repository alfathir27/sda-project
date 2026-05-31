from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List
import networkx as nx

from data_manager import dataset
from qm9_loader import resolve_names_batch, hill_formula
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


@app.get("/")
def root():
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/molecules")
def list_molecules(limit: int = 50, offset: int = 0):
    return dataset.list_molecules(limit, offset)


@app.get("/molecules/{mol_id}")
def get_molecule(mol_id: str):
    mol = dataset.get_molecule(mol_id)
    if not mol:
        raise HTTPException(status_code=404, detail="Molecule not found")
    return mol


@app.get("/search")
def search(q: str, limit: int = 50):
    """Cari berdasarkan formula (Hill, O(1)), SMILES (O(1)), atau substring (O(n))."""
    return dataset.search(q, limit)


class RenderRequest(BaseModel):
    smiles: str


@app.post("/render-smiles")
def render_smiles(req: RenderRequest):
    """
    Tier 3 fallback: render graf dari SMILES tanpa data koordinat / properti.
    Cuma struktur ikatan + layout 2D.
    """
    try:
        parsed = parse_smiles(req.smiles)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"SMILES invalid: {e}")

    atoms = parsed["atoms"]
    raw_bonds = parsed["bonds"]
    # bonds untuk layout butuh format (i, j, weight) — pakai 1.0 untuk semua
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


class CompareRequest(BaseModel):
    ids: List[str]


@app.post("/compare")
def compare_molecules(req: CompareRequest):
    return dataset.compare(req.ids)


@app.get("/properties/stats")
def get_stats():
    return dataset.stats()


@app.post("/resolve-names")
def resolve_names():
    cache = resolve_names_batch(dataset.molecules)
    resolved = sum(1 for m in dataset.molecules if m.get('name'))
    return {"resolved": resolved, "total": len(dataset.molecules), "unique_smiles": len(cache)}


app.mount("/", StaticFiles(directory=Path(__file__).parent / "static", html=True), name="static")
