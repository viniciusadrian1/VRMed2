"""Sala autoral em metros. Execute no Blender; não modifica a cena aberta."""
import bpy
import json
import math
from pathlib import Path
from mathutils import Vector

RAIZ = Path(__file__).resolve().parents[1]
DESTINO = RAIZ / 'public/models/props/escola-medicina.glb'
LAYOUT = json.loads((RAIZ / 'lib/escola-layout.json').read_text(encoding='utf-8'))
anterior = bpy.context.window.scene
cena = bpy.data.scenes.new('VRmed_Escola_Medicina')

def material(nome, cor, rough=.65, metal=0, emissao=0):
    m = bpy.data.materials.new('Escola_' + nome)
    m.diffuse_color = (*cor, 1)
    m.use_nodes = True
    p = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    p.inputs['Base Color'].default_value = (*cor, 1)
    p.inputs['Roughness'].default_value = rough
    p.inputs['Metallic'].default_value = metal
    p.inputs['Emission Color'].default_value = (*cor, 1)
    p.inputs['Emission Strength'].default_value = emissao
    return m

parede = material('Parede', (.54,.58,.51), .95)
marfim = material('Marfim', (.76,.73,.63), .65)
madeira = material('Carvalho', (.30,.16,.074), .62)
escuro = material('Grafite', (.026,.040,.034), .74)
verde = material('Lousa', (.026,.068,.05), .88)
metal = material('Metal', (.27,.30,.29), .35, .65)
latao = material('Latao', (.38,.26,.10), .4, .55)
luz = material('Luz', (.7,.82,.79), .8, 0, .35)
tecido = material('Tecido', (.074,.13,.11), .98)
ambar = material('Identidade', (.66,.39,.14), .62)
materiais = [parede, marfim, madeira, escuro, verde, metal, latao, luz, tecido, ambar]

def p(v): return Vector((v[0], -v[2], v[1]))

def caixa(nome, pos, tamanho, mat, borda=.012):
    bpy.ops.mesh.primitive_cube_add(size=1, location=p(pos))
    o = bpy.context.object
    o.name = nome
    o.dimensions = (tamanho[0], tamanho[2], tamanho[1])
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(mat)
    if borda:
        b = o.modifiers.new('Acabamento de borda', 'BEVEL')
        b.width = min(borda, min(tamanho)*.3)
        b.segments = 2
        bpy.ops.object.modifier_apply(modifier=b.name)
    return o

def tubo(nome, a, b, r, mat, lados=12):
    a,b=p(a),p(b)
    bpy.ops.mesh.primitive_cylinder_add(vertices=lados, radius=r, depth=(b-a).length, location=(a+b)/2)
    o=bpy.context.object; o.name=nome
    o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler()
    o.data.materials.append(mat)
    for face in o.data.polygons: face.use_smooth=len(face.vertices)==4
    return o

def texto(txt, pos, size=.07, mat=marfim):
    d=bpy.data.curves.new(txt,'FONT'); d.body=txt; d.size=size
    d.align_x='CENTER'; d.align_y='CENTER'; d.resolution_u=2
    o=bpy.data.objects.new(txt,d); cena.collection.objects.link(o)
    o.location=p(pos); o.rotation_euler=(math.pi/2,0,0); d.materials.append(mat)
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
    bpy.context.view_layer.objects.active=o; bpy.ops.object.convert(target='MESH')

def livro(x,y,z,w=.12,cor=ambar):
    caixa('Capa de atlas', (x,y,z),(w,.25,.19),cor,.006)
    caixa('Lombada do atlas', (x,y,z+.103),(w*.75,.016,.012),marfim,.002)

def mesa(x,z):
    caixa('Tampo de estudo',(x,.76,z),(LAYOUT['mesaLargura'],.07,LAYOUT['mesaProfundidade']),madeira,.025)
    for dx in (-.59,.59):
        for dz in (-.23,.23): tubo('Pé tubular',(x+dx,.04,z+dz),(x+dx,.73,z+dz),.022,metal)
    caixa('Caderno',(x-.25,.806,z),(.27,.023,.22),marfim,.005)

def posto(x, cor):
    # Demarcação rente ao piso, não um degrau; centro livre para ficar em pé.
    z = LAYOUT['postoZ']
    for dx in (-.38,.38):
        for dz in (-.38,.38):
            caixa('Demarcação do posto',(x+dx,.007,z+dz),(.18,.003,.018),cor,0)
            caixa('Demarcação do posto',(x+dx,.007,z+dz),(.018,.003,.18),cor,0)
    mesa(x,z-LAYOUT['mesaRecuo'])

try:
    bpy.context.window.scene=cena
    # Sala fechada em 360 graus; o corredor do jogador fica livre.
    caixa('Piso', (0,-.045,0), (7.2,.09,8), marfim)
    for x in range(-3,4): caixa('Junta piso',(x,.002,0),(.008,.004,8),parede,0)
    for z in range(-3,4): caixa('Junta piso',(0,.002,z),(7.2,.004,.008),parede,0)
    for z in (-3.92,3.92):
        caixa('Parede transversal',(0,1.6,z),(7.2,3.2,.12),parede)
        caixa('Rodapé',(0,.10,z+(.075 if z<0 else -.075)),(7.2,.20,.045),escuro)
    for x in (-3.54,3.54):
        caixa('Parede lateral',(x,1.6,0),(.12,3.2,8),parede)
        caixa('Lambril lateral',(x+(.072 if x<0 else -.072),.53,0),(.032,1.0,7.85),tecido)
        caixa('Friso lateral',(x+(.10 if x<0 else -.10),1.05,0),(.03,.035,7.85),madeira)
    caixa('Teto',(0,3.24,0),(7.2,.09,8),marfim)
    for z in (-2.8,0,2.8):
        caixa('Travessa acústica',(0,3.14,z),(7.0,.16,.1),madeira)
        for x in (-1.9,1.9):
            caixa('Luminária',(x,3.08,z),(.44,.09,1.15),escuro)
            caixa('Difusor',(x,3.025,z),(.37,.018,1.07),luz,.004)
    # Luz diurna sugerida por superfícies opacas: sem vidro/transparência cara.
    for z in (-1.8,1.35):
        caixa('Janela profunda',(-3.43,2.0,z),(.16,1.38,2.2),madeira,.025)
        caixa('Luz da janela',(-3.335,2.0,z),(.025,1.24,2.04),luz)
        for dz in (-.96,0,.96): caixa('Montante janela',(-3.30,2.0,z+dz),(.06,1.26,.035),escuro)
        caixa('Peitoril',(-3.27,1.29,z),(.32,.065,2.25),madeira)
    # Fundo do palco: painéis com absorção acústica, em vez de parede vazia.
    for x in (-2.8,-2.4,-2.0,-1.6,-1.2,-.8,.0,.4,.8,1.2,1.6,2.0,2.4,2.8):
        caixa('Painel acústico',(x,2.18,-3.82),(.22,1.7,.065),tecido)
    caixa('Letreiro departamento',(0,2.82,-3.70),(4.7,.32,.09),madeira)
    texto('VRmed  /  LABORATÓRIO DE ANATOMIA',(0,2.83,-3.64),.12)
    # Lousa nas coordenadas já testadas: alvo e escala de interação não mudam.
    caixa('Fundo da estação',(.36,.94,-1.40),(1.52,1.82,.12),madeira,.035)
    caixa('Moldura da lousa',(.36,1.18,-1.12),(1.35,1.02,.095),escuro,.035)
    caixa('Superfície de giz',(.36,1.18,-1.063),(1.23,.9,.018),verde,.018)
    caixa('Bandeja de giz',(.36,.65,-1.04),(1.40,.045,.20),madeira)
    caixa('Apagador',(.85,.69,-1.00),(.17,.035,.055),tecido)
    for x in (-.10,-.03,.04): tubo('Giz',(x,.68,-1.04),(x+.045,.68,-1.04),.008,marfim,8)
    caixa('Cabeçalho do desafio',(.36,1.80,-1.30),(1.5,.19,.08),verde)
    texto('DESAFIO DE ANATOMIA',(.36,1.81,-1.252),.058)
    # Bancada anatômica independente, ao lado da lousa.
    caixa('Rodapé bancada',(-.78,.08,-.95),(.82,.16,.63),escuro,.035)
    caixa('Bancada de demonstração',(-.78,.43,-.95),(.90,.70,.65),madeira,.04)
    caixa('Tampo anatômico',(-.78,.79,-.95),(1.04,.08,.77),marfim,.035)
    caixa('Área de demonstração',(-.78,.836,-.95),(.82,.012,.60),verde,.022)
    for y in (.27,.54):
        caixa('Frente gaveta',(-.78,y,-.603),(.78,.20,.02),tecido)
        caixa('Puxador bancada',(-.78,y+.04,-.581),(.27,.018,.025),latao)
    tubo('Haste luminária',(-1.29,.80,-1.13),(-1.29,2.02,-1.13),.018,metal)
    tubo('Braço luminária',(-1.29,2.02,-1.13),(-.80,2.02,-1.13),.018,metal)
    caixa('Luz de estudo',(-.80,2.00,-1.13),(.48,.045,.17),escuro)
    caixa('Difusor de estudo',(-.80,1.972,-1.13),(.40,.01,.13),luz,.003)
    # Vitrine anatômica. A anatomia vem de outro arquivo, nunca destas primitivas.
    x,z=1.82,-2.44
    caixa('Fundo vitrine',(x,1.12,z-.20),(1.04,2.12,.075),verde,.025)
    for dx in (-.57,.57): caixa('Montante vitrine',(x+dx,1.13,z),(.075,2.2,.50),madeira)
    for y in (.09,2.18): caixa('Vitrine base e topo',(x,y,z),(1.22,.10,.55),madeira)
    tubo('Suporte osteológico',(x,.15,z-.11),(x,1.90,z-.11),.012,metal)
    caixa('Base suporte',(x,.16,z),(.55,.03,.36),escuro)
    texto('OSTEOLOGIA',(x,2.36,z+.01),.085)
    # Bancada de microscopia e atlas na lateral direita.
    caixa('Armário de laboratório',(2.72,.48,.15),(1.1,.85,1.8),tecido,.04)
    caixa('Tampo laboratório',(2.72,.94,.15),(1.2,.08,1.93),marfim,.03)
    for z in (-.45,.35,.80):
        caixa('Porta de apoio',(2.105,.48,z),(.025,.68,.40),madeira)
        tubo('Puxador de apoio',(2.078,.68,z-.10),(2.078,.68,z+.10),.014,latao)
    for z in (-.42,.47):
        caixa('Base microscópio',(2.61,1.014,z),(.28,.05,.38),escuro,.025)
        tubo('Braço microscópio',(2.68,1.04,z-.11),(2.68,1.38,z-.16),.036,marfim)
        tubo('Cabeça microscópio',(2.68,1.38,z-.16),(2.53,1.48,z+.015),.045,escuro)
        tubo('Ocular',(2.53,1.48,z+.015),(2.49,1.53,z+.065),.028,metal)
        caixa('Platina microscópio',(2.56,1.15,z),(.22,.022,.18),metal,.004)
        tubo('Objetiva',(2.57,1.34,z),(2.57,1.23,z),.022,metal)
    for x in (-2.62,-2.18):
        caixa('Biblioteca de atlas',(x,1.1,-3.48),(.40,1.95,.34),madeira)
        for y in (.31,.83,1.35,1.87):
            caixa('Prateleira',(x,y,-3.32),(.37,.025,.36),marfim)
            for i in range(3): livro(x-.12+i*.12,y+.145,-3.29,.075,ambar if i%2 else tecido)
    texto('ATLAS / ESTUDO',(-2.4,2.20,-3.26),.075)
    # Dois competidores lado a lado; carteiras à frente, sem cadeiras nos corpos.
    posto(LAYOUT['adversarioX'], ambar)
    posto(LAYOUT['jogadorX'], luz)
    caixa('Marco porta',(0,1.10,3.79),(1.25,2.2,.10),madeira)
    caixa('Porta',(0,1.08,3.71),(1.10,2.09,.065),tecido)
    caixa('Visor porta',(0,1.65,3.665),(.38,.50,.02),luz)
    tubo('Maçaneta',(.35,1.03,3.62),(.48,1.03,3.62),.013,metal)
    # Agrupamento só do cenário, sem tocar geometria anatômica.
    for mat in materiais:
        objetos=[o for o in cena.objects if o.type=='MESH' and o.data.materials[0]==mat]
        if not objetos: continue
        bpy.ops.object.select_all(action='DESELECT')
        for o in objetos: o.select_set(True)
        bpy.context.view_layer.objects.active=objetos[0]; bpy.ops.object.join()
        objetos[0].name=mat.name
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(filepath=str(DESTINO), export_format='GLB', use_selection=True,
                              use_active_scene=True, export_animations=False, export_yup=True)
    for o in cena.objects: o.data.calc_loop_triangles()
    result={'bytes':DESTINO.stat().st_size,'malhas':len(cena.objects),
            'triangulos':sum(len(o.data.loop_triangles) for o in cena.objects),'materiais':len(materiais)}
    print(json.dumps(result))
finally:
    bpy.context.window.scene=anterior
