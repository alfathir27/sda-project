from pathlib import Path
import json
import time
import urllib.request
import urllib.parse
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np

COVALENT_RADII = {
    'H': 0.31, 'C': 0.76, 'N': 0.71, 'O': 0.66, 'F': 0.57,
    'S': 1.05, 'Cl': 0.99, 'P': 1.07, 'Si': 1.11, 'Br': 1.14,
    'B': 0.84, 'Li': 1.28, 'Na': 1.66, 'Mg': 1.41, 'Al': 1.21,
    'K': 2.03, 'Ca': 1.76, 'Fe': 1.32, 'Cu': 1.32, 'Zn': 1.22,
}

SMILES_TO_NAME = {
    'C': 'Methane', 'O': 'Water', 'N': 'Ammonia',
    'C#C': 'Acetylene', 'C#N': 'Hydrogen Cyanide',
    'C=C': 'Ethylene', 'C=O': 'Formaldehyde',
    'CC': 'Ethane', 'CO': 'Methanol', 'CN': 'Methylamine', 'CF': 'Fluoromethane',
    'CC=C': 'Propene', 'CC#C': 'Propyne', 'CCC': 'Propane',
    'C=CC': 'Propene', 'CCO': 'Ethanol', 'CCN': 'Ethylamine', 'CCF': 'Fluoroethane',
    'COC': 'Dimethyl Ether', 'CNC': 'Dimethylamine',
    'O=CO': 'Formic Acid', 'O=C=O': 'Carbon Dioxide', 'N#CC': 'Acetonitrile',
    'CC=O': 'Acetaldehyde', 'CCO=C': 'Dimethyl Ether',
    'CCCO': '1-Propanol', 'CCNC': 'Ethylmethylamine',
    'CCCC': 'Butane', 'CC=CC': '2-Butene', 'CC#CC': '2-Butyne',
    'C=CC=C': '1,3-Butadiene', 'C1=CC=CC=C1': 'Benzene',
    'c1ccccc1': 'Benzene', 'C1CCCCC1': 'Cyclohexane',
    'C1CCCC1': 'Cyclopentane', 'C1CCC1': 'Cyclobutane', 'C1CC1': 'Cyclopropane',
    'O=C(O)C': 'Acetic Acid', 'O=CC': 'Acetaldehyde',
    'O=CN': 'Formamide', 'O=CNC': 'N-Methylformamide',
    'CC(=O)C': 'Acetone', 'CC(=O)O': 'Acetic Acid',
    'CC(=O)N': 'Acetamide', 'C#CC#C': 'Diacetylene',
    'S': 'Hydrogen Sulfide', 'CS': 'Methanethiol', 'CCS': 'Ethanethiol',
    'C=S': 'Thioformaldehyde', 'OCS': 'Thioformaldehyde',
    'F': 'Hydrogen Fluoride', 'FCF': 'Difluoromethane',
    'O1CC1': 'Ethylene Oxide', 'C1OCC1': 'Oxetane',
    'N#N': 'Dinitrogen', 'O=O': 'Dioxygen',
    'C(=O)(O)O': 'Carbonic Acid', 'NC=O': 'Formamide',
    'NCN': 'Urea', 'NC(=O)N': 'Urea',
    'CC(=O)OC': 'Methyl Acetate', 'CCOC': 'Ethyl Methyl Ether',
    'C=NO': 'Formaldoxime', 'ON=O': 'Nitrous Acid',
    'O=N=O': 'Nitrogen Dioxide', 'N=O': 'Nitric Oxide',
    'C(F)(F)F': 'Trifluoromethane', 'C(Cl)Cl': 'Dichloromethane',
    'C(Br)Br': 'Dibromomethane',
    'CC(=O)CC': '2-Butanone', 'CCC(=O)C': '2-Butanone',
    'CCCO': '1-Propanol', 'CC(O)C': '2-Propanol',
    'C1COCC1': 'Tetrahydrofuran', 'C1CCNC1': 'Pyrrolidine',
    'C1CCOC1': 'Tetrahydrofuran',
    'c1ccncc1': 'Pyridine', 'c1ccc[nH]c1': 'Pyrrole',
    'c1ccco1': 'Furan', 'c1cc[nH]c1': 'Pyrrole',
    'c1ccsc1': 'Thiophene', 'c1ccnc1': 'Pyridine',
    'C1=CN=CC=C1': 'Pyridine',
}


def smiles_to_name(smiles):
    return SMILES_TO_NAME.get(smiles)


NAMES_CACHE_PATH = Path(__file__).parent.parent / "data" / "qm9_processed" / "names_cache.json"


def _load_names_cache():
    if NAMES_CACHE_PATH.exists():
        with open(NAMES_CACHE_PATH, 'r') as f:
            return json.load(f)
    return {}


def _save_names_cache(cache):
    NAMES_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(NAMES_CACHE_PATH, 'w') as f:
        json.dump(cache, f, indent=2)


def _pubchem_resolve(smiles):
    # ambil nama IUPAC dari PubChem REST API
    try:
        encoded = urllib.parse.quote(smiles, safe='')
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/{encoded}/property/IUPACName,Title/JSON"
        req = urllib.request.Request(url, headers={"User-Agent": "QM9GraphExplorer/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        props = data["PropertyTable"]["Properties"][0]
        return props.get("IUPACName") or props.get("Title")
    except Exception:
        return None


def resolve_names_batch(molecules, workers=8, save_every=200):
    cache = _load_names_cache()
    to_resolve = []
    for mol in molecules:
        smiles = mol.get("smiles")
        if not smiles:
            continue
        if mol.get("name"):
            cache[smiles] = mol["name"]
            continue
        if smiles in cache:
            mol["name"] = cache[smiles]
            continue
        to_resolve.append(mol)

    if not to_resolve:
        return cache

    # dedup smiles dulu, biar molekul yg punya smiles sama gak di-fetch dua kali
    unique_smiles = {}
    for mol in to_resolve:
        unique_smiles.setdefault(mol["smiles"], []).append(mol)

    print(f"resolve {len(unique_smiles)} smiles unik dari PubChem (workers={workers})")

    done = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(_pubchem_resolve, s): s for s in unique_smiles}
        for fut in as_completed(futures):
            smiles = futures[fut]
            name = fut.result()
            if name:
                cache[smiles] = name
                for mol in unique_smiles[smiles]:
                    mol["name"] = name
            done += 1
            if done % save_every == 0:
                _save_names_cache(cache)
                print(f"  {done}/{len(unique_smiles)}")

    _save_names_cache(cache)
    print(f"selesai. total {len(cache)} smiles tercache")
    return cache

PROPERTIES_NAMES = [
    "tag", "index", "A_GHz", "B_GHz", "C_GHz", "mu_Debye", "alpha_Bohr3",
    "homo_Hartree", "lumo_Hartree", "gap_Hartree", "r2_Bohr2",
    "zpve_Hartree", "U0_Hartree", "U_Hartree", "H_Hartree", "G_Hartree", "Cv_cal_mol_K"
]


# notasi Hill: C dulu, lalu H, sisanya alfabet
def hill_formula(atoms):
    counts = {}
    for a in atoms:
        counts[a] = counts.get(a, 0) + 1
    keys = []
    if 'C' in counts:
        keys.append('C')
        if 'H' in counts:
            keys.append('H')
        keys.extend(sorted(k for k in counts if k not in ('C', 'H')))
    else:
        keys = sorted(counts.keys())
    return ''.join(f"{k}{counts[k] if counts[k] > 1 else ''}" for k in keys)


# baca header xyz tanpa parse koordinat, dipakai pas build index
def parse_xyz_meta(path):
    with open(path, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]
    n_atoms = int(lines[0])

    props_line = lines[1].split()
    props = {}
    prop_keys = PROPERTIES_NAMES[1:]
    for i, name in enumerate(prop_keys):
        idx = i + 1
        if idx < len(props_line):
            try:
                props[name] = float(props_line[idx].replace('*^', 'e'))
            except ValueError:
                props[name] = None

    atoms = []
    for i in range(2, 2 + n_atoms):
        parts = lines[i].split()
        if parts:
            atoms.append(parts[0])
    smiles = None
    if len(lines) >= n_atoms + 5:
        smiles_line = lines[n_atoms + 3].split()
        if smiles_line:
            smiles = smiles_line[0]
    return {
        "mol_id": path.stem,
        "n_atoms": n_atoms,
        "formula": hill_formula(atoms),
        "smiles": smiles,
        "name": smiles_to_name(smiles) if smiles else None,
        "properties": props,
    }


def parse_xyz(path):
    with open(path, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]

    n_atoms = int(lines[0])

    # baris 2 di QM9: tag 'gdb', index, 15 properti numerik
    props_line = lines[1].split()
    props = {}
    prop_keys = PROPERTIES_NAMES[1:]
    for i, name in enumerate(prop_keys):
        idx = i + 1
        if idx < len(props_line):
            try:
                val = props_line[idx].replace('*^', 'e')
                props[name] = float(val)
            except ValueError:
                props[name] = None

    atoms = []
    coords = []
    for i in range(2, 2 + n_atoms):
        parts = lines[i].split()
        if len(parts) < 4:
            continue
        atoms.append(parts[0])
        coords.append([float(x) for x in parts[1:4]])

    if not atoms:
        raise ValueError(f"file kosong: {path}")

    coords = np.array(coords)

    # SMILES ada di baris ke-3 dari belakang
    smiles = None
    name = None
    if len(lines) >= n_atoms + 5:
        smiles_line = lines[n_atoms + 3].split()
        if smiles_line:
            smiles = smiles_line[0]
            name = smiles_to_name(smiles)

    return {
        "mol_id": path.stem,
        "n_atoms": n_atoms,
        "atoms": atoms,
        "coords": coords,
        "properties": props,
        "smiles": smiles,
        "name": name,
    }
