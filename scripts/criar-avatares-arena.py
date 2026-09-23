"""Variantes leves de personagens decorativos. NUNCA usar em anatomia."""
import bpy
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PASTA = RAIZ / "public/models/props"
anterior = bpy.context.window.scene
relatorio = []
try:
    for nome in ("dr-caloni", "dra-reis", "dr-chefe"):
        cena = bpy.data.scenes.new("VRmed_Avatar_" + nome)
        bpy.context.window.scene = cena
        bpy.ops.import_scene.gltf(filepath=str(PASTA / (nome + ".glb")))
        malhas = [obj for obj in cena.objects if obj.type == "MESH"]
        antes = sum(len(o.data.polygons) for o in malhas)
        imagens = set()
        for obj in malhas:
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            modificador = obj.modifiers.new("LOD de personagem decorativo", "DECIMATE")
            modificador.ratio = min(1, 45000 / max(1, len(obj.data.polygons)))
            modificador.use_collapse_triangulate = True
            bpy.ops.object.modifier_apply(modifier=modificador.name)
            for mat in obj.data.materials:
                if not mat or not mat.use_nodes:
                    continue
                for no in mat.node_tree.nodes:
                    if no.type == "TEX_IMAGE" and no.image:
                        imagens.add(no.image)
        for imagem in imagens:
            w, h = imagem.size
            if max(w, h) > 1024:
                fator = 1024 / max(w, h)
                imagem.scale(max(1, round(w * fator)), max(1, round(h * fator)))
                imagem.pack()
        destino = PASTA / (nome + "-arena.glb")
        bpy.ops.export_scene.gltf(filepath=str(destino), export_format="GLB", use_active_scene=True,
                                  export_animations=False, export_draco_mesh_compression_enable=True,
                                  export_draco_mesh_compression_level=6, export_image_quality=85)
        depois = 0
        for obj in malhas:
            obj.data.calc_loop_triangles()
            depois += len(obj.data.loop_triangles)
        relatorio.append({"personagem": nome, "faces_antes": antes, "triangulos_depois": depois,
                          "bytes": destino.stat().st_size, "texturas_max": 1024})
    result = {"avatares": relatorio, "originais_preservados": True}
    print(json.dumps(result))
finally:
    bpy.context.window.scene = anterior
