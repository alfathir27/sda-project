"""
Parser SMILES minimal untuk tier 3 fallback.

Subset yang didukung (cukup buat 99% kasus QM9 + permintaan umum):
  - atom: [A-Z][a-z]? (B, C, N, O, F, S, Cl, Br) + lowercase aromatik (c, n, o, s)
  - bracket atom: [H], [NH4+], dll (charge & H count diabaikan, cuma elemen yg dipakai)
  - bond: '-' single, '=' double, '#' triple, ':' aromatic (semuanya dianggap edge sederhana)
  - branch: '(' ... ')'
  - ring closure: digit 1-9 dan %nn

Output: {atoms: [str], bonds: [(i, j, order)]}.
Order disimpan tapi belum dipakai di rendering (semua bond ditampilkan sebagai
garis tunggal — sesuai konteks SDA: kita visualisasi struktur graf, bukan
representasi kimia akurat).
"""

import re
from typing import List, Tuple, Dict


# token regex: bracket atom, organik subset, bond, branch, ring digit
_TOKEN_RE = re.compile(
    r"""
    (\[[^\]]+\])           |   # bracket atom [NH4+]
    (Br|Cl|B|C|N|O|F|P|S|I|H) |  # organic subset (uppercase)
    ([bcnops])             |   # aromatic (lowercase)
    ([=#:\-/\\])           |   # bond
    (\()                   |   # branch open
    (\))                   |   # branch close
    (%\d{2})               |   # ring closure 2-digit
    (\d)                   |   # ring closure 1-digit
    (.)                        # unknown -> error
    """,
    re.VERBOSE,
)

_BOND_ORDER = {"-": 1, "=": 2, "#": 3, ":": 1, "/": 1, "\\": 1}

# valence default untuk atom organik. dipakai buat hitung implicit H.
# aromatik (lowercase) butuh 1 H lebih sedikit karena bond aromatic ~1.5
_VALENCE = {
    "B": 3, "C": 4, "N": 3, "O": 2, "P": 3, "S": 2,
    "F": 1, "Cl": 1, "Br": 1, "I": 1, "H": 1,
}


def parse_smiles(smiles: str) -> Dict:
    """Parse SMILES jadi list atom + bond. Raise ValueError kalau invalid."""
    if not smiles or not smiles.strip():
        raise ValueError("SMILES kosong")

    atoms: List[str] = []
    bonds: List[Tuple[int, int, int]] = []
    branch_stack: List[int] = []   # stack of last-atom-index sebelum '('
    ring_open: Dict[str, Tuple[int, int]] = {}  # ring digit -> (atom_idx, pending_order)
    prev: int = -1                 # index atom terakhir
    pending_order: int = 1         # order untuk bond berikutnya
    is_aromatic: List[bool] = []   # tandai atom aromatik untuk implicit H
    in_bracket: List[bool] = []    # bracket atom -> jangan tambah implicit H

    for m in _TOKEN_RE.finditer(smiles):
        bracket, organic, aromatic, bond, br_open, br_close, ring_long, ring_short, unknown = m.groups()

        if bracket:
            inner = bracket[1:-1]
            el_match = re.match(r"\d*([A-Z][a-z]?|[a-z])", inner)
            if not el_match:
                raise ValueError(f"Bracket atom invalid: {bracket}")
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
                raise ValueError("')' tanpa '(' yang sesuai")
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
            raise ValueError(f"Token tidak dikenal: {unknown!r}")

    if branch_stack:
        raise ValueError("'(' tanpa ')' yang sesuai")
    if ring_open:
        raise ValueError(f"Ring closure tidak lengkap: {list(ring_open)}")
    if not atoms:
        raise ValueError("Tidak ada atom")

    # tambah implicit hydrogen untuk atom organik (bukan bracket)
    _add_implicit_h(atoms, bonds, is_aromatic, in_bracket)

    return {"atoms": atoms, "bonds": bonds}


def _add_implicit_h(atoms, bonds, is_aromatic, in_bracket):
    """Hitung sisa valence, tambah atom H + bond untuk tiap atom organik."""
    # hitung total bond order per atom
    bond_sum = [0] * len(atoms)
    for i, j, order in bonds:
        # bond aromatik dihitung 1.5, dibulatkan ke 1 saat compute valence
        bond_sum[i] += order
        bond_sum[j] += order

    n_original = len(atoms)
    for i in range(n_original):
        if in_bracket[i]:
            continue  # bracket atom: H sudah eksplisit di SMILES
        el = atoms[i]
        valence = _VALENCE.get(el)
        if valence is None:
            continue
        # aromatic atom: anggap salah satu bond aromatik 1.5, jadi efektif +0.5
        # praktis: tambah 1 ke bond_sum kalau atom aromatik (untuk koreksi)
        effective = bond_sum[i] + (1 if is_aromatic[i] else 0)
        n_h = max(0, valence - effective)
        for _ in range(n_h):
            atoms.append("H")
            is_aromatic.append(False)
            in_bracket.append(False)
            bonds.append((i, len(atoms) - 1, 1))
