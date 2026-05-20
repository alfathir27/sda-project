# LAPORAN PROYEK

# Visualisasi Graf Molekul Dataset QM9 Berbasis Web Interaktif

---

## BAB I PENDAHULUAN

### 1.1 Latar Belakang

Perkembangan ilmu kimia komputasional telah menghasilkan dataset molekul berskala besar yang memuat informasi struktural dan properti kuantum. Salah satu dataset yang paling banyak digunakan dalam komunitas riset adalah QM9, yang berisi 133.885 molekul organik kecil beserta 16 properti kuantum yang dihitung menggunakan metode Density Functional Theory (DFT).

Paper *"Adaptive edge-aware graph convolutional with multi-task learning for simultaneous prediction of material properties"* mendemonstrasikan penggunaan graph neural network pada dataset QM9 untuk prediksi properti material secara simultan. Dalam konteks tersebut, representasi molekul sebagai graf — di mana atom menjadi node dan ikatan kimia menjadi edge — merupakan fondasi utama bagi pemrosesan dan pembelajaran mesin.

Namun, eksplorasi visual terhadap struktur graf molekul dalam dataset QM9 masih terbatas. Peneliti umumnya berinteraksi dengan data melalui skrip pemrograman tanpa antarmuka visual yang intuitif. Padahal, visualisasi graf molekul secara interaktif dapat membantu pemahaman terhadap hubungan struktur-properti, validasi inferensi ikatan, dan identifikasi pola dalam dataset.

Berdasarkan kesenjangan tersebut, proyek ini mengembangkan sebuah aplikasi web interaktif untuk visualisasi graf 2D molekul-molekul dalam dataset QM9, dengan fitur eksplorasi, perbandingan, dan tampilan properti kuantum.

### 1.2 Rumusan Masalah

1. Bagaimana memproses dataset QM9 dari format file `.xyz` menjadi representasi graf (node = atom, edge = ikatan) yang siap divisualisasikan?
2. Bagaimana menginferensi ikatan kimia antar-atom berdasarkan koordinat 3D tanpa menggunakan pustaka kemoinformatika yang berat (seperti RDKit)?
3. Bagaimana menghasilkan layout 2D yang informatif untuk visualisasi graf molekul?
4. Bagaimana membangun antarmuka web interaktif yang memungkinkan eksplorasi, seleksi, dan perbandingan molekul secara efisien?

### 1.3 Tujuan

1. Mengembangkan pipeline pemrosesan data QM9 yang mencakup parsing, inferensi ikatan, dan komputasi layout 2D.
2. Membangun backend API berbasis FastAPI yang menyajikan data graf dan properti molekul.
3. Membangun frontend web interaktif berbasis vanilla HTML/CSS/JS dan Cytoscape.js untuk visualisasi graf molekul.
4. Mengintegrasikan resolusi nama molekul via PubChem API untuk meningkatkan keterbacaan data.

### 1.4 Manfaat

- **Akademik**: Menjadi sarana visualisasi pendukung dalam riset machine learning pada dataset QM9, khususnya yang berkaitan dengan graph-based learning.
- **Praktis**: Memudahkan peneliti dan praktisi dalam mengeksplorasi struktur dan properti molekul tanpa menulis kode.
- **Edukatif**: Menjadi media pembelajaran interaktif untuk memahami hubungan antara struktur graf molekul dan properti kuantumnya.

### 1.5 Batasan

1. Dataset yang diproses dibatasi hingga 2.000 molekul (subset dari 133.885) untuk efisiensi komputasi dan penyimpanan.
2. Inferensi ikatan menggunakan pendekatan berbasis jarak (covalent radii + tolerance), bukan dari data topologi eksplisit.
3. Visualisasi hanya dalam bentuk graf 2D; tidak ada rendering struktur 3D.
4. Nama molekul di-resolve via PubChem API; molekul yang tidak ditemukan di PubChem tetap ditampilkan dengan ID dataset.

---

## BAB II TINJAUAN PUSTAKA

### 2.1 Dataset QM9

Dataset QM9 dikurasi oleh Ramakrishnan et al. (2014) dan dipublikasikan dalam jurnal *Scient Data*. Dataset ini merupakan subset dari GDB-17 — database virtual yang memuat 166 miliar molekul organik kecil yang mematuhi aturan valensi. QM9 memilih molekul dengan hingga 9 atom berat (C, N, O, F) dan menghitung properti kuantumnya menggunakan DFT pada level B3LYP/6-31G(2df,2p).

Setiap molekul direpresentasikan dalam file `.xyz` yang memuat:
- Jumlah atom
- 16 properti kuantum (rotational constants, momen dipol, polarizabilitas, HOMO/LUMO, gap, spatial extent, ZPVE, energi dalam, entalpi, energi bebas Gibbs, kapasitas panas)
- Koordinat 3D per atom beserta muatan parsial
- Frekuensi vibrasi
- SMILES kanonik dan isotopik
- InChI kanonik dan isotopik

### 2.2 Representasi Graf Molekul

Dalam konteks graph-based machine learning, molekul direpresentasikan sebagai graf \( G = (V, E) \) di mana:
- \( V = \{v_1, v_2, ..., v_n\} \) adalah himpunan node, masing-masing merepresentasikan atom dengan fitur (jenis elemen, muatan parsial, dll.)
- \( E \subseteq V \times V \) adalah himpunan edge yang merepresentasikan ikatan kimia antar-atom

Representasi ini memungkinkan penerapan graph neural network (GNN) untuk mempelajari hubungan struktur-properti, sebagaimana didemonstrasikan dalam paper rujukan yang menggunakan adaptive edge-aware graph convolutional network.

### 2.3 Inferensi Ikatan Kimia

Dalam file QM9, informasi ikatan tidak diberikan secara eksplisit — hanya koordinat 3D atom yang tersedia. Inferensi ikatan dapat dilakukan dengan pendekatan berbasis jarak:

Dua atom \( i \) dan \( j \) dianggap berikatan jika:

$$d_{ij} < r_i^{cov} + r_j^{cov} + \delta$$

di mana:
- \( d_{ij} \) = jarak Euclidean antar-atom
- \( r_i^{cov} \) = jari-jari kovalen atom \( i \)
- \( \delta \) = toleransi (pada proyek ini digunakan 0.45 Å)

Pendekatan ini sederhana namun efektif untuk molekul organik kecil tanpa stereochemistry yang kompleks.

### 2.4 Layout Graf 2D

Untuk visualisasi graf dalam bidang 2D, diperlukan algoritma layout yang menempatkan node pada posisi yang informatif. Algoritma yang digunakan:

1. **Kamada-Kawai**: Algoritma berbasis model spring yang meminimalkan energi dengan mempertimbangkan jarak graph-theoretic antar-node. Menghasilkan layout yang estetis dan terstruktur.
2. **Spring Layout (fallback)**: Jika Kamada-Kawai gagal (misalnya pada graf dengan komponen terputus), digunakan Fruchterman-Reingold spring layout sebagai alternatif.

### 2.5 SMILES dan PubChem

**SMILES** (Simplified Molecular-Input Line-Entry System) adalah notasi linear yang merepresentasikan struktur molekul sebagai string. Contoh: `C` untuk Methane, `CCO` untuk Ethanol, `c1ccccc1` untuk Benzene.

**PubChem** adalah database kimia milik NCBI yang menyediakan PUG REST API untuk mengakses data molekul secara programatik. API ini digunakan dalam proyek untuk menerjemahkan SMILES menjadi nama IUPAC atau nama umum molekul.

### 2.6 Teknologi yang Digunakan

#### 2.6.1 Backend

- **Python 3**: Bahasa pemrograman utama untuk pemrosesan data dan API
- **FastAPI**: Framework web modern yang mendukung async, validasi otomatis, dan dokumentasi OpenAPI
- **NetworkX**: Pustaka Python untuk analisis dan visualisasi graf, digunakan untuk komputasi layout 2D
- **NumPy**: Pustaka komputasi numerik untuk operasi array dan kalkulasi jarak
- **Uvicorn**: ASGI server untuk menjalankan aplikasi FastAPI

#### 2.6.2 Frontend

- **HTML5/CSS3/JavaScript (Vanilla)**: Tanpa framework frontend untuk kesederhanaan dan performa
- **Cytoscape.js**: Pustaka JavaScript untuk visualisasi graf interaktif dengan dukungan zoom, pan, dan styling per elemen

---

## BAB III METODOLOGI

### 3.1 Desain Sistem

Sistem dibangun dengan arsitektur **monolitik** di mana satu server FastAPI menyajikan baik API data maupun static files (HTML, CSS, JS). Pemilihan arsitektur ini didasarkan pada kesederhanaan deployment dan pengembangan.

```
┌─────────────────────────────────────────────────┐
│                  Browser (Client)                │
│  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
│  │ Molecule  │  │  Graph   │  │  Properties   │  │
│  │  Library  │  │  Viewer  │  │    Panel      │  │
│  └─────┬────┘  └────┬─────┘  └──────┬────────┘  │
│        │             │               │            │
│        └─────────────┴───────────────┘            │
│                      │ fetch()                    │
└──────────────────────┼───────────────────────────┘
                       │ HTTP
┌──────────────────────┼───────────────────────────┐
│              FastAPI Server (:8000)               │
│  ┌───────────────┐  │  ┌─────────────────────┐   │
│  │  API Routes   │  │  │   Static Files      │   │
│  │  /molecules   │──┘  │   /index.html       │   │
│  │  /compare     │     │   /style.css        │   │
│  │  /stats       │     │   /app.js           │   │
│  └───────┬───────┘     └─────────────────────┘   │
│          │                                        │
│  ┌───────┴───────────────────────────────────┐   │
│  │           Data Processing Pipeline         │   │
│  │  qm9_loader → graph_processor → cache     │   │
│  └───────────────────────────────────────────┘   │
└──────────────────────────────────────────────────┘
```

### 3.2 Pipeline Pemrosesan Data

#### 3.2.1 Parsing File XYZ

Modul `qm9_loader.py` membaca setiap file `.xyz` dan mengekstrak:
- Jumlah atom (baris 1)
- 16 properti kuantum (baris 2, setelah tag `gdb`)
- Daftar atom dan koordinat 3D (baris 3 sampai n+2)
- SMILES kanonik (baris n+4)

Penanganan khusus diterapkan untuk:
- Notasi ilmiah format QM9 (`2.1997*^-6` → `2.1997e-6`)
- Missing values pada beberapa file

#### 3.2.2 Inferensi Ikatan

Modul `graph_processor.py` mengimplementasikan inferensi ikatan berbasis jarak:

```python
def infer_bonds(atoms, coords, tolerance=0.45):
    for i, j:
        dist = euclidean_distance(coords[i], coords[j])
        if dist < covalent_radius[i] + covalent_radius[j] + tolerance:
            add_bond(i, j, dist)
```

Jari-jari kovalen digunakan dari tabel standar (C: 0.76 Å, H: 0.31 Å, N: 0.71 Å, O: 0.66 Å, F: 0.57 Å, dll.).

#### 3.2.3 Komputasi Layout 2D

Layout 2D dihitung menggunakan NetworkX:

1. Prioritas: **Kamada-Kawai layout** — menghasilkan posisi yang mempertimbangkan jarak graph-theoretic
2. Fallback: **Spring layout** (Fruchterman-Reingold) — digunakan jika Kamada-Kawai gagal
3. Normalisasi: Posisi di-scale ke rentang ±150 piksel dan di-center pada origin

#### 3.2.4 Resolusi Nama Molekul

Nama molekul di-resolve melalui dua tahap:

1. **Dictionary lokal** — berisi ~50 SMILES umum (Methane, Ethanol, Benzene, dll.)
2. **PubChem PUG REST API** — untuk SMILES yang tidak ada di dictionary, dilakukan query ke `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/{smiles}/property/IUPACName,Title/JSON`

Hasil resolusi di-cache secara permanen di `names_cache.json` sehingga API hanya dipanggil sekali per SMILES unik.

#### 3.2.5 Caching

Seluruh dataset yang telah diproses (node, edge, layout, properti) disimpan sebagai file pickle (`cache.pkl`) untuk menghindari pemrosesan ulang pada startup. File cache ini di-regenerate hanya jika dihapus secara manual.

### 3.3 API Design

| Method | Endpoint | Parameter | Respons |
|--------|----------|-----------|---------|
| GET | `/molecules` | `limit`, `offset` | Daftar molekul dengan paginasi |
| GET | `/molecules/{mol_id}` | — | Detail molekul: node, edge, properti |
| POST | `/compare` | `{"ids": [...]}` | Array molekul untuk perbandingan |
| GET | `/properties/stats` | — | Statistik (min, max, mean) per properti |
| POST | `/resolve-names` | — | Trigger resolusi nama via PubChem |

### 3.4 Desain Antarmuka

Antarmuka web dirancang dengan prinsip:
- **Sidebar kiri**: Molecule library dengan pencarian dan paginasi
- **Area utama**: Graph viewer (Cytoscape.js) + properties panel
- **Compare mode**: Tampilan side-by-side hingga 4 molekul

Styling menggunakan CSS murni dengan palet warna biru-putih, tipografi system-ui, dan layout CSS Grid.

---

## BAB IV IMPLEMENTASI

### 4.1 Struktur Proyek

```
SDA/
├── README.md
├── LAPORAN PROYEK.md
├── .gitignore
├── backend/
│   ├── main.py              # FastAPI: API + static serving
│   ├── qm9_loader.py        # Parser .xyz + PubChem resolver
│   ├── graph_processor.py   # Inferensi ikatan + layout 2D
│   ├── data_manager.py      # Load, cache, query dataset
│   ├── requirements.txt     # Dependensi Python
│   ├── .venv/               # Virtual environment
│   └── static/
│       ├── index.html        # Markup UI
│       ├── style.css         # Styling
│       └── app.js            # Logika frontend
└── data/
    ├── qm9_raw/              # File .xyz asli (133.885 file)
    └── qm9_processed/
        ├── cache.pkl         # Dataset cache
        └── names_cache.json  # Cache nama PubChem
```

### 4.2 Implementasi Backend

#### 4.2.1 Parser XYZ (`qm9_loader.py`)

Fungsi `parse_xyz()` membaca file QM9 dan menangani format khusus:
- Tag `gdb` pada baris properti di-skip saat parsing numerik
- Notasi `*^` (format QM9 untuk pangkat) dikonversi ke `e` (notasi Python)
- SMILES diekstrak dari baris ke-(n+4) setelah baris atom terakhir
- Validasi: file tanpa atom memicu exception

```python
def parse_xyz(path: Path) -> dict:
    lines = [line.strip() for line in f if line.strip()]
    n_atoms = int(lines[0])
    # Parse properties (skip 'gdb' tag)
    # Parse atoms + coords
    # Extract SMILES from line n+4
    return {"mol_id", "n_atoms", "atoms", "coords", "properties", "smiles", "name"}
```

#### 4.2.2 Inferensi Ikatan (`graph_processor.py`)

Implementasi iterasi pairwise O(n²) untuk mendeteksi ikatan:

```python
def infer_bonds(atoms, coords, tolerance=0.45):
    for i in range(n):
        for j in range(i+1, n):
            r1 = COVALENT_RADII[atoms[i]]
            r2 = COVALENT_RADII[atoms[j]]
            dist = np.linalg.norm(coords[i] - coords[j])
            if dist < r1 + r2 + tolerance:
                bonds.append((i, j, dist))
```

Kompleksitas O(n²) dapat diterima karena molekul QM9 memiliki maksimal ~29 atom (9 berat + ~20 H).

#### 4.2.3 Layout 2D (`graph_processor.py`)

```python
def compute_2d_layout(atoms, bonds, seed=42):
    G = nx.Graph()
    # Add nodes with element attribute
    # Add edges with length attribute
    pos = nx.kamada_kawai_layout(G)  # or spring_layout fallback
    # Normalize to ±150px, center on origin
    return centered_positions
```

#### 4.2.4 Manajemen Dataset (`data_manager.py`)

Kelas `QM9Dataset` mengorkestrasi seluruh pipeline:
- Pada inisialisasi: cek cache → jika ada, load pickle; jika tidak, proses dari raw files
- Menyediakan metode `list_molecules()`, `get_molecule()`, `compare()`, `stats()`
- Menerapkan names cache dari PubChem pada setiap load

#### 4.2.5 FastAPI Server (`main.py`)

Server menyajikan:
- Endpoint API (JSON) untuk data molekul
- Static files dari `backend/static/`
- Root `/` mengembalikan `index.html`

### 4.3 Implementasi Frontend

#### 4.3.1 Molecule Library

Komponen sidebar yang menampilkan daftar molekul dengan:
- Paginasi (20 item per halaman)
- Pencarian real-time berdasarkan ID, formula, atau nama
- Indikator aktif untuk molekul yang sedang dipilih
- Info ringkas: nama, formula, jumlah atom, momen dipol, HOMO-LUMO gap

#### 4.3.2 Graph Viewer

Visualisasi menggunakan Cytoscape.js dengan konfigurasi:
- **Node**: lingkaran berwarna per elemen (H: abu, C: slate, N: biru, O: merah, F: hijau, S: kuning)
- **Edge**: garis abu-abu dengan curve-style bezier
- **Interaksi**: zoom (scroll), pan (drag), hover info
- **Layout**: preset (posisi dari backend)

#### 4.3.3 Properties Panel

Grid 2 kolom yang menampilkan 16 properti kuantum dengan label deskriptif dan nilai terformat (4 desimal).

#### 4.3.4 Compare Mode

Tampilan grid responsif yang menampilkan hingga 4 molekul secara side-by-side, masing-masing dengan graph viewer dan info dasar.

---

## BAB V HASIL DAN PEMBAHASAN

### 5.1 Hasil Pemrosesan Dataset

Dari 2.000 file `.xyz` yang diproses:

| Metrik | Nilai |
|--------|-------|
| Total file diproses | 2.000 |
| Berhasil diparse | 1.996 |
| Gagal parse | 4 (format `*^` yang tidak terkonversi) |
| Molekul unik berhasil | 1.996 |
| Rata-rata atom per molekul | ~18 |
| Rata-rata ikatan per molekul | ~18 |

4 file yang gagal memiliki format notasi ilmiah `*^-6` yang tidak standar pada baris properti. Meskipun handler telah ditambahkan, beberapa kasus edge masih terlewat.

### 5.2 Hasil Inferensi Ikatan

Inferensi ikatan menggunakan pendekatan covalent radii + tolerance menghasilkan graf yang masuk akal untuk molekul organik kecil. Contoh hasil:

| Molekul | Atom | Ikatan (inferensi) | Ikatan (aktual) | Akurasi |
|---------|------|--------------------|-----------------|---------|
| Methane (CH₄) | 5 | 4 | 4 | 100% |
| Ethanol (C₂H₅OH) | 9 | 8 | 8 | 100% |
| Benzene (C₆H₆) | 12 | 12 | 12 | 100% |

Keterbatasan: pendekatan ini tidak membedakan ikatan tunggal/ganda/tripel dan dapat menghasilkan false positive pada molekul dengan jarak antar-atom yang kecil namun tidak berikatan.

### 5.3 Hasil Resolusi Nama

Resolusi nama dilakukan melalui dua sumber:

| Sumber | Jumlah |
|--------|--------|
| Dictionary lokal | ~50 SMILES umum |
| PubChem API | ~1.800 SMILES unik |
| Total ter-resolve | >95% molekul |

Proses resolusi PubChem membutuhkan ~6 menit untuk 1.971 SMILES (dengan rate limit 5 req/detik). Hasil di-cache permanen sehingga proses hanya perlu dilakukan sekali.

### 5.4 Performa Sistem

| Aspek | Pengukuran |
|-------|------------|
| Startup (dari cache) | ~2 detik |
| Startup (tanpa cache, 2000 mol) | ~30 detik |
| Respons API `/molecules` | <50ms |
| Respons API `/molecules/{id}` | <10ms |
| Ukuran cache pickle | ~15 MB |
| Ukuran names cache JSON | ~100 KB |

### 5.5 Tampilan Antarmuka

Antarmuka web menampilkan:

1. **Header** — judul aplikasi dan tombol compare mode
2. **Sidebar** — daftar molekul dengan nama (misal: "Methane", "Ethanol", "Benzene"), formula, dan properti ringkas
3. **Area utama** — graf 2D interaktif dengan node berwarna per elemen dan panel properti kuantum
4. **Compare mode** — tampilan grid hingga 4 molekul side-by-side

---

## BAB VI PENUTUP

### 6.1 Kesimpulan

Proyek ini berhasil mengembangkan aplikasi web interaktif untuk visualisasi graf molekul dataset QM9 dengan fitur-fitur berikut:

1. **Pipeline pemrosesan data** yang mencakup parsing file `.xyz`, inferensi ikatan berbasis jarak kovalen, dan komputasi layout 2D menggunakan NetworkX.
2. **Backend API** berbasis FastAPI yang menyajikan data molekul (node, edge, properti) melalui RESTful endpoints dengan caching untuk efisiensi.
3. **Frontend interaktif** menggunakan vanilla HTML/CSS/JS dan Cytoscape.js yang memungkinkan eksplorasi, seleksi, zoom/pan graf, dan perbandingan molekul.
4. **Resolusi nama molekul** via PubChem API dengan caching permanen, menghasilkan nama yang familiar (misal: "Methane" alih-alih "dsgdb9nsd_000001").

Sistem berjalan sebagai aplikasi monolitik pada satu port, dengan startup cepat (~2 detik dari cache) dan respons API yang responsif (<50ms).

### 6.2 Saran Pengembangan

1. **Visualisasi 3D** — Menambahkan rendering struktur molekul 3D menggunakan pustaka seperti 3Dmol.js untuk tampilan yang lebih akurat secara kimia.
2. **Distinguasi ikatan** — Membedakan ikatan tunggal, ganda, dan tripel dalam visualisasi (garis tebal/dobel) berdasarkan jarak dan konteks.
3. **Dataset lengkap** — Memperluas ke seluruh 133.885 molekul dengan database backend (SQLite/PostgreSQL) menggantikan pickle.
4. **Filter dan sorting** — Menambahkan filter berdasarkan rentang properti (misal: HOMO-LUMO gap < 0.3) dan sorting molekul.
5. **Integrasi GNN** — Menghubungkan visualisasi dengan model graph neural network untuk prediksi properti, sejalan dengan paper rujukan.
6. **Eksport** — Fitur ekspor graf sebagai gambar (PNG/SVG) atau data sebagai CSV/JSON untuk analisis lebih lanjut.

---

## DAFTAR PUSTAKA

1. Ramakrishnan, R., Dral, P.O., Rupp, M., & von Lilienfeld, O.A. (2014). Quantum chemistry structures and properties of 134 kilo molecules. *Scientific Data*, 1, 140022. https://doi.org/10.1038/sdata.2014.22

2. Adaptive edge-aware graph convolutional with multi-task learning for simultaneous prediction of material properties. Scopus: https://www.scopus.com/pages/publications/105028524571

3. Cytoscape.js — Graph theory library for visualisation and analysis. https://js.cytoscape.org/

4. FastAPI — Modern, fast web framework for building APIs with Python. https://fastapi.tiangolo.com/

5. NetworkX — Network analysis in Python. https://networkx.org/

6. PubChem PUG REST API. https://pubchem.ncbi.nlm.nih.gov/rest/pug/
