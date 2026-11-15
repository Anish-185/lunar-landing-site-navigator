// The cosmos behind chapters 1-2: a Big Bang of particles that cools into a starfield, then the Moon and Earth
// (NASA SVS CGI Moon Kit and Blue Marble textures). three.js does the work; this file only choreographs it.
import {
  AdditiveBlending, AmbientLight, BufferAttribute, BufferGeometry, Color, DirectionalLight, Group, MathUtils, Mesh,
  MeshStandardMaterial, PerspectiveCamera, Points, PointsMaterial, Scene, SphereGeometry, SRGBColorSpace,
  TextureLoader, WebGLRenderer, CanvasTexture,
} from "three";

const STAR_COLOURS = ["#ffffff", "#cfe6ff", "#ffe7b0", "#f6b94a", "#b9c7ff", "#ffd2a8"];

function dotTexture() {
  const c = document.createElement("canvas");
  c.width = c.height = 64;
  const g = c.getContext("2d");
  const r = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  r.addColorStop(0, "rgba(255,255,255,1)");
  r.addColorStop(0.25, "rgba(255,255,255,.8)");
  r.addColorStop(1, "rgba(255,255,255,0)");
  g.fillStyle = r;
  g.fillRect(0, 0, 64, 64);
  return new CanvasTexture(c);
}

export function createCosmos(canvas, { reduced = false, base = "./" } = {}) {
  const small = window.innerWidth < 760;
  const renderer = new WebGLRenderer({ canvas, antialias: !small, powerPreference: "high-performance" });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, small ? 1.5 : 1.75));
  renderer.setSize(window.innerWidth, window.innerHeight, false);
  renderer.outputColorSpace = SRGBColorSpace;
  renderer.setClearColor(0x04050f, 1);

  const scene = new Scene();
  const camera = new PerspectiveCamera(50, window.innerWidth / window.innerHeight, 0.1, 2000);
  camera.position.set(0, 0, 30);

  // --- Big Bang particles -> stars ---
  const N = small ? 5000 : 12000;
  const dir = new Float32Array(N * 3);
  const speed = new Float32Array(N);
  const pos = new Float32Array(N * 3);
  const col = new Float32Array(N * 3);
  const starCol = new Float32Array(N * 3);
  const tmp = new Color();
  for (let i = 0; i < N; i++) {
    const u = Math.random() * 2 - 1, th = Math.random() * Math.PI * 2, s = Math.sqrt(1 - u * u);
    dir.set([s * Math.cos(th), s * Math.sin(th), u], i * 3);
    speed[i] = 40 + Math.pow(Math.random(), 0.6) * 520;
    tmp.set(STAR_COLOURS[(Math.random() * STAR_COLOURS.length) | 0]);
    starCol.set([tmp.r, tmp.g, tmp.b], i * 3);
  }
  const geo = new BufferGeometry();
  geo.setAttribute("position", new BufferAttribute(pos, 3));
  geo.setAttribute("color", new BufferAttribute(col, 3));
  const mat = new PointsMaterial({ size: 1.4, map: dotTexture(), vertexColors: true, transparent: true,
    depthWrite: false, blending: AdditiveBlending, sizeAttenuation: true });
  const stars = new Points(geo, mat);
  scene.add(stars);

  // --- Moon and Earth ---
  const sys = new Group();
  scene.add(sys);
  const loader = new TextureLoader();
  const tex = (f) => { const t = loader.load(base + "media/" + f); t.colorSpace = SRGBColorSpace; t.anisotropy = 4; return t; };
  const moonMat = new MeshStandardMaterial({ map: tex("moon_color.jpg"), bumpMap: loader.load(base + "media/moon_bump.jpg"),
    bumpScale: 2.2, roughness: 1, metalness: 0, transparent: true, opacity: 0 });
  const moon = new Mesh(new SphereGeometry(4, small ? 64 : 128, small ? 48 : 96), moonMat);
  const earthMat = new MeshStandardMaterial({ map: tex("earth.jpg"), roughness: 0.75, metalness: 0, transparent: true, opacity: 0 });
  const earth = new Mesh(new SphereGeometry(4 * 3.67, 96, 64), earthMat);
  earth.position.set(-70, 16, -150);
  sys.add(moon, earth);
  const sun = new DirectionalLight(0xfff1d8, 3.2);
  sun.position.set(60, 8, 20);
  scene.add(sun, new AmbientLight(0x2a2f5c, 0.35));

  let bang = reduced ? 1 : 0;   // 0 -> 1 over the opening burst
  let p = 0;                    // scroll progress through chapters 1-2 (0..2)
  let visible = true;
  const start = performance.now();
  const BANG_MS = 2600;

  let particlesDone = false;
  function frame(now) {
    if (!reduced && bang < 1) bang = Math.min(1, (now - start) / BANG_MS);
    const e = 1 - Math.pow(1 - bang, 4);          // ease-out: hot and fast, then coasting
    const cool = MathUtils.smoothstep(bang, 0.15, 1);
    const drift = p * 0.6;                         // after the burst, everything moves with the reader's scroll
    if (!particlesDone) for (let i = 0; i < N; i++) {
      const r = speed[i] * e;
      pos[i * 3] = dir[i * 3] * r;
      pos[i * 3 + 1] = dir[i * 3 + 1] * r;
      pos[i * 3 + 2] = dir[i * 3 + 2] * r - 120 * cool;
      const hot = 1 - cool;                        // white-hot -> each star's own colour
      col[i * 3] = starCol[i * 3] * cool + hot;
      col[i * 3 + 1] = starCol[i * 3 + 1] * cool + hot * 0.92;
      col[i * 3 + 2] = starCol[i * 3 + 2] * cool + hot * 0.85;
    }
    if (!particlesDone) {
      geo.attributes.position.needsUpdate = true;
      geo.attributes.color.needsUpdate = true;
      particlesDone = bang >= 1;
    }
    mat.size = MathUtils.lerp(6, 1.25, cool);
    stars.rotation.y = drift + p * 0.25;
    stars.rotation.x = p * 0.08;

    // Moon and Earth arrive in the second half of chapter 1; in chapter 2 the camera swings to the south pole.
    const show = MathUtils.smoothstep(p, 0.45, 0.75);
    moonMat.opacity = show;
    earthMat.opacity = show * 0.95;
    const toPole = MathUtils.smoothstep(p, 1.0, 1.45);
    moon.rotation.y = 2.4 + p * 0.9 * (1 - toPole);
    moon.rotation.x = MathUtils.lerp(0.12, -Math.PI / 2 + 0.05, toPole);   // south pole turns toward us
    moon.position.x = MathUtils.lerp(small ? 0 : 7, 0, toPole);
    moon.position.y = MathUtils.lerp(small ? 3 : 0, 0, toPole);
    camera.position.z = MathUtils.lerp(30, 9.5, toPole);
    earth.rotation.y = p * 1.2;
    earthMat.opacity = show * 0.95 * (1 - toPole);
    canvas.style.opacity = String(1 - MathUtils.smoothstep(p, 1.4, 1.62));
    renderer.render(scene, camera);
  }

  // Render on demand: every frame during the opening burst, then only when the scroll position changes
  // (or textures arrive). An idle page costs nothing.
  let dirty = true, queued = false;
  const request = () => { dirty = true; if (!queued) { queued = true; requestAnimationFrame(tick); } };
  function tick(now) {
    queued = false;
    if (!visible) return;
    const animating = !reduced && bang < 1;
    if (dirty || animating) { dirty = false; frame(now); }
    if (animating) request();
  }
  request();
  loader.manager.onLoad = request;

  addEventListener("resize", () => {
    camera.aspect = innerWidth / innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(innerWidth, innerHeight, false);
    request();
  });

  return {
    setProgress(v) {
      if (v === p) return;
      p = v;
      visible = v < 1.64;
      if (!visible) canvas.style.opacity = "0";
      request();
    },
  };
}
