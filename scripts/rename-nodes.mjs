// Some Sketchfab exports store the structure name only at the end of a
// file-path node name (".../preprocess/Vagus.obj"). three.js's GLTFLoader
// strips "/" and "." from node names on load, destroying that path — so the
// name must be cleaned up *inside the GLB*, before the app loads it.
//
// This rewrites each path-like node name to just its basename, editing only
// the GLB's JSON chunk (the binary/Draco chunk is copied verbatim).
import { readFileSync, writeFileSync } from "node:fs";

const JSON_CHUNK = 0x4e4f534a;

function renameInGlb(file) {
  const buf = readFileSync(file);
  if (buf.readUInt32LE(0) !== 0x46546c67) throw new Error(`${file}: not a GLB`);

  const jsonLen = buf.readUInt32LE(12);
  if (buf.readUInt32LE(16) !== JSON_CHUNK) throw new Error(`${file}: chunk 0 not JSON`);
  const json = JSON.parse(buf.toString("utf8", 20, 20 + jsonLen));
  const binChunk = buf.subarray(20 + jsonLen); // length + type + data, padded

  let renamed = 0;
  for (const node of json.nodes ?? []) {
    if (node.name && /[/\\]/.test(node.name)) {
      const base = node.name
        .split(/[/\\]/)
        .pop()
        .replace(/\.(obj|fbx|gltf|glb|gles|osgb|dae|stl|ply)$/i, "")
        .trim();
      if (base) {
        node.name = base;
        renamed += 1;
      }
    }
  }

  // Re-serialize JSON, padded to a 4-byte boundary with spaces (glTF spec).
  let jsonBuf = Buffer.from(JSON.stringify(json), "utf8");
  const pad = (4 - (jsonBuf.length % 4)) % 4;
  if (pad) jsonBuf = Buffer.concat([jsonBuf, Buffer.alloc(pad, 0x20)]);

  const total = 12 + 8 + jsonBuf.length + binChunk.length;
  const out = Buffer.alloc(total);
  out.write("glTF", 0, "ascii");
  out.writeUInt32LE(2, 4);
  out.writeUInt32LE(total, 8);
  out.writeUInt32LE(jsonBuf.length, 12);
  out.writeUInt32LE(JSON_CHUNK, 16);
  jsonBuf.copy(out, 20);
  binChunk.copy(out, 20 + jsonBuf.length);
  writeFileSync(file, out);
  return renamed;
}

for (const file of process.argv.slice(2)) {
  console.log(`${file} — ${renameInGlb(file)} nó(s) de caminho renomeado(s)`);
}
