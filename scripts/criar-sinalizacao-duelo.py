"""Autoria via Blender MCP: cena isolada, placas métricas, atlas local e três malhas.

Antes: executar preparar-texturas-sinalizacao.py no Python de autoria.
Nenhuma cena, seleção ou objeto preexistente é apagado ou salvo por este script.
"""
import bpy
import json
import math
from pathlib import Path
from mathutils import Vector

RAIZ = Path(__file__).resolve().parents[1]
CONFIG = json.loads((RAIZ / "lib/sinalizacao-duelo.json").read_text(encoding="utf-8"))
LAYOUT_ESCOLA = json.loads((RAIZ / "lib/escola-layout.json").read_text(encoding="utf-8"))
TRABALHO = RAIZ / "tmp_sinalizacao"
anterior = bpy.context.window.scene
resumo = []


def ponto(p):
    return Vector((p[0], -p[2], p[1]))


def material(nome, cor, metal=0, rugosidade=.8):
    rgb = [int(cor[i:i+2], 16) / 255 for i in (1, 3, 5)]
    linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb]
    mat = bpy.data.materials.new(nome)
    mat.use_nodes = True
    shader = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    shader.inputs["Base Color"].default_value = (*linear, 1)
    shader.inputs["Metallic"].default_value = metal
    shader.inputs["Roughness"].default_value = rugosidade
    mat.diffuse_color = (*linear, 1)
    mat.use_backface_culling = True
    return mat


try:
    for sala, placas in CONFIG["placas"].items():
        if sala not in globals().get("SALAS", ("hospital", "escola")):
            continue
        cena = bpy.data.scenes.new(f"VRmed_Placas_{sala}")
        cena.unit_settings.system = "METRIC"
        bpy.context.window.scene = cena
        cores = CONFIG["acabamentos"][sala]
        metal = material(f"{sala}_Ferragens", cores["metal"], .45, .48)
        contato = material(f"{sala}_Junta", "#172625", 0, 1)
        tinta = material(f"{sala}_Impressao", "#ffffff", 0, .82)
        atlas = json.loads((TRABALHO / f"atlas-{sala}.json").read_text())
        imagem = bpy.data.images.load(str(TRABALHO / f"inscricoes-{sala}.png"), check_existing=False)
        imagem.pack()
        tex = tinta.node_tree.nodes.new("ShaderNodeTexImage")
        tex.image = imagem
        shader = next(n for n in tinta.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        tinta.node_tree.links.new(tex.outputs["Color"], shader.inputs["Base Color"])

        for placa, celula in zip(placas, atlas["regioes"]):
            w, h = placa["largura"], placa["altura"]
            ang = placa.get("giro", 0)
            c, s = math.cos(ang), math.sin(ang)
            px, py, pz = placa["posicao"]
            if sala == "escola" and placa["id"] == "lousa":
                py += LAYOUT_ESCOLA["elevacaoLousa"]

            def pos(x, y, z):
                return ponto((px + c*x + s*z, py+y, pz-s*x+c*z))

            def caixa(nome, p, dimensoes, mat, borda=0):
                bpy.ops.mesh.primitive_cube_add(size=1, location=pos(*p))
                obj = bpy.context.object
                obj.name = nome
                obj.dimensions = (dimensoes[0], dimensoes[2], dimensoes[1])
                bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
                obj.rotation_euler.z = ang
                obj.data.materials.append(mat)
                if borda:
                    mod = obj.modifiers.new("Borda usinada", "BEVEL")
                    mod.width, mod.segments = borda, 2
                    bpy.ops.object.modifier_apply(modifier=mod.name)
                return obj

            caixa(placa["id"] + " / carcaça", (0, 0, 0), (w, h, .053), metal, .004)
            caixa(placa["id"] + " / junta de contato", (0, 0, -.029), (w+.012, h+.012, .012), contato, .003)
            for lado in (-1, 1):
                bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=.007, depth=.006, location=pos(lado*(w/2-.012), 0, .027))
                obj = bpy.context.object
                obj.name = "Fixador da placa"
                obj.rotation_euler = (pos(0, 0, 1)-pos(0, 0, 0)).to_track_quat("Z", "Y").to_euler()
                obj.data.materials.append(metal)
                if placa.get("apoios"):
                    caixa("Suporte encaixado", (lado*w*.35, -h/2-.045, -.014), (.022, .17, .028), metal, .002)
            fw, fh, raio = w-.044, h-.044, .008
            vertices, uvs = [], []
            # Contorno anti-horário frontal; normais voltadas para o leitor.
            for cx, cy, inicio in ((fw/2-raio, fh/2-raio, 0), (-fw/2+raio, fh/2-raio, 90), (-fw/2+raio, -fh/2+raio, 180), (fw/2-raio, -fh/2+raio, 270)):
                for j in range(4):
                    a = math.radians(inicio + j*30)
                    x, y = cx+raio*math.cos(a), cy+raio*math.sin(a)
                    vertices.append(pos(x, y, .0273))
                    u, v = x/fw+.5, y/fh+.5
                    uvs.append(((celula["x"]+8+u*(celula["largura"]-16))/atlas["largura"], 1-(celula["y"]+8+(1-v)*(celula["altura"]-16))/atlas["altura"]))
            malha = bpy.data.meshes.new("Face impressa")
            malha.from_pydata(vertices, [], [list(range(len(vertices)))])
            malha.materials.append(tinta)
            uv = malha.uv_layers.new(name="Inscricoes")
            for loop in malha.loops:
                uv.data[loop.index].uv = uvs[loop.vertex_index]
            obj = bpy.data.objects.new(placa["id"] + " / impressão", malha)
            cena.collection.objects.link(obj)

        # Agrupa por material: não existe um objeto/draw call para cada letra.
        for mat in (metal, contato, tinta):
            bpy.ops.object.select_all(action="DESELECT")
            objetos = [o for o in cena.objects if o.type == "MESH" and o.data.materials[0] == mat]
            for o in objetos:
                o.select_set(True)
            bpy.context.view_layer.objects.active = objetos[0]
            bpy.ops.object.join()
            obj = bpy.context.object
            obj.name = mat.name
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
            obj.data.calc_loop_triangles()
        destino = RAIZ / f"public/models/props/sinalizacao-{sala}.glb"
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.export_scene.gltf(filepath=str(destino), export_format="GLB", use_selection=True,
            use_active_scene=True, export_animations=False, export_cameras=False, export_lights=False,
            export_yup=True, export_image_format="AUTO", export_extras=False)
        bpy.data.libraries.write(str(TRABALHO / f"sinalizacao-{sala}.blend"), {cena})
        resumo.append(dict(sala=sala, cena=cena.name, arquivo=str(destino), bytes=destino.stat().st_size,
            placas=len(placas), malhas=len(cena.objects), materiais=3,
            triangulos=sum(len(o.data.loop_triangles) for o in cena.objects),
            atlas=[atlas["largura"], atlas["altura"]], unidade="metro", animacoes=0, draco=False))
finally:
    bpy.context.window.scene = anterior
result = {"exportacoes": resumo, "cena_original_preservada": bpy.context.scene.name}
print(json.dumps(result, ensure_ascii=False))
