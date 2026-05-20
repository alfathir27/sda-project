from pathlib import Path
from typing import List
import numpy as np

COVALENT_RADII = {
    'H': 0.31, 'C': 0.76, 'N': 0.71, 'O': 0.66, 'F': 0.57,
    'S': 1.05, 'Cl': 0.99, 'P': 1.07, 'Si': 1.11, 'Br': 1.14,
    'B': 0.84, 'Li': 1.28, 'Na': 1.66, 'Mg': 1.41, 'Al': 1.21,
    'K': 2.03, 'Ca': 1.76, 'Fe': 1.32, 'Cu': 1.32, 'Zn': 1.22,
}

PROPERTIES_NAMES = [
    "tag", "index", "A_GHz", "B_GHz", "C_GHz", "mu_Debye", "alpha_Bohr3",
    "homo_Hartree", "lumo_Hartree", "gap_Hartree", "r2_Bohr2",
    "zpve_Hartree", "U0_Hartree", "U_Hartree", "H_Hartree", "G_Hartree", "Cv_cal_mol_K"
]


def parse_xyz(path: Path) -> dict:
    with open(path, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]

    n_atoms = int(lines[0])

    # QM9 format: line 2 starts with 'gdb' tag, then index, then 15 numeric properties
    # Example: gdb 1   157.7118  157.70997  157.70699  0.  13.21  -0.3877  ...
    props_line = lines[1].split()
    props = {}
    # Skip 'gdb' tag at index 0, then map properties starting from index 1
    prop_keys = PROPERTIES_NAMES[1:]  # skip 'tag', keep index + 15 properties
    for i, name in enumerate(prop_keys):
        idx = i + 1  # offset by 1 to skip 'gdb'
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
        raise ValueError(f"No atoms found in {path}")

    coords = np.array(coords)

    return {
        "mol_id": path.stem,
        "n_atoms": n_atoms,
        "atoms": atoms,
        "coords": coords,
        "properties": props,
    }
