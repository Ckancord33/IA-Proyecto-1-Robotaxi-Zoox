const CELL_FREE = 0;
const CELL_WALL = 1;
const CELL_START = 2;
const CELL_HIGH = 3;
const CELL_PASSENGER = 4;
const CELL_GOAL = 5;

const tileSize = 2.2;
const TAXI_FALLBACK_WORLD_Y = 0.72;
const TAXI_MODEL_CONFIG = {
  url: "assets/models/taxi.glb",
  scale: 1.4,
  // Ajustes por defecto para modelos exportados desde SketchUp ("acostados").
  yOffset: 0.02,
  worldY: 0.16,
  rotationX: -Math.PI / 2,
  rotationY: 0,
  rotationZ: 0,
  // Corrige el frente del modelo para que mire hacia la direccion de avance.
  headingOffset: Math.PI / 2,
};

const state = {
  maps: [],
  algorithms: [],
  world: null,
  result: null,
  taxiUsesModel: false,
  currentMapSignature: null,
  mapSyncInFlight: false,
  mapRefreshTimer: null,
  solve: {
    running: false,
    id: null,
    pollTimer: null,
  },
  solvedContext: {
    mapName: null,
    algorithm: null,
    canAnimate: false,
  },
  lastAlgorithmSelection: null,
  animation: {
    playing: false,
    pathIndex: 0,
    progress: 0,
    speed: 1.6,
  },
};

const dom = {
  mapSelect: document.getElementById("mapSelect"),
  algorithmSelect: document.getElementById("algorithmSelect"),
  solveBtn: document.getElementById("solveBtn"),
  playFloatingBtn: document.getElementById("playFloatingBtn"),
  resetFloatingBtn: document.getElementById("resetFloatingBtn"),
  speedRange: document.getElementById("speedRange"),
  speedValue: document.getElementById("speedValue"),
  metricsContent: document.getElementById("metricsContent"),
  logOutput: document.getElementById("logOutput"),
  clearLogBtn: document.getElementById("clearLogBtn"),
  sceneCanvas: document.getElementById("sceneCanvas"),
  sceneLoading: document.getElementById("sceneLoading"),
  sceneLoadingText: document.getElementById("sceneLoadingText"),
};

window.addEventListener("error", (event) => {
  if (dom.logOutput) {
    dom.logOutput.textContent += `[ERROR] ${event.message}\n`;
  }
  if (dom.metricsContent) {
    dom.metricsContent.textContent = `Error frontend: ${event.message}`;
  }
});

if (!window.THREE) {
  dom.metricsContent.textContent = "Error: Three.js no pudo cargarse.";
  throw new Error("Three.js no disponible en window");
}

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x14181f);
scene.fog = null;

const camera = new THREE.PerspectiveCamera(55, 1, 0.1, 300);
camera.position.set(18, 20, 24);

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.outputEncoding = THREE.sRGBEncoding;
dom.sceneCanvas.appendChild(renderer.domElement);

let controls = null;
let useManualOrbit = false;
const manualOrbit = {
  dragging: false,
  panning: false,
  lastX: 0,
  lastY: 0,
  target: new THREE.Vector3(8, 0, 8),
  radius: 34,
  theta: Math.PI / 4,
  phi: 1.02,
};

if (typeof THREE.OrbitControls === "function") {
  controls = new THREE.OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.enableRotate = true;
  controls.enableZoom = true;
  controls.enablePan = true;
  controls.rotateSpeed = 0.85;
  controls.zoomSpeed = 1.05;
  controls.panSpeed = 0.75;
  controls.minDistance = 6;
  controls.maxDistance = 120;
  controls.maxPolarAngle = Math.PI * 0.49;
  controls.target.set(8, 0, 8);
  appendLog("Controles de camara: OrbitControls activo (arrastrar/rueda). ");
} else {
  useManualOrbit = true;
  //appendLog("OrbitControls no disponible. Se activa modo manual.");
}

const hemi = new THREE.HemisphereLight(0xb8d4ff, 0x12161e, 1.1);
scene.add(hemi);

const directional = new THREE.DirectionalLight(0xffffff, 1.2);
directional.position.set(18, 24, 10);
scene.add(directional);

const fillLight = new THREE.DirectionalLight(0x8bd3ff, 0.42);
fillLight.position.set(-14, 10, -8);
scene.add(fillLight);

const boardGroup = new THREE.Group();
scene.add(boardGroup);

const passengerMeshes = new Map();
const modelCache = new Map();
let taxiMesh = null;
let routeLine = null;
const scriptLoadCache = new Map();

const GLTF_LOADER_URLS = [
  "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/examples/js/loaders/GLTFLoader.js",
  "https://unpkg.com/three@0.128.0/examples/js/loaders/GLTFLoader.js",
  "https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/GLTFLoader.js",
];

const DRACO_LOADER_URLS = [
  "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/examples/js/loaders/DRACOLoader.js",
  "https://unpkg.com/three@0.128.0/examples/js/loaders/DRACOLoader.js",
  "https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/DRACOLoader.js",
];

function loadScriptOnce(url) {
  if (scriptLoadCache.has(url)) {
    return scriptLoadCache.get(url);
  }

  const promise = new Promise((resolve) => {
    const script = document.createElement("script");
    script.src = url;
    script.async = true;
    script.onload = () => resolve(true);
    script.onerror = () => resolve(false);
    document.head.appendChild(script);
  });

  scriptLoadCache.set(url, promise);
  return promise;
}

async function ensureScriptGlobal(isAvailable, urls) {
  if (isAvailable()) {
    return true;
  }

  for (const url of urls) {
    const ok = await loadScriptOnce(url);
    if (ok && isAvailable()) {
      return true;
    }
  }

  return false;
}

function syncManualOrbitFromCamera(targetVec) {
  const offset = camera.position.clone().sub(targetVec);
  manualOrbit.radius = Math.max(6, offset.length());
  manualOrbit.theta = Math.atan2(offset.x, offset.z);
  const yNorm = THREE.MathUtils.clamp(offset.y / manualOrbit.radius, -1, 1);
  manualOrbit.phi = Math.acos(yNorm);
  manualOrbit.target.copy(targetVec);
}

function applyManualOrbitCamera() {
  const sinPhi = Math.sin(manualOrbit.phi);
  const x = manualOrbit.target.x + manualOrbit.radius * sinPhi * Math.sin(manualOrbit.theta);
  const y = manualOrbit.target.y + manualOrbit.radius * Math.cos(manualOrbit.phi);
  const z = manualOrbit.target.z + manualOrbit.radius * sinPhi * Math.cos(manualOrbit.theta);
  camera.position.set(x, y, z);
  camera.lookAt(manualOrbit.target);
}

function setupManualOrbitEvents() {
  const canvas = renderer.domElement;
  canvas.style.cursor = "grab";
  canvas.style.touchAction = "none";
  canvas.style.pointerEvents = "auto";

  canvas.addEventListener("contextmenu", (event) => {
    if (useManualOrbit) {
      event.preventDefault();
    }
  });

  canvas.addEventListener("pointerdown", (event) => {
    if (!useManualOrbit) {
      return;
    }
    manualOrbit.dragging = true;
    manualOrbit.panning = event.button === 1 || event.button === 2;
    manualOrbit.lastX = event.clientX;
    manualOrbit.lastY = event.clientY;
    canvas.style.cursor = "grabbing";
  });

  canvas.addEventListener("pointerup", () => {
    manualOrbit.dragging = false;
    manualOrbit.panning = false;
    canvas.style.cursor = "grab";
  });

  canvas.addEventListener("pointerleave", () => {
    manualOrbit.dragging = false;
    manualOrbit.panning = false;
    canvas.style.cursor = "grab";
  });

  canvas.addEventListener("pointermove", (event) => {
    if (!useManualOrbit || !manualOrbit.dragging) {
      return;
    }
    const dx = event.clientX - manualOrbit.lastX;
    const dy = event.clientY - manualOrbit.lastY;
    manualOrbit.lastX = event.clientX;
    manualOrbit.lastY = event.clientY;

    if (manualOrbit.panning) {
      const panScale = manualOrbit.radius * 0.0016;

      // Pan basado en la orientacion de camara para que el movimiento sea
      // coherente con la direccion del arrastre en pantalla.
      const camForward = new THREE.Vector3();
      camera.getWorldDirection(camForward);
      camForward.y = 0;
      if (camForward.lengthSq() < 1e-6) {
        camForward.set(0, 0, -1);
      }
      camForward.normalize();

      const camRight = new THREE.Vector3().crossVectors(camForward, new THREE.Vector3(0, 1, 0)).normalize();

      manualOrbit.target.add(camRight.multiplyScalar(-dx * panScale));
      manualOrbit.target.add(camForward.multiplyScalar(dy * panScale));
      return;
    }

    manualOrbit.theta -= dx * 0.006;
    manualOrbit.phi -= dy * 0.005;
    manualOrbit.phi = THREE.MathUtils.clamp(manualOrbit.phi, 0.24, Math.PI * 0.49);
  });

  canvas.addEventListener(
    "wheel",
    (event) => {
      if (!useManualOrbit) {
        return;
      }
      event.preventDefault();
      const factor = event.deltaY > 0 ? 1.08 : 0.92;
      manualOrbit.radius = THREE.MathUtils.clamp(manualOrbit.radius * factor, 6, 120);
    },
    { passive: false }
  );
}

function appendLog(message) {
  const now = new Date().toLocaleTimeString();
  dom.logOutput.textContent += `[${now}] ${message}\n`;
  dom.logOutput.scrollTop = dom.logOutput.scrollHeight;
}

function clearLog() {
  dom.logOutput.textContent = "";
}

function updateSolveButton() {
  if (state.solve.running) {
    dom.solveBtn.textContent = "Cancelar Calculo";
    dom.solveBtn.classList.add("danger");
    return;
  }
  if (state.solvedContext.canAnimate) {
    dom.solveBtn.textContent = "Animar Solucion";
    dom.solveBtn.classList.remove("danger");
    return;
  }
  dom.solveBtn.textContent = "Calcular Solucion";
  dom.solveBtn.classList.remove("danger");
}

function resetSolvedContext() {
  state.solvedContext.mapName = null;
  state.solvedContext.algorithm = null;
  state.solvedContext.canAnimate = false;
  updateSolveButton();
}

function setSceneLoading(isLoading, text = "Cargando mapa...") {
  if (!dom.sceneLoading) {
    return;
  }
  dom.sceneLoading.hidden = !isLoading;
  if (dom.sceneLoadingText) {
    dom.sceneLoadingText.textContent = text;
  }
}

function hasAnimatableSolution() {
  return Boolean(state.result && state.result.found && state.result.path && state.result.path.length > 0);
}

function updateFloatingControls() {
  const hasSolution = hasAnimatableSolution();
  dom.playFloatingBtn.disabled = !hasSolution;
  dom.playFloatingBtn.title = hasSolution
    ? "Reproducir animacion"
    : "Primero calcula la solucion.";

  dom.resetFloatingBtn.disabled = !hasSolution;
  dom.resetFloatingBtn.title = hasSolution
    ? "Reiniciar animacion"
    : "No hay animacion para reiniciar.";
}

function stopSolvePolling() {
  if (state.solve.pollTimer) {
    window.clearInterval(state.solve.pollTimer);
    state.solve.pollTimer = null;
  }
}

function markSolveStopped() {
  state.solve.running = false;
  state.solve.id = null;
  stopSolvePolling();
  updateSolveButton();
}

function arraysEqual(a, b) {
  if (a.length !== b.length) {
    return false;
  }
  for (let i = 0; i < a.length; i += 1) {
    if (a[i] !== b[i]) {
      return false;
    }
  }
  return true;
}

async function bridgeCall(name, ...args) {
  if (!window.eel || typeof window.eel[name] !== "function") {
    throw new Error("Eel no disponible en la ventana actual");
  }
  return window.eel[name](...args)();
}

function setMetrics(text) {
  dom.metricsContent.textContent = text;
}

function taxiWorldY() {
  return state.taxiUsesModel ? TAXI_MODEL_CONFIG.worldY : TAXI_FALLBACK_WORLD_Y;
}

function headingForStep(rowDelta, colDelta) {
  // Coordenadas del mundo: X=col, Z=row.
  // Convencion base: frente hacia +Z, corregible con headingOffset.
  if (rowDelta < 0) return Math.PI; // UP
  if (rowDelta > 0) return 0; // DOWN
  if (colDelta > 0) return Math.PI / 2; // RIGHT
  if (colDelta < 0) return -Math.PI / 2; // LEFT
  return 0;
}

function setTaxiHeading(rowDelta, colDelta) {
  if (!taxiMesh) {
    return;
  }
  taxiMesh.rotation.y = headingForStep(rowDelta, colDelta) + TAXI_MODEL_CONFIG.headingOffset;
}

function resetBoard() {
  while (boardGroup.children.length > 0) {
    const child = boardGroup.children[0];
    boardGroup.remove(child);
  }
  passengerMeshes.clear();
  taxiMesh = null;
  routeLine = null;
  state.taxiUsesModel = false;
}

function cellNeonColor(cellType) {
  if (cellType === CELL_HIGH) return 0xff2a2a; // trafico alto: rojo neon
  if (cellType === CELL_START) return 0x25ff73; // inicio: verde neon
  if (cellType === CELL_PASSENGER) return 0xf4feff; // pasajero: blanco neon
  if (cellType === CELL_GOAL) return 0xffb34f; // destino
  return 0x2ad6ff; // via libre: azul neon
}

function createNeonRoadCell(type, height, x, z) {
  const neon = cellNeonColor(type);
  const tileGroup = new THREE.Group();
  tileGroup.position.set(x, 0, z);

  const base = new THREE.Mesh(
    new THREE.BoxGeometry(tileSize, height, tileSize),
    new THREE.MeshStandardMaterial({
      color: 0x020305,
      roughness: 0.7,
      metalness: 0.05,
      emissive: neon,
      emissiveIntensity: 0.09,
    })
  );
  base.position.y = height / 2;
  tileGroup.add(base);

  const edgeLines = new THREE.LineSegments(
    new THREE.EdgesGeometry(new THREE.BoxGeometry(tileSize, height, tileSize)),
    new THREE.LineBasicMaterial({ color: neon })
  );
  edgeLines.position.y = height / 2;
  tileGroup.add(edgeLines);

  const topGrid = new THREE.GridHelper(tileSize - 0.02, 4, neon, neon);
  topGrid.position.y = height + 0.015;
  topGrid.material.opacity = 0.95;
  topGrid.material.transparent = true;
  tileGroup.add(topGrid);

  return tileGroup;
}

function createNeonWallCell(height, x, z) {
  const neonBlue = 0x2ad6ff;
  const wallGroup = new THREE.Group();
  wallGroup.position.set(x, 0, z);

  const wall = new THREE.Mesh(
    new THREE.BoxGeometry(1.8, height, 1.8),
    new THREE.MeshStandardMaterial({
      color: 0x010203,
      roughness: 0.85,
      metalness: 0.05,
    })
  );
  wall.position.y = height / 2;
  wallGroup.add(wall);

  const wallEdges = new THREE.LineSegments(
    new THREE.EdgesGeometry(new THREE.BoxGeometry(1.8, height, 1.8)),
    new THREE.LineBasicMaterial({ color: neonBlue })
  );
  wallEdges.position.y = height / 2;
  wallGroup.add(wallEdges);

  // Bandas neon para efecto de rayas estilo Tron.
  const bandMaterial = new THREE.MeshStandardMaterial({
    color: neonBlue,
    emissive: neonBlue,
    emissiveIntensity: 0.5,
    roughness: 0.35,
    metalness: 0.2,
  });

  const bandA = new THREE.Mesh(new THREE.BoxGeometry(1.82, 0.03, 1.82), bandMaterial);
  bandA.position.y = height * 0.38;
  wallGroup.add(bandA);

  const bandB = new THREE.Mesh(new THREE.BoxGeometry(1.82, 0.03, 1.82), bandMaterial);
  bandB.position.y = height * 0.72;
  wallGroup.add(bandB);

  return wallGroup;
}

function createRouteLine(path) {
  if (!path || path.length < 2) {
    return;
  }
  const points = path.map((node) =>
    new THREE.Vector3(node.col * tileSize, 0.8, node.row * tileSize)
  );
  const geometry = new THREE.BufferGeometry().setFromPoints(points);
  const material = new THREE.LineBasicMaterial({ color: 0x42f59e });
  routeLine = new THREE.Line(geometry, material);
  boardGroup.add(routeLine);
}

function createTaxiFallbackMesh() {
  const body = new THREE.Mesh(
    new THREE.BoxGeometry(1.35, 0.7, 1.0),
    new THREE.MeshStandardMaterial({ color: 0xffdc45, roughness: 0.42 })
  );
  const roof = new THREE.Mesh(
    new THREE.BoxGeometry(0.8, 0.35, 0.78),
    new THREE.MeshStandardMaterial({ color: 0x1f324a, roughness: 0.3 })
  );
  roof.position.y = 0.5;
  body.add(roof);
  return body;
}

function normalizeModelForTaxi(modelRoot) {
  // Centra y escala el modelo para que entre en una celda del tablero.
  // Se calcula despues de rotar para evitar desfases por pivote del archivo origen.
  const box = new THREE.Box3().setFromObject(modelRoot);
  if (box.isEmpty()) {
    return;
  }

  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());

  const maxDim = Math.max(size.x, size.y, size.z, 1e-6);
  const targetMaxDim = 1.35;
  const autoScale = targetMaxDim / maxDim;

  // Centrar en X/Z para que la posicion del taxi coincida con el centro de celda.
  modelRoot.position.x -= center.x;
  modelRoot.position.z -= center.z;
  modelRoot.scale.multiplyScalar(autoScale);

  const normalizedBox = new THREE.Box3().setFromObject(modelRoot);
  const minY = normalizedBox.min.y;
  if (Number.isFinite(minY)) {
    modelRoot.position.y -= minY;
  }
}

function loadGltfScene(url) {
  if (modelCache.has(url)) {
    return modelCache.get(url);
  }

  const loadingPromise = (async () => {
    const hasGltfLoader = await ensureScriptGlobal(
      () => typeof THREE.GLTFLoader === "function",
      GLTF_LOADER_URLS
    );
    if (!hasGltfLoader) {
      return null;
    }

    await ensureScriptGlobal(
      () => typeof THREE.DRACOLoader === "function",
      DRACO_LOADER_URLS
    );

    const loader = new THREE.GLTFLoader();
    if (typeof THREE.DRACOLoader === "function") {
      const dracoLoader = new THREE.DRACOLoader();
      dracoLoader.setDecoderPath("https://www.gstatic.com/draco/v1/decoders/");
      loader.setDRACOLoader(dracoLoader);
    }
    if (typeof window.MeshoptDecoder !== "undefined") {
      loader.setMeshoptDecoder(window.MeshoptDecoder);
    }

    return new Promise((resolve) => {
      loader.load(
        url,
        (gltf) => {
          resolve(gltf && gltf.scene ? gltf.scene : null);
        },
        undefined,
        () => {
          resolve(null);
        }
      );
    });
  })();

  modelCache.set(url, loadingPromise);
  return loadingPromise;
}

async function attachTaxiModel(taxiRoot, fallbackMesh) {
  const modelScene = await loadGltfScene(TAXI_MODEL_CONFIG.url);

  if (!modelScene) {
    return;
  }

  // Evita montar un modelo obsoleto si el tablero ya se regenero.
  if (taxiMesh !== taxiRoot) {
    return;
  }

  const modelInstance = modelScene.clone(true);
  modelInstance.rotation.x = TAXI_MODEL_CONFIG.rotationX;
  modelInstance.rotation.y = TAXI_MODEL_CONFIG.rotationY;
  modelInstance.rotation.z = TAXI_MODEL_CONFIG.rotationZ;
  normalizeModelForTaxi(modelInstance);
  modelInstance.scale.multiplyScalar(TAXI_MODEL_CONFIG.scale);
  modelInstance.position.y += TAXI_MODEL_CONFIG.yOffset;

  modelInstance.traverse((obj) => {
    if (obj && obj.isMesh) {
      obj.castShadow = true;
      obj.receiveShadow = true;
    }
  });

  taxiRoot.add(modelInstance);
  fallbackMesh.visible = false;
  state.taxiUsesModel = true;
  taxiRoot.position.y = taxiWorldY();
}

function createTaxi(position) {
  const root = new THREE.Group();
  root.position.set(position[1] * tileSize, taxiWorldY(), position[0] * tileSize);

  const fallbackMesh = createTaxiFallbackMesh();
  root.add(fallbackMesh);

  boardGroup.add(root);
  taxiMesh = root;

  void attachTaxiModel(root, fallbackMesh);
}

function renderWorld(world, options = {}) {
  const { preserveCamera = false } = options;
  resetBoard();
  state.world = world;

  const rows = world.rows;
  const cols = world.cols;
  const centerX = ((cols - 1) * tileSize) / 2;
  const centerZ = ((rows - 1) * tileSize) / 2;

  const basePlane = new THREE.Mesh(
    new THREE.BoxGeometry(cols * tileSize + 2, 0.2, rows * tileSize + 2),
    new THREE.MeshStandardMaterial({ color: 0x050608, roughness: 0.95, metalness: 0.04 })
  );
  basePlane.position.set(centerX, -0.15, centerZ);
  boardGroup.add(basePlane);

  // Plataforma continua oscura debajo de todas las casillas para que el piso se vea conectado.
  const roadDeck = new THREE.Mesh(
    new THREE.BoxGeometry(cols * tileSize, 0.06, rows * tileSize),
    new THREE.MeshStandardMaterial({ color: 0x020305, roughness: 0.88, metalness: 0.04 })
  );
  roadDeck.position.set(centerX, 0.03, centerZ);
  boardGroup.add(roadDeck);

  const guideGrid = new THREE.GridHelper(cols * tileSize + 2, cols, 0x2ad6ff, 0x2ad6ff);
  guideGrid.position.set(centerX, 0.01, centerZ);
  guideGrid.material.opacity = 0.18;
  guideGrid.material.transparent = true;
  boardGroup.add(guideGrid);

  for (let r = 0; r < rows; r += 1) {
    for (let c = 0; c < cols; c += 1) {
      const type = world.grid[r][c];
      const h = type === CELL_WALL ? 1.15 : 0.08;
      if (type === CELL_WALL) {
        boardGroup.add(createNeonWallCell(h, c * tileSize, r * tileSize));
      } else {
        boardGroup.add(createNeonRoadCell(type, h, c * tileSize, r * tileSize));
      }

      if (type === CELL_PASSENGER) {
        const passengerGeometry =
          typeof THREE.CapsuleGeometry === "function"
            ? new THREE.CapsuleGeometry(0.22, 0.48, 4, 8)
            : new THREE.SphereGeometry(0.34, 16, 16);
        const passenger = new THREE.Mesh(
          passengerGeometry,
          new THREE.MeshStandardMaterial({
            color: 0xf7fdff,
            emissive: 0xd8f8ff,
            emissiveIntensity: 0.42,
            roughness: 0.24,
            metalness: 0.08,
          })
        );
        passenger.position.set(c * tileSize, h + 0.36, r * tileSize);
        boardGroup.add(passenger);
        passengerMeshes.set(`${r}-${c}`, passenger);
      }

      if (type === CELL_GOAL) {
        const marker = new THREE.Mesh(
          new THREE.ConeGeometry(0.3, 0.9, 6),
          new THREE.MeshStandardMaterial({ color: 0xffb05a, emissive: 0x361500 })
        );
        marker.position.set(c * tileSize, h + 0.45, r * tileSize);
        boardGroup.add(marker);
      }
    }
  }

  createTaxi(world.start);
  if (!preserveCamera) {
    // Vista inicial alineada con el TXT (sin giro diagonal):
    // columnas -> izquierda/derecha, filas -> arriba/abajo, con plano picado.
    camera.position.set(centerX, Math.max(rows, cols) * 2.35, centerZ + rows * 0.95);
    camera.lookAt(centerX, 0, centerZ);

    if (controls && !useManualOrbit) {
      controls.target.set(centerX, 0, centerZ);
      controls.update();
    } else {
      syncManualOrbitFromCamera(new THREE.Vector3(centerX, 0, centerZ));
      applyManualOrbitCamera();
    }
  } else if (controls && !useManualOrbit) {
    controls.update();
  } else {
    applyManualOrbitCamera();
  }

  appendLog(`Mapa ${world.mapName} cargado (${rows}x${cols}).`);
}

function hidePickedPassengers(pickedUpFlags) {
  if (!state.world) return;
  state.world.passengers.forEach(([r, c], idx) => {
    const mesh = passengerMeshes.get(`${r}-${c}`);
    if (!mesh) return;
    mesh.visible = !pickedUpFlags[idx];
  });
}

function applyAnimationPose() {
  if (!taxiMesh || !state.result || !state.result.path.length) {
    return;
  }

  const path = state.result.path;
  const i = state.animation.pathIndex;

  if (i >= path.length - 1) {
    const end = path[path.length - 1];
    taxiMesh.position.set(end.col * tileSize, taxiWorldY(), end.row * tileSize);
    hidePickedPassengers(end.pickedUp);
    state.animation.playing = false;
    appendLog("Animacion terminada: taxi en destino.");
    return;
  }

  const from = path[i];
  const to = path[i + 1];
  const t = state.animation.progress;

  setTaxiHeading(to.row - from.row, to.col - from.col);

  const row = from.row + (to.row - from.row) * t;
  const col = from.col + (to.col - from.col) * t;

  taxiMesh.position.set(col * tileSize, taxiWorldY(), row * tileSize);
  hidePickedPassengers(from.pickedUp);
}

async function loadSelectedMap(options = {}) {
  const { skipMetrics = false } = options;
  const mapName = dom.mapSelect.value;
  setSceneLoading(true, `Cargando ${mapName}...`);
  try {
    const response = await bridgeCall("load_map", mapName);
    if (!response.ok) {
      appendLog(`Error cargando mapa: ${response.error}`);
      return;
    }

    renderWorld(response.payload.world);
    state.currentMapSignature = response.payload.world.sourceSignature || null;
    state.result = null;
    resetSolvedContext();
    state.animation.playing = false;
    state.animation.pathIndex = 0;
    state.animation.progress = 0;
    updateFloatingControls();

    if (!skipMetrics) {
      setMetrics("Mapa listo. Ejecuta 'Calcular Solucion'.");
    }
  } finally {
    setSceneLoading(false);
  }
}

function resultToMetrics(result, algorithmName) {
  if (!result.found) {
    return [
      `Algoritmo: ${algorithmName}`,
      "Resultado: sin solucion",
      `Nodos expandidos: ${result.nodesExpanded}`,
      `Tiempo: ${result.time.toFixed(4)} s`,
    ].join("\n");
  }

  return [
    `Algoritmo: ${algorithmName}`,
    "Resultado: solucion encontrada",
    `Nodos expandidos: ${result.nodesExpanded}`,
    `Profundidad: ${result.depth}`,
    `Costo total: ${result.cost}`,
    `Tiempo: ${result.time.toFixed(4)} s`
  ].join("\n");
}

function progressToMetrics(progress, algorithmName) {
  const nodesExpanded = Number(progress?.nodes_expanded ?? 0);
  const elapsed = Number(progress?.elapsed_time ?? 0);
  const frontierSize = Number(progress?.frontier_size ?? 0);

  return [
    `Algoritmo: ${algorithmName}`,
    "Resultado: calculando...",
    `Nodos expandidos (parcial): ${nodesExpanded}`,
    `Frontera actual: ${frontierSize}`,
    `Tiempo transcurrido: ${elapsed.toFixed(2)} s`,
  ].join("\n");
}

async function solveCurrentMap() {
  if (state.solve.running && state.solve.id !== null) {
    const cancelResponse = await bridgeCall("cancel_solve", state.solve.id);
    if (!cancelResponse.ok) {
      appendLog(`Error cancelando calculo: ${cancelResponse.error}`);
      return;
    }
    markSolveStopped();
    setSceneLoading(false);
    appendLog("Calculo cancelado por el usuario.");
    return;
  }

  const mapName = dom.mapSelect.value;
  const algorithm = dom.algorithmSelect.value;

  if (
    state.solvedContext.canAnimate &&
    state.solvedContext.mapName === mapName &&
    state.solvedContext.algorithm === algorithm
  ) {
    startAnimation();
    return;
  }

  appendLog(`Calculando ${algorithm} en ${mapName}...`);
  const startResponse = await bridgeCall("start_solve", mapName, algorithm);
  if (!startResponse.ok) {
    appendLog(`Error iniciando solver: ${startResponse.error}`);
    updateFloatingControls();
    return;
  }

  state.solve.running = true;
  state.solve.id = startResponse.solveId;
  updateSolveButton();
  setSceneLoading(true, `Calculando ${algorithm}...`);

  stopSolvePolling();
  state.solve.pollTimer = window.setInterval(async () => {
    if (!state.solve.running || state.solve.id === null) {
      return;
    }

    try {
      const status = await bridgeCall("get_solve_status", state.solve.id);
      if (!status.ok) {
        appendLog(`Error consultando solver: ${status.error}`);
        markSolveStopped();
        setSceneLoading(false);
        return;
      }

      if (status.state === "running") {
        if (status.progress) {
          const algorithmLabel = status.progress.algorithm || algorithm;
          setMetrics(progressToMetrics(status.progress, algorithmLabel));
        }
        return;
      }

      if (status.state === "done") {
        const payload = status.payload;
        state.world = payload.world;
        state.currentMapSignature = payload.world.sourceSignature || null;
        state.result = payload.result;

        renderWorld(state.world, { preserveCamera: true });
        createRouteLine(state.result.path);

        setMetrics(resultToMetrics(state.result, payload.algorithm));

        if (state.result.found) {
          appendLog(`Solucion encontrada. Costo ${state.result.cost}, pasos ${state.result.actions.length}.`);
          state.solvedContext.mapName = mapName;
          state.solvedContext.algorithm = algorithm;
          state.solvedContext.canAnimate = true;
        } else {
          appendLog("No se encontro solucion.");
          state.solvedContext.mapName = null;
          state.solvedContext.algorithm = null;
          state.solvedContext.canAnimate = false;
        }

        state.animation.playing = false;
        state.animation.pathIndex = 0;
        state.animation.progress = 0;
        updateFloatingControls();

        markSolveStopped();
        setSceneLoading(false);
        updateSolveButton();
        return;
      }

      if (status.state === "error") {
        appendLog(`Error en solver: ${status.error}`);
        markSolveStopped();
        setSceneLoading(false);
        updateFloatingControls();
        return;
      }

      if (status.state === "cancelled" || status.state === "idle" || status.state === "stale") {
        markSolveStopped();
        setSceneLoading(false);
        updateFloatingControls();
      }
    } catch (error) {
      appendLog(`Error consultando solver: ${error.message}`);
      markSolveStopped();
      setSceneLoading(false);
      updateFloatingControls();
    }
  }, 180);
}

function startAnimation() {
  if (!state.result || !state.result.found || !state.result.path.length) {
    appendLog("No hay solucion para animar.");
    updateFloatingControls();
    return;
  }

  if (state.result.path.length >= 2) {
    const first = state.result.path[0];
    const second = state.result.path[1];
    setTaxiHeading(second.row - first.row, second.col - first.col);
  }

  state.animation.playing = true;
  state.animation.pathIndex = 0;
  state.animation.progress = 0;
  appendLog("Animacion iniciada.");
}

function resetAnimation() {
  if (!hasAnimatableSolution()) {
    return;
  }

  state.animation.playing = false;
  state.animation.pathIndex = 0;
  state.animation.progress = 0;

  const path = state.result.path;
  const start = path[0];
  taxiMesh.position.set(start.col * tileSize, taxiWorldY(), start.row * tileSize);
  hidePickedPassengers(start.pickedUp);

  if (path.length >= 2) {
    const next = path[1];
    setTaxiHeading(next.row - start.row, next.col - start.col);
  }

  appendLog("Animacion reiniciada al inicio.");
}

function updateAnimation(delta) {
  if (!state.animation.playing || !state.result || state.result.path.length < 2) {
    return;
  }

  state.animation.progress += delta * state.animation.speed;

  while (state.animation.progress >= 1 && state.animation.playing) {
    state.animation.progress -= 1;
    state.animation.pathIndex += 1;
    if (state.animation.pathIndex >= state.result.path.length - 1) {
      state.animation.pathIndex = state.result.path.length - 1;
      state.animation.progress = 1;
      break;
    }
  }

  applyAnimationPose();
}

function resizeRenderer() {
  const width = dom.sceneCanvas.clientWidth;
  const height = dom.sceneCanvas.clientHeight;
  if (width <= 0 || height <= 0) {
    return;
  }
  renderer.setSize(width, height);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
}

let lastTs = performance.now();
function tick(ts) {
  const delta = (ts - lastTs) / 1000;
  lastTs = ts;

  resizeRenderer();
  updateAnimation(delta);
  if (controls && !useManualOrbit) {
    controls.update();
  } else {
    applyManualOrbitCamera();
  }
  renderer.render(scene, camera);
  requestAnimationFrame(tick);
}

function wireUiEvents() {
  dom.mapSelect.addEventListener("change", () => {
    if (state.solve.running) {
      appendLog("No puedes cambiar de mapa mientras hay un calculo en curso.");
      dom.mapSelect.value = state.world ? state.world.mapName : dom.mapSelect.value;
      return;
    }
    resetSolvedContext();
    void loadSelectedMap();
  });
  dom.algorithmSelect.addEventListener("change", () => {
    if (state.solve.running) {
      appendLog("No puedes cambiar de algoritmo mientras hay un calculo en curso.");
      if (state.lastAlgorithmSelection) {
        dom.algorithmSelect.value = state.lastAlgorithmSelection;
      }
      return;
    }
    state.lastAlgorithmSelection = dom.algorithmSelect.value;
    state.result = null;
    resetSolvedContext();
    updateFloatingControls();
    setMetrics("Mapa listo. Ejecuta 'Calcular Solucion'.");
  });
  dom.solveBtn.addEventListener("click", solveCurrentMap);
  dom.playFloatingBtn.addEventListener("click", startAnimation);
  dom.resetFloatingBtn.addEventListener("click", resetAnimation);

  dom.clearLogBtn.addEventListener("click", clearLog);

  dom.speedRange.addEventListener("input", () => {
    state.animation.speed = Number(dom.speedRange.value);
    dom.speedValue.textContent = `${state.animation.speed.toFixed(1)}x`;
  });

  window.addEventListener("keydown", (event) => {
    if (event.key.toLowerCase() !== "m") {
      return;
    }
    if (!controls) {
      useManualOrbit = true;
      appendLog("Modo manual activo (OrbitControls no disponible). ");
      return;
    }

    useManualOrbit = !useManualOrbit;
    if (useManualOrbit) {
      syncManualOrbitFromCamera(controls.target.clone());
      appendLog("Camara: modo manual activo. ");
    } else {
      controls.target.copy(manualOrbit.target);
      controls.update();
      appendLog("Camara: OrbitControls activo. ");
    }
  });

  window.addEventListener("resize", resizeRenderer);
}

function fillSelect(selectEl, values) {
  selectEl.innerHTML = "";
  values.forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    selectEl.appendChild(option);
  });
}

function syncSelectOptions(selectEl, values, preferredValue) {
  const currentValues = Array.from(selectEl.options).map((opt) => opt.value);
  const changedValues = !arraysEqual(currentValues, values);

  if (changedValues) {
    fillSelect(selectEl, values);
  }

  if (!values.length) {
    return { changedValues, changedSelection: false };
  }

  const currentSelection = selectEl.value;
  let nextSelection = currentSelection;

  if (!values.includes(nextSelection)) {
    if (preferredValue && values.includes(preferredValue)) {
      nextSelection = preferredValue;
    } else {
      nextSelection = values[0];
    }
  }

  const changedSelection = nextSelection !== currentSelection;
  selectEl.value = nextSelection;
  return { changedValues, changedSelection };
}

async function refreshAppState(options = {}) {
  const { autoReloadCurrent = false } = options;

  if (state.solve.running) {
    return;
  }

  if (state.mapSyncInFlight) {
    return;
  }

  state.mapSyncInFlight = true;
  try {
    const appState = await bridgeCall("get_app_state");
    const oldSelectedMap = dom.mapSelect.value;
    const worldMapName = state.world ? state.world.mapName : null;

    state.maps = appState.maps;
    state.algorithms = appState.algorithms;

    const mapSync = syncSelectOptions(dom.mapSelect, state.maps, worldMapName || oldSelectedMap);
    syncSelectOptions(dom.algorithmSelect, state.algorithms, dom.algorithmSelect.value);

    if (!state.maps.length) {
      state.currentMapSignature = null;
      return;
    }

    const selectedMap = dom.mapSelect.value;
    const selectedSignature = (appState.mapMeta && appState.mapMeta[selectedMap]) || null;
    const currentMapVisible = Boolean(state.world && state.world.mapName === selectedMap);
    const mapFileChanged = Boolean(
      currentMapVisible &&
        state.currentMapSignature &&
        selectedSignature &&
        selectedSignature !== state.currentMapSignature
    );

    if (autoReloadCurrent && mapFileChanged) {
      if (state.animation.playing) {
        state.animation.playing = false;
      }
      appendLog(`Cambio detectado en ${selectedMap}. Recargando mapa...`);
      await loadSelectedMap({ skipMetrics: true });
      return;
    }

    if (autoReloadCurrent && mapSync.changedSelection && !state.animation.playing) {
      appendLog(`Lista de mapas actualizada. Cargando ${selectedMap}...`);
      await loadSelectedMap({ skipMetrics: true });
      return;
    }

    if (currentMapVisible) {
      state.currentMapSignature = selectedSignature;
    }
  } catch (error) {
    appendLog(`Error refrescando mapas: ${error.message}`);
  } finally {
    state.mapSyncInFlight = false;
  }
}

async function init() {
  wireUiEvents();
  setupManualOrbitEvents();
  resizeRenderer();
  requestAnimationFrame(tick);

  try {
    updateSolveButton();
    updateFloatingControls();
    await refreshAppState({ autoReloadCurrent: false });

    state.lastAlgorithmSelection = dom.algorithmSelect.value || null;

    if (state.maps.length > 0) {
      await loadSelectedMap();
    }

    state.mapRefreshTimer = window.setInterval(() => {
      void refreshAppState({ autoReloadCurrent: true });
    }, 1000);

    appendLog("Interfaz 3D inicializada.");
  } catch (error) {
    appendLog(`Error inicializando app: ${error.message}`);
    setMetrics("Error inicializando backend Eel.");
  }
}

init();
