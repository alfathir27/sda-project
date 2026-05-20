from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List
from data_manager import dataset

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


class CompareRequest(BaseModel):
    ids: List[str]


@app.post("/compare")
def compare_molecules(req: CompareRequest):
    return dataset.compare(req.ids)


@app.get("/properties/stats")
def get_stats():
    return dataset.stats()


app.mount("/", StaticFiles(directory=Path(__file__).parent / "static", html=True), name="static")
