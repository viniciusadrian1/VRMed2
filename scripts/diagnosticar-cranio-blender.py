"""Auditoria e comparação controlada; o GLB original nunca é sobrescrito."""
import bpy
import json
import numpy as np
from pathlib import Path
from mathutils import Vector

RAIZ = Path(__file__).resolve().parents[1]
PASTA = RAIZ / "docs/evidencias-arena"
PASTA.mkdir(parents=True, exist_ok=True)
anterior = bpy.context.window.scene
cena = bpy.data.scenes.new("VRmed_Cranio_Comparacao")
try:
    bpy.context.window.scene = cena
    bpy.ops.import_scene.gltf(filepath=str(RAIZ / "public/models/organs/cranio.glb"))
    cena.frame_set(0)
    objetos = list(cena.objects)
    malhas = [o for o in objetos if o.type == "MESH"]
    fechados = {o.name: o.matrix_world.copy() for o in objetos}
    cena.frame_set(96)
    movidos = [o.name for o in objetos if any(abs(a - b) > 1e-5 for linha_a, linha_b in zip(o.matrix_world, fechados[o.name]) for a, b in zip(linha_a, linha_b))]
    cena.frame_set(0)
    normais_invalidas = 0
    for obj in malhas:
        normais = np.empty(len(obj.data.vertices) * 3, dtype=np.float32)
        obj.data.vertices.foreach_get("normal", normais)
        normais = normais.reshape((-1, 3))
        normais_invalidas += int(np.count_nonzero(~np.isfinite(normais).all(axis=1) | (np.linalg.norm(normais, axis=1) < .1)))
    pontos = [o.matrix_world @ Vector(v) for o in malhas for v in o.bound_box]
    minimo = Vector([min(v[i] for v in pontos) for i in range(3)])
    maximo = Vector([max(v[i] for v in pontos) for i in range(3)])
    escala = 2 / max(maximo - minimo)
    centro = (minimo + maximo) / 2
    raiz = bpy.data.objects.new("Normalização apenas da bancada", None)
    cena.collection.objects.link(raiz)
    for obj in objetos:
        if obj.parent is None:
            obj.parent = raiz
    raiz.scale = (escala,) * 3
    raiz.location = -centro * escala
    camera_data = bpy.data.cameras.new("Comparação fixa")
    camera = bpy.data.objects.new("Comparação fixa", camera_data)
    cena.collection.objects.link(camera)
    camera.location = (2.4, -4.0, 1.8)
    camera.rotation_euler = (-camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera_data.lens = 58
    cena.camera = camera
    mundo = bpy.data.worlds.new("Estúdio neutro")
    mundo.use_nodes = True
    fundo = next(n for n in mundo.node_tree.nodes if n.type == "BACKGROUND")
    fundo.inputs[0].default_value = (.055, .08, .10, 1)
    fundo.inputs[1].default_value = .35
    cena.world = mundo
    for nome, pos, energia, tamanho in (("Chave", (-3,-4,5), 380, 3), ("Recorte", (3,2,3), 300, 2)):
        luz_data = bpy.data.lights.new(nome, "AREA")
        luz_data.energy = energia
        luz_data.shape = "DISK"
        luz_data.size = tamanho
        luz = bpy.data.objects.new(nome, luz_data)
        cena.collection.objects.link(luz)
        luz.location = pos
        luz.rotation_euler = (-luz.location).to_track_quat('-Z', 'Y').to_euler()
    cena.render.engine = 'BLENDER_EEVEE'
    cena.render.resolution_x = 1000
    cena.render.resolution_y = 800
    cena.render.resolution_percentage = 100
    cena.render.image_settings.file_format = 'PNG'
    cena.render.filepath = str(PASTA / "blender-cranio-original.png")
    bpy.ops.render.render(write_still=True)
    # Material uniforme de osso, sem inventar sulcos ou pintar anatomia inexistente.
    for obj in malhas:
        dente = "teeth" in obj.name.lower()
        mat = bpy.data.materials.new("Osso seco / dentes" if dente else "Osso seco / cortical")
        mat.use_nodes = True
        no = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        no.inputs["Base Color"].default_value = (.62,.57,.46,1) if dente else (.50,.44,.34,1)
        no.inputs["Roughness"].default_value = .38 if dente else .72
        no.inputs["Metallic"].default_value = 0
        obj.data.materials.clear()
        obj.data.materials.append(mat)
    cena.render.filepath = str(PASTA / "blender-cranio-osso.png")
    bpy.ops.render.render(write_still=True)
    cena.frame_set(96)
    pontos_abertos = [o.matrix_world @ Vector(v) for o in malhas for v in o.bound_box]
    minimo_aberto = Vector([min(v[i] for v in pontos_abertos) for i in range(3)])
    maximo_aberto = Vector([max(v[i] for v in pontos_abertos) for i in range(3)])
    centro_aberto = (minimo_aberto + maximo_aberto) / 2
    distancia_aberta = max(maximo_aberto - minimo_aberto) * 2
    camera.location = centro_aberto + Vector((.45, -.75, .35)).normalized() * distancia_aberta
    camera.rotation_euler = (centro_aberto - camera.location).to_track_quat('-Z', 'Y').to_euler()
    cena.render.filepath = str(PASTA / "blender-cranio-aberto.png")
    bpy.ops.render.render(write_still=True)
    result = {"malhas": len(malhas), "uv_malhas": sum(bool(o.data.uv_layers) for o in malhas),
              "normais_nulas_ou_nao_finitas": normais_invalidas,
              "transformacoes_negativas": sum(o.matrix_world.determinant() < 0 for o in malhas),
              "nos_movidos_na_abertura": len(movidos), "frames_comparados": [0,96],
              "dimensoes_fechado_originais": list(maximo - minimo),
              "geometria_modificada": False, "arquivo_original_modificado": False,
              "limite": "Normais invertidas localmente e fidelidade anatômica exigem revisão especializada; verificação numérica não certifica anatomia."}
    (PASTA / "auditoria-cranio-blender.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
finally:
    bpy.context.window.scene = anterior
