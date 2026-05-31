# parser SMILES sederhana buat fallback render
# subset yg didukung:
#   - atom organik (B, C, N, O, F, P, S, Cl, Br, I, H) plus aromatik lowercase
#   - bracket atom kayak [NH4+], cuma elemennya yg dipakai
#   - bond: -, =, #, : (semua dianggap edge biasa)
#   - branch ( ), ring closure 1-9 dan %nn

import re

_TOKEN_RE = re.compile(
    r"""
    (\[[^\]]+\])           |
    (Br|Cl|B|C|N|O|F|P|S|I|H) |
    ([bcnops])             |
    ([=#:\-/\\])           |
    (\()                   |
    (\))                   |
    (%\d{2})               |
    (\d)                   |
    (.)
    """,
    re.VERBOSE,
)

_BOND_ORDER = {"-": 1, "=": 2, "#": 3, ":": 1, "/": 1, "\\": 1}

# valensi default buat hitung implicit H
_VALENCE = {
    "B": 3, "C": 4, "N": 3, "O": 2, "P": 3, "S": 2,
    "F": 1, "Cl": 1, "Br": 1, "I": 1, "H": 1,
}


def parse_smiles(smiles):
    if not smiles or not smiles.strip():
        raise ValueError("smiles kosong")

    atoms = []
    bonds = []
    branch_stack = []
    ring_open = {}
    prev = -1
    pending_order = 1
    is_aromatic = []
    in_bracket = []

    for m in _TOKEN_RE.finditer(smiles):
        bracket, organic, aromatic, bond, br_open, br_close, ring_long, ring_short, unknown = m.groups()

        if bracket:
            inner = bracket[1:-1]
            el_match = re.match(r"\d*([A-Z][a-z]?|[a-z])", inner)
            if not el_match:
                raise ValueError(f"bracket atom invalid: {bracket}")
            el = el_match.group(1)
            atoms.append(el[0].upper() + el[1:] if len(el) > 1 else el.upper())
            is_aromatic.append(False)
            in_bracket.append(True)
            if prev >= 0:
                bonds.append((prev, len(atoms) - 1, pending_order))
            prev = len(atoms) - 1
            pending_order = 1
        elif organic:
            atoms.append(organic)
            is_aromatic.append(False)
            in_bracket.append(False)
            if prev >= 0:
                bonds.append((prev, len(atoms) - 1, pending_order))
            prev = len(atoms) - 1
            pending_order = 1
        elif aromatic:
            atoms.append(aromatic.upper())
            is_aromatic.append(True)
            in_bracket.append(False)
            if prev >= 0:
                bonds.append((prev, len(atoms) - 1, pending_order))
            prev = len(atoms) - 1
            pending_order = 1
        elif bond:
            pending_order = _BOND_ORDER.get(bond, 1)
        elif br_open:
            branch_stack.append(prev)
        elif br_close:
            if not branch_stack:
                raise ValueError("')' tanpa '('")
            prev = branch_stack.pop()
        elif ring_long or ring_short:
            digit = ring_long or ring_short
            if digit in ring_open:
                start_idx, start_order = ring_open.pop(digit)
                order = max(start_order, pending_order)
                bonds.append((start_idx, prev, order))
                pending_order = 1
            else:
                ring_open[digit] = (prev, pending_order)
                pending_order = 1
        elif unknown:
            raise ValueError(f"token tidak dikenal: {unknown!r}")

    if branch_stack:
        raise ValueError("'(' tanpa ')'")
    if ring_open:
        raise ValueError(f"ring closure tidak lengkap: {list(ring_open)}")
    if not atoms:
        raise ValueError("tidak ada atom")

    _add_implicit_h(atoms, bonds, is_aromatic, in_bracket)
    return {"atoms": atoms, "bonds": bonds}


def _add_implicit_h(atoms, bonds, is_aromatic, in_bracket):
    bond_sum = [0] * len(atoms)
    for i, j, order in bonds:
        bond_sum[i] += order
        bond_sum[j] += order

    n_original = len(atoms)
    for i in range(n_original):
        if in_bracket[i]:
            continue
        el = atoms[i]
        valence = _VALENCE.get(el)
        if valence is None:
            continue
        # atom aromatik: tambah 1 ke bond_sum buat koreksi bond aromatic ~1.5
        effective = bond_sum[i] + (1 if is_aromatic[i] else 0)
        n_h = max(0, valence - effective)
        for _ in range(n_h):
            atoms.append("H")
            is_aromatic.append(False)
            in_bracket.append(False)
            bonds.append((i, len(atoms) - 1, 1))
