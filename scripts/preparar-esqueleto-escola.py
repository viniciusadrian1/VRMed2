"""Extrai ossos e dentes do acervo, sem simplificação; renderiza alternativa leve."""
import bpy
import json
from pathlib import Path
from mathutils import Vector

RAIZ=Path(__file__).resolve().parents[1]
PASTA=RAIZ/'public/models/props'
anterior=bpy.context.window.scene
cena=bpy.data.scenes.new('VRmed_Osteologia_Original')
try:
    bpy.context.window.scene=cena
    bpy.ops.import_scene.gltf(filepath=str(RAIZ/'public/models/systems/arthrology.glb'))
    selecionados=[]
    for o in list(cena.objects):
        if o.type!='MESH' or not o.data.materials: continue
        nome=o.data.materials[0].name
        if nome.split('.')[0] in ('Bone','Teeth'):
            o.data.calc_loop_triangles()
            if not o.data.loop_triangles: continue
            mundo=o.matrix_world.copy(); o.parent=None; o.matrix_world=mundo
            m=bpy.data.materials.new('Osso de estudo' if nome.startswith('Bone') else 'Dentes de estudo')
            m.use_nodes=True
            shader=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
            shader.inputs['Base Color'].default_value=(.68,.61,.46,1)
            shader.inputs['Roughness'].default_value=.72 if nome.startswith('Bone') else .38
            o.data.materials.clear(); o.data.materials.append(m)
            selecionados.append(o)
    assert len(selecionados)==3, 'O acervo mudou: rever os ossos e dentes antes de exportar.'
    triangulos=sum(len(o.data.loop_triangles) for o in selecionados)
    assert triangulos==158090, 'Não alterar a geometria anatômica silenciosamente.'
    for o in list(cena.objects):
        if o not in selecionados: cena.collection.objects.unlink(o) if o.name in cena.collection.objects else None
    bpy.ops.object.select_all(action='DESELECT')
    for o in selecionados: o.select_set(True)
    bpy.context.view_layer.objects.active=selecionados[0]
    arquivo=PASTA/'esqueleto-estudo.glb'
    bpy.ops.export_scene.gltf(filepath=str(arquivo),export_format='GLB',use_selection=True,
        use_active_scene=True,export_animations=False,export_yup=True,
        export_draco_mesh_compression_enable=True,export_draco_position_quantization=16)
    # A prancha é uma renderização da anatomia original, não uma malha inventada.
    for o in cena.objects: o.hide_render=o not in selecionados
    cena.world=bpy.data.worlds.new('Fundo osteologia'); cena.world.use_nodes=True
    fundo=next(n for n in cena.world.node_tree.nodes if n.type=='BACKGROUND')
    fundo.inputs[0].default_value=(.023,.054,.039,1); fundo.inputs[1].default_value=.45
    bpy.ops.object.camera_add(location=(0,-4,.87)); cam=bpy.context.object
    cam.rotation_euler=(Vector((0,0,.87))-cam.location).to_track_quat('-Z','Y').to_euler()
    cam.data.type='ORTHO'; cam.data.ortho_scale=1.88; cena.camera=cam
    for pos,energia,tamanho in [((-2,-3,3),350,3),((2,-1,1),100,2)]:
        bpy.ops.object.light_add(type='AREA',location=pos); l=bpy.context.object
        l.data.energy=energia; l.data.shape='DISK'; l.data.size=tamanho
        l.rotation_euler=(Vector((0,0,.9))-l.location).to_track_quat('-Z','Y').to_euler()
    cena.render.engine='CYCLES'; cena.cycles.samples=24
    cena.render.resolution_x=512; cena.render.resolution_y=1024; cena.render.resolution_percentage=100
    cena.render.image_settings.file_format='PNG'; cena.render.film_transparent=False
    cena.render.filepath=str(PASTA/'esqueleto-prancha.png')
    bpy.ops.render.render(write_still=True)
    print(json.dumps({'arquivo':str(arquivo),'bytes':arquivo.stat().st_size,'triangulos':triangulos,'simplificado':False}))
finally:
    bpy.context.window.scene=anterior
