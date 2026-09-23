import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";

for (const arquivo of process.argv.slice(2)) {
  const dados = readFileSync(arquivo);
  const gltf = JSON.parse(dados.toString("utf8", 20, 20 + dados.readUInt32LE(12)).trim());
  const primitivas = (gltf.meshes ?? []).flatMap((m) => m.primitives);
  console.log(JSON.stringify({ arquivo, bytes: dados.length,
    sha256: createHash("sha256").update(dados).digest("hex"),
    malhas: gltf.meshes?.length ?? 0, materiais: gltf.materials?.length ?? 0,
    triangulos: primitivas.reduce((n, p) => n + (gltf.accessors[p.indices ?? p.attributes.POSITION]?.count ?? 0) / 3, 0),
    vertices: primitivas.reduce((n, p) => n + (gltf.accessors[p.attributes.POSITION]?.count ?? 0), 0),
    animacoes: gltf.animations?.length ?? 0, canais: (gltf.animations ?? []).reduce((n, a) => n + a.channels.length, 0),
    imagens: gltf.images?.map((i) => ({ tipo: i.mimeType, bytes: gltf.bufferViews[i.bufferView]?.byteLength })) ?? [],
    extensoes: gltf.extensionsUsed ?? [],
  }));
}
