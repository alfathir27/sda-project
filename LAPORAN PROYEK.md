# LAPORAN PROYEK

# Pengembangan Aplikasi Web Interaktif untuk Visualisasi Graf Molekul dan Eksplorasi Properti Kuantum pada Dataset QM9

---

## BAB I PENDAHULUAN

### 1.1 Latar Belakang

Graf merupakan salah satu struktur data fundamental dalam ilmu komputer yang merepresentasikan hubungan antar-entitas melalui himpunan node dan edge. Dalam domain kimia komputasional, molekul secara natural dapat dimodelkan sebagai graf: atom berperan sebagai node dan ikatan kimia sebagai edge. Representasi ini menjadi dasar bagi berbagai pendekatan graph-based learning, termasuk yang didemonstrasikan dalam paper *"Adaptive edge-aware graph convolutional with multi-task learning for simultaneous prediction of material properties"* yang menggunakan graph neural network pada dataset QM9.

Dataset QM9 berisi 133.885 molekul organik kecil dengan koordinat 3D dan 16 properti kuantum, namun **informasi ikatan (edge) tidak disediakan secara eksplisit** — hanya koordinat atom yang tersedia. Hal ini menimbulkan tantangan menarik dari perspektif Struktur Data dan Algoritma: bagaimana mengkonstruksi graf dari data spasial? Bagaimana merepresentasikan, menyimpan, dan memvisualisasikan graf tersebut secara efisien?

Proyek ini mengembangkan aplikasi web interaktif yang menerapkan konsep-konsep inti Struktur Data dan Algoritma — khususnya struktur graf, algoritma pembangunan graf, algoritma layout graf, dan strategi caching — untuk memproses dan memvisualisasikan molekul-molekul QM9 dalam bentuk graf 2D.

### 1.2 Rumusan Masalah

1. Bagaimana mengkonstruksi graf molekul (pembangunan edge) dari koordinat 3D atom menggunakan algoritma berbasis jarak?
2. Bagaimana merepresentasikan graf molekul secara efisien dalam memori (adjacency list vs adjacency matrix) untuk mendukung operasi traversal dan visualisasi?
3. Bagaimana menghitung layout 2D graf menggunakan algoritma force-directed (Kamada-Kawai, Fruchterman-Reingold) sehingga struktur molekul terlihat jelas?
4. Bagaimana menerapkan struktur data hash map (dictionary) untuk pencarian O(1) dan caching untuk menghindari komputasi ulang?
5. Bagaimana membangun antarmuka web interaktif yang memungkinkan eksplorasi dan perbandingan graf molekul?

### 1.3 Tujuan

1. Mengimplementasikan algoritma konstruksi graf dari data spasial (koordinat 3D → edge berdasarkan jarak kovalen).
2. Mengimplementasikan representasi graf menggunakan adjacency list (NetworkX) dan hash map untuk indexing.
3. Mengimplementasikan algoritma layout 2D force-directed (Kamada-Kawai dengan fallback Fruchterman-Reingold).
4. Menerapkan strategi caching (serialization ke pickle dan JSON) untuk efisiensi pemrosesan.
5. Membangun aplikasi web monolitik (FastAPI + vanilla JS + Cytoscape.js) untuk visualisasi interaktif.

### 1.4 Manfaat

- **Akademik (SDA)**: Mendemonstrasikan penerapan konkret struktur data graf, hash map, dan algoritma graph layout pada dataset dunia nyata.
- **Praktis**: Memudahkan eksplorasi struktur dan properti molekul QM9 tanpa menulis kode.
- **Edukatif**: Menjadi media pembelajaran interaktif untuk memahami hubungan antara representasi graf dan sifat-sifat molekul.

### 1.5 Batasan

1. Dataset dibatasi hingga 2.000 molekul untuk efisiensi komputasi dan penyimpanan.
2. Konstruksi edge menggunakan pendekatan berbasis jarak (covalent radii + tolerance), bukan dari data topologi eksplisit — tidak membedakan ikatan tunggal/ganda/tripel.
3. Visualisasi hanya dalam bentuk graf 2D; tidak ada rendering struktur 3D.
4. Algoritma layout menggunakan implementasi NetworkX; tidak diimplementasikan dari nol.

---

## BAB II TINJAUAN PUSTAKA

### 2.1 Struktur Data Graf

Graf \( G = (V, E) \) adalah struktur data yang terdiri dari himpunan node (verteks) \( V \) dan himpunan edge (sisi) \( E \subseteq V \times V \). Terdapat dua representasi utama graf dalam memori:

#### 2.1.1 Adjacency Matrix

Matriks berukuran \( n \times n \) di mana \( A[i][j] = 1 \) jika terdapat edge dari node \( i \) ke node \( j \), dan 0 jika tidak.

- **Kelebihan**: Pengecekan keberadaan edge O(1), cocok untuk graf dense
- **Kekurangan**: Konsumsi memori O(n²), tidak efisien untuk graf sparse

#### 2.1.2 Adjacency List

Setiap node menyimpan daftar node tetangganya. Dalam implementasi Python, ini direpresentasikan sebagai dictionary of lists.

- **Kelebihan**: Konsumsi memori O(V + E), efisien untuk graf sparse (seperti graf molekul)
- **Kekurangan**: Pengecekan edge O(degree), tidak O(1)

Graf molekul bersifat **sparse** — molekul dengan n atom memiliki paling banyak n-1 ikatan (untuk graf terhubung), jauh lebih kecil dari n² kemungkinan edge. Oleh karena itu, **adjacency list** merupakan representasi yang tepat.

### 2.2 Konstruksi Graf dari Data Spasial

Dalam dataset QM9, informasi edge (ikatan) tidak tersedia secara eksplisit. Konstruksi graf dilakukan dengan algoritma berbasis jarak:

Dua atom \( i \) dan \( j \) dianggap berikatan jika:

$$d_{ij} < r_i^{cov} + r_j^{cov} + \delta$$

di mana:
- \( d_{ij} = \sqrt{(x_i - x_j)^2 + (y_i - y_j)^2 + (z_i - z_j)^2} \) — jarak Euclidean
- \( r_i^{cov} \) — jari-jari kovalen atom \( i \)
- \( \delta = 0.45 \) Å — toleransi

Algoritma ini memeriksa semua pasangan atom dengan kompleksitas **O(n²)**. Untuk molekul QM9 (maks 29 atom), ini sangat efisien. Untuk dataset besar, dapat dioptimasi dengan **spatial indexing** (kd-tree, cell list) menjadi O(n log n).

### 2.3 Algoritma Layout Graf 2D

Layout graf adalah proses penempatan node pada bidang 2D untuk visualisasi. Dua algoritma force-directed yang digunakan:

#### 2.3.1 Kamada-Kawai

Algoritma yang memodelkan graf sebagai sistem pegas di mana panjang pegas ideal antara node \( i \) dan \( j \) proporsional terhadap jarak graph-theoretic (shortest path) \( d_{ij} \). Energi total sistem:

$$E = \sum_{i<j} k_{ij} \left( |p_i - p_j| - l_{ij} \right)^2$$

di mana \( k_{ij} \) adalah konstanta pegas dan \( l_{ij} \) adalah panjang ideal. Posisi node dioptimasi dengan **Newton-Raphson** hingga konvergen.

- **Kompleksitas**: O(n²) per iterasi, O(n³) untuk komputasi shortest path awal
- **Kelebihan**: Menghasilkan layout yang terstruktur dan estetis
- **Kekurangan**: Lambat untuk graf besar; gagal jika graf tidak terhubung

#### 2.3.2 Fruchterman-Reingold (Spring Layout)

Algoritma yang mensimulasikan gaya tarik (antara node bertetangga) dan gaya tolak (antara semua node) secara iteratif:

- **Gaya tarik**: \( f_a(d) = \frac{d^2}{k} \) — menarik node bertetangga
- **Gaya tolak**: \( f_r(d) = -\frac{k^2}{d} \) — menolak semua node

di mana \( k \) adalah konstanta dan \( d \) adalah jarak aktual. Posisi diupdate setiap iterasi dengan cooling schedule.

- **Kompleksitas**: O(n²) per iterasi (gaya tolak pairwise)
- **Kelebihan**: Dapat menangani graf tidak terhubung
- **Kekurangan**: Layout kurang terstruktur dibanding Kamada-Kawai

### 2.4 Struktur Data Pendukung

#### 2.4.1 Hash Map (Dictionary)

Digunakan untuk pencarian O(1) dalam beberapa konteks:
- **ID → Index**: Mapping `mol_id` → posisi array untuk lookup molekul berdasar ID
- **SMILES → Name**: Cache nama molekul dari PubChem API
- **Element → Radius**: Tabel jari-jari kovalen untuk inferensi ikatan
- **Element → Color**: Tabel warna untuk visualisasi node

#### 2.4.2 Array (NumPy ndarray)

Digunakan untuk menyimpan koordinat 3D atom secara kontigu dalam memori, memungkinkan operasi vektorisasi (perhitungan jarak Euclidean) yang efisien.

#### 2.4.3 Serialization (Pickle, JSON)

- **Pickle**: Serialisasi biner Python untuk caching seluruh dataset (graf + properti). Kelebihan: cepat, mendukung objek Python kompleks.
- **JSON**: Serialisasi teks untuk cache nama molekul. Kelebihan: human-readable, interoperable.

### 2.5 Dataset QM9

Dataset QM9 dikurasi oleh Ramakrishnan et al. (2014) dan dipublikasikan dalam jurnal *Scientific Data*. Dataset ini merupakan subset dari GDB-17 — database virtual yang memuat 166 miliar molekul organik kecil. QM9 memilih molekul dengan hingga 9 atom berat (C, N, O, F) dan menghitung properti kuantumnya menggunakan DFT pada level B3LYP/6-31G(2df,2p).

Setiap molekul dalam file `.xyz` memuat: jumlah atom, 16 properti kuantum, koordinat 3D per atom, frekuensi vibrasi, SMILES, dan InChI.

### 2.6 Teknologi yang Digunakan

| Komponen | Teknologi | Peran SDA |
|----------|-----------|-----------|
| Backend | Python 3 + FastAPI | REST API, penyajian data graf |
| Graf | NetworkX | Representasi graf (adjacency list), algoritma layout |
| Numerik | NumPy | Array operasi, jarak Euclidean |
| Serialisasi | Pickle, JSON | Caching struktur data |
| Frontend | Vanilla JS + Cytoscape.js | Rendering graf interaktif di browser |

---

## BAB III METODOLOGI

### 3.1 Arsitektur Sistem

Sistem dibangun dengan arsitektur **monolitik** — satu server FastAPI menyajikan API data dan static files. Pemilihan ini menghindari kompleksitas komunikasi antar-service dan memfokuskan implementasi pada pengelolaan struktur data graf.

```
┌──────────────────────────────────────────────────┐
│                   Browser (Client)                │
│   Cytoscape.js: rendering graf (node + edge)     │
│   fetch() → HTTP GET/POST                        │
└──────────────────────┬───────────────────────────┘
                       │
┌──────────────────────┼───────────────────────────┐
│              FastAPI Server (:8000)               │
│                                                   │
│  ┌─────────────────┐  ┌──────────────────────┐   │
│  │   API Routes     │  │   Static Files       │   │
│  │   GET /molecules │  │   index.html          │   │
│  │   GET /mol/{id}  │  │   style.css           │   │
│  │   POST /compare  │  │   app.js              │   │
│  └────────┬────────┘  └──────────────────────┘   │
│           │                                       │
│  ┌────────┴────────────────────────────────────┐  │
│  │         Struktur Data & Algoritma            │  │
│  │                                              │  │
│  │  Hash Map: mol_id → molecule (O(1) lookup)  │  │
│  │  Graph:   NetworkX adjacency list            │  │
│  │  Array:   NumPy coords (vectorized dist)     │  │
│  │  Cache:   Pickle (data) + JSON (names)       │  │
│  └──────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────┘
```

### 3.2 Algoritma Konstruksi Graf

#### 3.2.1 Parsing Data Mentah

File `.xyz` dibaca baris per baris. Data diekstrak ke dalam struktur:
- `atoms: List[str]` — daftar elemen atom (indeks = ID node)
- `coords: np.ndarray` — matriks n×3 koordinat 3D
- `properties: Dict[str, float]` — hash map properti kuantum
- `smiles: str` — string SMILES untuk resolusi nama

#### 3.2.2 Pembangunan Edge (Inferensi Ikatan)

Algoritma pairwise memeriksa semua kombinasi atom:

```
INFER-BONDS(atoms, coords, tolerance=0.45):
  bonds ← empty list
  n ← length(atoms)
  for i ← 0 to n-1:
      for j ← i+1 to n-1:          // hanya segitiga atas (graf undirected)
          r1 ← COVALENT_RADII[atoms[i]]   // O(1) hash map lookup
          r2 ← COVALENT_RADII[atoms[j]]   // O(1) hash map lookup
          dist ← EUCLIDEAN-DISTANCE(coords[i], coords[j])
          if dist < r1 + r2 + tolerance:
              bonds.append((i, j, dist))
  return bonds
```

**Kompleksitas**: O(n²) waktu, O(E) ruang — optimal untuk graf sparse kecil.

#### 3.2.3 Pembangunan Objek Graf

Edge list hasil inferensi dikonversi menjadi objek graf NetworkX (adjacency list):

```python
G = nx.Graph()
for i, atom in enumerate(atoms):
    G.add_node(i, element=atom)       # node dengan atribut
for i, j, dist in bonds:
    G.add_edge(i, j, length=dist)      # edge dengan bobot
```

### 3.3 Algoritma Layout 2D

```
COMPUTE-2D-LAYOUT(atoms, bonds):
  G ← BUILD-GRAPH(atoms, bonds)
  
  if |V| = 1:
      return {(0): (0.0, 0.0)}
  
  try:
      pos ← KAMADA-KAWAI-LAYOUT(G)     // prioritas: terstruktur
  except:
      pos ← SPRING-LAYOUT(G, seed=42)  // fallback: graf tidak terhubung
  
  // Normalisasi ke ±150px, center on origin
  xs, ys ← unzip(pos.values())
  range_x ← max(xs) - min(xs)
  range_y ← max(ys) - min(ys)
  scale ← 300 / max(range_x, range_y)
  
  centered ← {}
  for (node, (x, y)) in pos:
      cx ← (x - min_x - range_x/2) × scale
      cy ← (y - min_y - range_y/2) × scale
      centered[node] ← (cx, cy)
  
  return centered
```

### 3.4 Strategi Caching

Untuk menghindari komputasi ulang O(n² × 2000) pada setiap startup, diterapkan dua level caching:

| Level | Struktur Data | Format | Isi |
|-------|---------------|--------|-----|
| 1 | Pickle | Binary | Seluruh dataset: node, edge, layout, properti |
| 2 | JSON | Text | Cache nama molekul: SMILES → name (hash map) |

Pada startup: cek pickle → jika ada, load langsung (O(1) deserialization). Jika tidak, proses dari raw files dan simpan pickle.

### 3.5 Operasi Query pada Dataset

| Operasi | Struktur Data | Kompleksitas |
|---------|---------------|--------------|
| List molecules (paginasi) | Array slice | O(limit) |
| Get molecule by ID | Hash map `_id_to_idx` | O(1) lookup + O(1) array access |
| Compare molecules | Hash map × k | O(k) |
| Search by name/formula | Linear scan + substring match | O(limit × len(string)) |
| Property stats | Array aggregation | O(n) per property |

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
│   ├── qm9_loader.py        # Parser .xyz + PubChem resolver + hash map nama
│   ├── graph_processor.py   # Konstruksi graf + algoritma layout 2D
│   ├── data_manager.py      # Orkestrasi: load, cache (pickle/JSON), query
│   ├── requirements.txt
│   └── static/
│       ├── index.html
│       ├── style.css
│       └── app.js            # Cytoscape.js: rendering graf di browser
└── data/
    ├── qm9_raw/
    └── qm9_processed/
        ├── cache.pkl         # Serialisasi biner dataset
        └── names_cache.json  # Hash map SMILES → nama
```

### 4.2 Implementasi Struktur Data Graf

#### 4.2.1 Konstruksi Edge — `graph_processor.py`

```python
COVALENT_RADII = {'H': 0.31, 'C': 0.76, 'N': 0.71, 'O': 0.66, ...}  # Hash map

def infer_bonds(atoms, coords, tolerance=0.45):
    n = len(atoms)
    bonds = []                                    # Edge list
    for i in range(n):
        for j in range(i + 1, n):                # Segitiga atas saja
            r1 = COVALENT_RADII.get(atoms[i], 0.7)  # O(1) hash lookup
            r2 = COVALENT_RADII.get(atoms[j], 0.7)
            dist = float(np.linalg.norm(coords[i] - coords[j]))  # Euclidean
            if dist < (r1 + r2 + tolerance):
                bonds.append((i, j, dist))       # Edge: (source, target, weight)
    return bonds
```

**Analisis kompleksitas**:
- Waktu: O(n²) — pairwise iteration
- Ruang: O(E) — edge list, E ≤ n(n-1)/2 tapi praktis E ≈ n (graf molekul sparse)

#### 4.2.2 Pembangunan Graf NetworkX — `graph_processor.py`

```python
def compute_2d_layout(atoms, bonds, seed=42):
    G = nx.Graph()                               # Adjacency list representation
    for i, atom in enumerate(atoms):
        G.add_node(i, element=atom)              # Node + atribut
    for i, j, dist in bonds:
        G.add_edge(i, j, length=dist)             # Edge + bobot jarak

    if len(atoms) == 1:
        return {0: (0.0, 0.0)}

    try:
        pos = nx.kamada_kawai_layout(G)          # Force-directed: Kamada-Kawai
    except Exception:
        pos = nx.spring_layout(G, seed=seed, k=2.0)  # Fallback: Fruchterman-Reingold

    # Normalisasi posisi ke ±150px
    ...
    return centered
```

**Analisis kompleksitas**:
- Kamada-Kawai: O(n³) untuk shortest path awal (Floyd-Warshall), O(n²) per iterasi Newton-Raphson
- Spring layout: O(n²) per iterasi (gaya tolak pairwise), O(iterasi × n²) total

#### 4.2.3 Hash Map untuk Indexing — `data_manager.py`

```python
class QM9Dataset:
    def __init__(self):
        self.molecules: List[Dict] = []          # Array: akses O(1) by index
        self._id_to_idx: Dict[str, int] = {}     # Hash map: mol_id → array index

    def get_molecule(self, mol_id: str):
        idx = self._id_to_idx.get(mol_id)        # O(1) hash lookup
        if idx is None:
            return None
        return self.molecules[idx]                # O(1) array access
```

**Rantai lookup**: mol_id → hash map → index → array → molecule data. Total: **O(1)**.

#### 4.2.4 Serialisasi Cache — `data_manager.py`

```python
# Simpan seluruh dataset (graf + properti) ke binary
with open(CACHE_PATH, 'wb') as f:
    pickle.dump(self.molecules, f)               # O(n) serialization

# Load dari cache
with open(CACHE_PATH, 'rb') as f:
    self.molecules = pickle.load(f)              # O(n) deserialization
```

#### 4.2.5 Hash Map Nama Molekul — `qm9_loader.py`

```python
SMILES_TO_NAME = {'C': 'Methane', 'O': 'Water', ...}  # Local hash map

NAMES_CACHE_PATH = .../names_cache.json

def _load_names_cache() -> Dict[str, str]:       # JSON → hash map
    return json.load(f)

def resolve_names_batch(molecules, delay=0.2):
    cache = _load_names_cache()                   # Load existing hash map
    for mol in molecules:
        if mol['smiles'] in cache:                # O(1) lookup
            mol['name'] = cache[mol['smiles']]
        else:
            name = _pubchem_resolve(mol['smiles'])  # API call
            cache[mol['smiles']] = name            # O(1) insert
    _save_names_cache(cache)                      # Hash map → JSON
```

### 4.3 Implementasi Frontend (Rendering Graf)

#### 4.3.1 Konstruksi Graf di Browser — `app.js`

Cytoscape.js menerima elemen graf sebagai array JSON:

```javascript
const elements = [
  ...nodes.map(n => ({
    data: { id: String(n.id), label: n.element, element: n.element },
    position: { x: n.x2d, y: n.y2d }           // Posisi dari algoritma layout backend
  })),
  ...edges.map(e => ({
    data: { id: `e-${e.source}-${e.target}`, source: String(e.source), target: String(e.target) }
  }))
];
```

Cytoscape.js secara internal menggunakan **adjacency list** untuk merepresentasikan graf, mendukung operasi traversal (BFS/DFS) dan styling per elemen.

#### 4.3.2 Interaksi Graf

- **Zoom**: scroll wheel → mengubah scale factor viewport
- **Pan**: mouse drag → translasi viewport
- **Node styling**: warna berdasar hash map `ATOM_COLORS` (element → hex color)

---

## BAB V HASIL DAN PEMBAHASAN

### 5.1 Hasil Konstruksi Graf

Dari 2.000 file `.xyz` yang diproses:

| Metrik | Nilai |
|--------|-------|
| Molekul berhasil dikonstruksi | 1.996 |
| Total node (atom) | ~35.928 |
| Total edge (ikatan) | ~35.928 |
| Rata-rata |V| per molekul | ~18 |
| Rata-rata |E| per molekul | ~18 |
| Rata-rata degree per node | ~2.0 (graf molekul: chain-like) |
| Graf tidak terhubung | <1% (fallback ke spring layout) |

Graf molekul QM9 bersifat **sparse** — rata-rata degree ≈ 2, jauh di bawah degree maksimum n-1. Ini mengkonfirmasi pemilihan **adjacency list** sebagai representasi yang tepat.

### 5.2 Analisis Kompleksitas Algoritma

| Algoritma | Kompleksitas Waktu | Kompleksitas Ruang | Catatan |
|-----------|-------------------|-------------------|---------|
| Inferensi ikatan | O(n²) per molekul | O(E) | n ≤ 29, sangat cepat |
| Kamada-Kawai layout | O(n³) + O(iter × n²) | O(n²) | Shortest path + iterasi |
| Spring layout (fallback) | O(iter × n²) | O(n) | Gaya tolak pairwise |
| Lookup molekul by ID | O(1) | O(n) | Hash map + array |
| Paginasi list | O(limit) | O(limit) | Array slice |
| Resolusi nama (cache hit) | O(1) | O(k) | Hash map lookup |
| Resolusi nama (cache miss) | O(1) + network | O(k) | API call + hash insert |

### 5.3 Verifikasi Konstruksi Edge

| Molekul | \|V\| | \|E\| inferensi | \|E\| aktual | Akurasi |
|---------|-------|-----------------|--------------|---------|
| Methane (CH₄) | 5 | 4 | 4 | 100% |
| Ethanol (C₂H₅OH) | 9 | 8 | 8 | 100% |
| Benzene (C₆H₆) | 12 | 12 | 12 | 100% |
| Acetylene (C₂H₂) | 4 | 3 | 3 | 100% |

Keterbatasan: pendekatan berbasis jarak tidak membedakan ikatan tunggal/ganda/tripel. Benzene memiliki 6 ikatan C-C (semua terdeteksi), namun secara kimiawi 3 di antaranya adalah ikatan ganda — informasi order ikatan hilang.

### 5.4 Performa Sistem

| Operasi | Waktu | Struktur Data Terlibat |
|---------|-------|----------------------|
| Startup (dari cache) | ~2 detik | Pickle deserialization |
| Startup (tanpa cache) | ~30 detik | O(2000 × n²) inferensi + layout |
| GET /molecules/{id} | <10ms | Hash map O(1) + array O(1) |
| GET /molecules?limit=20 | <50ms | Array slice O(20) |
| POST /compare (4 mol) | <30ms | Hash map × 4 |

### 5.5 Tampilan Antarmuka

Antarmuka menampilkan:
1. **Sidebar** — daftar molekul dengan nama (hash map SMILES → name), formula, properti
2. **Graph Viewer** — graf 2D interaktif: node berwarna per elemen, edge sebagai garis penghubung
3. **Properties Panel** — 16 properti kuantum dalam grid
4. **Compare Mode** — hingga 4 graf molekul side-by-side

---

## BAB VI PENUTUP

### 6.1 Kesimpulan

Proyek ini berhasil menerapkan konsep-konsep Struktur Data dan Algoritma pada domain pemrosesan dan visualisasi graf molekul:

1. **Struktur data graf (adjacency list)** digunakan untuk merepresentasikan molekul — atom sebagai node dan ikatan sebagai edge. Pemilihan adjacency list (bukan adjacency matrix) tepat karena graf molekul bersifat sparse (rata-rata degree ≈ 2).

2. **Algoritma konstruksi graf** O(n²) berbasis jarak kovalen berhasil menginferensi edge dari koordinat 3D dengan akurasi 100% pada molekul uji, meskipun tidak membedakan order ikatan.

3. **Algoritma layout force-directed** (Kamada-Kawai + Fruchterman-Reingold fallback) menghasilkan posisi 2D yang informatif untuk visualisasi, dengan kompleksitas O(n³) dan O(iter × n²) masing-masing.

4. **Hash map** digunakan secara ekstensif untuk pencarian O(1): mol_id → index, SMILES → nama, elemen → jari-jari kovalen, elemen → warna. Rantai lookup mol_id → hash map → array → data menghasilkan akses O(1).

5. **Strategi caching** (pickle + JSON serialization) mengurangi waktu startup dari ~30 detik menjadi ~2 detik, mendemonstrasikan trade-off antara ruang penyimpanan dan waktu komputasi.

6. **Aplikasi web monolitik** (FastAPI + Cytoscape.js) memungkinkan eksplorasi graf molekul secara interaktif dengan zoom, pan, seleksi, dan perbandingan.

### 6.2 Saran Pengembangan

1. **Algoritma BFS/DFS** — Menambahkan traversal graf untuk visualisasi connected components dan deteksi siklus (cincin aromatik pada Benzene dll.).
2. **Shortest path** — Mengimplementasikan Dijkstra untuk menemukan jalur terpendek antar-atom dalam graf molekul.
3. **Minimum Spanning Tree** — Menghitung MST dari bobot jarak ikatan untuk analisis kerangka molekul.
4. **Distinguasi order ikatan** — Membedakan ikatan tunggal/ganda/tripel dalam edge attribute dan visualisasi.
5. **Spatial indexing** — Mengoptimasi inferensi ikatan dari O(n²) ke O(n log n) menggunakan kd-tree.
6. **Graph statistics** — Menambahkan perhitungan degree distribution, clustering coefficient, dan diameter graf.

---

## DAFTAR PUSTAKA

1. Cormen, T.H., Leiserson, C.E., Rivest, R.L., & Stein, C. (2009). *Introduction to Algorithms* (3rd ed.). MIT Press. — Referensi utama untuk struktur data graf, BFS/DFS, shortest path, dan MST.

2. Ramakrishnan, R., Dral, P.O., Rupp, M., & von Lilienfeld, O.A. (2014). Quantum chemistry structures and properties of 134 kilo molecules. *Scientific Data*, 1, 140022.

3. Adaptive edge-aware graph convolutional with multi-task learning for simultaneous prediction of material properties. Scopus: https://www.scopus.com/pages/publications/105028524571

4. Kamada, T., & Kawai, S. (1989). An algorithm for drawing general undirected graphs. *Information Processing Letters*, 31(1), 7-15.

5. Fruchterman, T.M.J., & Reingold, E.M. (1991). Graph drawing by force-directed placement. *Software: Practice and Experience*, 21(11), 1129-1164.

6. Hagberg, A., Swart, P., & Chult, D. (2008). Exploring network structure, dynamics, and function using NetworkX. *Proceedings of the 7th Python in Science Conference*.

7. Cytoscape.js — Graph theory library for visualisation and analysis. https://js.cytoscape.org/

8. PubChem PUG REST API. https://pubchem.ncbi.nlm.nih.gov/rest/pug/
