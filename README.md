# Pengembangan Aplikasi Web Interaktif untuk Visualisasi Graf Molekul dan Eksplorasi Properti Kuantum pada Dataset QM9

Aplikasi web monolitik untuk mengeksplorasi dataset QM9 dalam bentuk graf 2D interaktif. Backend Python (FastAPI) memproses data molekul dan menyajikan API + static files, frontend vanilla HTML/CSS/JS menampilkan visualisasi graf menggunakan Cytoscape.js.

## Tentang Dataset QM9

**QM9** adalah dataset komputasional yang berisi **133.885 molekul organik kecil** (hingga 9 atom berat: C, N, O, F) yang dikurasi oleh Ramakrishnan et al. (2014). Dataset ini merupakan subset dari GDB-17 (database 166 miliar molekul organik virtual) dan banyak digunakan dalam riset machine learning untuk prediksi properti molekul.

### Sumber

Proyek ini mengacu pada paper:

> **Adaptive edge-aware graph convolutional with multi-task learning for simultaneous prediction of material properties**
>
> Scopus: https://www.scopus.com/pages/publications/105028524571?origin=resultslist

Paper tersebut menggunakan dataset QM9 untuk prediksi properti material secara simultan menggunakan graph neural network. Implementasi di proyek ini **berfokus pada visualisasi graf molekul** — menampilkan struktur graf 2D interaktif, inferensi ikatan, dan eksplorasi properti — bukan pada model prediktif.

Dataset QM9 sendiri dipublikasikan oleh:

- Ramakrishnan, R., Dral, P.O., Rupp, M., & von Lilienfeld, O.A. (2014). *Quantum chemistry structures and properties of 134 kilo molecules.* Scientific Data, 1, 140022.
- **Download**: https://ndownloader.figshare.com/files/3195389 (`dsgdb9nsd.xyz.tar.bz2`)

### Format File

Setiap molekul disimpan dalam file `.xyz` dengan format:

```
<n_atoms>                                    ← Baris 1: jumlah atom
gdb <index> <prop1> <prop2> ... <prop16>    ← Baris 2: tag gdb + 16 properti
<element> <x> <y> <z> <partial_charge>      ← Baris 3..n+2: koordinat 3D atom
...                                          ← (satu baris per atom)
<freq1> <freq2> ... <freq3N-6>              ← Baris n+3: frekuensi vibrasi
<SMILES1> <SMILES2>                         ← Baris n+4: SMILES (kanonik + isotopik)
<InChI1> <InChI2>                           ← Baris n+5: InChI
```

### 16 Properti Per Molekul

Semua properti dihitung dengan metode DFT (B3LYP/6-31G(2df,2p)):

| # | Nama | Satuan | Deskripsi |
|---|------|--------|-----------|
| 1 | tag | — | Identifikasi gdb |
| 2 | index | — | Indeks molekul |
| 3 | A | GHz | Konstanta rotasi A |
| 4 | B | GHz | Konstanta rotasi B |
| 5 | C | GHz | Konstanta rotasi C |
| 6 | μ | Debye | Momen dipol |
| 7 | α | Bohr³ | Polarizabilitas isotropik |
| 8 | ε_HOMO | Hartree | Energi HOMO (orbital molekul terisi tertinggi) |
| 9 | ε_LUMO | Hartree | Energi LUMO (orbital molekul kosong terendah) |
| 10 | Δε | Hartree | Gap HOMO-LUMO (ε_LUMO − ε_HOMO) |
| 11 | ⟨R²⟩ | Bohr² | Luas spatial elektronik |
| 12 | ZPVE | Hartree | Energi titik nol vibrasional |
| 13 | U₀ | Hartree | Energi dalam pada 0 K |
| 14 | U | Hartree | Energi dalam pada 298.15 K |
| 15 | H | Hartree | Entalpi pada 298.15 K |
| 16 | G | Hartree | Energi bebas Gibbs pada 298.15 K |
| 17 | C_v | cal/mol·K | Kapasitas panas pada 298.15 K |

### Elemen yang Terwakili

QM9 hanya mengandung molekul dengan atom berat (non-H) hingga 9 buah, tersusun dari:

- **C** (Karbon), **N** (Nitrogen), **O** (Oksigen), **F** (Fluorin)
- Ditambah atom **H** (Hidrogen) sebagai ligan

Contoh molekul: Methane (CH₄), Water (H₂O), Ammonia (NH₃), Ethanol (C₂H₅OH), Benzene (C₆H₆), Acetone (C₃H₆O), dll.

## Arsitektur Aplikasi

```
SDA/
├── backend/
│   ├── main.py              # FastAPI app: API endpoints + static file serving
│   ├── qm9_loader.py        # Parser file .xyz QM9 + resolver nama via PubChem API
│   ├── graph_processor.py   # Inferensi ikatan kimia + layout 2D (NetworkX)
│   ├── data_manager.py      # Manajemen dataset: load, cache, query
│   ├── requirements.txt     # Dependensi Python
│   ├── .venv/               # Virtual environment
│   └── static/
│       ├── index.html        # UI utama
│       ├── style.css         # Styling
│       └── app.js            # Logika frontend (vanilla JS + Cytoscape.js)
└── data/
    ├── qm9_raw/              # 133.885 file .xyz (di-gitignore)
    └── qm9_processed/
        ├── cache.pkl         # Cache dataset yang sudah diproses
        └── names_cache.json  # Cache nama molekul dari PubChem
```

### Alur Pemrosesan Data

1. **Parsing** — `qm9_loader.py` membaca file `.xyz`, mengekstrak atom, koordinat 3D, properti, dan SMILES
2. **Inferensi Ikatan** — `graph_processor.py` menghitung jarak antar-atom dan menentukan ikatan berdasarkan jumlah jari-jari kovalen + toleransi (0.45 Å)
3. **Layout 2D** — Menggunakan algoritma Kamada-Kawai (NetworkX) untuk menempatkan node dalam bidang 2D
4. **Resolusi Nama** — SMILES di-resolve ke nama IUPAC/umum via PubChem PUG REST API, hasil di-cache permanen
5. **Caching** — Dataset yang sudah diproses disimpan sebagai pickle untuk loading cepat

### API Endpoints

| Method | Path | Deskripsi |
|--------|------|-----------|
| GET | `/molecules?limit=&offset=` | Daftar molekul (paginasi) |
| GET | `/molecules/{mol_id}` | Detail molekul: node, edge, properti |
| POST | `/compare` | Bandingkan beberapa molekul (body: `{"ids": [...]}`) |
| GET | `/properties/stats` | Statistik (min/max/mean) per properti |
| POST | `/resolve-names` | Trigger resolusi nama via PubChem API |

### Fitur Frontend

- **Molecule Library** — daftar molekul dengan nama, formula, dan properti ringkas; paginasi dan pencarian
- **2D Graph Viewer** — visualisasi graf molekul interaktif (zoom, pan) dengan warna per elemen
- **Properties Panel** — tampilan lengkap 16 properti kuantum
- **Compare Mode** — bandingkan hingga 4 molekul secara side-by-side

## Cara Menjalankan

```bash
# Setup (sekali saja)
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Jalankan server
backend/.venv/bin/uvicorn main:app --app-dir backend --host 0.0.0.0 --port 8000
```

Buka `http://localhost:8000` di browser.

### Resolusi Nama Molekul

Nama molekul di-resolve secara bertahap. Pada loading pertama, nama yang sudah ada di dictionary lokal langsung tampil. Untuk resolve sisanya via PubChem:

```bash
curl -X POST http://localhost:8000/resolve-names
```

Proses ini membutuhkan beberapa menit (rate limit 5 req/detik), namun hasilnya di-cache permanen di `data/qm9_processed/names_cache.json`.

## Dependensi

**Backend (Python):**
- FastAPI, Uvicorn — web framework & server
- NetworkX — layout graf 2D
- NumPy — komputasi numerik
- Pandas — manipulasi data
- Pydantic — validasi schema

**Frontend (CDN):**
- Cytoscape.js — visualisasi graf interaktif
