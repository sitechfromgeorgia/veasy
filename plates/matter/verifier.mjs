/**
 * plates/matter/verifier.mjs
 *
 * Verifier and fact validator for physical quantities in Veasy plates.
 * Enforces the Isotype principle: count * unit = fact exactly.
 *
 * Rules:
 *   1. Exact divisibility: fact % unit === 0. Never round, never approximate.
 *   2. Capacity: count <= 3000 blocks.
 *   3. Positive integers: fact > 0, unit > 0.
 *   4. Groups partition: sum(group.fact) === fact, and each group.fact % unit === 0.
 *   5. Forbidden categories: news, crime, incidents, deaths, real place assertions
 *      refused under CLAUDE.md § N and plates/README.md.
 *   6. Story resolution: resolve facts from story files (e.g. stories/24835.json).
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const MAX_BLOCK_COUNT = 3000;

export const FORBIDDEN_CATEGORIES = new Set([
  "news",
  "crime",
  "incident",
  "incidents",
  "death",
  "deaths",
]);

export const DEATH_KEYWORDS = [
  "დაიღუპა",
  "მსხვერპლი",
  "გარდაიცვალა",
  "მკვლელობა",
  "death",
  "deaths",
  "fatal",
  "killed",
  "murder",
];

export class UnitMismatchError extends Error {
  constructor(message, { unit, fact, remainder } = {}) {
    super(message);
    this.name = "UnitMismatchError";
    this.unit = unit;
    this.fact = fact;
    this.remainder = remainder;
  }
}

export class BlockCountExceededError extends Error {
  constructor(message, { count, maxCapacity } = {}) {
    super(message);
    this.name = "BlockCountExceededError";
    this.count = count;
    this.maxCapacity = maxCapacity ?? MAX_BLOCK_COUNT;
  }
}

export class ForbiddenCategoryError extends Error {
  constructor(message, { reason, category, place } = {}) {
    super(message);
    this.name = "ForbiddenCategoryError";
    this.reason = reason;
    this.category = category;
    this.place = place;
  }
}

export class GroupPartitionError extends Error {
  constructor(message, { sum, fact } = {}) {
    super(message);
    this.name = "GroupPartitionError";
    this.sum = sum;
    this.fact = fact;
  }
}

export class InvalidFactError extends Error {
  constructor(message) {
    super(message);
    this.name = "InvalidFactError";
  }
}

/**
 * Check whether a spec, options, or story involves forbidden categories
 * or real-place assertions.
 */
export function checkForbidden(spec = {}, options = {}, story = null) {
  const category = (spec.category || options.category || "").toLowerCase().trim();
  const program = (spec.program || options.program || "").toLowerCase().trim();

  if (category && FORBIDDEN_CATEGORIES.has(category)) {
    throw new ForbiddenCategoryError(
      `plates are strictly forbidden for category "${category}" under CLAUDE.md § N and plates/README.md`,
      { reason: "category", category }
    );
  }

  if (program && FORBIDDEN_CATEGORIES.has(program)) {
    throw new ForbiddenCategoryError(
      `plates are strictly forbidden for program "${program}" under CLAUDE.md § N and plates/README.md`,
      { reason: "program", category: program }
    );
  }

  if (story && typeof story === "object") {
    const storyCat = (story.category || "").toLowerCase().trim();
    const storyProg = (story.program || "").toLowerCase().trim();

    if (storyCat && FORBIDDEN_CATEGORIES.has(storyCat)) {
      throw new ForbiddenCategoryError(
        `plates are strictly forbidden for story category "${storyCat}" under CLAUDE.md § N and plates/README.md`,
        { reason: "story_category", category: storyCat }
      );
    }

    if (storyProg && FORBIDDEN_CATEGORIES.has(storyProg)) {
      throw new ForbiddenCategoryError(
        `plates are strictly forbidden for story program "${storyProg}" under CLAUDE.md § N and plates/README.md`,
        { reason: "story_program", category: storyProg }
      );
    }

    const narration = (story.narration || "").toLowerCase();
    for (const kw of DEATH_KEYWORDS) {
      if (narration.includes(kw)) {
        throw new ForbiddenCategoryError(
          `plates are strictly forbidden for stories about deaths ("${kw}") under CLAUDE.md § N and plates/README.md`,
          { reason: "deaths", category: "deaths" }
        );
      }
    }
  }

  if (
    spec.real_place ||
    spec.real_place_assertion ||
    spec.is_real_place ||
    spec.place ||
    options.real_place ||
    options.place
  ) {
    const placeVal = spec.place || options.place || "real place";
    throw new ForbiddenCategoryError(
      `plates are strictly forbidden from real place assertions ("${placeVal}") under CLAUDE.md § N and plates/README.md: a plate is an abstract physical model, never a picture of a real place`,
      { reason: "real_place", place: placeVal }
    );
  }
}

/**
 * Resolve a factual number from a story object using a key descriptor.
 * Supports:
 *   - Direct property: e.g. "value", "fact"
 *   - Scene index notation: "scene-1-value", "scenes[1].value", "scene_1_value"
 *   - Scene type notation: "stat.value", "stat"
 *   - Dot path: "scenes.1.value"
 */
export function resolveStoryKey(story, key = "value") {
  if (!story || typeof story !== "object") {
    throw new InvalidFactError("Invalid story object provided");
  }

  if (key in story && typeof story[key] === "number") {
    return story[key];
  }

  const sceneMatch = key.match(/^scenes?[_.\-\[](\d+)[\].\-_]*(.*)$/i);
  if (sceneMatch) {
    const idx = parseInt(sceneMatch[1], 10);
    const subProp = sceneMatch[2].replace(/^[_.\-]+/, "") || "value";
    if (Array.isArray(story.scenes) && story.scenes[idx]) {
      const val = story.scenes[idx][subProp];
      if (val !== undefined && val !== null) {
        const num = Number(val);
        if (Number.isFinite(num)) return num;
      }
    }
  }

  if (key.includes(".")) {
    const parts = key.split(".");
    let cur = story;
    for (const p of parts) {
      if (cur == null) break;
      cur = cur[p];
    }
    if (cur !== undefined && cur !== null) {
      const num = Number(cur);
      if (Number.isFinite(num)) return num;
    }
  }

  if (Array.isArray(story.scenes)) {
    const typeMatch = key.match(/^([a-z0-9_-]+)(?:[-.]([a-z0-9_-]+))?$/i);
    if (typeMatch) {
      const targetType = typeMatch[1];
      const targetProp = typeMatch[2] || "value";
      const sc = story.scenes.find((s) => s && s.type === targetType);
      if (sc && sc[targetProp] !== undefined && sc[targetProp] !== null) {
        const num = Number(sc[targetProp]);
        if (Number.isFinite(num)) return num;
      }
    }

    if (key === "value") {
      for (const sc of story.scenes) {
        if (sc && typeof sc.value === "number") {
          return sc.value;
        }
      }
    }
  }

  throw new InvalidFactError(`Could not resolve fact key "${key}" from story`);
}

/**
 * Resolve a factual number from a literal or a story reference object.
 */
export function resolveFact(factOrRef, options = {}) {
  if (typeof factOrRef === "number") {
    if (!Number.isFinite(factOrRef)) {
      throw new InvalidFactError(`Fact must be a finite number, got ${factOrRef}`);
    }
    return factOrRef;
  }

  if (typeof factOrRef === "string" && /^-?\d+(\.\d+)?$/.test(factOrRef.trim())) {
    return Number(factOrRef.trim());
  }

  if (factOrRef && typeof factOrRef === "object") {
    // If in-memory story object is supplied
    if (factOrRef.story || options.story) {
      const story = factOrRef.story || options.story;
      checkForbidden({}, options, story);
      const key = factOrRef.key || factOrRef.field || factOrRef.prop || "value";
      return resolveStoryKey(story, key);
    }

    const filePath = factOrRef.file || factOrRef.ref || factOrRef.path;
    const key = factOrRef.key || factOrRef.field || factOrRef.prop || "value";

    if (!filePath) {
      throw new InvalidFactError(`Story fact reference missing file/ref path: ${JSON.stringify(factOrRef)}`);
    }

    const rootDir = options.rootDir || process.cwd();
    const here = path.dirname(fileURLToPath(import.meta.url));
    const repoRoot = path.resolve(here, "../..");

    const candidatePaths = [
      path.resolve(rootDir, filePath),
      path.resolve(process.cwd(), filePath),
      path.resolve(repoRoot, filePath),
    ];

    let resolvedPath = candidatePaths.find((p) => fs.existsSync(p));
    if (!resolvedPath) {
      throw new InvalidFactError(`Story file not found: ${filePath}`);
    }

    let story;
    try {
      story = JSON.parse(fs.readFileSync(resolvedPath, "utf8"));
    } catch (e) {
      throw new InvalidFactError(`Failed to parse story JSON at ${filePath}: ${e.message}`);
    }

    checkForbidden({}, options, story);
    return resolveStoryKey(story, key);
  }

  throw new InvalidFactError(`Invalid fact or fact_ref: ${JSON.stringify(factOrRef)}`);
}

/**
 * Verify a matter plate specification.
 *
 * @param {object} spec
 * @param {object} [options]
 * @returns {object} Verified spec with computed integer count and validated partition
 */
export function verifySpec(spec, options = {}) {
  if (!spec || typeof spec !== "object") {
    throw new Error("Spec must be an object");
  }

  // 1. Refuse forbidden categories on spec / options
  checkForbidden(spec, options);

  // 2. Resolve fact
  let fact;
  if (spec.fact_ref) {
    fact = resolveFact(spec.fact_ref, options);
  } else if (spec.fact !== undefined && spec.fact !== null) {
    fact = resolveFact(spec.fact, options);
  } else {
    throw new InvalidFactError("Spec must define 'fact' or 'fact_ref'");
  }

  // 3. Validate fact is a positive integer
  if (typeof fact !== "number" || !Number.isFinite(fact)) {
    throw new InvalidFactError(`fact must be a valid number, got ${fact}`);
  }
  if (fact <= 0) {
    throw new InvalidFactError(`fact must be a positive integer, got ${fact}`);
  }
  if (!Number.isInteger(fact)) {
    throw new InvalidFactError(`fact must be an integer, got ${fact}`);
  }

  // 4. Validate unit is a positive integer
  if (spec.unit === undefined || spec.unit === null) {
    throw new Error("Spec must define 'unit'");
  }
  const unit = Number(spec.unit);
  if (!Number.isFinite(unit)) {
    throw new Error(`Unit must be a valid number, got ${spec.unit}`);
  }
  if (unit <= 0) {
    throw new Error(`unit must be a positive integer, got ${unit}`);
  }
  if (!Number.isInteger(unit)) {
    throw new Error(`unit must be an integer, got ${unit}`);
  }

  // 5. Exact divisibility: fact % unit === 0
  const bFact = BigInt(fact);
  const bUnit = BigInt(unit);
  const bRemainder = bFact % bUnit;
  if (bRemainder !== 0n) {
    const remainder = Number(bRemainder);
    throw new UnitMismatchError(
      `unit ${unit} does not divide fact ${fact} exactly (remainder ${remainder})`,
      { unit, fact, remainder }
    );
  }

  // 6. Compute block count
  const count = Number(bFact / bUnit);

  // 7. Enforce capacity limit (max 3000 blocks)
  if (count > MAX_BLOCK_COUNT) {
    throw new BlockCountExceededError(
      `block count ${count} exceeds maximum capacity of 3000 blocks; choose a larger unit`,
      { count, maxCapacity: MAX_BLOCK_COUNT }
    );
  }

  // 8. Groups partition validation
  let verifiedGroups = [];
  if (spec.groups !== undefined && spec.groups !== null) {
    if (!Array.isArray(spec.groups)) {
      throw new Error("'groups' must be an array");
    }

    if (spec.groups.length > 0) {
      let groupSum = 0;
      verifiedGroups = spec.groups.map((group, idx) => {
        if (!group || typeof group !== "object") {
          throw new Error(`Group at index ${idx} must be an object`);
        }

        let gFact;
        if (group.fact_ref) {
          gFact = resolveFact(group.fact_ref, options);
        } else if (group.fact !== undefined && group.fact !== null) {
          gFact = resolveFact(group.fact, options);
        } else {
          throw new InvalidFactError(`Group "${group.name || idx}" missing 'fact' or 'fact_ref'`);
        }

        if (typeof gFact !== "number" || !Number.isFinite(gFact) || gFact <= 0 || !Number.isInteger(gFact)) {
          throw new InvalidFactError(`Group "${group.name || idx}" fact must be a positive integer, got ${gFact}`);
        }

        const bGFact = BigInt(gFact);
        const bGRem = bGFact % bUnit;
        if (bGRem !== 0n) {
          const gRem = Number(bGRem);
          throw new UnitMismatchError(
            `unit ${unit} does not divide group "${group.name || idx}" fact ${gFact} exactly (remainder ${gRem})`,
            { unit, fact: gFact, remainder: gRem }
          );
        }

        const gCount = Number(bGFact / bUnit);
        groupSum += gFact;

        return {
          ...group,
          fact: gFact,
          count: gCount,
        };
      });

      if (groupSum !== fact) {
        throw new GroupPartitionError(
          `sum of group facts (${groupSum}) does not equal total fact (${fact})`,
          { sum: groupSum, fact }
        );
      }
    }
  }

  return {
    ...spec,
    fact,
    unit,
    count,
    unit_label: spec.unit_label || "",
    groups: verifiedGroups,
    form: spec.form || "pile",
    camera: spec.camera || "auto",
    block_size: spec.block_size !== undefined ? Number(spec.block_size) : 0.42,
    verified: true,
  };
}

// CLI entry point
if (process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1])) {
  try {
    const rawArg = process.argv[2];
    if (!rawArg) {
      console.error("Usage: node verifier.mjs <spec.json | json-string>");
      process.exit(2);
    }
    let spec;
    if (fs.existsSync(rawArg)) {
      spec = JSON.parse(fs.readFileSync(rawArg, "utf8"));
    } else {
      spec = JSON.parse(rawArg);
    }
    const result = verifySpec(spec);
    console.log(JSON.stringify(result));
    process.exit(0);
  } catch (err) {
    console.error(err.message || String(err));
    process.exit(1);
  }
}
