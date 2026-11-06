/**
 * plates/diorama/lib/anchors.mjs
 *
 * 3D-to-2D Screen Coordinate Projection & Anchor Exporter System
 * for the Veasy Paper Stage Diorama Engine.
 *
 * PURPOSE:
 * Veasy films display DOM text, kickers, headlines, stat numbers, and the brand accent dot
 * over the baked plate video. The DOM elements follow moving points in the 3D world
 * (e.g. the top of a pedestal, an archway apex, a paper standee figure, or the primary focal center).
 *
 * CONTRACT & GUARANTEES:
 * 1. Projection Math:
 *    - World space point -> camera.updateMatrixWorld() -> Vector3.project(camera).
 *    - NDC [-1, 1] mapped to viewport pixels:
 *        x = ((ndc.x + 1) / 2) * viewportWidth
 *        y = ((1 - ndc.y) / 2) * viewportHeight
 * 2. Frustum & Occlusion Check:
 *    - In front of camera: ndc.z < 1.0 (Three.js perspective projection).
 *    - Viewport bounds check: normalized u in [-0.1, 1.1] and v in [-0.1, 1.1].
 *    - Anchor is visible iff inFront && inBounds.
 * 3. Scale Invariance:
 *    - Coordinates can be exported in current viewport pixels or normalized to the canonical
 *      Veasy 1080x1920 reference frame. When baked via plates/run.mjs with --scale s,
 *      page coordinates are divided by s to yield byte-identical 1080x1920 tracks.
 * 4. Export Contract:
 *    - Per frame: window.anchors(t) -> { [name]: [x, y] }
 *    - Full track manifest: anchors.json -> { fps, width, height, tracks: { [name]: [[x0, y0], ...] } }
 * 5. Determinism:
 *    - Pure function of time t, camera state, and scene hierarchy. No Math.random, no clock.
 */

import * as THREE from "three";

// ============================================================================
// 1. CONSTANTS & SPECIFICATION DEFAULTS
// ============================================================================

export const REFERENCE_WIDTH = 1080;
export const REFERENCE_HEIGHT = 1920;
export const DEFAULT_FPS = 30;

/** Frustum NDC bounds: [-1, 1] with 10% bleed margin corresponds to normalized [ -0.1, 1.1 ] */
export const BOUNDS_MIN = -0.1;
export const BOUNDS_MAX = 1.1;

/** In Three.js perspective camera, points behind camera plane have ndc.z > 1.0 */
export const NDC_Z_MAX = 1.0;

/**
 * Veasy safe zone constraints for portrait films (1080x1920).
 * Maximum text bottom Y is 1380.
 * Right-edge social interface cut begins at Y=1100 with X limit 940.
 */
export const SAFE_ZONE = Object.freeze({
  maxTextY: 1380,
  socialRightCutY: 1100,
  socialRightLimitX: 940,
});

/**
 * Standard semantic anchor names used in Veasy film compositions.
 */
export const ANCHOR_ROLES = Object.freeze({
  DOT: "dot",                  // Brand accent dot following hero artifact/standee
  KICKER: "kicker",            // Section or category kicker text above feature
  HEADLINE: "headline",        // Main scene headline text
  STAT: "stat",                // Numeric statistic callout badge
  LABEL: "label",              // Secondary descriptive label
  PEDESTAL: "pedestal",        // Exhibition plinth or pedestal surface
  ARCH_APEX: "arch_apex",      // Architectural archway center apex
});

// Scratch objects to avoid GC pressure in hot render loops (30-60 fps)
const _scratchVec3 = new THREE.Vector3();
const _scratchCamPos = new THREE.Vector3();
const _scratchBox = new THREE.Box3();

// ============================================================================
// 2. MATHEMATICAL PROJECTION HELPERS
// ============================================================================

/**
 * Converts any vector-like coordinate to a THREE.Vector3.
 * Supports THREE.Vector3, [x, y, z], or {x, y, z}.
 *
 * @param {THREE.Vector3|Array<number>|Object} v
 * @param {THREE.Vector3} [out] Optional target vector to write into
 * @returns {THREE.Vector3}
 */
export function toVector3(v, out = new THREE.Vector3()) {
  if (!v) {
    return out.set(0, 0, 0);
  }
  if (v.isVector3) {
    return out.copy(v);
  }
  if (Array.isArray(v)) {
    return out.set(v[0] || 0, v[1] || 0, v[2] || 0);
  }
  if (typeof v === "object") {
    return out.set(v.x || 0, v.y || 0, v.z || 0);
  }
  return out.set(0, 0, 0);
}

/**
 * Projects a 3D world space coordinate into 2D screen space.
 *
 * MATH DETAILS:
 * 1. World point is multiplied by camera.matrixWorldInverse and camera.projectionMatrix.
 * 2. Perspective divide produces Normalized Device Coordinates (NDC) in [-1, 1].
 * 3. NDC to Normalized Viewport (u, v):
 *      u = (ndc.x + 1) / 2      (0.0 = left edge, 1.0 = right edge)
 *      v = (1 - ndc.y) / 2      (0.0 = top edge, 1.0 = bottom edge)
 * 4. Viewport Pixels:
 *      pixelX = u * viewportWidth
 *      pixelY = v * viewportHeight
 * 5. Frustum & Visibility Check:
 *      inFront: ndc.z < NDC_Z_MAX (1.0)
 *      inBounds: u in [BOUNDS_MIN, BOUNDS_MAX] && v in [BOUNDS_MIN, BOUNDS_MAX]
 *      visible: inFront && inBounds
 *
 * @param {THREE.Vector3|Array<number>|Object} worldPoint 3D point in world space
 * @param {THREE.Camera} camera Three.js perspective or orthographic camera
 * @param {number} [viewportWidth=1080] Width of viewport in pixels
 * @param {number} [viewportHeight=1920] Height of viewport in pixels
 * @param {Object} [options={}] Additional projection options
 * @param {number} [options.boundsMin=-0.1] Minimum viewport bounds margin
 * @param {number} [options.boundsMax=1.1] Maximum viewport bounds margin
 * @param {number} [options.zMax=1.0] Maximum NDC Z depth before considered behind camera
 * @param {number} [options.decimals=1] Rounding precision for pixel coordinates
 * @returns {Object} Comprehensive projection result
 */
export function projectWorldToScreen(
  worldPoint,
  camera,
  viewportWidth = REFERENCE_WIDTH,
  viewportHeight = REFERENCE_HEIGHT,
  options = {}
) {
  const boundsMin = options.boundsMin !== undefined ? options.boundsMin : BOUNDS_MIN;
  const boundsMax = options.boundsMax !== undefined ? options.boundsMax : BOUNDS_MAX;
  const zMax = options.zMax !== undefined ? options.zMax : NDC_Z_MAX;
  const decimals = options.decimals !== undefined ? options.decimals : 1;

  // Make sure camera world matrices are up to date
  camera.updateMatrixWorld();

  // Scratch vector for projection
  const p = _scratchVec3;
  toVector3(worldPoint, p);

  // Transform point to camera view space to check distance along camera optical axis
  _scratchCamPos.copy(p).applyMatrix4(camera.matrixWorldInverse);
  const cameraSpaceZ = _scratchCamPos.z;

  // Project point to NDC [-1, 1]
  p.project(camera);

  const ndcX = p.x;
  const ndcY = p.y;
  const ndcZ = p.z;

  // Viewport normalized coordinates (0,0 is top-left)
  const u = (ndcX + 1) * 0.5;
  const v = (1 - ndcY) * 0.5;

  // Screen pixels in target viewport
  const rawX = u * viewportWidth;
  const rawY = v * viewportHeight;

  // Frustum & Occlusion rules:
  // 1. inFront: In Three.js perspective projection, points in front have cameraSpaceZ < 0
  //    and ndc.z < 1.0 (points behind the camera have negative w, causing ndc.z > 1.0).
  const inFront = ndcZ < zMax && (camera.isOrthographicCamera || cameraSpaceZ < 0);

  // 2. inBounds: Check if point falls within normalized viewport with bleed margin [-0.1, 1.1]
  const inBounds = u >= boundsMin && u <= boundsMax && v >= boundsMin && v <= boundsMax;

  // 3. Overall visibility
  const visible = inFront && inBounds;

  // 4. Safe zone check for portrait video overlays
  const inSafeZone =
    visible &&
    rawY <= SAFE_ZONE.maxTextY &&
    (rawY <= SAFE_ZONE.socialRightCutY || rawX <= SAFE_ZONE.socialRightLimitX);

  const factor = 10 ** decimals;
  const x = Math.round(rawX * factor) / factor;
  const y = Math.round(rawY * factor) / factor;

  return {
    x,
    y,
    u,
    v,
    ndc: { x: ndcX, y: ndcY, z: ndcZ },
    cameraSpaceZ,
    inFront,
    inBounds,
    visible,
    inSafeZone,
    pixel: [x, y],
  };
}

/**
 * Projects a world point directly to canonical reference pixels (1080x1920),
 * regardless of the render scale.
 *
 * @param {THREE.Vector3|Array<number>} worldPoint
 * @param {THREE.Camera} camera
 * @param {Object} [options]
 * @returns {Array<number>} [x, y] in standard 1080x1920 reference frame
 */
export function projectToReferenceScreen(worldPoint, camera, options = {}) {
  const result = projectWorldToScreen(worldPoint, camera, REFERENCE_WIDTH, REFERENCE_HEIGHT, options);
  return result.pixel;
}

// ============================================================================
// 3. ANCHOR TRACKER & SYSTEM
// ============================================================================

/**
 * Represents an individual 3D anchor entry.
 */
export class AnchorDefinition {
  /**
   * @param {string} name Unique identifier (e.g. 'dot', 'kicker', 'headline')
   * @param {THREE.Object3D|THREE.Vector3|Array<number>|Function} target
   * @param {Object} [options={}]
   */
  constructor(name, target, options = {}) {
    this.name = name;
    this.target = target;
    this.offset = toVector3(options.offset || [0, 0, 0]);
    this.role = options.role || name;
    this.description = options.description || "";
    this.required = options.required || false;
    this.keypoint = options.keypoint || null; // 'top' | 'center' | 'bottom' | null
    this.policy = options.policy || "clamp";   // 'clamp' | 'omit' | 'lastKnown' | 'always'
    this.lastValidPixel = null;
  }

  /**
   * Resolves the current 3D world position of this anchor at time t.
   *
   * @param {number} t Time in seconds
   * @param {THREE.Vector3} [out] Target vector
   * @returns {THREE.Vector3} 3D world coordinates
   */
  resolveWorldPosition(t = 0, out = new THREE.Vector3()) {
    let resolved = this.target;

    // 1. Dynamic trajectory function: (t) => Vector3 | Object3D | [x, y, z]
    if (typeof resolved === "function") {
      resolved = resolved(t);
    }

    // 2. Three.js Object3D (Mesh, Group, Bone, Standee)
    if (resolved && resolved.isObject3D) {
      resolved.updateMatrixWorld(true);

      // Handle bounding box keypoints (e.g. top of pedestal, arch apex)
      if (this.keypoint) {
        _scratchBox.setFromObject(resolved);
        if (!_scratchBox.isEmpty()) {
          switch (this.keypoint) {
            case "top":
            case "apex":
              out.set(
                (_scratchBox.min.x + _scratchBox.max.x) * 0.5,
                _scratchBox.max.y,
                (_scratchBox.min.z + _scratchBox.max.z) * 0.5
              );
              break;
            case "bottom":
            case "base":
              out.set(
                (_scratchBox.min.x + _scratchBox.max.x) * 0.5,
                _scratchBox.min.y,
                (_scratchBox.min.z + _scratchBox.max.z) * 0.5
              );
              break;
            case "center":
            default:
              _scratchBox.getCenter(out);
              break;
          }
          if (this.offset.lengthSq() > 0) {
            out.add(this.offset);
          }
          return out;
        }
      }

      // Default Object3D world position with local offset transformed by matrixWorld
      if (this.offset.lengthSq() > 0) {
        out.copy(this.offset).applyMatrix4(resolved.matrixWorld);
      } else {
        resolved.getWorldPosition(out);
      }
      return out;
    }

    // 3. Static vector or array
    toVector3(resolved, out);
    if (this.offset.lengthSq() > 0) {
      out.add(this.offset);
    }
    return out;
  }
}

/**
 * AnchorSystem coordinates anchor registration, scene graph scanning,
 * per-frame 2D projection, and anchors.json track exporting.
 */
export class AnchorSystem {
  /**
   * @param {THREE.Camera|Object} camera Three.js camera or DioramaCameraController
   * @param {Object} [ctx={}] Context from run.mjs: { width, height, fps, seconds, seed, scale }
   * @param {Object} [options={}] Additional configuration options
   */
  constructor(camera, ctx = {}, options = {}) {
    this.rawCamera = camera;
    this.ctx = {
      width: ctx.width || REFERENCE_WIDTH,
      height: ctx.height || REFERENCE_HEIGHT,
      fps: ctx.fps || DEFAULT_FPS,
      seconds: ctx.seconds || 6.0,
      scale: ctx.scale || (ctx.width ? ctx.width / REFERENCE_WIDTH : 1.0),
      seed: ctx.seed || 1,
    };
    this.options = {
      defaultPolicy: options.defaultPolicy || "clamp", // 'clamp' | 'omit' | 'lastKnown' | 'always'
      boundsMin: options.boundsMin !== undefined ? options.boundsMin : BOUNDS_MIN,
      boundsMax: options.boundsMax !== undefined ? options.boundsMax : BOUNDS_MAX,
      zMax: options.zMax !== undefined ? options.zMax : NDC_Z_MAX,
      decimals: options.decimals !== undefined ? options.decimals : 1,
      ...options,
    };

    /** @type {Map<string, AnchorDefinition>} */
    this.anchors = new Map();

    /** Track history for full-take baking */
    this.recordedTracks = {};
  }

  /**
   * Resolves the underlying Three.js Camera instance.
   * @returns {THREE.Camera}
   */
  getCamera() {
    if (this.rawCamera.isCamera) {
      return this.rawCamera;
    }
    if (this.rawCamera.camera && this.rawCamera.camera.isCamera) {
      return this.rawCamera.camera;
    }
    return this.rawCamera;
  }

  /**
   * Registers a 3D anchor target.
   *
   * @param {string} name Unique identifier (e.g. 'dot', 'kicker', 'headline')
   * @param {THREE.Object3D|THREE.Vector3|Array<number>|Function} target
   * @param {Object} [options={}]
   * @returns {AnchorSystem} this
   */
  add(name, target, options = {}) {
    const def = new AnchorDefinition(name, target, {
      policy: this.options.defaultPolicy,
      ...options,
    });
    this.anchors.set(name, def);
    return this;
  }

  /**
   * Convenience helper to attach an anchor to an Object3D's geometric bounding box keypoint
   * (e.g. apex of an arch, top of a pedestal, head of a standee).
   *
   * @param {string} name Anchor name
   * @param {THREE.Object3D} object Target mesh/group
   * @param {'top'|'center'|'bottom'|'apex'|'base'} [keypoint='top']
   * @param {THREE.Vector3|Array<number>} [offset=[0, 0, 0]] Local offset
   * @param {Object} [options={}]
   * @returns {AnchorSystem} this
   */
  addKeypoint(name, object, keypoint = "top", offset = [0, 0, 0], options = {}) {
    return this.add(name, object, {
      keypoint,
      offset,
      ...options,
    });
  }

  /**
   * Loads anchor definitions from a diorama set JSON structure (e.g. museum-hall.json, classroom.json).
   *
   * @param {Object} setSpec Set specification object
   * @returns {AnchorSystem} this
   */
  loadFromSet(setSpec) {
    if (!setSpec) return this;

    // Load explicit anchors array: [ { id: "dot", position: [x, y, z], description: "..." }, ... ]
    if (Array.isArray(setSpec.anchors)) {
      for (const item of setSpec.anchors) {
        if (item.id && item.position) {
          this.add(item.id, item.position, {
            description: item.description || "",
            role: item.id,
          });
        }
      }
    }

    // Load camera target if defined
    if (setSpec.camera && setSpec.camera.target && !this.anchors.has("dot")) {
      this.add("dot", setSpec.camera.target, { role: "dot", description: "Camera focus target" });
    }

    return this;
  }

  /**
   * Scans a Three.js scene graph for tagged anchor objects.
   * Recognizes:
   * 1. object.name starting with 'anchor:' (e.g. 'anchor:dot', 'anchor:kicker')
   * 2. object.userData.anchor (string name or array of names)
   * 3. object.userData.anchors (object mapping { name: [offsetX, offsetY, offsetZ] })
   *
   * @param {THREE.Object3D} rootObject Root scene or group to traverse
   * @returns {number} Count of anchors discovered
   */
  scanScene(rootObject) {
    if (!rootObject || !rootObject.traverse) return 0;
    let count = 0;

    rootObject.traverse((obj) => {
      // 1. By object name prefix
      if (obj.name && obj.name.startsWith("anchor:")) {
        const name = obj.name.slice(7).trim();
        if (name) {
          this.add(name, obj);
          count++;
        }
      }

      // 2. By userData.anchor
      if (obj.userData && obj.userData.anchor) {
        const tag = obj.userData.anchor;
        if (typeof tag === "string") {
          this.add(tag, obj);
          count++;
        } else if (Array.isArray(tag)) {
          tag.forEach((n) => {
            this.add(n, obj);
            count++;
          });
        }
      }

      // 3. By userData.anchors dictionary
      if (obj.userData && typeof obj.userData.anchors === "object" && !Array.isArray(obj.userData.anchors)) {
        for (const [name, offset] of Object.entries(obj.userData.anchors)) {
          this.add(name, obj, { offset });
          count++;
        }
      }
    });

    return count;
  }

  /**
   * Evaluates all registered anchors at time t and returns a clean dictionary
   * matching the export contract of window.anchors(t):
   *   { [name]: [x, y] }
   *
   * Coordinates are returned in current viewport pixels (width x height),
   * which run.mjs automatically divides by job.scale to produce scale-invariant 1080x1920 tracks.
   *
   * @param {number} [t=0] Time in seconds
   * @returns {Object<string, Array<number>>} Dictionary of projected 2D coordinates [x, y]
   */
  get(t = 0) {
    const camera = this.getCamera();
    const result = {};
    const width = this.ctx.width;
    const height = this.ctx.height;

    for (const [name, def] of this.anchors.entries()) {
      const worldPos = def.resolveWorldPosition(t, _scratchVec3);
      const proj = projectWorldToScreen(worldPos, camera, width, height, {
        boundsMin: this.options.boundsMin,
        boundsMax: this.options.boundsMax,
        zMax: this.options.zMax,
        decimals: this.options.decimals,
      });

      if (proj.visible) {
        def.lastValidPixel = proj.pixel;
        result[name] = proj.pixel;
        continue;
      }

      // Handle out-of-bounds or behind-camera anchors according to policy
      switch (def.policy) {
        case "omit":
          // Omit from dictionary
          break;

        case "lastKnown":
          if (def.lastValidPixel) {
            result[name] = def.lastValidPixel;
          }
          break;

        case "always":
          result[name] = proj.pixel;
          break;

        case "clamp":
        default: {
          // If in front but out of bounds, clamp to viewport boundary
          // If behind camera, mirror or fallback to last known / edge
          if (proj.inFront) {
            const clampedX = Math.max(0, Math.min(width, proj.x));
            const clampedY = Math.max(0, Math.min(height, proj.y));
            const clamped = [
              Math.round(clampedX * 10) / 10,
              Math.round(clampedY * 10) / 10,
            ];
            def.lastValidPixel = clamped;
            result[name] = clamped;
          } else if (def.lastValidPixel) {
            result[name] = def.lastValidPixel;
          } else {
            // Anchor was never visible; omit
          }
          break;
        }
      }
    }

    return result;
  }

  /**
   * Returns rich diagnostic information for all anchors at time t,
   * including 3D world position, NDC, visibility flags, and safe zone compliance.
   *
   * @param {number} [t=0]
   * @returns {Object<string, Object>}
   */
  getDetailed(t = 0) {
    const camera = this.getCamera();
    const detailed = {};
    const width = this.ctx.width;
    const height = this.ctx.height;

    for (const [name, def] of this.anchors.entries()) {
      const worldPos = def.resolveWorldPosition(t, new THREE.Vector3());
      const proj = projectWorldToScreen(worldPos, camera, width, height, {
        boundsMin: this.options.boundsMin,
        boundsMax: this.options.boundsMax,
        zMax: this.options.zMax,
        decimals: this.options.decimals,
      });

      detailed[name] = {
        name,
        role: def.role,
        description: def.description,
        worldPosition: [worldPos.x, worldPos.y, worldPos.z],
        pixel: proj.pixel,
        x: proj.x,
        y: proj.y,
        u: proj.u,
        v: proj.v,
        ndc: proj.ndc,
        inFront: proj.inFront,
        inBounds: proj.inBounds,
        visible: proj.visible,
        inSafeZone: proj.inSafeZone,
      };
    }

    return detailed;
  }

  /**
   * Records the anchor positions for frame at time t into the internal track recorder.
   *
   * @param {number} t
   */
  recordFrame(t) {
    const frameAnchors = this.get(t);
    const scale = this.ctx.scale;

    for (const [name, pixel] of Object.entries(frameAnchors)) {
      if (!this.recordedTracks[name]) {
        this.recordedTracks[name] = [];
      }
      // Scale-normalized coordinates in canonical 1080x1920 reference space
      const normX = Math.round((pixel[0] / scale) * 10) / 10;
      const normY = Math.round((pixel[1] / scale) * 10) / 10;
      this.recordedTracks[name].push([normX, normY]);
    }
  }

  /**
   * Exports the complete anchors.json track manifest.
   *
   * @returns {Object} { fps, width, height, tracks }
   */
  exportTracks() {
    return {
      fps: this.ctx.fps,
      width: REFERENCE_WIDTH,
      height: REFERENCE_HEIGHT,
      tracks: this.recordedTracks,
    };
  }

  /**
   * Binds this AnchorSystem to window.anchors for plates/run.mjs headless execution.
   */
  bindToWindow() {
    if (typeof window !== "undefined") {
      window.anchors = (t) => this.get(t);
    }
    return this;
  }
}

// ============================================================================
// 4. FACTORY & BINDING CONVENIENCE
// ============================================================================

/**
 * Creates and initializes an AnchorSystem.
 *
 * @param {THREE.Camera|Object} camera
 * @param {Object} ctx Setup context { width, height, fps, seconds, seed, scale }
 * @param {Object} [options]
 * @returns {AnchorSystem}
 */
export function createAnchorSystem(camera, ctx, options = {}) {
  return new AnchorSystem(camera, ctx, options);
}

/**
 * Convenience helper to attach an AnchorSystem directly to window.anchors
 * and return the instance.
 *
 * @param {THREE.Camera|Object} camera
 * @param {Object} ctx
 * @param {Object} [options]
 * @returns {AnchorSystem}
 */
export function setupWindowAnchors(camera, ctx, options = {}) {
  const system = new AnchorSystem(camera, ctx, options);
  system.bindToWindow();
  return system;
}
