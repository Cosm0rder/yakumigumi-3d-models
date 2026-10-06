import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

const $ = id => document.getElementById(id);
const canvas = $('viewport');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.NoToneMapping;
const scene = new THREE.Scene();
scene.background = new THREE.Color('#f6f2e9');
const camera = new THREE.PerspectiveCamera(36, 1, .01, 100);
scene.add(new THREE.HemisphereLight(0xfff7e7, 0xc6b69e, 2.2));
const keyLight = new THREE.DirectionalLight(0xffffff, 2.1);
keyLight.position.set(3, 5, 4);
scene.add(keyLight);
const fillLight = new THREE.DirectionalLight(0xe8efff, .8);
fillLight.position.set(-3, 2, -2);
scene.add(fillLight);
const clock = new THREE.Clock();
const state = { root: null, mixer: null, action: null, clip: null, playing: false, loading: false, model: null, report: null, loadErrors: [], skinned: [], meshes: [], bones: [], baseline: new Map(), samples: [], generation: 0 };
const orbit = { target: new THREE.Vector3(), radius: 4, fitRadius:0, yaw: .15, pitch: .12 };
let fitSize = null;
function radiusToFitViewport(size) {
  const tangent = Math.tan(THREE.MathUtils.degToRad(camera.fov/2));
  const horizontalExtent = Math.hypot(size.x,size.z);
  const distance = Math.max(horizontalExtent/(2*tangent*Math.max(camera.aspect,.01)),size.y/(2*tangent));
  return Math.max(.4, Math.max(size.x,size.y,size.z)*1.95,(distance+size.z/2)*1.15);
}
const expectedBones = ['root', 'body', 'arm.L', 'arm.R', 'leg.L', 'leg.R'];
// GLTFLoader removes punctuation in names for animation track binding.
// Preserve raw names in the report; canonical aliases are for validation only.
const boneAliases = { armL:'arm.L', armR:'arm.R', legL:'leg.L', legR:'leg.R' };
const canonicalBoneName = name => boneAliases[name] || name;
const sampleSpecs = [
  { label: 'rest', blenderFrame: 1, gltfFrame: 0, timeSeconds: 1/12 },
  { label: 'arms', blenderFrame: 7, gltfFrame: 6, timeSeconds: 7/12 },
  { label: 'legs', blenderFrame: 13, gltfFrame: 12, timeSeconds: 13/12 },
];
const round = x => Number(Number(x).toFixed(7));
const vec = a => a.toArray().map(round);
const boxJSON = box => box.isEmpty() ? null : { min: vec(box.min), max: vec(box.max), size: vec(box.getSize(new THREE.Vector3())) };
const named = object => object.name || object.type;
const reportDOM = () => {
  $('runtime-report').textContent = JSON.stringify(state.report, null, 2);
  const r = state.report;
  const summary = r.checks ? {
    status:r.status, engine:r.engine, model:r.model, checks:r.checks,
    canonicalBones:r.structure.canonicalBones, rawBones:r.structure.uniqueBones,
    skinnedMeshCount:r.structure.skinnedMeshCount, meshCount:r.structure.meshCount,
    textureCount:r.textures.length, loaderErrors:r.loaderErrors,
    samples:r.samples.map((s,i)=>({label:s.label,timeSeconds:s.timeSeconds,maximumVertexDeltaFromRest:s.maximumVertexDeltaFromRest,nonFiniteVertices:s.nonFiniteVertices,jointRotationDeltaRadiansFromRest:r.jointRotationDeltaRadiansFromRest[i]}))
  } : r;
  $('check-summary').textContent = JSON.stringify(summary,null,2);
};
const status = s => { $('status').textContent = s; };
function controlsEnabled(enabled) {
  for (const id of ['rest','arms','legs','play','stop','sample-all','save-report','save-image']) $(id).disabled = !enabled;
}
function updateCamera() {
  const cp = Math.cos(orbit.pitch);
  camera.position.set(
    orbit.target.x + Math.sin(orbit.yaw) * cp * orbit.radius,
    orbit.target.y + Math.sin(orbit.pitch) * orbit.radius,
    orbit.target.z + Math.cos(orbit.yaw) * cp * orbit.radius
  );
  camera.lookAt(orbit.target);
}
function resize() {
  const rect = canvas.parentElement.getBoundingClientRect();
  renderer.setSize(Math.max(1, rect.width), Math.max(1, rect.height), false);
  camera.aspect = Math.max(1, rect.width) / Math.max(1, rect.height);
  camera.updateProjectionMatrix();
  if (state.root && fitSize) {
    const zoomRatio = orbit.fitRadius > 0 ? orbit.radius/orbit.fitRadius : 1;
    orbit.fitRadius = radiusToFitViewport(fitSize);
    orbit.radius = orbit.fitRadius*zoomRatio;
    camera.near = Math.max(.001,orbit.radius/500);
    camera.far = Math.max(30,orbit.radius*20);
    camera.updateProjectionMatrix(); updateCamera();
  }
}
new ResizeObserver(resize).observe(canvas.parentElement);
let pointer = null;
canvas.addEventListener('pointerdown', e => { pointer = { x: e.clientX, y: e.clientY }; canvas.setPointerCapture(e.pointerId); });
canvas.addEventListener('pointermove', e => {
  if (!pointer) return;
  orbit.yaw -= (e.clientX - pointer.x) * .008;
  orbit.pitch = THREE.MathUtils.clamp(orbit.pitch + (e.clientY - pointer.y) * .008, -1.2, 1.2);
  pointer = { x: e.clientX, y: e.clientY };
  updateCamera();
});
canvas.addEventListener('pointerup', () => { pointer = null; });
canvas.addEventListener('pointercancel', () => { pointer = null; });
canvas.addEventListener('wheel', e => {
  e.preventDefault();
  orbit.radius = THREE.MathUtils.clamp(orbit.radius * Math.exp(e.deltaY * .001), .15, 30);
  updateCamera();
}, { passive: false });
$('front').onclick = () => { orbit.yaw = 0; orbit.pitch = .05; updateCamera(); };
$('oblique').onclick = () => { orbit.yaw = .6; orbit.pitch = .18; updateCamera(); };
$('side').onclick = () => { orbit.yaw = Math.PI / 2; orbit.pitch = .05; updateCamera(); };

function disposeModel() {
  fitSize=null; orbit.fitRadius=0;
  state.playing = false;
  if (state.mixer) state.mixer.stopAllAction();
  if (state.root) {
    scene.remove(state.root);
    state.root.traverse(o => {
      if (o.geometry) o.geometry.dispose();
      const mats = o.material ? (Array.isArray(o.material) ? o.material : [o.material]) : [];
      for (const mat of mats) {
        for (const value of Object.values(mat)) if (value?.isTexture) value.dispose();
        mat.dispose();
      }
    });
  }
  Object.assign(state, { root: null, mixer: null, action: null, clip: null, skinned: [], meshes: [], bones: [], baseline: new Map(), samples: [] });
}

function updateBones() {
  state.root.updateMatrixWorld(true);
  for (const mesh of state.skinned) mesh.skeleton.update();
}

function capture(spec, keepBaseline = false) {
  updateBones();
  const allBounds = new THREE.Box3();
  const limbDeformation = Object.fromEntries(['arm.L','arm.R','leg.L','leg.R'].map(name => [name, {dominantWeightedVertices:0, movedVertices:0, maximumVertexDeltaFromRest:0}]));
  const outputMeshes = [];
  let nonFiniteVertices = 0;
  let maximumVertexDelta = 0;
  const p = new THREE.Vector3();
  for (const mesh of state.meshes) {
    const count = mesh.geometry?.attributes?.position?.count || 0;
    const bounds = new THREE.Box3();
    const coordinates = keepBaseline ? new Float32Array(count * 3) : null;
    const baseline = state.baseline.get(mesh.uuid);
    const skinIndex = mesh.geometry.getAttribute('skinIndex');
    const skinWeight = mesh.geometry.getAttribute('skinWeight');
    let meshMaxDelta = 0, movedVertices = 0;
    const representative = [];
    for (let i = 0; i < count; i++) {
      mesh.getVertexPosition(i, p);
      p.applyMatrix4(mesh.matrixWorld);
      if (![p.x,p.y,p.z].every(Number.isFinite)) { nonFiniteVertices++; continue; }
      bounds.expandByPoint(p);
      if (coordinates) { coordinates[i*3]=p.x; coordinates[i*3+1]=p.y; coordinates[i*3+2]=p.z; }
      if (baseline) {
        const d = Math.hypot(p.x-baseline[i*3], p.y-baseline[i*3+1], p.z-baseline[i*3+2]);
        meshMaxDelta = Math.max(meshMaxDelta, d);
        if (d > 1e-5) movedVertices++;
        if (mesh.isSkinnedMesh && skinIndex && skinWeight) {
          const indices = [skinIndex.getX(i),skinIndex.getY(i),skinIndex.getZ(i),skinIndex.getW(i)];
          const weights = [skinWeight.getX(i),skinWeight.getY(i),skinWeight.getZ(i),skinWeight.getW(i)];
          const strongest = weights.indexOf(Math.max(...weights));
          const bone = mesh.skeleton.bones[indices[strongest]];
          const limb = bone ? limbDeformation[canonicalBoneName(bone.name)] : null;
          if (limb && weights[strongest] > 1e-6) {
            limb.dominantWeightedVertices++;
            if (d > 1e-5) limb.movedVertices++;
            limb.maximumVertexDeltaFromRest = Math.max(limb.maximumVertexDeltaFromRest,d);
          }
        }
      }
      if (i === 0 || i === Math.floor(count/2) || i === count-1) representative.push({ index: i, world: vec(p) });
    }
    if (coordinates) state.baseline.set(mesh.uuid, coordinates);
    allBounds.union(bounds);
    maximumVertexDelta = Math.max(maximumVertexDelta, meshMaxDelta);
    outputMeshes.push({ name: named(mesh), skinned: !!mesh.isSkinnedMesh, vertices: count, worldBounds: boxJSON(bounds), maximumVertexDeltaFromRest: round(meshMaxDelta), movedVertices, representativeVertices: representative });
  }
  const bones = state.bones.map(b => ({
    name: named(b), canonicalName: canonicalBoneName(b.name), parent: b.parent?.name || b.parent?.type || null,
    localPosition: vec(b.position), localQuaternion: vec(b.quaternion),
    worldPosition: vec(b.getWorldPosition(new THREE.Vector3())),
    worldQuaternion: vec(b.getWorldQuaternion(new THREE.Quaternion()))
  }));
  for (const value of Object.values(limbDeformation)) value.maximumVertexDeltaFromRest = round(value.maximumVertexDeltaFromRest);
  return { ...spec, limbDeformation, actualActionTime: round(state.action?.time || 0), nonFiniteVertices, maximumVertexDeltaFromRest: round(maximumVertexDelta), worldBounds: boxJSON(allBounds), bones, meshes: outputMeshes };
}

function seek(spec) {
  state.playing = false;
  state.action.paused = false;
  state.action.enabled = true;
  state.mixer.timeScale = 1;
  state.mixer.setTime(spec.timeSeconds);
  state.action.paused = true;
  updateBones();
  renderer.render(scene, camera);
  status(state.model.label + ' · ' + spec.label + ' / ' + spec.timeSeconds + '秒');
}

function texturesInfo() {
  const textures = new Map();
  for (const mesh of state.meshes) {
    const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
    for (const mat of mats) {
      if (!mat) continue;
      for (const [slot, t] of Object.entries(mat)) {
        if (!t?.isTexture || textures.has(t.uuid)) continue;
        const image = t.image || t.source?.data;
        textures.set(t.uuid, { name: t.name || '(embedded)', slot, width: image?.width ?? null, height: image?.height ?? null, ready: (image?.width || 0) > 0 && (image?.height || 0) > 0, colorSpace: t.colorSpace || null });
      }
    }
  }
  return [...textures.values()];
}

function vertexColorInfo() {
  return state.meshes.map(mesh => {
    const color = mesh.geometry.getAttribute('color');
    const position = mesh.geometry.getAttribute('position');
    const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
    let finite = !!color;
    const min = [Infinity,Infinity,Infinity], max = [-Infinity,-Infinity,-Infinity];
    if (color) for (let i=0;i<color.count;i++) {
      const rgb=[color.getX(i),color.getY(i),color.getZ(i)];
      for(let channel=0;channel<3;channel++) {
        if(!Number.isFinite(rgb[channel])) finite=false;
        min[channel]=Math.min(min[channel],rgb[channel]); max[channel]=Math.max(max[channel],rgb[channel]);
      }
    }
    return {mesh:named(mesh),colorAttributePresent:!!color,colorVertices:color?.count || 0,
      positionVertices:position?.count || 0,itemSize:color?.itemSize || 0,finite,
      allMaterialsUseVertexColors:mats.every(mat=>mat?.vertexColors===true),
      channelMin:color?min.map(round):null,channelMax:color?max.map(round):null};
  });
}
function sampleAll() {
  if (!state.action) return;
  state.baseline.clear();
  state.samples = sampleSpecs.map((s, i) => { seek(s); return capture(s, i === 0); });
  const present = new Set(state.bones.map(b => canonicalBoneName(b.name)));
  const textures = texturesInfo();
  const vertexColors = vertexColorInfo();
  const jointDeltas = state.samples.map(sample => Object.fromEntries(expectedBones.map(name => {
    const rest = state.samples[0].bones.find(b => b.canonicalName === name);
    const posed = sample.bones.find(b => b.canonicalName === name);
    const angle = rest && posed ? new THREE.Quaternion().fromArray(rest.localQuaternion).normalize().angleTo(new THREE.Quaternion().fromArray(posed.localQuaternion).normalize()) : null;
    return [name, angle === null ? null : round(angle)];
  })));
  state.report = {
    schema: 'yakumigumi-threejs-runtime-v1',
    status: 'sampled_runtime; visual_reference_comparison_still_required',
    timestampUTC: new Date().toISOString(),
    engine: { name: 'Three.js', revision: THREE.REVISION },
    model: { label: state.model.label, source: state.model.publicPath || 'local_browser_file', testedGLBSha256: state.model.testedGLBSha256, testedGLBBytes: state.model.testedGLBBytes, clipName: state.clip.name, clipDurationSeconds: round(state.clip.duration), clipTrackCount: state.clip.tracks.length },
    frameMapping: 'Original exported GLB timestamps preserve Blender frames: 1/7/13 at 12 fps -> 1/12, 7/12, 13/12 seconds',
    structure: { skinnedMeshCount: state.skinned.length, meshCount: state.meshes.length, uniqueBones: [...new Set(state.bones.map(b=>b.name))], canonicalBones: [...present], skeletonJointCounts: state.skinned.map(m => ({ mesh: named(m), joints: m.skeleton.bones.length })) },
    textures, vertexColors, expectedEmbeddedTextureCount:0, loaderErrors: [...state.loadErrors],
    jointRotationDeltaRadiansFromRest: jointDeltas,
    checks: {
      loaded: true,
      expectedClipPresent: state.clip.name === state.model.clip,
      skinnedMeshesPresent: state.skinned.length > 0,
      expectedSixBonesPresent: expectedBones.every(b => present.has(b)),
      finiteDeformedVertices: state.samples.every(s => s.nonFiniteVertices === 0),
      armsPoseChangesVertices: state.samples[1].maximumVertexDeltaFromRest > 1e-5,
      legsPoseChangesVertices: state.samples[2].maximumVertexDeltaFromRest > 1e-5,
      bothArmJointRotationsChange: ['arm.L','arm.R'].every(name => jointDeltas[1][name] > 1e-5),
      bothLegJointRotationsChange: ['leg.L','leg.R'].every(name => jointDeltas[2][name] > 1e-5),
      allReferencedTextureImagesReady: textures.every(t => t.ready),
      loaderReportedNoMissingResources: state.loadErrors.length === 0,
      expectedVertexPaintAndMaterialCount: vertexColors.length === state.model.expectedMeshCount,
      bakedVertexColorsPresentFiniteAndUsed: vertexColors.length > 0 && vertexColors.every(row=>row.colorAttributePresent && row.finite && row.colorVertices===row.positionVertices && row.allMaterialsUseVertexColors),
      noRasterMapsExpectedOrMissing: textures.length === 0 && state.loadErrors.length === 0,
      independentlyWeightedLeftAndRightArmsDeform: ['arm.L','arm.R'].every(name=>state.samples[1].limbDeformation[name].dominantWeightedVertices>0 && state.samples[1].limbDeformation[name].movedVertices>0 && state.samples[1].limbDeformation[name].maximumVertexDeltaFromRest>1e-5),
      independentlyWeightedLeftAndRightLegsDeform: ['leg.L','leg.R'].every(name=>state.samples[2].limbDeformation[name].dominantWeightedVertices>0 && state.samples[2].limbDeformation[name].movedVertices>0 && state.samples[2].limbDeformation[name].maximumVertexDeltaFromRest>1e-5)
    },
    samples: state.samples
  };
  seek(sampleSpecs[0]);
  reportDOM();
  return state.report;
}

async function loadModel(model, buffer = null) {
  const generation = ++state.generation;
  state.loading = true;
  controlsEnabled(false);
  status(model.label + ' を読み込み中');
  disposeModel();
  state.model = model;
  state.loadErrors = [];
  try {
    const manager = new THREE.LoadingManager();
    manager.onError = url => { state.loadErrors.push(url.startsWith('blob:') ? '(embedded blob)' : url.split('/').pop()); };
    const loader = new GLTFLoader(manager);
    let testedBytes = buffer;
    let baseURL = '';
    if (!testedBytes) {
      const resolvedURL = new URL(model.url, location.href);
      const response = await fetch(resolvedURL, { cache: 'no-store' });
      if (!response.ok) throw new Error('GLB HTTP ' + response.status);
      testedBytes = await response.arrayBuffer();
      baseURL = new URL('./', resolvedURL).href;
    }
    const digest = await crypto.subtle.digest('SHA-256', testedBytes);
    const testedGLBSha256 = Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('');
    // Hash and parse the exact same bytes, including files selected locally.
    const profile = models.find(item=>item.expectedGLBSha256===testedGLBSha256);
    if(profile) model={...model,...profile,publicPath:buffer?'local_browser_file':model.publicPath};
    const gltf = await loader.parseAsync(testedBytes, baseURL);
    if (generation !== state.generation) return;
    state.model = { ...model, testedGLBSha256, testedGLBBytes: testedBytes.byteLength };
    const selectedProfile=models.findIndex(item=>item.key===model.key);
    if(selectedProfile>=0) $('model-select').value=selectedProfile;
    state.root = gltf.scene;
    scene.add(state.root);
    const boneIDs = new Set();
    state.root.traverse(o => {
      if (o.isMesh) { o.frustumCulled = false; state.meshes.push(o); }
      if (o.isSkinnedMesh) state.skinned.push(o);
      if (o.isBone && !boneIDs.has(o.uuid)) { boneIDs.add(o.uuid); state.bones.push(o); }
    });
    state.clip = gltf.animations.find(c => c.name === model.clip) || gltf.animations[0];
    if (!state.clip) throw new Error('GLBにanimation clipがありません');
    state.mixer = new THREE.AnimationMixer(state.root);
    state.action = state.mixer.clipAction(state.clip);
    state.action.setLoop(THREE.LoopRepeat, Infinity).play();
    updateBones();
    const bounds = new THREE.Box3().setFromObject(state.root, true);
    bounds.getCenter(orbit.target);
    const size = bounds.getSize(new THREE.Vector3());
    fitSize=size.clone(); orbit.fitRadius=radiusToFitViewport(fitSize); orbit.radius=orbit.fitRadius;
    orbit.yaw = 0; orbit.pitch = .06;
    camera.near = Math.max(.001, orbit.radius / 500);
    camera.far = Math.max(30, orbit.radius * 20);
    camera.updateProjectionMatrix(); updateCamera();
    sampleAll();
    controlsEnabled(true);
    state.loading = false;
  } catch (error) {
    state.loading = false;
    state.report = { status: 'load_failed', model: model.label, error: String(error.message || error), loaderErrors: state.loadErrors };
    reportDOM(); status('読込失敗: ' + (error.message || error)); controlsEnabled(false);
  }
}

$('rest').onclick = () => seek(sampleSpecs[0]);
$('arms').onclick = () => seek(sampleSpecs[1]);
$('legs').onclick = () => seek(sampleSpecs[2]);
$('sample-all').onclick = sampleAll;
$('play').onclick = () => { state.action.paused = false; state.playing = true; clock.getDelta(); status(state.model.label + ' · 動作を再生中'); };
$('stop').onclick = () => { state.playing = false; state.action.paused = true; status(state.model.label + ' · 停止 / ' + round(state.action.time) + '秒'); };
function saveBlob(blob, name) {
  const link = document.createElement('a'); link.href = URL.createObjectURL(blob); link.download = name; link.click();
  setTimeout(() => URL.revokeObjectURL(link.href), 1000);
}
$('save-report').onclick = () => { if (state.report) saveBlob(new Blob([JSON.stringify(state.report,null,2)], {type:'application/json'}), state.model.key + '-threejs-runtime.json'); };
$('save-image').onclick = () => { renderer.render(scene,camera); canvas.toBlob(blob => saveBlob(blob, state.model.key + '-threejs-preview.png'), 'image/png'); };
$('local-file').onchange = async e => {
  const file = e.target.files[0]; if (!file) return;
  const label = file.name.replace(/\.glb$/i,'');
  const key = label.replace(/[^a-z0-9_-]+/gi,'-');
  const guessedName = label.replace(/_rigged$/i,'') + '_FK_motion_check';
  await loadModel({ key, label, clip: guessedName, publicPath: 'local_browser_file' }, await file.arrayBuffer());
};

let models = [];
async function loadSelected() {
  const model = models[Number($('model-select').value)];
  if (model?.url) await loadModel(model);
  else {
    disposeModel(); state.model=null; controlsEnabled(false);
    state.report={status:'choose_local_GLB',model:model?.label || null}; reportDOM();
    status('v1.1.0のZIPを展開し、ローカルのGLBからファイルを選択してください');
  }
}
$('reload').onclick = loadSelected;
$('model-select').onchange = loadSelected;
try {
  const payload = await (await fetch('./models.json', { cache: 'no-store' })).json();
  models = payload.models;
  $('model-select').replaceChildren(...models.map((m,i) => { const o=document.createElement('option');o.value=i;o.textContent=m.label;return o; }));
  const wanted = new URLSearchParams(location.search).get('model');
  const idx = models.findIndex(m => m.key === wanted);
  if (idx >= 0) $('model-select').value = idx;
  await loadSelected();
} catch (error) { status('モデル一覧の読込失敗: ' + error.message); }
let lastTelemetry = 0;
function updateTelemetry() {
  const rect=canvas.getBoundingClientRect();
  const size=renderer.getSize(new THREE.Vector2());
  const buffer=renderer.getDrawingBufferSize(new THREE.Vector2());
  $('render-state').textContent=JSON.stringify({
    model:state.model?.key || null,
    animation:{playing:state.playing, actionTime:round(state.action?.time || 0), duration:round(state.clip?.duration || 0)},
    camera:{aspect:round(camera.aspect),position:vec(camera.position),target:vec(orbit.target),radius:round(orbit.radius),yaw:round(orbit.yaw),pitch:round(orbit.pitch),projectionMatrixFinite:camera.projectionMatrix.elements.every(Number.isFinite)},
    viewport:{cssWidth:round(rect.width),cssHeight:round(rect.height),rendererWidth:size.x,rendererHeight:size.y,drawingBufferWidth:buffer.x,drawingBufferHeight:buffer.y,pixelRatio:renderer.getPixelRatio(),aspectMatches:Math.abs(camera.aspect-rect.width/rect.height)<1e-5},
    specifications:{appearance:'baked vertex-color/PBR approximation; blend authoritative',facialDrivers:'Blender only; GLB has evaluated initial expression'}
  },null,2);
}
function tick() {
  requestAnimationFrame(tick);
  const dt = Math.min(clock.getDelta(), .05);
  if (state.playing && state.mixer) { state.mixer.update(dt); updateBones(); }
  renderer.render(scene,camera);
  if(performance.now()-lastTelemetry>200){lastTelemetry=performance.now();updateTelemetry();}
}
resize(); updateCamera(); tick();
