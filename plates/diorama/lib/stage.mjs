// A set (sets/*.json) as a scene: parts as cards, merged into one mesh, one light.
// The set never moves, so its shadow is a bake: rendered once at setup and only read after that, with one hardware
// shadow fetch a pixel. The shader is ours and small (a tone, not a colour): three's Lambert, spot and PCF chunks cost
// 800 ms a frame here, on software GL, and this page has 370.
import * as THREE from "three";
import { mergePaper, seedPaper } from "./paper.mjs";
import { PARTS } from "./parts.mjs";

const VERTEX = /* glsl */ `
in vec3 ink;
uniform mat4 lightMatrix;
uniform vec3 keyAt;
uniform vec3 fillFrom;
uniform float fill, keyPower, fogNear, fogFar;
out float vTone, vGlow, vKey, vAmbient, vFog, vRough;
out vec4 vLight;
out vec2 vPaper;
void main() {
  vTone = ink.x;
  vGlow = ink.y;
  vec3 toKey = normalize(keyAt - position);
  vKey = max(dot(normal, toKey), 0.0) * keyPower;
  vAmbient = fill * (0.6 + 0.4 * dot(normal, fillFrom));
  vLight = lightMatrix * vec4(position + normal * 0.012, 1.0);
  vRough = 0.3 + 0.85 * fract(ink.z * 7.0);
  vPaper = vec2(position.x + position.z * 0.61, position.y + position.z * 0.83) * (0.3 + 0.24 * ink.z) + ink.z * vec2(13.0, 7.0);
  vec4 view = modelViewMatrix * vec4(position, 1.0);
  vFog = 1.0 - clamp((-view.z - fogNear) / (fogFar - fogNear), 0.0, 1.0);
  gl_Position = projectionMatrix * view;
}`;

const FRAGMENT = /* glsl */ `
precision highp float;
precision highp sampler2DShadow;
uniform sampler2DShadow shade;
uniform sampler2D grain;
uniform float poolEdge, soft, fogTone;
in float vTone, vGlow, vKey, vAmbient, vFog, vRough;
in vec4 vLight;
in vec2 vPaper;
out vec4 frag;
void main() {
  vec3 lit = vLight.xyz / vLight.w;
  float pool = 1.0 - smoothstep(poolEdge, 1.0, length(lit.xy * 2.0 - 1.0));
  float direct = vKey * pool;
  if (direct > 0.002) { // four fetches, each already a bilinear compare: a soft edge at the cost of one per corner
    float z = lit.z - 0.00006;
    direct *= 0.25 * (texture(shade, vec3(lit.xy + vec2(soft, soft * 0.4), z)) + texture(shade, vec3(lit.xy + vec2(-soft * 0.4, soft), z))
      + texture(shade, vec3(lit.xy + vec2(-soft, -soft * 0.4), z)) + texture(shade, vec3(lit.xy + vec2(soft * 0.4, -soft), z)));
  }
  float tooth = texture(grain, vPaper).r; // the sheet's tooth shows in the light that rakes it, far less in the shade
  float tone = vTone * (direct * (1.0 + (tooth - 0.5) * vRough) + vAmbient * (0.8 + 0.4 * tooth) + vGlow);
  frag = vec4(vec3(sqrt(mix(fogTone, tone, vFog))), 1.0); // a quick gamma: a plate is tone
}`;

function grainTexture(random) { // the tooth of a rough board: soft blobs at three sizes, embossed, with long fibres, tiled over the world
  const size = 512, field = new Float32Array(size * size), at = (x, y) => ((y + size) % size) * size + ((x + size) % size);
  for (const [cell, weight] of [[3, 0.5], [9, 0.8], [40, 0.7]]) { // value noise, wrapped
    const grid = Math.floor(size / cell), knots = new Float32Array(grid * grid).map(() => random() - 0.5);
    for (let y = 0; y < size; y++) {
      for (let x = 0; x < size; x++) {
        const gx = x / size * grid, gy = y / size * grid, ix = Math.floor(gx), iy = Math.floor(gy);
        const fx = gx - ix, fy = gy - iy, sx = fx * fx * (3 - 2 * fx), sy = fy * fy * (3 - 2 * fy);
        const k = (a, b) => knots[((iy + b) % grid) * grid + ((ix + a) % grid)];
        field[y * size + x] += weight * (k(0, 0) * (1 - sx) * (1 - sy) + k(1, 0) * sx * (1 - sy) + k(0, 1) * (1 - sx) * sy + k(1, 1) * sx * sy);
      }
    }
  }
  for (let n = 0; n < 900; n++) { // fibres
    let x = random() * size, y = random() * size, a = random() * 6.3;
    const strength = (random() - 0.5) * 0.9, long = 18 + random() * 40;
    for (let s = 0; s < long; s++) {
      field[at(x | 0, y | 0)] += strength;
      a += (random() - 0.5) * 0.3;
      x += Math.cos(a);
      y += Math.sin(a);
    }
  }
  const data = new Uint8Array(size * size);
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) { // embossed from one side, as a raking light sees it, over a slow mottle
      const relief = field[at(x, y)] - field[at(x + 2, y + 2)];
      data[y * size + x] = Math.min(255, Math.max(0, 128 + relief * 70 + field[at(x, y)] * 26));
    }
  }
  const texture = new THREE.DataTexture(data, size, size, THREE.RedFormat);
  texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
  texture.magFilter = THREE.LinearFilter;
  texture.minFilter = THREE.LinearMipmapLinearFilter;
  texture.generateMipmaps = true;
  texture.needsUpdate = true;
  return texture;
}

function bakeShadow(renderer, mesh, s) { // the one render of the light's view; the material reads its depth from now on
  const { key = [-3.5, 15, 6], aim = [0, 1, -1], angle = 26, map = 4096 } = s;
  const eye = new THREE.PerspectiveCamera(angle * 2, 1, s.shadowNear ?? 2, s.shadowFar ?? 40);
  eye.position.set(...key);
  eye.lookAt(...aim);
  eye.updateMatrixWorld();
  const target = new THREE.WebGLRenderTarget(map, map, { depthBuffer: true, generateMipmaps: false });
  target.depthTexture = new THREE.DepthTexture(map, map, THREE.UnsignedIntType);
  target.depthTexture.compareFunction = THREE.LessEqualCompare;
  target.depthTexture.magFilter = target.depthTexture.minFilter = THREE.LinearFilter;
  const scene = new THREE.Scene();
  scene.add(new THREE.Mesh(mesh.geometry, new THREE.MeshBasicMaterial({ colorWrite: false })));
  renderer.setRenderTarget(target);
  renderer.render(scene, eye);
  renderer.setRenderTarget(null);
  const toTexture = new THREE.Matrix4().set(0.5, 0, 0, 0.5, 0, 0.5, 0, 0.5, 0, 0, 0.5, 0.5, 0, 0, 0, 1);
  return { texture: target.depthTexture, matrix: toTexture.multiply(eye.projectionMatrix).multiply(eye.matrixWorldInverse) };
}

export function buildStage(spec, { renderer, random, drawings }) {
  seedPaper(random);
  const s = spec.stage || {};
  const root = new THREE.Group();
  for (const item of spec.parts || []) {
    const make = PARTS[item.part];
    if (!make) throw new Error(`no part "${item.part}"`);
    root.add(make(item, { drawings, random }));
  }
  const geometry = mergePaper(root);
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x000000);

  const mesh = new THREE.Mesh(geometry);
  const shadow = bakeShadow(renderer, mesh, s);
  const [fogNear, fogFar] = s.fog || [9, 26];
  const key = new THREE.Vector3(...(s.key || [-3.5, 15, 6]));
  mesh.material = new THREE.ShaderMaterial({
    glslVersion: THREE.GLSL3,
    vertexShader: VERTEX,
    fragmentShader: FRAGMENT,
    uniforms: {
      lightMatrix: { value: shadow.matrix }, keyAt: { value: key }, keyPower: { value: s.power ?? 1.1 },
      fillFrom: { value: new THREE.Vector3(...(s.fillFrom || [0.3, 0.8, 0.5])).normalize() }, fill: { value: s.fill ?? 0.16 },
      fogNear: { value: fogNear }, fogFar: { value: fogFar }, poolEdge: { value: s.pool ?? 0.55 }, fogTone: { value: (s.fogTone ?? 0) ** 2 }, soft: { value: (s.soft ?? 1.2) / (s.map ?? 4096) },
      shade: { value: shadow.texture }, grain: { value: grainTexture(random) },
    },
    depthFunc: THREE.LessEqualDepth,
  });
  // A depth pass first: flats stand behind flats here, and this shades each pixel once.
  const early = new THREE.Mesh(geometry, new THREE.MeshBasicMaterial({ colorWrite: false }));
  early.renderOrder = -1;
  mesh.frustumCulled = early.frustumCulled = false;
  scene.add(early, mesh);
  return scene;
}
