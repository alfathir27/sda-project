import numpy as np
import networkx as nx
from qm9_loader import COVALENT_RADII


def infer_bonds(atoms, coords, tolerance=0.45):
    n = len(atoms)
    bonds = []
    for i in range(n):
        for j in range(i + 1, n):
            r1 = COVALENT_RADII.get(atoms[i], 0.7)
            r2 = COVALENT_RADII.get(atoms[j], 0.7)
            dist = float(np.linalg.norm(coords[i] - coords[j]))
            if dist < (r1 + r2 + tolerance):
                bonds.append((i, j, dist))
    return bonds


def compute_2d_layout(atoms, bonds, seed=42):
    G = nx.Graph()
    for i, atom in enumerate(atoms):
        G.add_node(i, element=atom)
    for i, j, dist in bonds:
        G.add_edge(i, j, length=dist)

    if len(atoms) == 1:
        return {0: (0.0, 0.0)}

    try:
        pos = nx.kamada_kawai_layout(G)
    except (nx.NetworkXError, ValueError):
        # Kamada-Kawai gagal pada graf tidak terhubung — fallback ke Fruchterman-Reingold
        pos = nx.spring_layout(G, seed=seed, k=2.0)

    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    range_x = max_x - min_x if max_x != min_x else 1.0
    range_y = max_y - min_y if max_y != min_y else 1.0
    scale = 300.0 / max(range_x, range_y)

    centered = {}
    for node_id, (x, y) in pos.items():
        cx = (x - min_x - range_x / 2) * scale
        cy = (y - min_y - range_y / 2) * scale
        centered[node_id] = (float(cx), float(cy))
    return centered
