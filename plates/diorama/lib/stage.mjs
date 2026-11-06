// A set (sets/*.json) as a scene: parts as cards, merged into one mesh, one light.
// The set never moves, so its shadow is a bake: rendered once at setup and only read after that, with one hardware
// shadow fetch a pixel. The shader is ours and small (a tone, not a colour): three's Lambert, spot and PCF chunks cost
// 800 ms a frame here, on software GL, and this page has 370.
import * as THREE from "three";
import { mergePaper, seedPaper } from "./paper.mjs";
import { PARTS } from "./parts.mjs";

const VERTEX = /* glsl */ `
in vec2 ink;
uniform mat4 lightMatrix;
uniform vec3 keyAt;
uniform vec3 fillFrom;
uniform float fill, keyPower, fogNear, fogFar;
out float vTone, vGlow, vKey, vAmbient, vFog;
out vec4 vLight;
out vec2 vPaper;
void main() {
  vTone = ink.x;
  vGlow = ink.y;
  vec3 toKey = normalize(keyAt - position);
  vKey = max(dot(normal, toKey), 0.0) * keyPower;
  vAmbient = fill * (0.6 + 0.4 * dot(normal, fillFrom));
  vLight = lightMatrix * vec4(position + normal * 0.012, 1.0);
  vPaper = vec2(position.x + position.z * 0.61, position.y + position.z * 0.83) * 1.7;
  vec4 view = modelViewMatrix * vec4(position, 1.0);
  vFog = 1.0 - clamp((-view.z - fogNear) / (fogFar - fogNear), 0.0, 1.0);
  gl_Position = projectionMatrix * view;
}`;

const FRAGMENT = /* glsl */ `
precision highp float;
precision highp sampler2DShadow;
uniform sampler2DShadow shade;
uniform sampler2D grain;
uniform float poolEdge, soft;
in float vTone, vGlow, vKey, vAmbient, vFog;
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
  float fibre = texture(grain, vPaper).r, mottle = texture(grain, vPaper * 0.11).r;
  float tone = vTone * (0.62 + 0.42 * fibre + 0.34 * mottle) * (direct + vAmbient + vGlow);
  frag = vec4(vec3(sqrt(tone * vFog)), 1.0); // a quick gamma: a plate is tone, and fog falls to the canvas
}`;

function grainTexture(random) { // paper fibre: tone noise with a few long strokes, tiled over the world
  const size = 256, data = new Uint8Array(size * size);
  const value = new Float32Array(size * size);
  for (let i = 0; i < value.length; i++) value[i] = random() - 0.5;
  for (let n = 0; n < 1400; n++) { // fibres
    let x = random() * size, y = random() * size;
    const a = random() * Math.PI, strength = (random() - 0.5) * 0.7;
    for (let s = 0; s < 14; s++) {
      value[((y | 0) & 255) * size + ((x | 0) & 255)] += strength;
      x += Math.cos(a);
      y += Math.sin(a);
    }
  }
  for (let i = 0; i < value.length; i++) data[i] = Math.min(255, Math.max(0, 128 + value[i] * 90));
  const texture = new THREE.DataTexture(data, size, size, THREE.RedFormat);
  texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
  texture.magFilter = THREE.LinearFilter;
  texture.minFilter = THREE.LinearMipmapLinearFilter;
  texture.generateMipmaps = true;
  texture.needsUpdate = true;
  return texture;
}

function bakeShadow(renderer, mesh, s) { // the one render of the light's view; the material reads its depth from now on
  const { key = [-3.5, 15, 6], aim = [0, 1, -1], angle = 26, map = 2048 } = s;
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
      fogNear: { value: fogNear }, fogFar: { value: fogFar }, poolEdge: { value: s.pool ?? 0.55 }, soft: { value: (s.soft ?? 1.6) / (s.map ?? 2048) },
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
