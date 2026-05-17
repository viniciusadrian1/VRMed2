// Compute the true world-space bounding box of a GLB by walking the
// scene graph and composing node transforms. Flags models whose parts
// are spread far apart (defective export).
import { readFileSync } from "node:fs";
import * as THREE from "three";

function load(file) {
  const buf = readFileSync(file);
  const jsonLen = buf.readUInt32LE(12);
  return JSON.parse(buf.toString("utf8", 20, 20 + jsonLen));
}

function nodeMatrix(n) {
  const m = new THREE.Matrix4();
  if (n.matrix) return m.fromArray(n.matrix);
  const t = n.translation ?? [0, 0, 0];
  const r = n.rotation ?? [0, 0, 0, 1];
  const s = n.scale ?? [1, 1, 1];
  return m.compose(
    new THREE.Vector3(...t),
    new THREE.Quaternion(...r),
    new THREE.Vector3(...s),
  );
}

for (const file of process.argv.slice(2)) {
  const j = load(file);
  const box = new THREE.Box3();
  const corner = new THREE.Vector3();
  const walk = (idx, parent) => {
    const n = j.nodes[idx];
    const world = parent.clone().multiply(nodeMatrix(n));
    if (n.mesh != null) {
      for (const p of j.meshes[n.mesh].primitives ?? []) {
        const a = j.accessors[p.attributes?.POSITION];
        if (!a?.min) continue;
        for (let i = 0; i < 8; i++) {
          corner.set(
            i & 1 ? a.max[0] : a.min[0],
            i & 2 ? a.max[1] : a.min[1],
            i & 4 ? a.max[2] : a.min[2],
          );
          box.expandByPoint(corner.applyMatrix4(world));
        }
      }
    }
    for (const c of n.children ?? []) walk(c, world);
  };
  for (const s of j.scenes ?? [])
    for (const idx of s.nodes ?? []) walk(idx, new THREE.Matrix4());

  const size = box.getSize(new THREE.Vector3());
  const max = Math.max(size.x, size.y, size.z);
  const min = Math.min(size.x, size.y, size.z);
  const ratio = min > 0 ? (max / min).toFixed(1) : "inf";
  const name = file.split(/[/\\]/).pop();
  console.log(
    `${name.padEnd(26)} span ${size.toArray().map((v) => v.toFixed(1)).join(" x ")}  aspect ${ratio}`,
  );
}
