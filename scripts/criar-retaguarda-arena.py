"""Apoio hospitalar autoral em metros. Não altera o centro nem a cena aberta."""
import bpy
import json
import math
from pathlib import Path
from mathutils import Vector

RAIZ = Path(__file__).resolve().parents[1]
DESTINO = RAIZ / 'public/models/props/retaguarda-arena.glb'
anterior = bpy.context.window.scene
cena = bpy.data.scenes.new('VRmed_Retaguarda_Arena')

def material(nome, cor, rough=.65, metal=0, emissao=0):
    mat = bpy.data.materials.new('Retaguarda_' + nome)
    mat.diffuse_color = (*cor, 1)
    mat.use_nodes = True
    p = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    p.inputs['Base Color'].default_value = (*cor, 1)
    p.inputs['Roughness'].default_value = rough
    p.inputs['Metallic'].default_value = metal
    p.inputs['Emission Color'].default_value = (*cor, 1)
    p.inputs['Emission Strength'].default_value = emissao
    return mat

marfim = material('Marfim', (.68,.70,.61), .7)
esmalte = material('Esmalte', (.39,.49,.47), .48, .1)
petroleo = material('Petroleo', (.025,.069,.083), .7)
metal = material('Metal', (.26,.34,.37), .36, .62)
borracha = material('Borracha', (.011,.023,.028), .88)
tecido = material('Tecido', (.15,.32,.34), .98)
ciano = material('Ciano', (.075,.44,.51), .55, 0, .25)
luz = material('Difusor', (.80,.78,.62), .7, 0, .4)
materiais = [marfim, esmalte, petroleo, metal, borracha, tecido, ciano, luz]

def p(pos): return Vector((pos[0], -pos[2], pos[1]))

def caixa(nome, pos, tam, mat, borda=.012, giro=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=p(pos))
    o = bpy.context.object
    o.name = nome
    o.dimensions = (tam[0], tam[2], tam[1])
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(mat)
    if borda:
        mod = o.modifiers.new('Arestas acabadas', 'BEVEL')
        mod.width = min(borda, min(tam)*.3)
        mod.segments = 2
        bpy.ops.object.modifier_apply(modifier=mod.name)
    o.rotation_euler.z = giro
    return o

def tubo(nome, a, b, raio, mat, lados=12):
    a,b = p(a),p(b)
    bpy.ops.mesh.primitive_cylinder_add(vertices=lados, radius=raio, depth=(b-a).length, location=(a+b)/2)
    o = bpy.context.object
    o.name = nome
    o.rotation_euler = (b-a).to_track_quat('Z','Y').to_euler()
    o.data.materials.append(mat)
    for f in o.data.polygons: f.use_smooth = len(f.vertices)==4
    return o

def texto(conteudo, pos, tamanho=.07, giro=0, mat=marfim):
    dados = bpy.data.curves.new(conteudo, 'FONT')
    dados.body = conteudo
    dados.align_x = 'CENTER'
    dados.align_y = 'CENTER'
    dados.size = tamanho
    dados.resolution_u = 5
    o = bpy.data.objects.new(conteudo, dados)
    cena.collection.objects.link(o)
    o.location = p(pos)
    o.rotation_euler = (math.pi/2, 0, giro)
    dados.materials.append(mat)
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.convert(target='MESH')

def rodas(x,z,largura,comprimento):
    for dx in (-largura/2,largura/2):
        for dz in (-comprimento/2,comprimento/2):
            tubo('Rodízio', (x+dx-.035,.11,z+dz),(x+dx+.035,.11,z+dz),.095,borracha)
            caixa('Garfo do rodízio',(x+dx,.19,z+dz),(.09,.1,.12),metal)

def modulo_lateral(nome, centro, giro, largura):
    """Peças em coordenadas locais: frente +Z, giradas em direção ao jogador."""
    x,y,z = centro
    def pos(a,b,c):
        return (x+a*math.cos(giro)+c*math.sin(giro), y+b, z-a*math.sin(giro)+c*math.cos(giro))
    def bloco(n,a,b,c,tam,mat,borda=.012):
        return caixa(nome+' / '+n,pos(a,b,c),tam,mat,borda,giro)
    def rotulo(t,a,b,c,s=.07,mat=marfim): texto(t,pos(a,b,c),s,giro,mat)
    bloco('painel',0,1.7,0,(largura,1.8,.08),petroleo,.025)
    return pos,bloco,rotulo

try:
    bpy.context.window.scene = cena
    # LEITO: cama vazia de treinamento, sem paciente ou anatomia inventada.
    x,z = -3.05,2.50
    rodas(x,z,.92,1.65)
    caixa('Chassi do leito',(x,.28,z),(1.10,.16,1.91),metal,.035)
    caixa('Coluna elevatória',(x,.48,z),(.56,.40,.78),esmalte,.035)
    caixa('Estrado',(x,.69,z),(1.18,.13,2.23),petroleo,.04)
    caixa('Colchão',(x,.80,z),(1.06,.15,2.09),marfim,.065)
    caixa('Cobertura de treino',(x,.882,z-.24),(1.07,.022,1.44),tecido,.016)
    caixa('Dobra da cobertura',(x,.904,z+.43),(1.04,.022,.11),esmalte,.008)
    caixa('Travesseiro',(x,.93,z+.73),(.75,.13,.40),marfim,.10)
    for dz in (-1.13,1.13):
        for dx in (-.48,.48): tubo('Suporte cabeceira',(x+dx,.69,z+dz),(x+dx,1.08,z+dz),.023,metal)
        caixa('Cabeceira do leito',(x,1.01,z+dz),(1.08,.36,.085),esmalte,.045)
        caixa('Recorte cabeceira',(x,1.08,z+dz-.047),(.56,.072,.018),petroleo,.015)
    for dx in (-.63,.63):
        for dz in (-.64,.64): tubo('Grade vertical',(x+dx,.68,z+dz),(x+dx,1.05,z+dz),.018,metal)
        for y in (.89,1.07): tubo('Grade lateral',(x+dx,y,z-.74),(x+dx,y,z+.74),.022,metal)
    # A cabeceira técnica organiza a parede sem apresentar gases ou sinais clínicos.
    caixa('Painel do leito',(-2.95,1.60,4.43),(2.72,2.72,.09),esmalte,.035)
    caixa('Faixa cabeceira',(-2.95,1.57,4.32),(2.42,.28,.12),petroleo)
    for i in range(4):
        caixa('Módulo de conexão',(-3.70+i*.26,1.57,4.248),(.16,.17,.024),marfim,.009)
        tubo('Conector de treino',(-3.70+i*.26,1.57,4.23),(-3.70+i*.26,1.57,4.21),.034,metal)
    texto('LEITO DE TREINAMENTO',(-2.95,2.55,4.366),.115,math.pi,petroleo)
    texto('02  /  APOIO À SIMULAÇÃO',(-2.95,2.33,4.366),.065,math.pi,petroleo)
    caixa('Luz da cabeceira',(-2.95,2.08,4.28),(2.2,.085,.12),petroleo)
    caixa('Difusor cabeceira',(-2.95,2.045,4.21),(2.06,.04,.045),luz,.006)
    # Armário de cabeceira mantém o corredor central livre.
    caixa('Mesa de cabeceira',(-1.83,.45,3.51),(.49,.76,.55),esmalte,.035)
    caixa('Tampo cabeceira',(-1.83,.855,3.51),(.56,.05,.60),marfim,.025)
    for y in (.37,.66):
        caixa('Gaveta cabeceira',(-1.83,y,3.218),(.43,.21,.025),petroleo)
        caixa('Alça cabeceira',(-1.83,y+.015,3.19),(.19,.024,.025),metal)
    # Suporte de infusão de demonstração; bolsa opaca e tubo preso à estação.
    x,z = -3.98,3.42
    tubo('Haste de suporte',(x,.12,z),(x,2.22,z),.015,metal)
    for i in range(4):
        dx,dz = .23*math.cos(i*math.pi/2), .23*math.sin(i*math.pi/2)
        tubo('Base do suporte',(x,.16,z),(x+dx,.07,z+dz),.02,metal)
    tubo('Gancho suporte',(x-.16,2.20,z),(x+.16,2.20,z),.012,metal)
    caixa('Bolsa de demonstração',(x-.12,1.97,z),(.16,.30,.055),marfim,.028)
    caixa('Etiqueta bolsa',(x-.12,1.98,z-.032),(.1,.13,.008),tecido,.003)
    tubo('Linha recolhida',(x-.12,1.80,z),(x-.12,1.13,z),.005,tecido,6)
    # Cortina recolhida: malha de tecido corrugado, não dezenas de props soltos.
    tubo('Trilho cortina',(-4.25,2.94,1.16),(-1.83,2.94,1.16),.019,metal)
    tubo('Retorno trilho',(-1.83,2.94,1.16),(-1.83,2.94,3.93),.019,metal)
    for cx in (-4.22,-3.92): tubo('Suspensão trilho',(cx,2.94,1.16),(cx,3.53,1.16),.012,metal)
    vertices,faces = [],[]
    for i in range(37):
        cx = -4.28+i*.018
        cz = 1.16+.055*math.cos(i*math.pi/3)
        vertices.extend([(cx,-cz,.32),(cx,-cz,2.80)])
        if i: faces.append((2*i-2,2*i,2*i+1,2*i-1))
    dados=bpy.data.meshes.new('Pregas da cortina')
    dados.from_pydata(vertices,[],faces)
    dados.materials.append(tecido)
    cortina=bpy.data.objects.new('Cortina recolhida',dados)
    cena.collection.objects.link(cortina)
    bpy.context.view_layer.objects.active=cortina
    cortina.select_set(True)
    esp=cortina.modifiers.new('Espessura tecido','SOLIDIFY'); esp.thickness=.005
    bpy.ops.object.modifier_apply(modifier=esp.name)
    for i in range(7): tubo('Suspensor da cortina',(-4.25+i*.09,2.80,1.16),(-4.25+i*.09,2.94,1.16),.007,metal,8)
    # Monitor da baía sem números fisiológicos fictícios.
    pos,b,t = modulo_lateral('Monitor de apoio',(-4.39,0,2.65),math.pi/2,1.05)
    b('braço',0,1.67,.12,(.13,.13,.28),metal)
    b('carcaça',0,1.76,.29,(.84,.59,.12),esmalte,.03)
    b('visor',0,1.76,.358,(.71,.46,.018),borracha)
    t('SIMULAÇÃO',0,1.89,.373,.06)
    t('EM ESPERA',0,1.73,.373,.053,ciano)
    for a in (-.20,0,.20): b('indicador',a,1.62,.374,(.11,.024,.006),ciano,0)
    # DIREITA: reserva de materiais/tecidos, nunca objetos no corredor do jogador.
    x,z = 2.98,4.18
    caixa('Baía de materiais',(x,1.52,4.43),(2.48,2.79,.09),petroleo,.03)
    caixa('Rodapé armário',(x,.10,z),(2.27,.20,.58),borracha)
    caixa('Armário de apoio',(x,.61,z),(2.32,.93,.59),esmalte,.035)
    for dx in (-.77,0,.77):
        caixa('Porta apoio',(x+dx,.62,z-.31),(.70,.80,.04),marfim)
        caixa('Puxador apoio',(x+dx,.88,z-.34),(.27,.025,.035),metal)
    caixa('Tampo apoio',(x,1.11,z),(2.43,.09,.70),marfim,.035)
    for y in (1.52,2.06):
        caixa('Prateleira apoio',(x,y,z),(2.34,.045,.56),metal)
        for dx in (-.85,.85): caixa('Suporte prateleira',(x+dx,y-.12,z+.17),(.045,.25,.3),metal)
    for dx in (-.79,0,.79):
        for y in (1.30,1.69):
            caixa('Caixa de materiais',(x+dx,y,z-.02),(.62,.30,.46),tecido,.018)
            caixa('Tampa da caixa',(x+dx,y+.16,z-.02),(.65,.035,.49),esmalte,.012)
            caixa('Etiqueta caixa',(x+dx,y,z-.259),(.25,.09,.008),marfim,.003)
    for dx in (-.74,0,.74):
        for y in (2.12,2.20,2.28): caixa('Tecido dobrado',(x+dx,y,z),(.56,.065,.37),marfim,.025)
    texto('APOIO / MATERIAIS',(x,2.64,4.366),.115,math.pi)
    # Higienização lateral, com cuba realmente recuada e torneira articulada.
    pos,b,t = modulo_lateral('Higienização',(4.39,0,2.46),-math.pi/2,1.6)
    b('gabinete',0,.55,.25,(1.45,.92,.51),esmalte,.03)
    for a in (-.37,.37):
        b('porta',a,.55,.52,(.67,.78,.035),petroleo)
        b('puxador',a,.85,.55,(.23,.028,.028),metal)
    b('cuba fundo',0,.93,.30,(.71,.025,.33),borracha)
    for a in (-.57,.57): b('tampo lateral',a,1.05,.32,(.39,.09,.68),marfim,.02)
    for c in (.045,.60): b('borda cuba',0,1.05,c,(.75,.09,.12),metal,.012)
    for a in (-.38,.38): b('lateral cuba',a,.98,.32,(.018,.14,.45),metal,.004)
    b('fundo cuba',0,.98,.085,(.75,.14,.018),metal,.004)
    b('frente cuba',0,.98,.554,(.75,.14,.018),metal,.004)
    for a,bp in [((0,1.09,.07),(0,1.36,.07)),((0,1.36,.07),(0,1.36,.36)),((0,1.36,.36),(0,1.28,.36))]:
        tubo('Torneira higienização',pos(*a),pos(*bp),.018,metal)
    b('dispensador',-.55,1.60,.13,(.27,.39,.18),marfim,.025)
    b('visor dispensador',-.55,1.60,.225,(.16,.13,.008),tecido)
    b('toalheiro',.50,1.70,.13,(.42,.37,.18),esmalte,.025)
    b('folha de papel',.50,1.46,.17,(.25,.17,.012),marfim,.003)
    t('HIGIENIZAÇÃO',0,2.30,.055,.10)
    # Estação compacta de observação na metade lateral da sala.
    pos,b,t = modulo_lateral('Posto de apoio',(4.39,0,.20),-math.pi/2,1.55)
    b('tampo',0,1.0,.37,(1.48,.08,.75),marfim,.025)
    for a in (-.55,.55): b('mão francesa',a,.81,.26,(.07,.31,.48),metal)
    b('pé monitor',0,1.10,.25,(.32,.10,.20),metal)
    b('monitor',0,1.43,.20,(.91,.57,.11),petroleo,.025)
    b('visor',0,1.43,.262,(.80,.46,.018),borracha)
    t('APOIO AO TREINO',0,1.54,.276,.062)
    for i in range(3): b('linha da interface',-.13,1.41-i*.055,.276,(.41-i*.06,.015,.005),ciano,0)
    b('quadro do visor',.25,1.34,.276,(.17,.15,.005),tecido,0)
    b('teclado',0,1.065,.57,(.65,.035,.23),petroleo,.008)
    for a in (-.24,-.12,0,.12,.24): b('teclas',a,1.087,.57,(.08,.01,.14),esmalte,.003)
    for a in (-.59,-.48): b('pasta de apoio',a,1.24,.23,(.07,.40,.32),tecido)
    t('POSTO DE APOIO',0,2.25,.055,.095)
    # Fundo central: mesma porta, agora com vidro fosco, soleira e identificação.
    caixa('Identificação da entrada',(0,2.77,4.35),(2.43,.33,.08),petroleo,.025)
    texto('CENTRO DE SIMULAÇÃO',(0,2.78,4.302),.117,math.pi)
    for x in (-.42,.42):
        caixa('Visor fosco',(x,1.64,4.229),(.42,.61,.013),esmalte,.008)
        for y in (1.45,1.57,1.69,1.81): caixa('Faixa de privacidade',(x,y,4.216),(.41,.025,.008),marfim,0)
        caixa('Proteção da porta',(x,.34,4.245),(.72,.40,.018),metal,.008)
    caixa('Soleira plana',(0,.007,4.13),(1.85,.008,.24),metal,0)
    # Acabamento longitudinal e iluminação física de fundo, sem luzes em runtime.
    for x in (-2.8,2.8):
        caixa('Luminária posterior',(x,3.51,2.72),(.52,.09,1.65),petroleo,.02)
        caixa('Difusor posterior',(x,3.455,2.72),(.41,.016,1.50),luz,.005)
    for x in (-4.46,4.46):
        caixa('Proteção lateral',(x,.93,2.27),(.055,.16,3.69),esmalte,.015)
        caixa('Montante posterior',(x,1.8,3.55),(.12,3.58,.13),metal,.018)
    # Área do leito marcada no piso, sem volume que force a pessoa a subir.
    for x in (-3.81,-2.26): caixa('Demarcação leito',(x,.006,2.50),(.022,.005,2.62),esmalte,0)
    for z in (1.19,3.81): caixa('Demarcação leito',(-3.035,.006,z),(1.57,.005,.022),esmalte,0)
    # Agrupamento por material. Nenhum órgão é carregado ou simplificado aqui.
    for mat in materiais:
        objetos=[o for o in cena.objects if o.type=='MESH' and o.data.materials[0]==mat]
        if not objetos: continue
        bpy.ops.object.select_all(action='DESELECT')
        for o in objetos: o.select_set(True)
        bpy.context.view_layer.objects.active=objetos[0]
        bpy.ops.object.join()
        objetos[0].name=mat.name
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(filepath=str(DESTINO),export_format='GLB',use_selection=True,
                              use_active_scene=True,export_animations=False,export_yup=True)
    for o in cena.objects: o.data.calc_loop_triangles()
    result={'bytes':DESTINO.stat().st_size,'malhas':len(cena.objects),'materiais':len(materiais),
            'triangulos':sum(len(o.data.loop_triangles) for o in cena.objects),'texturas':0,'animacoes':0}
    print(json.dumps(result))
finally:
    bpy.context.window.scene=anterior
