// Dump node / mesh / material names from a GLB's JSON chunk.
import { readFileSync } from "node:fs";

const file = process.argv[2];
if (!file) {
  console.error("usage: node inspect-glb.mjs <file.glb>");
  process.exit(1);
}

const buf = readFileSync(file);
const jsonLen = buf.readUInt32LE(12);
const json = JSON.parse(buf.toString("utf8", 20, 20 + jsonLen));

const names = (arr) => (arr ?? []).map((x) => x.name ?? "<sem nome>");
const tally = (list) => {
  const m = new Map();
  for (const n of list) m.set(n, (m.get(n) ?? 0) + 1);
  return [...m.entries()].sort((a, b) => b[1] - a[1]);
};

console.log(`\n=== ${file} ===`);
console.log(`nodes: ${json.nodes?.length ?? 0}`);
console.log(`meshes: ${json.meshes?.length ?? 0}`);
console.log(`materials: ${json.materials?.length ?? 0}`);

console.log("\n-- node names (top 40 by frequency) --");
for (const [n, c] of tally(names(json.nodes)).slice(0, 40)) {
  console.log(`  ${c.toString().padStart(4)}  ${n}`);
}
console.log("\n-- mesh names (top 40) --");
for (const [n, c] of tally(names(json.meshes)).slice(0, 40)) {
  console.log(`  ${c.toString().padStart(4)}  ${n}`);
}
console.log("\n-- material names --");
for (const [n, c] of tally(names(json.materials))) {
  console.log(`  ${c.toString().padStart(4)}  ${n}`);
}
if (json.extensionsUsed) {
  console.log("\n-- extensions --");
  console.log("  " + json.extensionsUsed.join(", "));
}
