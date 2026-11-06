#!/usr/bin/env node
// plates/run.mjs serves plates/ only, so a page can't read assets/drawings: this copies them into one local file.
//   node plates/diorama/tools/bundle_drawings.mjs        (write plates/diorama/drawings.json)
//   node plates/diorama/tools/bundle_drawings.mjs --check (fail if it is stale)
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SOURCE = path.resolve(HERE, "..", "..", "..", "assets", "drawings");
const TARGET = path.resolve(HERE, "..", "drawings.json");

export function bundle() {
  const out = {};
  for (const name of fs.readdirSync(SOURCE).sort()) {
    if (!name.endsWith(".json")) continue;
    const { motif, about, svg } = JSON.parse(fs.readFileSync(path.join(SOURCE, name), "utf8"));
    out[name.replace(/\.json$/, "")] = { motif, about, svg };
  }
  return `${JSON.stringify(out, null, 0)}\n`;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const fresh = bundle();
  if (process.argv.includes("--check")) {
    if (!fs.existsSync(TARGET) || fs.readFileSync(TARGET, "utf8") !== fresh) {
      console.error("drawings.json is stale: run tools/bundle_drawings.mjs");
      process.exit(1);
    }
  } else {
    fs.writeFileSync(TARGET, fresh);
    console.log(`${Object.keys(JSON.parse(fresh)).length} drawings, ${fresh.length} bytes`);
  }
}
