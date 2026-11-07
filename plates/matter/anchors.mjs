// plates/matter/anchors.mjs
// Calculates 2D screen coordinates (anchors) in [0..1080, 0..1920] pixel space for DOM elements.
// Computes 3D bounding box / centroids for each group/share.
// Projects 3D world coordinates to 2D screen coordinates using camera projection matrix.
// Formats into { dot: [x, y], label: [x, y] } for each group key, matching plates/run.mjs anchors contract.

import * as THREE from "three";
import { computeGroupBounds } from "./forms.mjs";

export const DEFAULT_VIEWPORT_WIDTH = 1080;
export const DEFAULT_VIEWPORT_HEIGHT = 1920;

/**
 * Projects a 3D point to 2D screen pixel coordinates [x, y].
 * Supports THREE.Camera, or objects with view and projection matrices, or pure math.
 * 
 * @param {[number, number, number]|object} point3D 3D world coordinates [x, y, z] or {x, y, z}
 * @param {object} cameraOrMatrices THREE.Camera or { projectionMatrix, matrixWorldInverse }
 * @param {number} [width=1080] Viewport width in pixels
 * @param {number} [height=1920] Viewport height in pixels
 * @returns {[number, number]} [screenX, screenY] in viewport pixels
 */
export function project3DToScreen(point3D, cameraOrMatrices, width = DEFAULT_VIEWPORT_WIDTH, height = DEFAULT_VIEWPORT_HEIGHT) {
  const px = Array.isArray(point3D) ? point3D[0] : (typeof point3D.x === "number" ? point3D.x : 0);
  const py = Array.isArray(point3D) ? point3D[1] : (typeof point3D.y === "number" ? point3D.y : 0);
  const pz = Array.isArray(point3D) ? point3D[2] : (typeof point3D.z === "number" ? point3D.z : 0);

  // If a THREE.Camera instance is provided
  if (cameraOrMatrices && typeof cameraOrMatrices.isCamera === "boolean" && cameraOrMatrices.isCamera) {
    const v = new THREE.Vector3(px, py, pz);
    v.project(cameraOrMatrices);
    const screenX = Number((((v.x + 1) / 2) * width).toFixed(1));
    const screenY = Number((((1 - v.y) / 2) * height).toFixed(1));
    return [screenX, screenY];
  }

  // Pure 4x4 matrix projection (column-major IEEE 754 float array)
  let viewMat = null;
  let projMat = null;

  if (cameraOrMatrices) {
    if (cameraOrMatrices.matrixWorldInverse && cameraOrMatrices.projectionMatrix) {
      viewMat = cameraOrMatrices.matrixWorldInverse.elements || cameraOrMatrices.matrixWorldInverse;
      projMat = cameraOrMatrices.projectionMatrix.elements || cameraOrMatrices.projectionMatrix;
    } else if (cameraOrMatrices.viewMatrix && cameraOrMatrices.projectionMatrix) {
      viewMat = cameraOrMatrices.viewMatrix.elements || cameraOrMatrices.viewMatrix;
      projMat = cameraOrMatrices.projectionMatrix.elements || cameraOrMatrices.projectionMatrix;
    }
  }

  if (viewMat && projMat) {
    // Transform by view matrix: V = M_view * [x, y, z, 1]^T
    const vx = viewMat[0] * px + viewMat[4] * py + viewMat[8] * pz + viewMat[12];
    const vy = viewMat[1] * px + viewMat[5] * py + viewMat[9] * pz + viewMat[13];
    const vz = viewMat[2] * px + viewMat[6] * py + viewMat[10] * pz + viewMat[14];
    const vw = viewMat[3] * px + viewMat[7] * py + viewMat[11] * pz + viewMat[15];

    // Transform by projection matrix: C = M_proj * V
    const cx = projMat[0] * vx + projMat[4] * vy + projMat[8] * vz + projMat[12] * vw;
    const cy = projMat[1] * vx + projMat[5] * vy + projMat[9] * vz + projMat[13] * vw;
    const cw = projMat[3] * vx + projMat[7] * vy + projMat[11] * vz + projMat[15] * vw;

    if (Math.abs(cw) > 1e-6) {
      const ndcX = cx / cw;
      const ndcY = cy / cw;
      const screenX = Number((((ndcX + 1) / 2) * width).toFixed(1));
      const screenY = Number((((1 - ndcY) / 2) * height).toFixed(1));
      return [screenX, screenY];
    }
  }

  // Fallback if no valid camera or matrix is provided
  return [Number((width * 0.5).toFixed(1)), Number((height * 0.5).toFixed(1))];
}

/**
 * Computes 3D group centroids, bounds, and 3D anchor points (dot and label) for groups and total.
 * 
 * @param {Array<[number, number, number]>|Float32Array} positions Block positions
 * @param {Array<object>} [assignments=null] Block group assignments
 * @param {object} [options={}] Optional form geometry or resting bounds
 * @returns {object} Map of group IDs to 3D anchor points and bounds
 */
export function computeAnchors3D(positions, assignments = null, options = {}) {
  let bounds = computeGroupBounds(positions, assignments);

  // If blocks are currently in the sky (e.g. drop waves at t=0) and resting bounds are provided,
  // use the stable resting table mound bounds so DOM dot doesn't fly off-screen into the clouds.
  const formGeom = options.formGeometry || null;
  const restBounds = formGeom ? formGeom.bounds : (options.restBounds || null);

  if (restBounds && bounds.total.centroid[1] > 5.0) {
    bounds = restBounds;
  }

  // For too-tall form, anchor tracks the current climbing focal height
  let focalY = bounds.total.max[1];
  if (options.form === "too-tall" && typeof options.climbTargetY === "number") {
    focalY = options.climbTargetY;
  }

  const result = {
    total: {
      centroid: bounds.total.centroid,
      bounds: bounds.total,
      dot3D: [
        bounds.total.centroid[0],
        focalY + 0.08,
        bounds.total.centroid[2]
      ],
      label3D: [
        bounds.total.centroid[0],
        focalY + 0.48,
        bounds.total.centroid[2]
      ]
    },
    groups: {}
  };

  for (const [gid, gBounds] of Object.entries(bounds.groups)) {
    const groupFocalY = (options.form === "too-tall" && typeof options.climbTargetY === "number")
      ? options.climbTargetY
      : gBounds.max[1];

    result.groups[gid] = {
      centroid: gBounds.centroid,
      bounds: gBounds,
      dot3D: [
        gBounds.centroid[0],
        groupFocalY + 0.08,
        gBounds.centroid[2]
      ],
      label3D: [
        gBounds.centroid[0],
        groupFocalY + 0.48,
        gBounds.centroid[2]
      ]
    };
  }

  return result;
}

/**
 * Calculates 2D screen anchors formatted for the plates/run.mjs contract.
 * Returns an object with { dot: [x, y], label: [x, y], ... } matching run.mjs expectations.
 * 
 * @param {Array<[number, number, number]>|Float32Array} positions Current block positions at time t
 * @param {Array<object>} assignments Group assignments
 * @param {object} cameraOrMatrices Camera or projection context
 * @param {number} [width=1080] Viewport width
 * @param {number} [height=1920] Viewport height
 * @param {object} [options={}] Formatting options (e.g. formGeometry, form, climbTargetY)
 * @returns {Record<string, [number, number]>} Anchors dictionary mapping track names to [x, y] screen coordinates
 */
export function calculateAnchors(
  positions,
  assignments,
  cameraOrMatrices,
  width = DEFAULT_VIEWPORT_WIDTH,
  height = DEFAULT_VIEWPORT_HEIGHT,
  options = {}
) {
  const anchors3D = computeAnchors3D(positions, assignments, options);
  const out = {};

  // 1. Primary/Active dot and label (default keys "dot" and "label")
  // In split form, "share" is the active sliding share
  const groupKeys = Object.keys(anchors3D.groups);
  let primaryTarget = anchors3D.total;

  if (options.primaryGroup && anchors3D.groups[options.primaryGroup]) {
    primaryTarget = anchors3D.groups[options.primaryGroup];
  } else if (anchors3D.groups.share) {
    primaryTarget = anchors3D.groups.share;
  } else if (groupKeys.length === 1 && anchors3D.groups[groupKeys[0]]) {
    primaryTarget = anchors3D.groups[groupKeys[0]];
  }

  out.dot = project3DToScreen(primaryTarget.dot3D, cameraOrMatrices, width, height);
  out.label = project3DToScreen(primaryTarget.label3D, cameraOrMatrices, width, height);

  // 2. Per-group anchors: "dot:<group>" and "label:<group>"
  for (const [gid, gAnchor] of Object.entries(anchors3D.groups)) {
    out[`dot:${gid}`] = project3DToScreen(gAnchor.dot3D, cameraOrMatrices, width, height);
    out[`label:${gid}`] = project3DToScreen(gAnchor.label3D, cameraOrMatrices, width, height);
  }

  // 3. Explicit total anchor if multiple groups exist
  if (groupKeys.length > 1) {
    out["dot:total"] = project3DToScreen(anchors3D.total.dot3D, cameraOrMatrices, width, height);
    out["label:total"] = project3DToScreen(anchors3D.total.label3D, cameraOrMatrices, width, height);
  }

  return out;
}

/**
 * Creates an anchor tracker helper for index.html plate runtime.
 * @param {object} formGeometry Result of getFormGeometry()
 * @param {object} [options={}] Options
 * @returns {object} Tracker with getAnchors(positions, camera, width, height)
 */
export function createAnchorTracker(formGeometry, options = {}) {
  const assignments = formGeometry ? formGeometry.assignments : null;

  return {
    getAnchors(positions, camera, width = DEFAULT_VIEWPORT_WIDTH, height = DEFAULT_VIEWPORT_HEIGHT) {
      return calculateAnchors(positions, assignments, camera, width, height, options);
    }
  };
}
