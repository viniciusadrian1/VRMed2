"""Entorno autoral em metros: peças com acabamento, agrupadas por material para WebXR."""
import bpy
import json
from pathlib import Path
from mathutils import Vector

RAIZ = Path(__file__).resolve().parents[1]
DESTINO = RAIZ / "public/models/props/entorno-arena.glb"
anterior = bpy.context.window.scene
cena = bpy.data.scenes.new("VRmed_Entorno_Autoral")

def material(nome, cor, metal=0, rough=0.6, emissao=0):
    mat = bpy.data.materials.new(nome)
    mat.diffuse_color = (*cor, 1)
    mat.use_nodes = True
    shader = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    shader.inputs["Base Color"].default_value = (*cor, 1)
    shader.inputs["Metallic"].default_value = metal
    shader.inputs["Roughness"].default_value = rough
    if emissao:
        shader.inputs["Emission Color"].default_value = (*cor, 1)
        shader.inputs["Emission Strength"].default_value = emissao
    return mat

esmalte = material("Entorno_Esmalte", (0.39, 0.49, 0.47), 0.1, 0.48)
marfim = material("Entorno_Marfim", (0.68, 0.70, 0.61), 0.05, 0.58)
petroleo = material("Entorno_Petroleo", (0.025, 0.069, 0.083), 0.15)
metal = material("Entorno_Metal", (0.26, 0.34, 0.37), 0.62, 0.36)
escuro = material("Entorno_Borracha", (0.011, 0.023, 0.028), 0, 0.78)
ciano = material("Entorno_Ciano", (0.075, 0.44, 0.51), 0.05, 0.45, 0.35)
ambar = material("Entorno_Ambar", (0.66, 0.34, 0.095), 0, 0.58)
vidro = material("Entorno_Visor_Opaco", (0.023, 0.055, 0.067), 0.3, 0.23)
materiais = [esmalte, marfim, petroleo, metal, escuro, ciano, ambar, vidro]

def ponto(pos):
    # Entrada na convenção Three.js: Y para cima e -Z à frente.
    return Vector((pos[0], -pos[2], pos[1]))

def caixa(nome, pos, tam, mat, borda=0.015):
    bpy.ops.mesh.primitive_cube_add(size=1, location=ponto(pos))
    obj = bpy.context.object
    obj.name = nome
    obj.dimensions = (tam[0], tam[2], tam[1])
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    if borda:
        mod = obj.modifiers.new("Arestas acabadas", "BEVEL")
        mod.width = min(borda, min(tam) * 0.3)
        mod.segments = 2
        bpy.ops.object.modifier_apply(modifier=mod.name)
    return obj

def tubo(nome, inicio, fim, raio, mat, lados=12):
    a, b = ponto(inicio), ponto(fim)
    bpy.ops.mesh.primitive_cylinder_add(vertices=lados, radius=raio, depth=(b-a).length, location=(a+b)/2)
    obj = bpy.context.object
    obj.name = nome
    obj.rotation_euler = (b-a).to_track_quat("Z", "Y").to_euler()
    obj.data.materials.append(mat)
    for pol in obj.data.polygons:
        pol.use_smooth = len(pol.vertices) == 4
    return obj

def cabo(nome, pontos, raio, mat):
    curva = bpy.data.curves.new(nome, "CURVE")
    curva.dimensions = "3D"
    curva.resolution_u = 6
    curva.bevel_depth = raio
    curva.bevel_resolution = 1
    spline = curva.splines.new("BEZIER")
    spline.bezier_points.add(len(pontos)-1)
    for vertice, pos in zip(spline.bezier_points, pontos):
        vertice.co = ponto(pos)
        vertice.handle_left_type = vertice.handle_right_type = "AUTO"
    obj = bpy.data.objects.new(nome, curva)
    cena.collection.objects.link(obj)
    curva.materials.append(mat)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.convert(target="MESH")
    obj.select_set(False)

def texto(conteudo, pos, tamanho=0.07, mat=marfim):
    dados = bpy.data.curves.new("Sinalização", "FONT")
    dados.body = conteudo
    dados.align_x = "CENTER"
    dados.align_y = "CENTER"
    dados.size = tamanho
    dados.resolution_u = 2
    obj = bpy.data.objects.new(conteudo, dados)
    cena.collection.objects.link(obj)
    obj.location = ponto(pos)
    obj.rotation_euler = (1.57079632679, 0, 0)
    dados.materials.append(mat)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target="MESH")
    obj.select_set(False)

def rodinhas(x, z, largura, fundo):
    for dx in (-largura/2, largura/2):
        for dz in (-fundo/2, fundo/2):
            tubo("Rodízio", (x+dx-.03, .09, z+dz), (x+dx+.03, .09, z+dz), .075, escuro)
            caixa("Garfo do rodízio", (x+dx,.16,z+dz), (.075,.08,.11), metal)

try:
    bpy.context.window.scene = cena
    # Baías laterais: molduras, divisões de material e armários com ferragens reais.
    for x, nome in ((-3.32, "PREPARO"), (3.32, "SUPRIMENTOS")):
        caixa("Baía técnica", (x,1.8,-4.43), (2.15,3.38,.16), petroleo, .05)
        caixa("Cabeçalho da baía", (x,3.17,-4.31), (1.95,.28,.12), escuro)
        texto(nome, (x,3.18,-4.235), .11)
        caixa("Rodapé recuado", (x,.09,-3.95), (1.76,.18,.72), escuro)
        caixa("Armário inferior", (x,.51,-3.96), (1.84,.78,.77), esmalte, .035)
        caixa("Tampo de preparo", (x,.94,-3.94), (1.96,.11,.92), marfim, .045)
        for dx in (-.46,.46):
            caixa("Porta do armário", (x+dx,.52,-3.553), (.87,.70,.045), petroleo)
            caixa("Friso da porta", (x+dx,.51,-3.523), (.76,.57,.025), esmalte)
            caixa("Puxador escovado", (x+dx,.78,-3.483), (.27,.028,.04), metal, .012)
        caixa("Painel perfurado", (x,1.4,-4.28), (1.91,.65,.04), esmalte)
        for dx in (-.75,-.5,-.25,0,.25,.5,.75):
            caixa("Ranhura técnica", (x+dx,1.43,-4.248), (.018,.37,.006), petroleo, 0)
        caixa("Armário superior", (x,2.33,-4.18), (1.88,.94,.48), esmalte, .035)
        for dx in (-.46,.46):
            caixa("Porta superior", (x+dx,2.33,-3.929), (.85,.81,.035), petroleo)
            caixa("Visor acetinado", (x+dx,2.4,-3.904), (.66,.51,.015), vidro)
            caixa("Reflexo do visor", (x+dx-.22,2.4,-3.893), (.028,.43,.007), metal, 0)
            caixa("Alça vertical", (x+dx+.32,2.19,-3.884), (.024,.21,.035), metal)
        caixa("Iluminação sob armário", (x,1.855,-4.00), (1.7,.024,.23), ciano, .005)
    # Cuba e torneira, recipientes separados em suportes; sem anatomia fictícia.
    caixa("Cuba rebaixada", (-3.52,1.003,-3.88), (.63,.018,.44), escuro)
    caixa("Borda da cuba", (-3.52,1.015,-3.88), (.54,.018,.34), metal)
    cabo("Torneira", [(-3.52,1.00,-4.17),(-3.52,1.3,-4.16),(-3.52,1.34,-3.99),(-3.52,1.2,-3.98)], .018, metal)
    for x, z in ((-2.73,-3.88),(2.78,-3.97),(3.12,-3.97),(3.55,-3.97)):
        tubo("Frasco de preparo", (x,1.01,z), (x,1.24,z), .075, marfim)
        tubo("Tampa dosadora", (x,1.24,z), (x,1.29,z), .055, petroleo)
        caixa("Faixa do frasco", (x,1.12,z+.07), (.085,.08,.015), ciano)
    caixa("Bandeja de amostras", (3.3,1.015,-3.6), (1.2,.035,.24), metal)
    for i in range(7):
        x = 2.85 + i*.15
        tubo("Tubo de treinamento", (x,1.05,-3.6), (x,1.19,-3.6), .026, marfim, 8)
        tubo("Tampa de tubo", (x,1.19,-3.6), (x,1.22,-3.6), .03, ambar if i%3==0 else ciano, 8)
    # Carrinho autoral: rodas, trilhos, gavetas e bandeja com instrumentos legíveis.
    x,z = -2.84,-1.32
    rodinhas(x,z,.70,.48)
    caixa("Base carrinho", (x,.23,z), (.85,.11,.66), petroleo, .04)
    caixa("Gaveteiro móvel", (x,.54,z), (.75,.51,.55), esmalte, .04)
    for y in (.40,.57,.72):
        caixa("Gaveta móvel", (x,y,z+.29), (.63,.12,.04), petroleo)
        caixa("Alça gaveta", (x,y+.014,z+.323), (.23,.024,.025), metal)
    caixa("Tampo móvel", (x,.85,z), (.89,.08,.68), marfim, .05)
    for dx in (-.39,.39):
        tubo("Trilho de bandeja", (x+dx,.91,z-.24), (x+dx,.91,z+.24), .016, metal)
    caixa("Bandeja de instrumentos", (x,.91,z), (.62,.03,.38), metal)
    for dx in (-.18,0,.17):
        tubo("Instrumento de treino", (x+dx,.937,z-.1), (x+dx+.03,.937,z+.12), .009, metal, 8)
        caixa("Cabo do instrumento", (x+dx+.02,.944,z+.06), (.025,.018,.10), petroleo, .004)
    cabo("Alça de transporte", [(x-.4,.74,z-.27),(x-.5,.91,z-.27),(x-.5,.91,z+.27),(x-.4,.74,z+.27)], .02, metal)
    # Estação de aquisição estilizada; visor abstrato rotulado, sem dados clínicos.
    x,z = 2.96,-1.82
    rodinhas(x,z,.64,.58)
    caixa("Base equipamento", (x,.23,z), (.83,.17,.77), petroleo, .07)
    caixa("Coluna equipamento", (x,.69,z-.04), (.39,.79,.39), esmalte, .06)
    caixa("Faixa lateral", (x+.204,.67,z-.04), (.025,.53,.25), ciano)
    caixa("Mesa de controle", (x,1.02,z+.05), (.83,.12,.58), marfim, .05)
    caixa("Teclado", (x,1.09,z+.13), (.51,.025,.20), escuro)
    for dx in (-.17,-.085,0,.085,.17):
        caixa("Teclas grandes", (x+dx,1.109,z+.1), (.054,.014,.1), esmalte, .003)
    tubo("Eixo monitor", (x,1.05,z-.17), (x,1.3,z-.17), .055, metal)
    caixa("Monitor equipamento", (x,1.52,z-.17), (.84,.59,.12), petroleo, .045)
    caixa("Tela equipamento", (x,1.52,z-.102), (.71,.46,.018), vidro)
    texto("SIMULAÇÃO", (x,1.68,z-.088), .054, ciano)
    for i in range(3):
        caixa("Interface abstrata", (x-.14,1.55-i*.072,z-.085), (.28-i*.05,.018,.006), ciano, 0)
    caixa("Janela do visor", (x+.19,1.46,z-.086), (.22,.22,.006), petroleo, .012)
    cabo("Cabo da sonda", [(x+.34,1.06,z),(x+.52,.57,z+.07),(x+.63,.59,z+.04),(x+.54,1.15,z)], .013, escuro)
    caixa("Sonda de treinamento", (x+.52,1.21,z), (.11,.23,.09), marfim, .035)
    # Fechamento arquitetônico: dutos, arcos laterais e janela técnica opaca.
    for x in (-4.4,4.4):
        caixa("Pilar lateral", (x,1.8,-2.8), (.17,3.6,.22), petroleo, .035)
        caixa("Duto longitudinal", (x,3.31,0), (.22,.19,8.2), metal, .035)
        for z in (-2.7,0,2.7):
            caixa("Abraçadeira do duto", (x,3.31,z), (.25,.22,.065), petroleo)
    for x in (-3.4,3.4):
        caixa("Ventilação", (x,3.12,-4.29), (1.25,.025,.03), metal, 0)
    for z in (-2.8,.2,3.15):
        caixa("Travessa do forro", (0,3.51,z), (8.75,.12,.11), petroleo, .025)
        for x in (-3.05,3.05):
            caixa("Cassete de ventilação", (x,3.49,z+.56), (.74,.12,.76), metal, .035)
            for i in range(7):
                caixa("Aleta de ventilação", (x,3.415,z+.32+i*.08), (.60,.025,.029), escuro, .004)
    caixa("Moldura janela lateral", (-4.47,2.17,-.15), (.15,1.31,2.22), metal, .04)
    caixa("Vidro técnico opaco", (-4.37,2.17,-.15), (.045,1.12,2.02), vidro)
    for z in (-.8,-.15,.5):
        caixa("Montante janela", (-4.332,2.17,z), (.032,1.1,.035), esmalte, .004)
    caixa("Reflexo janela", (-4.33,2.48,-.15), (.015,.024,1.94), ciano, 0)
    # Porta de apoio na parede de fundo atrás do usuário, sem mudar circulação.
    caixa("Portal de apoio", (0,1.25,4.43), (1.85,2.5,.18), petroleo, .035)
    for x in (-.42,.42):
        caixa("Folha de porta", (x,1.21,4.31), (.81,2.32,.09), esmalte, .025)
        caixa("Visor da porta", (x,1.64,4.248), (.45,.65,.015), vidro)
        caixa("Barra da porta", (x,.98,4.21), (.57,.04,.05), metal)
    # Une decoração por material: poucos draw calls mesmo com muitas peças.
    for mat in materiais:
        bpy.ops.object.select_all(action="DESELECT")
        grupo = [obj for obj in cena.objects if obj.type == "MESH" and obj.data.materials[0] == mat]
        if not grupo:
            continue
        for obj in grupo:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = grupo[0]
        bpy.ops.object.join()
        grupo[0].name = mat.name
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(filepath=str(DESTINO), export_format="GLB", use_selection=True,
                              use_active_scene=True, export_animations=False, export_yup=True)
    triangulos = 0
    for obj in cena.objects:
        obj.data.calc_loop_triangles()
        triangulos += len(obj.data.loop_triangles)
    result = {"arquivo": str(DESTINO), "bytes": DESTINO.stat().st_size,
              "malhas": len(cena.objects), "materiais": len(materiais), "triangulos": triangulos,
              "animacoes": 0, "texturas": 0, "unidade": "metro", "draco": False}
    print(json.dumps(result, ensure_ascii=False))
finally:
    bpy.context.window.scene = anterior
