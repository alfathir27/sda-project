# Pengembangan Aplikasi Web Interaktif untuk Visualisasi Graf Molekul dan Eksplorasi Properti Kuantum pada Dataset QM9

Aplikasi web monolitik yang menerapkan konsep **Struktur Data dan Algoritma**. Beberapa konsep yang dipakai meliputi struktur graf, algoritma pembentukan graf, algoritma layout berbasis gaya, hash map, dan strategi caching. Tujuannya adalah memproses lalu menggambar molekul dari dataset QM9 dalam bentuk graf 2D yang interaktif.

## Fokus SDA: Struktur Data dan Algoritma yang Diterapkan

### Struktur Data Graf (Adjacency List)

Setiap molekul digambarkan sebagai graf \( G = (V, E) \) dengan rincian:
- **Node** = atom, lengkap dengan atribut elemen, koordinat 3D, dan posisi 2D.
- **Edge** = ikatan kimia, beserta bobot berupa jarak antar atom.

Implementasinya memakai **adjacency list** lewat NetworkX (`nx.Graph`). Pilihan ini diambil karena graf molekul tergolong **sparse**, dengan rata-rata derajat sekitar 2 saja. Kalau dipaksakan ke adjacency matrix berukuran O(n²), banyak slot yang kosong sehingga memori jadi terbuang sia-sia.

### Algoritma Konstruksi Graf, O(n²)

Pada dataset QM9, file mentah yang tersedia hanya memuat koordinat 3D atom **tanpa keterangan ikatan**. Karena itu, edge harus dibentuk sendiri lewat algoritma berbasis jarak antar atom:

```
INFER-BONDS(atoms, coords, tolerance=0.45):
  for i ← 0 to n-1:
      for j ← i+1 to n-1:              // segitiga atas (graf undirected)
          dist ← EUCLIDEAN-DISTANCE(coords[i], coords[j])
          if dist < COVALENT_RADII[i] + COVALENT_RADII[j] + tolerance:
              add_edge(i, j, weight=dist)
```

Nilai jari-jari kovalen tiap elemen disimpan dalam **hash map** bernama `COVALENT_RADII`, sehingga proses pengambilan datanya berlangsung dalam waktu konstan O(1).

### Algoritma Layout 2D (Force-Directed)

1. **Kamada-Kawai** sebagai pilihan utama. Algoritma ini bekerja dengan meminimalkan energi sistem pegas, di mana panjang ideal antar node dibuat sebanding dengan shortest path. Kompleksitasnya O(n³) untuk perhitungan shortest path dan O(n²) per iterasi Newton-Raphson.
2. **Fruchterman-Reingold** dipakai sebagai cadangan ketika graf tidak terhubung. Algoritma ini mengkombinasikan gaya tarik antar tetangga dengan gaya tolak pairwise. Kompleksitasnya O(iter × n²).

### Hash Map (Pencarian O(1))

| Hash Map | Key → Value | Kegunaan |
|----------|-------------|----------|
| `meta` | mol_id → metadata | Lookup molekul by ID |
| `formula_idx` | formula (Hill) → list mol_id | Cari molekul by rumus kimia (mis. `H2O`, `C6H6`) |
| `smiles_idx` | SMILES → mol_id | Cari molekul by SMILES |
| `COVALENT_RADII` | element → radius | Inferensi ikatan |
| `SMILES_TO_NAME` | SMILES → nama | Resolusi nama lokal |
| `names_cache.json` | SMILES → nama | Cache nama PubChem |
| `ATOM_COLORS` | element → hex color | Warna node di frontend |

Rantai akses datanya kira-kira begini: `query → hash map → mol_id → cache pickle / parse on-demand`. Hasil akhirnya berkecepatan **O(1)** untuk lookup, ditambah satu kali parse file `.xyz` ketika molekul dibuka pertama kali.

### Caching (Trade-off Waktu vs Ruang)

| Level | Format | Isi | Efek |
|-------|--------|-----|------|
| Index | JSON | Metadata seluruh 134K molekul (formula, SMILES, nama, properti) | Startup sekitar 1 detik, lookup tetap O(1) |
| Cache | Pickle | Molekul yang sudah pernah diakses pengguna (graf + layout) | Detail jadi langsung tampil setelah parse pertama |
| Names | JSON | Hash map SMILES ke nama hasil resolusi PubChem | Mencegah pemanggilan API berulang kali |

---

## Tentang Dataset QM9

Dataset **QM9** memuat **133.885 molekul organik kecil** dengan maksimal 9 atom berat (C, N, O, F). Setiap molekul disertai 16 properti kuantum hasil hitungan DFT pada level B3LYP/6-31G(2df,2p). Paper rujukan utamanya:

> **Adaptive edge-aware graph convolutional with multi-task learning for simultaneous prediction of material properties**
>
> Scopus: https://www.scopus.com/pages/publications/105028524571

Cakupan proyek ini berhenti di tahap **pengelolaan graf**, mulai dari konstruksi, representasi, layout, sampai visualisasi. Pengembangan model prediktif tidak masuk lingkup pembahasan.

---

## Arsitektur

```
SDA/
├── setup.py                    # Otomatisasi: venv, install deps, download dataset, build index
├── backend/
│   ├── main.py                 # FastAPI: API + static serving
│   ├── qm9_loader.py           # Parser .xyz + hash map nama (PubChem)
│   ├── graph_processor.py      # Konstruksi graf + algoritma layout 2D
│   ├── data_manager.py         # Lazy load via index, cache pickle, query O(1)
│   ├── index_builder.py        # Scan 134K .xyz → hash map index
│   ├── smiles_parser.py        # Parser SMILES untuk fallback render
│   ├── requirements.txt
│   └── static/
│       ├── index.html
│       ├── style.css
│       └── app.js              # Cytoscape.js: rendering graf (adjacency list)
└── data/
    ├── qm9_raw/                # 133.885 file .xyz
    └── qm9_processed/
        ├── index.json          # Hash map: formula/SMILES → mol_id + metadata
        ├── cache.pkl           # Cache molekul yang sudah pernah dibuka
        └── names_cache.json    # Hash map SMILES → nama
```

### API Endpoints

| Method | Path | Deskripsi | Kompleksitas |
|--------|------|-----------|--------------|
| GET | `/molecules?limit=&offset=` | Daftar molekul | O(limit) |
| GET | `/molecules/{mol_id}` | Detail graf + properti (lazy parse) | O(1) cached, O(n²) parse pertama |
| GET | `/search?q=` | Cari by formula / SMILES / substring | O(1) untuk formula & SMILES |
| POST | `/render-formula` | Render graf naif dari formula (fallback) | O(n) + O(n³) layout |
| POST | `/render-smiles` | Render graf dari SMILES (fallback) | O(n) parse + O(n³) layout |
| POST | `/compare` | Bandingkan molekul | O(k) |
| GET | `/properties/stats` | Statistik 16 properti kuantum | O(n) |
| POST | `/resolve-names` | Resolusi nama PubChem | O(m) + network |

### Fitur Frontend

- **Daftar Molekul**: paginasi mencakup 134 ribu molekul, kolom pencarian dengan debounce di sisi server.
- **Search Tier**:
  - Tier 1: cek dulu di cache pickle (O(1))
  - Tier 2: cari di hash map indeks penuh berdasarkan formula atau SMILES (O(1))
  - Tier 3: render naif dari formula atau SMILES kalau molekul yang dicari tidak ada di dataset
- **2D Graph Viewer**: ditangani Cytoscape.js, lengkap dengan zoom, pan, dan node yang diwarnai per elemen.
- **Properties Panel**: menampilkan 16 properti kuantum hasil DFT.
- **Compare Mode**: pengguna bisa menampilkan sampai 4 graf secara berdampingan.

---

## Cara Menjalankan

```bash
# Setup otomatis: bikin venv, install deps, download dataset (~83 MB), extract, build index
python setup.py

# Jalankan
backend/.venv/bin/uvicorn main:app --app-dir backend --port 8000
```

Setelah server hidup, akses lewat `http://localhost:8000`. Bila ingin meresolve nama molekul melalui PubChem (cukup dijalankan sekali, prosesnya bisa memakan waktu beberapa menit):

```bash
curl -X POST http://localhost:8000/resolve-names
```

## Dependensi

- **NetworkX**: representasi graf berbasis adjacency list dan algoritma layout.
- **NumPy**: array koordinat dan perhitungan jarak Euclidean.
- **FastAPI + Uvicorn**: server web.
- **Cytoscape.js**: rendering graf interaktif di sisi peramban.
