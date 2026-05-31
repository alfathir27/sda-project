const API = '';

let molecules = [];
let total = 0;
let offset = 0;
const LIMIT = 20;
let currentMol = null;
let compareIds = [];
let showCompare = false;
let cyInstance = null;

const ATOM_COLORS = {
  H: '#e2e8f0', C: '#64748b', N: '#3b82f6', O: '#ef4444', F: '#22c55e',
  S: '#eab308', Cl: '#10b981', P: '#f97316', Si: '#06b6d4', Br: '#a3e635', B: '#f472b6',
};

const PROP_LABELS = {
  A_GHz: 'Rot. Const A (GHz)', B_GHz: 'Rot. Const B (GHz)', C_GHz: 'Rot. Const C (GHz)',
  mu_Debye: 'Dipole Moment (Debye)', alpha_Bohr3: 'Polarizability (Bohr³)',
  homo_Hartree: 'HOMO (Hartree)', lumo_Hartree: 'LUMO (Hartree)',
  gap_Hartree: 'HOMO-LUMO Gap (Hartree)', r2_Bohr2: 'Spatial Extent (Bohr²)',
  zpve_Hartree: 'ZPVE (Hartree)', U0_Hartree: 'U₀ (Hartree)', U_Hartree: 'U (Hartree)',
  H_Hartree: 'H (Hartree)', G_Hartree: 'G (Hartree)', Cv_cal_mol_K: 'Cv (cal/mol·K)',
};

// --- API ---
async function apiFetch(url, opts) {
  const res = await fetch(API + url, opts);
  if (!res.ok) throw new Error(res.statusText);
  return res.json();
}

// --- Molecule list ---
let searchQuery = '';
let searchTimer = null;

async function loadMolecules() {
  if (searchQuery) {
    const data = await apiFetch(`/search?q=${encodeURIComponent(searchQuery)}&limit=${LIMIT}`);
    molecules = data.items;
    total = data.total;
    document.getElementById('search-meta').textContent =
      data.total === 0
        ? `Tidak ada hasil. Coba klik "Render dari SMILES" di bawah.`
        : `${data.total} hasil (matched: ${data.matched_by})`;
  } else {
    const data = await apiFetch(`/molecules?limit=${LIMIT}&offset=${offset}`);
    molecules = data.items;
    total = data.total;
    document.getElementById('search-meta').textContent = '';
  }
  renderList();
  renderPagination();
}

function renderList() {
  const el = document.getElementById('mol-list');
  if (molecules.length === 0) {
    el.innerHTML = '<p class="text-muted text-sm" style="padding:8px">Tidak ada molekul.</p>';
    return;
  }
  el.innerHTML = molecules.map(m => `
    <button class="mol-item ${currentMol && currentMol.mol_id === m.mol_id ? 'active' : ''}"
            onclick="selectMol('${m.mol_id}')">
      <span class="mol-id">${m.name || m.mol_id}</span>
      <span class="mol-formula">${m.formula}</span>
      <div class="mol-meta">${m.name ? m.mol_id : ''} ${m.name ? '·' : ''} ${m.n_atoms} atoms &middot; μ: ${m.mu?.toFixed(2) ?? '-'} &middot; gap: ${m.gap?.toFixed(3) ?? '-'}</div>
    </button>
  `).join('');
}

function renderPagination() {
  const pages = Math.max(1, Math.ceil(total / LIMIT));
  const current = searchQuery ? 1 : Math.floor(offset / LIMIT) + 1;
  document.getElementById('page-info').textContent = `${current} / ${pages}`;
  document.getElementById('btn-prev').disabled = searchQuery || offset === 0;
  document.getElementById('btn-next').disabled = searchQuery || offset + LIMIT >= total;
}

function prevPage() { if (offset > 0) { offset -= LIMIT; loadMolecules(); } }
function nextPage() { if (offset + LIMIT < total) { offset += LIMIT; loadMolecules(); } }

function onSearch() {
  searchQuery = document.getElementById('search-input').value.trim();
  // debounce 250ms supaya gak hit server tiap keystroke
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    offset = 0;
    loadMolecules();
  }, 250);
}

async function renderFromSmiles() {
  const q = document.getElementById('search-input').value.trim();
  if (!q) return;
  showView('loading');
  try {
    const mol = await apiFetch('/render-smiles', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ smiles: q }),
    });
    currentMol = mol;
    renderMolecule();
    showView('mol');
  } catch (e) {
    alert(`SMILES invalid: ${e.message}`);
    showView('empty');
  }
}

// --- Select molecule ---
async function selectMol(id) {
  showView('loading');
  try {
    currentMol = await apiFetch(`/molecules/${id}`);
    renderMolecule();
    showView('mol');
  } catch (e) {
    console.error(e);
    showView('empty');
  }
}

function showView(view) {
  document.getElementById('empty-state').style.display = view === 'empty' ? '' : 'none';
  document.getElementById('loading-state').style.display = view === 'loading' ? '' : 'none';
  document.getElementById('mol-view').style.display = view === 'mol' ? '' : 'none';
  document.getElementById('compare-view').style.display = view === 'compare' ? '' : 'none';
}

// --- Render molecule ---
function renderMolecule() {
  if (!currentMol) return;
  document.getElementById('mol-title').textContent = currentMol.name || currentMol.mol_id;
  document.getElementById('mol-subtitle').textContent =
    `${currentMol.name ? currentMol.mol_id + ' · ' : ''}${currentMol.formula} · ${currentMol.n_atoms} atoms · ${currentMol.edges.length} bonds${currentMol.smiles ? ' · SMILES: ' + currentMol.smiles : ''}`;

  const btn = document.getElementById('btn-add-compare');
  const inCompare = compareIds.includes(currentMol.mol_id);
  btn.textContent = inCompare ? '✓ In compare' : '+ Add to compare';
  btn.className = inCompare ? 'btn btn-primary' : 'btn btn-outline';

  renderGraph('cy-container', currentMol.nodes, currentMol.edges);
  renderProps('props-grid', currentMol.properties);
  renderList(); // refresh active state
}

function renderGraph(containerId, nodes, edges) {
  const prev = document.getElementById(containerId)._cy;
  if (prev) prev.destroy();

  const cy = cytoscape({
    container: document.getElementById(containerId),
    elements: [
      ...nodes.map(n => ({
        data: { id: String(n.id), label: n.element, element: n.element },
        position: { x: n.x2d, y: n.y2d },
      })),
      ...edges.map(e => ({
        data: { id: `e-${e.source}-${e.target}`, source: String(e.source), target: String(e.target) },
      })),
    ],
    style: [
      { selector: 'node', style: {
        'border-color': '#334155', 'border-width': 1.5,
        width: 24, height: 24, label: 'data(label)', 'font-size': '10px',
        'text-valign': 'center', 'text-halign': 'center', color: '#1e293b',
        'text-outline-color': '#ffffff', 'text-outline-width': 2,
        'background-color': (el) => ATOM_COLORS[el.data('element')] || '#94a3b8',
      }},
      { selector: 'edge', style: {
        width: 2, 'line-color': '#cbd5e1', 'curve-style': 'bezier',
      }},
    ],
    layout: { name: 'preset' },
    minZoom: 0.3, maxZoom: 3, wheelSensitivity: 0.3,
  });

  document.getElementById(containerId)._cy = cy;
}

function renderProps(containerId, props) {
  const el = document.getElementById(containerId);
  const entries = Object.entries(props || {})
    .filter(([k]) => k !== 'tag' && k !== 'index' && props[k] !== null && props[k] !== undefined);
  if (entries.length === 0) {
    el.innerHTML = '<p class="text-muted text-sm" style="grid-column:1/-1">Tidak ada data properti (graf disintesis dari SMILES).</p>';
    return;
  }
  el.innerHTML = entries
    .map(([k, v]) => `
      <div class="prop-item">
        <span class="prop-label">${PROP_LABELS[k] || k}</span>
        <span class="prop-value">${Number(v).toFixed(4)}</span>
      </div>
    `).join('');
}

// --- Compare ---
function toggleCompareId() {
  if (!currentMol) return;
  const id = currentMol.mol_id;
  if (compareIds.includes(id)) {
    compareIds = compareIds.filter(x => x !== id);
  } else if (compareIds.length < 4) {
    compareIds.push(id);
  }
  updateCompareUI();
  renderMolecule();
}

function removeCompareId(id) {
  compareIds = compareIds.filter(x => x !== id);
  updateCompareUI();
  if (showCompare) renderCompare();
}

function clearCompare() {
  compareIds = [];
  updateCompareUI();
  if (showCompare) toggleCompare();
}

function updateCompareUI() {
  const badge = document.getElementById('compare-badge');
  if (compareIds.length > 0) {
    badge.style.display = '';
    badge.textContent = compareIds.length;
  } else {
    badge.style.display = 'none';
  }

  const sel = document.getElementById('compare-selection');
  sel.style.display = compareIds.length > 0 ? '' : 'none';
  document.getElementById('compare-tags').innerHTML = compareIds.map(id =>
    `<span class="compare-tag">${id} <button onclick="removeCompareId('${id}')">&times;</button></span>`
  ).join('');
}

async function toggleCompare() {
  showCompare = !showCompare;
  const btn = document.getElementById('btn-compare');
  btn.className = showCompare ? 'btn btn-primary' : 'btn btn-outline';

  if (showCompare) {
    showView('compare');
    await renderCompare();
  } else {
    if (currentMol) { showView('mol'); } else { showView('empty'); }
  }
}

async function renderCompare() {
  if (compareIds.length < 2) {
    document.getElementById('compare-grid').innerHTML =
      '<p class="text-muted" style="grid-column:1/-1">Select at least 2 molecules to compare.</p>';
    return;
  }
  const mols = await apiFetch('/compare', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ids: compareIds }),
  });
  const grid = document.getElementById('compare-grid');
  grid.innerHTML = mols.map(m => `
    <div class="compare-mol">
      <div class="mol-header">
        <div><strong>${m.name || m.mol_id}</strong><br><span class="text-muted">${m.name ? m.mol_id + ' · ' : ''}${m.formula} · ${m.n_atoms} atoms</span></div>
      </div>
      <div id="cy-${m.mol_id}" class="cy-container"></div>
    </div>
  `).join('');
  mols.forEach(m => {
    setTimeout(() => renderGraph(`cy-${m.mol_id}`, m.nodes, m.edges), 50);
  });
}

// --- Init ---
loadMolecules();
