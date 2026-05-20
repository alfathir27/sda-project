# Pengembangan Aplikasi Web Interaktif untuk Visualisasi Graf Molekul dan Eksplorasi Properti Kuantum pada Dataset QM9

Aplikasi web monolitik yang menerapkan konsep **Struktur Data dan Algoritma** — khususnya struktur graf, algoritma konstruksi graf, algoritma layout force-directed, hash map, dan caching — untuk memproses dan memvisualisasikan molekul dari dataset QM9 sebagai graf 2D interaktif.

## Fokus SDA: Struktur Data dan Algoritma yang Diterapkan

### Struktur Data Graf (Adjacency List)

Molekul direpresentasikan sebagai graf \( G = (V, E) \):
- **Node** = atom (dengan atribut: elemen, koordinat, posisi 2D)
- **Edge** = ikatan kimia (dengan bobot: jarak antar-atom)

Representasi menggunakan **adjacency list** (NetworkX `nx.Graph`), dipilih karena graf molekul bersifat **sparse** — rata-rata degree ≈ 2, jauh di bawah n-1. Adjacency matrix O(n²) akan memboroskan memori.

### Algoritma Konstruksi Graf — O(n²)

Dataset QM9 hanya menyediakan koordinat 3D atom, **tanpa informasi ikatan**. Edge dikonstruksi dengan algoritma berbasis jarak:

```
INFER-BONDS(atoms, coords, tolerance=0.45):
  for i ← 0 to n-1:
      for j ← i+1 to n-1:              // segitiga atas (graf undirected)
          dist ← EUCLIDEAN-DISTANCE(coords[i], coords[j])
          if dist < COVALENT_RADII[i] + COVALENT_RADII[j] + tolerance:
              add_edge(i, j, weight=dist)
```

Jari-jari kovalen disimpan dalam **hash map** (`COVALENT_RADII`) untuk lookup O(1).

### Algoritma Layout 2D — Force-Directed

1. **Kamada-Kawai** (prioritas): Meminimalkan energi sistem pegas. Panjang ideal antar-node proporsional terhadap shortest path. Kompleksitas: O(n³) untuk shortest path + O(n²) per iterasi Newton-Raphson.
2. **Fruchterman-Reingold** (fallback): Gaya tarik antar tetangga + gaya tolak pairwise. Digunakan jika graf tidak terhubung. Kompleksitas: O(iter × n²).

### Hash Map — Pencarian O(1)

| Hash Map | Key → Value | Kegunaan |
|----------|-------------|----------|
| `_id_to_idx` | mol_id → array index | Lookup molekul by ID |
| `COVALENT_RADII` | element → radius | Inferensi ikatan |
| `SMILES_TO_NAME` | SMILES → nama | Resolusi nama lokal |
| `names_cache.json` | SMILES → nama | Cache nama PubChem |
| `ATOM_COLORS` | element → hex color | Warna node di frontend |

Rantai lookup: `mol_id → hash map → index → array → molecule`. Total: **O(1)**.

### Caching — Trade-off Waktu vs Ruang

| Level | Format | Isi | Efek |
|-------|--------|-----|------|
| Pickle | Binary | Graf + properti lengkap | Startup: 30s → 2s |
| JSON | Text | Hash map SMILES → nama | Hindari API call ulang |

---

## Tentang Dataset QM9

**QM9** berisi **133.885 molekul organik kecil** (hingga 9 atom berat: C, N, O, F) dengan 16 properti kuantum (DFT B3LYP/6-31G(2df,2p)). Paper rujukan:

> **Adaptive edge-aware graph convolutional with multi-task learning for simultaneous prediction of material properties**
>
> Scopus: https://www.scopus.com/pages/publications/105028524571

Proyek ini berfokus pada **pengelolaan graf** (konstruksi, representasi, layout, visualisasi), bukan pada model prediktif.

---

## Arsitektur

```
SDA/
├── backend/
│   ├── main.py              # FastAPI: API + static serving
│   ├── qm9_loader.py        # Parser .xyz + hash map nama (PubChem)
│   ├── graph_processor.py   # Konstruksi graf + algoritma layout 2D
│   ├── data_manager.py      # Orkestrasi: cache (pickle/JSON), query O(1)
│   ├── requirements.txt
│   └── static/
│       ├── index.html
│       ├── style.css
│       └── app.js            # Cytoscape.js: rendering graf (adjacency list)
└── data/
    ├── qm9_raw/
    └── qm9_processed/
        ├── cache.pkl         # Serialisasi biner dataset
        └── names_cache.json  # Hash map SMILES → nama
```

### API Endpoints

| Method | Path | Deskripsi | Kompleksitas |
|--------|------|-----------|--------------|
| GET | `/molecules?limit=&offset=` | Daftar molekul | O(limit) |
| GET | `/molecules/{mol_id}` | Detail graf + properti | O(1) |
| POST | `/compare` | Bandingkan molekul | O(k) |
| GET | `/properties/stats` | Statistik properti | O(n) |
| POST | `/resolve-names` | Resolusi nama PubChem | O(m) + network |

### Fitur Frontend

- **Molecule Library** — daftar dengan nama, formula, properti; paginasi + pencarian
- **2D Graph Viewer** — Cytoscape.js: zoom, pan, node berwarna per elemen
- **Properties Panel** — 16 properti kuantum
- **Compare Mode** — hingga 4 graf side-by-side

---

## Cara Menjalankan

```bash
# Setup
cd backend && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

# Jalankan
backend/.venv/bin/uvicorn main:app --app-dir backend --host 0.0.0.0 --port 8000
```

Buka `http://localhost:8000`. Untuk resolve nama molekul via PubChem (sekali saja):

```bash
curl -X POST http://localhost:8000/resolve-names
```

## Dependensi

- **NetworkX** — representasi graf (adjacency list), algoritma layout
- **NumPy** — array koordinat, jarak Euclidean
- **FastAPI + Uvicorn** — web server
- **Cytoscape.js** — rendering graf interaktif
