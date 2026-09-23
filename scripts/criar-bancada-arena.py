"""Prop autoral do VRmed. Executar pelo Blender MCP; preserva a cena aberta."""
import bpy
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DESTINO = RAIZ / "public/models/props/bancada-arena.glb"
anterior = bpy.context.window.scene
cena = bpy.data.scenes.new("VRmed_Bancada_Autoral")

def material(nome, cor, metal=0.0, rough=0.6):
    mat = bpy.data.materials.new(nome)
    mat.diffuse_color = (*cor, 1)
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*cor, 1)
    bsdf.inputs["Metallic"].default_value = metal
    bsdf.inputs["Roughness"].default_value = rough
    return mat

marfim = material("Arena_Esmalte_Marfim", (0.64, 0.70, 0.67), 0.1, 0.5)
azul = material("Arena_Petroleo", (0.022, 0.07, 0.09), 0.2)
metal = material("Arena_Aluminio_Acetinado", (0.22, 0.30, 0.32), 0.65, 0.4)
borracha = material("Arena_Borracha", (0.013, 0.021, 0.026))
difusor = material("Arena_Difusor", (0.8, 0.74, 0.59))
bsdf = next(n for n in difusor.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
bsdf.inputs["Emission Color"].default_value = (0.85, 0.78, 0.62, 1)
bsdf.inputs["Emission Strength"].default_value = 0.55

def caixa(nome, pos, tam, mat, bevel=0.025):
    bpy.ops.mesh.primitive_cube_add(size=1, location=pos)
    obj = bpy.context.object
    obj.name = nome
    obj.dimensions = tam
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    mod = obj.modifiers.new("Bordas arredondadas", "BEVEL")
    mod.width = bevel
    mod.segments = 2
    bpy.ops.object.modifier_apply(modifier=mod.name)
    for face in obj.data.polygons:
        face.use_smooth = False
    return obj

try:
    bpy.context.window.scene = cena
    caixa("Rodape", (0, 0, 0.09), (1.05, 0.87, 0.18), borracha, 0.07)
    caixa("Corpo", (0, 0, 0.43), (0.98, 0.82, 0.64), azul, 0.07)
    caixa("Tampo", (0, 0, 0.79), (1.22, 1.07, 0.13), marfim, 0.06)
    caixa("Superficie_de_estudo", (0, 0, 0.854), (0.96, 0.85, 0.014), azul, 0.01)
    for altura in (0.26, 0.44):
        caixa("Gaveta", (0, -0.416, altura), (0.8, 0.025, 0.15), marfim, 0.015)
        caixa("Puxador", (0, -0.449, altura + 0.018), (0.29, 0.037, 0.025), metal, 0.008)
    # Luminária articulada: difusores grandes e legíveis, sem luzes extras no GLB.
    caixa("Coluna", (-0.44, 0.40, 1.55), (0.075, 0.08, 1.50), metal)
    caixa("Braco_superior", (-0.22, 0.23, 2.31), (0.52, 0.40, 0.085), metal)
    caixa("Cabeca_luminaria", (0, 0.10, 2.30), (0.73, 0.53, 0.14), marfim, 0.065)
    for x in (-0.21, 0, 0.21):
        caixa("Difusor", (x, 0.10, 2.222), (0.15, 0.35, 0.017), difusor, 0.01)
    for x in (-0.52, 0.52):
        caixa("Alca_lateral", (x, 0, 0.65), (0.055, 0.52, 0.055), metal)
    # Junta apenas decoração por material. Nenhum órgão é simplificado.
    for mat in (marfim, azul, metal, borracha, difusor):
        bpy.ops.object.select_all(action="DESELECT")
        grupo = [obj for obj in cena.objects if obj.type == "MESH" and obj.data.materials[0] == mat]
        for obj in grupo:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = grupo[0]
        bpy.ops.object.join()
        grupo[0].name = mat.name
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(filepath=str(DESTINO), export_format="GLB", use_selection=True, use_active_scene=True,
                              export_animations=False, export_yup=True)
    triangulos = 0
    for obj in cena.objects:
        obj.data.calc_loop_triangles()
        triangulos += len(obj.data.loop_triangles)
    result = {"arquivo": str(DESTINO), "bytes": DESTINO.stat().st_size,
              "objetos": len(cena.objects), "triangulos": triangulos,
              "materiais": 5, "animacoes": 0, "unidade": "metro", "draco": False,
              "autoria": "VRmed, geração procedural própria"}
    print(json.dumps(result, ensure_ascii=False))
finally:
    bpy.context.window.scene = anterior
