"""Biblioteca de estudo autoral. Executar via Blender MCP, sem alterar a cena aberta.

Reutiliza a encadernação autoral da Escola, não os modelos anatômicos.
Pré-requisito: executar texturas-escola-revisao.py para gerar os mapas locais.
Geometria em metros, UVs normalizadas e oclusão calculada offline.
"""
import ast
import json
import math
from pathlib import Path
import bpy
import bmesh
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

RAIZ = Path(__file__).resolve().parents[1]
PASTA = RAIZ / 'public/models/props'
TEMP = RAIZ / 'tmp_sala_estudos'
TEMP.mkdir(exist_ok=True)
TEXTURAS = RAIZ / 'tmp_escola_revisao'
LAYOUT = json.loads((RAIZ/'lib/sala-estudos-layout.json').read_text(encoding='utf-8'))
ANTERIOR = bpy.context.window.scene
CENA = bpy.data.scenes.new('VRmed_Sala_Estudos_Revisao')
RAIOS = 8
DIRECOES = []
for i in range(RAIOS):
    r = math.sqrt((i+.5)/RAIOS)
    a = i*2.399963229728653
    DIRECOES.append(Vector((r*math.cos(a), r*math.sin(a), math.sqrt(1-r*r))))

def reutilizar(arquivo, nomes):
    arv = ast.parse(arquivo.read_text(encoding='utf-8'))
    funcoes = [n for n in arv.body if isinstance(n, ast.FunctionDef) and n.name in nomes]
    assert len(funcoes) == len(nomes)
    exec(compile(ast.Module(body=funcoes, type_ignores=[]), str(arquivo), 'exec'), globals())

reutilizar(RAIZ/'scripts/refinar-ambientes-duelo.py',
    ['p','selecionar','shader','caixa','tubo','arvore','oclusao','acabamento','agrupar','exportar'])
reutilizar(RAIZ/'scripts/criar-escola-revisao.py', ['material','curva','malha','uv_cor','livro','girar'])

def mapa(mat, nome):
    imagem = bpy.data.images.load(str(TEXTURAS/nome), check_existing=True)
    tex = mat.node_tree.nodes.new('ShaderNodeTexImage'); tex.image = imagem
    shader(mat).inputs['Base Color'].default_value = (1,1,1,1)
    mat.node_tree.links.new(tex.outputs['Color'], shader(mat).inputs['Base Color'])

def esfera(nome, pos, escala, mat):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, location=p(pos))
    o=bpy.context.object; o.name=nome; o.scale=(escala[0],escala[2],escala[1])
    o.data.materials.append(mat)
    for f in o.data.polygons: f.use_smooth=True
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return o

def escrita(texto, pos, largura, altura, mat):
    c=bpy.data.curves.new('Inscrição na superfície','FONT')
    c.body=texto; c.align_x='CENTER'; c.align_y='CENTER'; c.size=altura
    c.space_character=1.05; c.extrude=.00025; c.resolution_u=3
    fonte=Path('C:/Windows/Fonts/segoeuib.ttf')
    if fonte.exists(): c.font=bpy.data.fonts.load(str(fonte),check_existing=True)
    o=bpy.data.objects.new('Placa '+texto,c); CENA.collection.objects.link(o)
    o.location=p(pos); o.rotation_euler.x=math.pi/2; c.materials.append(mat)
    bpy.context.view_layer.update()
    if o.dimensions.x>largura: o.scale*=largura/o.dimensions.x
    selecionar([o]); bpy.ops.object.convert(target='MESH')
    return bpy.context.object

def biblioteca(x,z,w=1.0):
    caixa('Rodapé recuado da biblioteca',(x,.05,z),(w-.09,.1,.39),grafite,.008)
    caixa('Costas encaixadas',(x,1.30,z-.208),(w,2.5,.045),verde,.007)
    for dx in (-w/2+.02,w/2-.02):
        caixa('Lateral de marcenaria',(x+dx,1.30,z),(.045,2.5,.46),carvalho,.008)
    for y in (.11,.66,1.13,1.60,2.07,2.55):
        caixa('Prateleira com borda',(x,y,z),(w,.035,.47),carvalho,.008)
    for dx in (-w/4,w/4):
        caixa('Porta inferior com folga',(x+dx,.383,z+.228),(w/2-.012,.482,.03),verde,.006)
        tubo('Puxador latão',(x+dx-.07,.54,z+.256),(x+dx+.07,.54,z+.256),.007,latao,10)
    for nivel in range(3):
        y=.68+nivel*.47
        for j in range(6):
            h=.285+.025*((j+nivel)%3)
            livro(x-w/2+.125+j*.105,y,z+.05,(j+2*nivel)%8,.068,h,.215,
                  .10 if j==5 else 0)
    # Aparador de livros: chapa dobrada com pé, não um bloco solto.
    for y in (.68,1.15,1.62):
        caixa('Aparador vertical',(x+.31,y+.13,z+.06),(.009,.26,.22),latao,.002)
        caixa('Pé do aparador',(x+.26,y+.005,z+.06),(.12,.008,.22),latao,.002)

def planta(x,z):
    tubo('Cachepô cerâmico',(x,.015,z),(x,.38,z),.17,ceramica,24)
    tubo('Terra',(x,.379,z),(x,.383,z),.15,grafite,20)
    for i in range(8):
        ang=i*2.39996; h=.63+(i%3)*.16
        fim=(x+.24*math.cos(ang),h,z+.24*math.sin(ang))
        curva('Haste orgânica',[(x,.37,z),(x+.09*math.cos(ang),h*.8,z+.09*math.sin(ang)),fim],.004,folha)
        # Folhas em lâminas curvas com nervura central, não cones.
        vs=[]; fs=[]
        for j in range(9):
            t=j/8; raio=.10*math.sin(math.pi*t)
            cx=fim[0]+math.cos(ang)*t*.28; cz=fim[2]+math.sin(ang)*t*.28
            for lado in (-1,0,1):
                vs.append((cx+lado*raio*math.sin(ang),h+.10*math.sin(t*math.pi)-abs(lado)*.015,cz-lado*raio*math.cos(ang)))
        for j in range(8):
            for k in range(2):
                a=j*3+k; fs.append((a,a+1,a+4,a+3))
        o=malha('Folha com nervura',vs,fs,folha,True,(0,0,1))
        # Dupla face geométrica evita transparência no mobile.
        so=o.modifiers.new('Espessura da folha','SOLIDIFY'); so.thickness=.001
        selecionar([o]); bpy.ops.object.modifier_apply(modifier=so.name)

try:
    bpy.context.window.scene=CENA
    carvalho=material('Sala_Carvalho','a48761',.58); mapa(carvalho,'carvalho.png')
    encadernacao=material('Sala_Encadernacao','ffffff',.7); mapa(encadernacao,'encadernacao.png')
    papel=material('Sala_Papel','e3dfd0',.95); mapa(papel,'folhas.png')
    verde=material('Sala_Salvia','344d48',.78)
    parede=material('Sala_Cal','dcd8cc',.96)
    grafite=material('Sala_Grafite','273234',.7)
    latao=material('Sala_Latao','b59a62',.38,.35)
    linho=material('Sala_Tecido','87918a',.98)
    ambar=material('Sala_Argila','a15e43',.74)
    ceramica=material('Sala_Ceramica','d6c8ac',.38)
    folha=material('Sala_Folha','47644d',.86)
    luz=material('Sala_Difusor','fff0d4',.8,0,.65)
    ceu=material('Sala_Ceu','b4c8c9',.9,0,.3)

    # Arquitetura contínua, cornijas, rodapés e marcenaria sob medida.
    caixa('Piso',(0,-.034,0),(5,.068,5),carvalho,0)
    caixa('Teto',(0,3.045,0),(5,.09,5),parede,0)
    for x in (-2.55,2.55): caixa('Parede lateral',(x,1.5,0),(.1,3,5),parede,0)
    for z in (-2.55,2.55): caixa('Parede',(0,1.5,z),(5,3,.1),parede,0)
    for x in (-2.46,2.46):
        caixa('Rodapé lateral',(x,.075,0),(.075,.15,5),verde,.004)
        caixa('Cornija lateral',(x,2.86,0),(.10,.18,5),carvalho,.008)
    for z in (-2.46,2.46):
        caixa('Rodapé',(0,.075,z),(5,.15,.075),verde,.004)
        caixa('Cornija',(0,2.86,z),(5,.18,.10),carvalho,.008)
    # Painel principal não concorre com a tela; ripas e tecido absorvente.
    caixa('Fundo de estudo',(0,1.44,-2.443),(2.67,2.57,.06),verde,.01)
    caixa('Painel acústico',(0,1.94,-2.392),(1.61,1.43,.035),linho,.018)
    for lado in (-1,1):
        for i in range(7):
            caixa('Ripa com espaçamento',(lado*(.9+i*.064),1.47,-2.384),(.032,2.45,.07),carvalho,.005)
    caixa('Placa de estudo',(0,2.20,-2.352),(1.40,.32,.027),verde,.01)
    escrita('SALA DE ESTUDOS',(0,2.215,-2.335),1.22,.12,ceramica)
    escrita('VRmed',(0,2.115,-2.335),.4,.039,latao)
    for x in (-1.84,1.84): biblioteca(x,-2.23,1.02)
    # Mesa com canto confortável, espessura de tampo real, ferragens e gaveteiro.
    caixa('Tampo de escrita',LAYOUT['tampo']['posicao'],LAYOUT['tampo']['tamanho'],carvalho,.026)
    caixa('Saia posterior',(0,.64,-2.29),(2.35,.13,.045),verde,.008)
    for x in (-1.14,1.14):
        for z in (-2.23,-1.57):
            tubo('Pé metálico',(x,.025,z),(x,.71,z),.027,grafite,12)
            tubo('Sapata',(x,.005,z),(x,.034,z),.033,grafite,12)
    caixa('Gaveteiro lateral',(.92,.43,-2.00),(.43,.54,.55),verde,.016)
    for y in (.285,.535):
        caixa('Frente de gaveta',(.92,y,-1.713),(.407,.23,.025),carvalho,.006)
        tubo('Puxador de gaveta',(.85,y+.055,-1.685),(.99,y+.055,-1.685),.007,latao,10)
    # Tapete retangular com borda costurada, fora da área dos cliques.
    caixa('Tapete de leitura',(0,.008,-.58),(2.65,.015,2.75),linho,.018)
    for x in (-1.26,1.26): caixa('Borda tecida',(x,.017,-.58),(.022,.001,2.63),verde,0)
    for z in (-1.88,.72): caixa('Borda tecida',(0,.017,z),(2.52,.001,.022),verde,0)
    # Janela esquerda recuada e persiana: vista opaca, sem blending.
    caixa('Nicho da janela',(-2.44,1.82,-.25),(.11,1.58,2.25),verde,.009)
    caixa('Vidro difuso',(-2.373,1.82,-.25),(.008,1.43,2.1),ceu,0)
    for z in (-1.31,.81): caixa('Marco da janela',(-2.335,1.82,z),(.11,1.58,.055),carvalho,.008)
    for y in (1.07,2.57): caixa('Travessa da janela',(-2.335,y,-.25),(.11,.055,2.21),carvalho,.008)
    caixa('Peitoril',(-2.26,1.046,-.25),(.28,.055,2.30),carvalho,.012)
    for y in (2.45,2.35,2.25,2.15): caixa('Lâmina da persiana',(-2.27,y,-.25),(.12,.025,2.1),linho,.004)
    caixa('Montante central',(-2.32,1.81,-.25),(.08,1.48,.035),verde,.004)
    # Luz de tarefa articulada afastada do livro e das alternativas.
    tubo('Base da luminária',(-1.13,.766,-2.15),(-1.13,.784,-2.15),.09,latao,24)
    curva('Braço de leitura',[(-1.13,.78,-2.15),(-1.13,1.03,-2.15),(-.96,1.24,-2.14),(-.87,1.24,-2.14)],.012,grafite)
    tubo('Cabeça da luminária',(-.88,1.22,-2.14),(-.88,1.26,-2.14),.095,verde,24)
    tubo('Difusor de leitura',(-.88,1.21,-2.14),(-.88,1.22,-2.14),.084,luz,24)
    # Pendente de tecido + aros; não adiciona luz dinâmica no aplicativo.
    tubo('Cabo do pendente',(0,3,-.8),(0,2.69,-.8),.008,grafite,8)
    tubo('Cúpula do pendente',(0,2.43,-.8),(0,2.69,-.8),.34,linho,32)
    tubo('Aro do pendente',(0,2.425,-.8),(0,2.448,-.8),.345,latao,32)
    tubo('Difusor do pendente',(0,2.42,-.8),(0,2.425,-.8),.326,luz,32)
    # Retaguarda de leitura e porta, com centro livre para levantar do assento.
    caixa('Banco de apoio',(-1.7,.31,1.93),(1.36,.5,.57),carvalho,.025)
    caixa('Assento estofado',(-1.7,.595,1.93),(1.36,.12,.59),linho,.045)
    caixa('Painel da retaguarda',(-1.7,1.62,2.39),(1.36,1.49,.06),verde,.015)
    for x in (-2.21,-1.19): caixa('Moldura vertical',(x,1.62,2.35),(.035,1.25,.06),carvalho,.004)
    caixa('Porta',(0,1.12,2.43),(1.0,2.24,.055),verde,.009)
    for x in (-.56,.56): caixa('Batente',(x,1.17,2.4),(.085,2.34,.12),carvalho,.01)
    caixa('Batente superior',(0,2.36,2.4),(1.20,.09,.12),carvalho,.01)
    curva('Maçaneta',[(.36,1.03,2.392),(.36,1.03,2.32),(.24,1.03,2.32)],.012,latao)
    planta(2.1,1.97)
    ambiente=list(CENA.objects)
    # Monitor novo em asset próprio: carcassa, moldura, pedestal e ventilação.
    caixa('Base do monitor',(0,.78,-2.12),(.38,.03,.23),grafite,.015)
    caixa('Coluna do monitor',(0,.858,-2.115),(.08,.15,.05),latao,.014)
    caixa('Carcassa do monitor',(0,1.22,-2.10),(1.12,.65,.095),grafite,.022)
    caixa('Vidro do monitor',(0,1.22,-2.051),(1.055,.585,.006),verde,.008)
    for x in (-.54,.54): caixa('Aro lateral',(x,1.22,-2.043),(.014,.595,.008),latao,.003)
    for y in (.917,1.523): caixa('Aro horizontal',(0,y,-2.043),(1.085,.013,.008),latao,.003)
    for i in range(14): caixa('Ventilação traseira',((i-6.5)*.033,1.20,-2.152),(.018,.09,.008),verde,.003)
    monitor=[o for o in CENA.objects if o not in ambiente]
    # Aplica transformações e unifica nomes das UVs ANTES de juntar materiais.
    for o in list(CENA.objects):
        o.data.transform(o.matrix_world); o.matrix_world.identity(); o.data.update()
        uv=o.data.uv_layers.active or o.data.uv_layers.new(name='UVMap')
        uv.name='UVMap'; uv.active_render=True
        if o.get('uv_autoral'): continue
        for f in o.data.polygons:
            eixo=max(range(3),key=lambda i:abs(f.normal[i])); a,b=[(1,2),(0,2),(0,1)][eixo]
            for k in f.loop_indices:
                co=o.data.vertices[o.data.loops[k].vertex_index].co
                uv.data[k].uv=(co[a]*1.8,co[b]*1.2)
    quantidade=len(CENA.objects)
    bvh=arvore(list(CENA.objects)); acabamento(list(CENA.objects),bvh)
    result={'ambiente':exportar('sala-estudos-revisao',agrupar(ambiente)),
            'monitor':exportar('monitor-estudos-revisao',agrupar(monitor)),
            'objetos_autorados':quantidade, 'cena_original_preservada':ANTERIOR.name}
    bpy.data.libraries.write(str(TEMP/'sala-estudos-revisao.blend'),{CENA})
    (TEMP/'resumo.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
finally:
    bpy.context.window.scene=ANTERIOR
