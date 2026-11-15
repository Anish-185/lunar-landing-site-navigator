// "Be the Sun": the LOLA polar cap (80-90 S, site/public/media/pole_height.png, written by pipeline/media.py) relit in
// a fragment shader with ray-marched cast shadows. The Sun sits 1.5° above the pole's horizon; each pixel's own Sun
// elevation adds its tilt from the pole (colatitude toward the Sun), so the geometry is right across the cap. three.js
// draws one full-screen quad; this file is the shader and its inputs.
import { Mesh, OrthographicCamera, PlaneGeometry, Scene, ShaderMaterial, TextureLoader, NearestFilter, NoColorSpace, WebGLRenderer } from "three";

const frag = /* glsl */ `
precision highp float;
uniform sampler2D hmap;
uniform vec2 sunDir;      // unit vector toward the Sun in texture space (x right, y up)
uniform float sunEl;      // Sun elevation above the pole's horizon (radians)
uniform float range;      // height range of the texture (m)
uniform float px;         // metres per texel
uniform float texel;      // 1 / texture width
uniform float capRad;     // half the texture width in colatitude radians
varying vec2 vUv;
uniform float W;          // texture width in texels
// Heights are split over two bytes, so hardware filtering would blend the bytes, not the heights: fetch texels with
// nearest filtering and interpolate decoded heights (hN for the shadow march, h for the surface).
float hN(vec2 uv) { vec4 c = texture2D(hmap, uv); return (c.r * 255.0 * 256.0 + c.g * 255.0) / 65535.0 * range; }
float h(vec2 uv) {
  vec2 p = uv * W - 0.5; vec2 f = fract(p); vec2 b = (floor(p) + 0.5) / W;
  return mix(mix(hN(b), hN(b + vec2(texel, 0.0)), f.x), mix(hN(b + vec2(0.0, texel)), hN(b + vec2(texel)), f.x), f.y);
}
void main() {
  vec4 c0 = texture2D(hmap, vUv);
  if (c0.b < 0.5) { gl_FragColor = vec4(0.0); return; }
  float z = h(vUv);
  // Surface normal from central differences (metres).
  float dx = (h(vUv + vec2(texel, 0.0)) - h(vUv - vec2(texel, 0.0))) / (2.0 * px);
  float dy = (h(vUv + vec2(0.0, texel)) - h(vUv - vec2(0.0, texel))) / (2.0 * px);
  vec3 n = normalize(vec3(-dx, -dy, 1.0));
  // The local Sun is higher on the side of the pole facing it (curvature of the sphere).
  vec2 fromPole = (vUv - 0.5) * 2.0;
  float el = sunEl + capRad * dot(fromPole, sunDir);
  vec3 L = normalize(vec3(sunDir * cos(el), sin(el)));
  float lambert = max(dot(n, L), 0.0);
  // March toward the Sun: any terrain above the ray means shadow. Steps grow with distance (out to ~300 km).
  float lit = 1.0;
  float t = 1.5;
  float tanEl = tan(el);
  for (int i = 0; i < 72; i++) {
    vec2 uv = vUv + sunDir * t * texel;
    if (uv.x < 0.0 || uv.y < 0.0 || uv.x > 1.0 || uv.y > 1.0) break;
    float ray = z + tanEl * t * px;
    float d = hN(uv) - ray;
    lit = min(lit, clamp(1.0 - d / 40.0, 0.0, 1.0));   // 40 m soft edge: the Sun is half a degree wide
    if (lit <= 0.0) break;
    t *= 1.075;
    t += 0.6;
  }
  float light = lambert * lit;
  // Regolith lit by a low gold Sun; shadow lifted by a whisper of earthshine so relief is never pure black.
  vec3 sunCol = vec3(1.0, 0.86, 0.66);
  vec3 col = sunCol * pow(light, 0.75) * 1.25 + vec3(0.035, 0.04, 0.06) * (0.4 + 0.6 * n.z);
  float vign = smoothstep(1.02, 0.55, length(fromPole));
  gl_FragColor = vec4(col * vign, 1.0);
}`;

export function createRelight(canvas, meta, base) {
  const renderer = new WebGLRenderer({ canvas, antialias: false, alpha: true, powerPreference: "high-performance" });
  const dpr = Math.min(devicePixelRatio, 1.5);
  const scene = new Scene();
  const camera = new OrthographicCamera(-1, 1, 1, -1, 0, 1);
  const uniforms = {
    hmap: { value: null }, sunDir: { value: [Math.cos(2.36), Math.sin(2.36)] }, sunEl: { value: (1.5 * Math.PI) / 180 },
    range: { value: meta.max_m - meta.min_m }, W: { value: meta.width }, px: { value: meta.px_m }, texel: { value: 1 / meta.width },
    capRad: { value: ((meta.width / 2) * meta.px_m) / 1737400 },
  };
  const mat = new ShaderMaterial({ uniforms, fragmentShader: frag,
    vertexShader: "varying vec2 vUv; void main(){ vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }" });
  scene.add(new Mesh(new PlaneGeometry(2, 2), mat));
  let queued = false, ready = false;
  const render = () => { queued = false; if (ready) renderer.render(scene, camera); };
  const request = () => { if (!queued) { queued = true; requestAnimationFrame(render); } };
  const size = () => {
    const w = Math.max(1, Math.round(canvas.clientWidth * dpr));   // layout size; the zoom is a CSS transform
    renderer.setPixelRatio(1);
    renderer.setSize(Math.min(w, 1600), Math.min(w, 1600), false);
    request();
  };
  return new Promise((resolve, reject) => {
    new TextureLoader().load(base + "media/pole_height.png", (tex) => {
      tex.colorSpace = NoColorSpace;              // packed data, not colour
      tex.minFilter = tex.magFilter = NearestFilter;
      tex.generateMipmaps = false;
      tex.flipY = true;
      uniforms.hmap.value = tex;
      ready = true;
      size();
      addEventListener("resize", size);
      resolve({
        /** azimuth in degrees, compass-style on the map: 0 = up (toward 0° longitude), clockwise */
        setSun(azDeg) {
          const a = (azDeg * Math.PI) / 180;
          uniforms.sunDir.value = [Math.sin(a), Math.cos(a)];
          request();
        },
      });
    }, undefined, reject);
  });
}
