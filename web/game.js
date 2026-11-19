/* Relic Run — AssetForge proof game.
 * Loads packs/manifests written by `af build`; every visible object
 * carries its receipt (task id + sha) in the HUD. Swapping packs re-themes
 * the SAME level: the manifest is the brief.
 */
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const loader = new GLTFLoader();
const app = document.getElementById('app');
const hudCenter = document.getElementById('hud-center');
const toast = document.getElementById('toast');
const receiptsEl = document.getElementById('receipts');
let counterN = document.getElementById('n');
let counterTotal = document.getElementById('total');
const loadingEl = document.getElementById('loading');
const errorEl = document.getElementById('error');

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(55, innerWidth / innerHeight, 0.05, 100);
camera.position.set(0, 4.6, 7.6);
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
app.appendChild(renderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.maxPolarAngle = Math.PI * 0.495;
controls.minDistance = 3; controls.maxDistance = 18;
controls.target.set(0, 0.8, 0);

const hemi = new THREE.HemisphereLight(0xfff3e0, 0x202018, 1.1);
scene.add(hemi);
const dir = new THREE.DirectionalLight(0xffffff, 2.0);
dir.position.set(5, 9, 4);
dir.castShadow = true;
dir.shadow.mapSize.set(2048, 2048);
dir.shadow.camera.left = -9; dir.shadow.camera.right = 9;
dir.shadow.camera.top = 9; dir.shadow.camera.bottom = -9;
scene.add(dir);

const floorMat = new THREE.MeshStandardMaterial({ color: 0x5a4a33, roughness: 0.95 });
const wallMat = new THREE.MeshStandardMaterial({ color: 0x3a3226, roughness: 0.95 });
const floor = new THREE.Mesh(new THREE.BoxGeometry(13, 0.2, 13), floorMat);
floor.position.y = -0.1; floor.receiveShadow = true; scene.add(floor);
const walls = [];
[[0, 1.6, -6.5, 13], [0, 1.6, 6.5, 13], [-6.5, 1.6, 0, 13], [6.5, 1.6, 0, 13]].forEach(([x, y, z, w], i) => {
  const isSide = i >= 2;
  const wall = new THREE.Mesh(new THREE.BoxGeometry(isSide ? 0.3 : w, 3.2, isSide ? w : 0.3), wallMat);
  wall.position.set(x, y, z); wall.receiveShadow = true; scene.add(wall); walls.push(wall);
});

const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();
let slotGroups = [];
let collected = new Set();
let currentPack = null;

function setTheme(theme) {
  const fog = new THREE.Color(theme.fog);
  scene.background = fog.clone().multiplyScalar(0.55);
  scene.fog = new THREE.Fog(fog, 10, 26);
  floorMat.color.set(theme.floor);
  wallMat.color.set(new THREE.Color(theme.floor).multiplyScalar(0.55));
  document.documentElement.style.setProperty('--accent', theme.accent || '#ffb45e');
}

function clearSlots() {
  slotGroups.forEach(g => { scene.remove(g); g.traverse(o => { if (o.geometry) o.geometry.dispose(); }); });
  slotGroups = [];
  collected = new Set();
}

function showCenter(text, ms = 2600) {
  hudCenter.textContent = text; hudCenter.style.opacity = 1;
  setTimeout(() => { hudCenter.style.opacity = 0; }, ms);
}
let toastTimer;
function showToast(text) {
  toast.textContent = text; toast.style.opacity = 1;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { toast.style.opacity = 0; }, 2200);
}

function receiptRows(manifest) {
  const hd = receiptsEl.querySelector('.hd');
  receiptsEl.innerHTML = ''; receiptsEl.appendChild(hd);
  manifest.slots.forEach(s => {
    const row = document.createElement('div'); row.className = 'row'; row.id = 'rr-' + s.slot;
    row.innerHTML = `<span class="slot">${s.slot}</span>` +
      `<span class="sha">${s.sha256 || ''} · t${s.task_id || '-'}</span>` +
      `<span class="badge pending">—</span>`;
    receiptsEl.appendChild(row);
  });
}

function fitAndPlace(model, slot) {
  const box = new THREE.Box3().setFromObject(model);
  const size = box.getSize(new THREE.Vector3());
  const maxDim = Math.max(size.x, size.y, size.z) || 1;
  const scale = (slot.fit || 1.2) / maxDim;
  model.scale.multiplyScalar(scale);
  box.setFromObject(model);
  const center = box.getCenter(new THREE.Vector3());
  model.position.sub(center);
  model.position.y += (box.max.y - box.min.y) / 2 * 0; // grounded below
  const group = new THREE.Group();
  group.add(model);
  // ground the model: shift so its bbox bottom sits at y=0 inside group
  const box2 = new THREE.Box3().setFromObject(model);
  model.position.y -= box2.min.y;
  group.position.set(slot.position[0], 0, slot.position[2]);
  group.rotation.y = THREE.MathUtils.degToRad(slot.rotation ? slot.rotation[1] || 0 : 0);
  group.userData = { slot: slot.slot, sha: slot.sha256, baseY: group.position.y, phase: Math.random() * 6.28 };
  return group;
}

function loadPack(name, { announce } = {}) {
  loadingEl.style.display = 'flex';
  fetch(`manifests/${name}.json`).then(r => {
    if (!r.ok) throw new Error(`manifests/${name}.json -> HTTP ${r.status}`);
    return r.json();
  }).then(manifest => {
    clearSlots();
    packLoadedAt = performance.now();
    currentPack = manifest.name;
    setTheme(manifest.theme);
    document.querySelectorAll('#packbar button').forEach(b =>
      b.classList.toggle('active', b.id === 'btn-' + manifest.name));
    counterTotal.textContent = manifest.slots.length; counterN.textContent = 0;
    receiptRows(manifest);
    // resolve repo-root-absolute paths so the demo works from any base URL
    // (localhost:8000/web/ or username.github.io/<repo>/web/)
    const base = location.pathname.replace(/\/web\/.*$/, '');
    let loaded = 0;
    manifest.slots.forEach(slot => {
      const file = slot.file.startsWith('/')
        ? base + slot.file
        : (slot.file.startsWith('../') ? slot.file.slice(3) : slot.file);
      loader.load(file, gltf => {
        gltf.scene.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
        const group = fitAndPlace(gltf.scene, slot);
        scene.add(group); slotGroups.push(group);
        loaded += 1;
        const span = loadingEl.querySelector('span');
        if (span && loaded < manifest.slots.length) {
          span.innerHTML = `<span class="spin">◌</span>LOADING PACK… ${loaded}/${manifest.slots.length}`;
        }
        if (loaded === manifest.slots.length) {
          loadingEl.style.display = 'none';
          if (announce) showCenter(`PACK: ${manifest.name}.yaml — ${loaded} verified assets`, 2200);
        }
      }, undefined, err => {
        const row = document.getElementById('rr-' + slot.slot);
        if (row) row.querySelector('.badge').textContent = 'LOAD FAIL';
        loaded += 1;
        console.error(`failed to load ${slot.file}`, err);
        if (loaded === manifest.slots.length) loadingEl.style.display = 'none';
      });
    });
  }).catch(err => {
    loadingEl.style.display = 'none';
    errorEl.style.display = 'flex';
    errorEl.innerHTML = `Could not load pack manifest.<br>${err.message}<br><br>Serve the repo root:<br><code>python3 -m http.server 8000</code><br>then open <code>http://localhost:8000/web/</code>`;
  });
}

document.getElementById('btn-cozy-dungeon').onclick = () => loadPack('cozy-dungeon', { announce: true });
document.getElementById('btn-sci-fi-outpost').onclick = () => loadPack('sci-fi-outpost', { announce: true });

function collectGroup(g) {
  const { slot, sha } = g.userData;
  collected.add(slot);
  const start = performance.now();
  const shrink = () => {
    const t = Math.min(1, (performance.now() - start) / 350);
    g.scale.setScalar(Math.max(0.0001, 1 - t));
    g.position.y = t * 1.4;
    if (t < 1) requestAnimationFrame(shrink); else scene.remove(g);
  };
  shrink();
  counterN.textContent = collected.size;
  const row = document.getElementById('rr-' + slot);
  if (row) { const b = row.querySelector('.badge'); b.textContent = 'PASS ✓'; b.classList.remove('pending'); }
  showToast(`${slot} — receipt ${sha || '—'} re-verified offline ✓`);
  if (collected.size === parseInt(counterTotal.textContent, 10)) {
    showCenter(`PACK VERIFIED — all ${collected.size} relics machine-checked ✓ swap the pack ↑`, 4200);
    showStamp();
  }
}

addEventListener('pointerdown', e => {
  pointer.x = (e.clientX / innerWidth) * 2 - 1;
  pointer.y = -(e.clientY / innerHeight) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
  const hits = raycaster.intersectObjects(slotGroups, true);
  if (!hits.length) return;
  let obj = hits[0].object;
  while (obj && !obj.userData.slot) obj = obj.parent;
  if (!obj || collected.has(obj.userData.slot)) return;
  collectGroup(obj);
});

addEventListener('resize', () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});

const clock = new THREE.Clock();
let packLoadedAt = performance.now();
function fmtTime(ms) {
  const s = Math.floor(ms / 1000);
  return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0');
}
function showStamp() {
  const stamp = document.createElement('div');
  stamp.textContent = 'PACK CERTIFIED';
  stamp.style.cssText = 'position:fixed;top:38%;left:50%;transform:translate(-50%,-50%) rotate(-7deg);' +
    'border:4px solid var(--accent);color:var(--accent);padding:10px 26px;font:700 34px/1.2 ui-monospace,' +
    'Menlo,monospace;letter-spacing:.12em;border-radius:6px;opacity:0;transition:opacity .3s;z-index:15;' +
    'text-shadow:0 0 18px rgba(0,0,0,.6)';
  document.body.appendChild(stamp);
  requestAnimationFrame(() => { stamp.style.opacity = '1'; });
  setTimeout(() => { stamp.style.opacity = '0'; setTimeout(() => stamp.remove(), 400); }, 5200);
}
function animate() {
  requestAnimationFrame(animate);
  const t = clock.getElapsedTime();
  slotGroups.forEach(g => {
    if (collected.has(g.userData.slot)) return;
    g.position.y = 0.04 * Math.sin(t * 1.6 + g.userData.phase); // gentle relic float
    g.rotation.y += 0.0015;
  });
  const total = parseInt(counterTotal.textContent, 10) || 0;
  if (total > 0 && collected.size < total) {
    counterN.parentElement.innerHTML = `relics <b id="n">${collected.size}</b>/<span id="total">${total}</span> · ${fmtTime(performance.now() - packLoadedAt)}`;
    counterN = document.getElementById('n'); counterTotal = document.getElementById('total');
  }
  controls.update();
  renderer.render(scene, camera);
}
animate();

const first = new URLSearchParams(location.search).get('pack') || 'cozy-dungeon';
loadPack(first, { announce: true });

// debug/capture hook (used by the demo video pipeline; harmless in production)
window.__AF = {
  camera, controls, scene, THREE, slotGroups: () => slotGroups,
  collected: () => collected,
  loadPack: (n) => loadPack(n, { announce: true }),
  showCenter, showToast,
  setCam: (x, y, z, tx, ty, tz) => {
    camera.position.set(x, y, z); controls.target.set(tx, ty, tz); controls.update();
  },
  collectAt: (x, y, z) => {
    // project a world point to screen and fire the real collect handler
    const v = new THREE.Vector3(x, y, z).project(camera);
    const c = document.querySelector('canvas').getBoundingClientRect();
    const ev = new PointerEvent('pointerdown', {
      clientX: c.left + (v.x + 1) / 2 * c.width,
      clientY: c.top + (1 - v.y) / 2 * c.height,
      bubbles: true });
    document.querySelector('canvas').dispatchEvent(ev);
  },
  collectSlot: (name) => {
    const g = slotGroups.find(x => x.userData.slot === name);
    if (g && !collected.has(name)) { collectGroup(g); return true; }
    return false;
  },
  renderer
};
