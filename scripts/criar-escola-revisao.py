"""Escola versionada: marcenaria, encadernação e laboratório, em cena independente.

Preserva as versões anteriores e os postos. Elevação da lousa vem do layout compartilhado.
Execute texturas-escola-revisao.py antes; depois execute este script via Blender.
"""
import ast
import json
import math
import bpy
import bmesh
import numpy as np
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

RAIZ = Path(__file__).resolve().parents[1]
TEMP = RAIZ/'tmp_escola_revisao'
PASTA = RAIZ/'public/models/props'
LAYOUT = json.loads((RAIZ/'lib/escola-layout.json').read_text(encoding='utf-8'))
ANTERIOR = bpy.context.window.scene

def extrair(caminho, nomes):
    modulo = ast.parse(caminho.read_text(encoding='utf-8'))
    return [n for n in modulo.body if isinstance(n, ast.FunctionDef) and n.name in nomes]

# Autoria sem exportação: mantém as peças centrais aprovadas em suas coordenadas.
arquivo = RAIZ/'scripts/dirigir-arte-escola.py'
exec(compile(ast.Module(body=extrair(arquivo, ['autoria_original']), type_ignores=[]), str(arquivo), 'exec'))
base = autoria_original()
CENA = base['cena']
CENA.name = 'VRmed_Escola_Revisao'
for nome in ('p','caixa','tubo','casca','painel'):
    globals()[nome] = base[nome]
parede,marfim,madeira,escuro,verde,metal,latao,luz,tecido,ambar,azul = base['materiais']

def vertices_mundo(obj):
    return sorted(tuple(round(v, 5) for v in obj.matrix_world @ ponto.co) for ponto in obj.data.vertices)

def material(nome, cor, rough=.65, metallic=0, emissao=0):
    m = bpy.data.materials.new('EscolaRevisao_'+nome)
    m.use_nodes = True
    sh = next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    rgb = [int(cor[i:i+2],16)/255 for i in (0,2,4)]
    rgb = [x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4 for x in rgb]
    sh.inputs['Base Color'].default_value=(*rgb,1)
    sh.inputs['Roughness'].default_value=rough
    sh.inputs['Metallic'].default_value=metallic
    sh.inputs['Emission Color'].default_value=(*rgb,1)
    sh.inputs['Emission Strength'].default_value=emissao
    return m

def imagem(mat, arquivo, entrada='Base Color', nao_cor=False):
    sh=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    tex=mat.node_tree.nodes.new('ShaderNodeTexImage')
    tex.image=bpy.data.images.load(str(TEMP/arquivo),check_existing=True)
    if nao_cor: tex.image.colorspace_settings.name='Non-Color'
    mat.node_tree.links.new(tex.outputs['Color'],sh.inputs[entrada])
    return tex

def curva(nome, pontos, raio, mat):
    c=bpy.data.curves.new(nome,'CURVE'); c.dimensions='3D'; c.resolution_u=7
    c.bevel_depth=raio; c.bevel_resolution=2
    s=c.splines.new('BEZIER'); s.bezier_points.add(len(pontos)-1)
    for v,pos in zip(s.bezier_points,pontos):
        v.co=p(pos); v.handle_left_type=v.handle_right_type='AUTO'
    o=bpy.data.objects.new(nome,c); CENA.collection.objects.link(o); c.materials.append(mat)
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active=o
    bpy.ops.object.convert(target='MESH')
    return bpy.context.object

def malha(nome, vs, fs, mat, suave=False, normal_alvo=None):
    m=bpy.data.meshes.new(nome); m.from_pydata([p(v) for v in vs],[],fs); m.materials.append(mat)
    bm=bmesh.new(); bm.from_mesh(m); bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    if normal_alvo and sum(f.normal.dot(Vector(normal_alvo)) for f in bm.faces)<0:
        bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
    bm.to_mesh(m); bm.free()
    for face in m.polygons: face.use_smooth=suave
    o=bpy.data.objects.new(nome,m); CENA.collection.objects.link(o)
    return o

def girar(objetos, centro, angulo):
    tr=Matrix.Translation(p(centro)); mat=tr @ Matrix.Rotation(angulo,4,'Z') @ tr.inverted()
    for obj in objetos: obj.matrix_world=mat@obj.matrix_world

def uv_cor(obj, indice):
    uv=obj.data.uv_layers.active or obj.data.uv_layers.new(name='UVMap')
    for loop in uv.data: loop.uv=((indice+.12)/8,.98)
    obj['uv_autoral']=True

def livro(x,y,z,indice=0,w=.085,h=.34,d=.235,inclinado=0):
    antes=set(CENA.objects)
    bloco=caixa('Miolo com folhas',(x,y+h/2,z),(w-.014,h-.016,d-.023),papel,.004)
    for dx in (-w/2,w/2):
        o=caixa('Capa com sobrecapa',(x+dx,y+h/2,z),(.009,h,d),encadernacao,.003)
        uv_cor(o,indice)
    vs=[]; fs=[]; n=10
    for altura in (y,y+h):
        for j in range(n+1):
            t=j/n
            vs.append((x+(t-.5)*w,altura,z+d/2+.003+.009*math.sin(t*math.pi)))
    for j in range(n): fs.append((j,j+1,n+2+j,n+1+j))
    lombada=malha('Lombada arredondada impressa',vs,fs,encadernacao,True,(0,-1,0))
    uv=lombada.data.uv_layers.new(name='UVMap')
    for loop in lombada.data.loops:
        co=lombada.data.vertices[loop.vertex_index].co
        fu=(co.x-(x-w/2))/w; fv=(co.z-y)/h
        uv.data[loop.index].uv=((indice+.02+fu*.96)/8,.505+fv*.490)
    lombada['uv_autoral']=True
    # Cabeceado e vinco reais dão espessura e separam capa e bloco de papel.
    for altura in (y+.009,y+h-.009):
        tubo('Cabeceado do livro',(x-w*.36,altura,z+d/2),(x+w*.36,altura,z+d/2),.0025,linho,8)
    if indice%3==0:
        caixa('Fita de marcação',(x+.006,y+h+.001,z-.08),(.012,.002,.14),ambar,.0005)
    objetos=set(CENA.objects)-antes
    if inclinado:
        # Inclinar em torno da base; compensar a altura para não atravessar a prateleira.
        tr=Matrix.Translation(p((x,y,z)))
        giro=tr @ Matrix.Rotation(inclinado,4,'Y') @ tr.inverted()
        for obj in objetos: obj.matrix_world=giro@obj.matrix_world
        minimo=min((obj.matrix_world@v.co).z for obj in objetos for v in obj.data.vertices)
        for obj in objetos: obj.matrix_world=Matrix.Translation((0,0,y-minimo))@obj.matrix_world
    return objetos

def alca(x,y,z,w=.22):
    curva('Puxador com retorno',[(x-w/2,y,z),(x-w/2+.017,y,z+.035),
          (x+w/2-.017,y,z+.035),(x+w/2,y,z)],.010,latao)

def armario(x,z,w,h=.82,prof=.52):
    caixa('Soco recuado',(x,.065,z),(w-.12,.13,prof-.10),escuro,.012)
    caixa('Caixa de marcenaria',(x,h/2+.1,z),(w,h,prof),carvalho,.018)
    n=max(2,round(w/.55))
    for i in range(n):
        xx=x-w/2+(i+.5)*w/n
        caixa('Folga da frente',(xx,h/2+.11,z+prof/2+.004),(w/n-.01,h-.06,.012),escuro,.004)
        caixa('Porta emoldurada',(xx,h/2+.11,z+prof/2+.02),(w/n-.032,h-.082,.031),carvalho,.008)
        caixa('Painel verde rebaixado',(xx,h/2+.11,z+prof/2+.037),(w/n-.105,h-.16,.012),verde,.014)
        alca(xx,h-.035,z+prof/2+.05,min(.24,w/n*.55))
    caixa('Tampo com fita de borda',(x,h+.13,z),(w+.06,.07,prof+.09),carvalho,.019)

def estante(x,z,w=1.56,fundo=False):
    antes=set(CENA.objects)
    armario(x,z,w,.62,.47)
    caixa('Fundo encaixado',(x,1.48,z-.22),(w,1.47,.038),verde,.012)
    for dx in (-w/2+.025,w/2-.025):
        caixa('Montante com espessura',(x+dx,1.42,z),(.05,1.46,.49),carvalho,.009)
    for y in (.77,1.205,1.64,2.075):
        caixa('Prateleira em encaixe',(x,y,z),(w,.035,.50),carvalho,.009)
        caixa('Filete de bordo',(x,y-.007,z+.251),(w-.06,.012,.006),latao,.002)
    for linha,y in enumerate((.789,1.224,1.659)):
        for i in range(9):
            livro(x-w/2+.13+i*.135,y,z+.065,(i+linha*3)%8,.07+(i%3)*.009,.275+(i%4)*.026,
                  .22+(i%2)*.018,.04 if i==8 else 0)
        caixa('Aparador de atlas',(x+w/2-.125,y+.10,z+.07),(.007,.20,.22),latao,.002)
    caixa('Luz de acervo',(x,2.045,z+.065),(w-.15,.013,.15),difusor,.003)
    if fundo: girar(set(CENA.objects)-antes,(x,0,z),math.pi)

def microscopio(x,z):
    # Carcaça contínua moldada, vão óptico, pés e trilhos distinguem-no de blocos.
    for dx in (-.14,.14):
        for dz in (-.12,.12): tubo('Pé antideslizante',(x+dx,1.005,z+dz),(x+dx,1.025,z+dz),.027,escuro,12)
    casca('Sapata de microscopia',(x,0,z),[(1.021,.42,.37,0,0),(1.065,.46,.39,0,0),
          (1.09,.37,.33,.02,0)],marfim,raio=.11)
    casca('Braço óptico moldado',(x,0,z),[(1.085,.15,.19,.11,0),(1.16,.13,.17,.16,0),
          (1.36,.11,.14,.21,0),(1.51,.18,.20,.12,0),(1.56,.23,.22,.005,0)],marfim,raio=.055)
    for dz in (-.074,.074):
        tubo('Tubo binocular',(x-.015,1.515,z+dz),(x-.155,1.634,z+dz),.034,escuro,20)
        tubo('Borracha ocular',(x-.155,1.634,z+dz),(x-.18,1.655,z+dz),.041,escuro,20)
        tubo('Lente recolhida',(x-.179,1.654,z+dz),(x-.181,1.656,z+dz),.026,vidro,20)
    tubo('Revólver óptico',(x-.025,1.46,z),(x-.025,1.418,z),.078,metal,24)
    for dx,dz,tam in ((-.05,0,.09),(.025,-.045,.065),(.025,.045,.075)):
        tubo('Corpo de objetiva',(x-.025+dx,1.42,z+dz),(x-.025+dx,1.42-tam,z+dz),.019,metal,16)
        tubo('Faixa de objetiva',(x-.025+dx,1.395,z+dz),(x-.025+dx,1.385,z+dz),.020,latao,16)
    caixa('Platina metálica',(x-.035,1.258,z),(.31,.025,.285),escuro,.012)
    for dz in (-.105,.105): tubo('Trilho da platina',(x-.15,1.28,z+dz),(x+.10,1.28,z+dz),.007,metal,10)
    caixa('Lâmina didática',(x-.045,1.279,z),(.15,.006,.07),vidro,.001)
    tubo('Condensador',(x-.03,1.13,z),(x-.03,1.235,z),.055,metal,20)
    tubo('Diafragma',(x-.03,1.185,z),(x-.03,1.196,z),.064,escuro,20)
    tubo('Iluminador',(x-.03,1.09,z),(x-.03,1.099,z),.058,difusor,20)
    for lado in (-1,1):
        tubo('Foco grosso',(x+.14,1.255,z+lado*.073),(x+.14,1.255,z+lado*.142),.055,escuro,24)
        tubo('Foco fino',(x+.14,1.255,z+lado*.143),(x+.14,1.255,z+lado*.172),.025,metal,20)
        for i in range(12):
            a=i*math.tau/12
            tubo('Serrilha do foco',(x+.14+.054*math.cos(a),1.255+.054*math.sin(a),z+lado*.096),
                 (x+.14+.054*math.cos(a),1.255+.054*math.sin(a),z+lado*.136),.003,metal,6)
    curva('Cabo de microscopia',[(x+.17,1.06,z),(x+.39,1.023,z+.07),(3.15,1.023,z+.15)],.007,escuro)

try:
    bpy.context.window.scene=CENA
    manter=('Tampo de estudo','Pé tubular','Área de trabalho','Prancheta','Ficha de estudo',
      'Demarcação do posto','Zona dos postos','Fundo da estação','Moldura da lousa',
      'Superfície de giz','Bandeja de giz','Cabeçalho do desafio','Rodapé bancada',
      'Bancada de demonstração','Tampo anatômico','Área de demonstração','Apagador','Giz',
      'Frente gaveta','Puxador bancada','Haste luminária','Braço luminária','Luz de estudo',
      'Difusor de estudo','Clipe da ficha','Linha da ficha','Lápis de estudo','Faixa da estação',
      'Suporte osteológico','Base suporte')
    protegidos={o:vertices_mundo(o) for o in CENA.objects if o.type=='MESH' and o.name.startswith(manter)}
    for o in list(CENA.objects):
        if o not in protegidos: bpy.data.objects.remove(o,do_unlink=True)
    carvalho=material('Carvalho_autoral','ffffff',.59)
    pintura=material('Pintura_cal','d6d4c7',.95)
    forro=material('Forro_difuso','d2d0c2',.92,0,.10)
    linho=material('Linho_claro','c7c4b2',.94)
    difusor=material('Difusor_quente','fff0d2',.7,0,.30)
    vidro=material('Vidro_opaco','334e45',.35,.12)
    papel=material('Folhas','ffffff',.97)
    encadernacao=material('Encadernacao','ffffff',.67)
    imagem(carvalho,'carvalho.png'); imagem(papel,'folhas.png'); imagem(encadernacao,'encadernacao.png')
    sh=next(n for n in carvalho.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    t=carvalho.node_tree.nodes.new('ShaderNodeTexImage'); t.image=bpy.data.images.load(str(TEMP/'carvalho-normal.png')); t.image.colorspace_settings.name='Non-Color'
    normal=carvalho.node_tree.nodes.new('ShaderNodeNormalMap'); normal.inputs['Strength'].default_value=.25
    carvalho.node_tree.links.new(t.outputs['Color'],normal.inputs['Color']); carvalho.node_tree.links.new(normal.outputs['Normal'],sh.inputs['Normal'])
    t=carvalho.node_tree.nodes.new('ShaderNodeTexImage'); t.image=bpy.data.images.load(str(TEMP/'carvalho-rough.png')); t.image.colorspace_settings.name='Non-Color'
    sep=carvalho.node_tree.nodes.new('ShaderNodeSeparateColor'); carvalho.node_tree.links.new(t.outputs['Color'],sep.inputs['Color']); carvalho.node_tree.links.new(sep.outputs['Green'],sh.inputs['Roughness'])
    # Arquitetura: caixilhos, lambris com painéis, rodapé e forro com encaixes.
    for z in (-3.92,3.92):
        caixa('Parede de cal',(0,1.60,z),(7.2,3.2,.12),pintura,0)
        caixa('Rodapé transversal',(0,.10,z+(.075 if z<0 else -.075)),(7.15,.2,.055),carvalho,.008)
    for lado in (-1,1):
        x=lado*3.54
        caixa('Parede lateral',(x,1.60,0),(.12,3.2,8),pintura,0)
        caixa('Rodapé contínuo',(lado*3.456,.09,0),(.045,.18,7.85),carvalho,.008)
        caixa('Moldura superior de lambril',(lado*3.453,.96,0),(.055,.065,7.82),carvalho,.009)
        for z in (-3.2,-2.1,-1, .1,1.2,2.3,3.4):
            caixa('Painel de lambril',(lado*3.463,.51,z),(.028,.75,1.035),verde,.012)
            for dz in (-.527,.527): caixa('Montante do lambril',(lado*3.432,.51,z+dz),(.058,.82,.035),carvalho,.006)
    caixa('Forro claro',(0,3.235,0),(7.2,.075,8),forro,0)
    for x in (-3.35,-1.70,0,1.70,3.35):
        caixa('Longarina de forro',(x,3.09,0),(.075,.20,7.75),carvalho,.012)
    for z in (-3.75,-2.20,-.65,.90,2.45,3.75):
        caixa('Travessa de forro',(0,3.09,z),(6.76,.20,.065),carvalho,.01)
    for x in (-1.70,1.70):
        for z in (-1.45,1.65):
            for dz in (-.57,.57): tubo('Suspensão de luminária',(x,3.16,z+dz),(x,2.91,z+dz),.005,metal,8)
            caixa('Perfil de luminária',(x,2.91,z),(.14,.07,1.46),escuro,.017)
            caixa('Difusor contínuo',(x,2.87,z),(.107,.012,1.37),difusor,.005)
    # Fachada didática: mesma placa, encaixada em marcenaria contínua.
    caixa('Painel do departamento',(0,2.73,-3.77),(6.66,.70,.13),carvalho,.025)
    caixa('Rebaixo da placa principal',(0,2.83,-3.68),(4.91,.41,.058),verde,.012)
    for x in (-3.30,3.30): caixa('Pilastra frontal',(x,1.61,-3.77),(.14,3.08,.13),carvalho,.016)
    for x,w in ((-2.40,1.75),(-.42,1.85),(1.82,2.24)):
        caixa('Painel acústico',(x,1.51,-3.827),(w,1.64,.032),linho,.025)
    estante(-2.40,-3.44)
    # Janela dupla, veneziana recuada e peitoril espesso.
    for z in (-1.8,1.35):
        caixa('Caixilho de janela',(-3.43,1.98,z),(.16,1.51,2.22),carvalho,.016)
        caixa('Plano difuso diurno',(-3.337,1.98,z),(.016,1.34,2.04),difusor,.003)
        for dz in (-.98,0,.98): caixa('Montante da janela',(-3.28,1.98,z+dz),(.08,1.40,.046),carvalho,.005)
        for y in (1.51,1.72,1.93,2.14,2.35,2.56): caixa('Lâmina da persiana',(-3.30,y,z),(.057,.02,1.97),linho,.003)
        caixa('Peitoril com retorno',(-3.25,1.245,z),(.35,.055,2.31),carvalho,.013)
    # Vitrine do acervo: mesma área anatômica, com juntas e suporte de exposição.
    x,z=1.82,-2.44
    caixa('Fundo da vitrine',(x,1.14,z-.225),(1.14,2.14,.045),verde,.013)
    for dx in (-.605,.605):
        caixa('Pilar da vitrine',(x+dx,1.14,z),(.073,2.20,.55),carvalho,.018)
        tubo('Canal de acabamento',(x+dx,.20,z+.284),(x+dx,2.08,z+.284),.006,latao,8)
    for y in (.105,2.18):
        caixa('Travessa encaixada da vitrine',(x,y,z),(1.35,.10,.62),carvalho,.022)
    caixa('Difusor de vitrine',(x,2.12,z),(.99,.012,.28),difusor,.004)
    # Bancada lateral com painel de serviços, gavetas e armários da mesma família.
    antes=set(CENA.objects)
    armario(0,0,2.24,.84,.78)
    for o in set(CENA.objects)-antes:
        o.matrix_world=Matrix.Translation(p((2.82,0,.10))) @ Matrix.Rotation(-math.pi/2,4,'Z') @ o.matrix_world
    caixa('Tampo cerâmico de microscopia',(2.79,.990,.10),(.91,.040,2.33),marfim,.016)
    caixa('Espelho técnico',(3.27,1.12,.1),(.024,.26,2.31),carvalho,.006)
    microscopio(2.62,-.28); microscopio(2.62,.65)
    for z in (-.42,.50):
        caixa('Tomada em painel',(3.25,1.16,z),(.027,.095,.12),marfim,.01)
    for x in (2.27,3.14): tubo('Suporte setor',(x,1.012,-.68),(x,1.98,-.68),.011,metal)
    caixa('Suporte placa de microscopia',(2.705,1.89,-.68),(1.04,.27,.05),carvalho,.01)
    for z in (-1.38,1.59):
        caixa('Painel de parede da bancada',(3.44,2.03,z),(.055,1.02,.85),carvalho,.018)
        caixa('Inserto de tecido',(3.406,2.03,z),(.009,.91,.74),linho,.012)
    # Retaguarda de estudo: biblioteca e bancada, sem cadeiras nos postos.
    estante(-2.36,3.43,1.72,True)
    antes=set(CENA.objects); armario(2.30,3.43,1.83,.78,.60)
    girar(set(CENA.objects)-antes,(2.30,0,3.43),math.pi)
    caixa('Painel do roteiro',(2.30,1.99,3.79),(1.93,1.55,.075),carvalho,.02)
    caixa('Tecido do painel',(2.30,1.99,3.742),(1.80,1.42,.02),linho,.015)
    for indice,dx in enumerate((-.40,.40)):
        caixa('Ficha afixada',(2.30+dx,2.08,3.725),(.61,.78,.008),papel,.002)
        cx=2.30+dx
        ficha=malha('Roteiro impresso',[(cx-.295,1.70,3.719),(cx+.295,1.70,3.719),
                    (cx+.295,2.46,3.719),(cx-.295,2.46,3.719)],[(0,1,2,3)],encadernacao,False,(0,1,0))
        uv=ficha.data.uv_layers.new(name='UVMap')
        for loop in ficha.data.loops:
            co=ficha.data.vertices[loop.vertex_index].co
            uv.data[loop.index].uv=(((.5-(co.x-cx)/.59)*.49)+indice*.5+.005,
                                   .005+(.5+(co.z-2.08)/.76)*.49)
        ficha['uv_autoral']=True
        tubo('Pino da ficha',(2.30+dx,2.41,3.713),(2.30+dx,2.41,3.725),.010,latao,10)
    for i in range(2):
        antes=set(CENA.objects); livros=livro(2.74,.97+i*.064,3.38,3+i,.05,.32,.24)
        tr=Matrix.Translation(p((2.74,.97+i*.064,3.38)))
        giro=tr @ Matrix.Rotation(math.pi/2,4,'Y') @ tr.inverted()
        for o in livros: o.matrix_world=giro@o.matrix_world
        minimo=min((o.matrix_world@v.co).z for o in livros for v in o.data.vertices)
        for o in livros: o.matrix_world=Matrix.Translation((0,0,.96+i*.061-minimo))@o.matrix_world
    # Livro aberto com folhas abauladas e textura de roteiro autoral.
    x,z=1.90,3.34
    caixa('Capa do caderno aberto',(x,.938,z),(.62,.015,.38),verde,.008)
    vs=[]; fs=[]; nx,nz=32,10
    for j in range(nz+1):
        for i in range(nx+1):
            dx=(i/nx-.5)*.59
            altura=.96+.031*math.sin(abs(dx)/.295*math.pi)+.006*(1-abs(dx)/.295)
            vs.append((x+dx,altura,z+(j/nz-.5)*.35))
    for j in range(nz):
        for i in range(nx):
            k=j*(nx+1)+i; fs.append((k,k+nx+1,k+nx+2,k+1))
    o=malha('Páginas abertas do caderno',vs,fs,encadernacao,True,(0,0,1))
    uv=o.data.uv_layers.new(name='UVMap')
    for loop in o.data.loops:
        co=o.data.vertices[loop.vertex_index].co
        uv.data[loop.index].uv=(.5-(co.x-x)/.59,.25-(co.y+z)/.35*.49)
    o['uv_autoral']=True
    curva('Fita no caderno',[(x,.969,z-.16),(x,.968,z),(x,.960,z+.18),(x,.939,z+.24)],.002,ambar)
    # Entrada com portas construídas, sem invadir corredor.
    for x in (-.55,.55): caixa('Batente da entrada',(x,1.18,3.78),(.085,2.36,.15),carvalho,.012)
    caixa('Bandeira da entrada',(0,2.39,3.78),(1.19,.095,.15),carvalho,.012)
    caixa('Folha da porta',(0,1.15,3.80),(1.05,2.28,.075),verde,.017)
    caixa('Moldura do visor',(0,1.70,3.75),(.49,.62,.035),carvalho,.01)
    caixa('Visor opaco',(0,1.70,3.728),(.39,.51,.012),vidro,.008)
    curva('Maçaneta de retorno',[(.33,1.08,3.73),(.33,1.08,3.68),(.46,1.08,3.68)],.012,latao)
    for o,antes in protegidos.items():
        assert vertices_mundo(o)==antes, f'Geometria protegida alterada: {o.name}'
    # Subir somente o conjunto da lousa: borda inferior a .83 m, nivelada ao
    # tampo branco anatômico. O suporte cresce para continuar apoiado no piso.
    elevacao = LAYOUT['elevacaoLousa']
    nomes_lousa = ('Moldura da lousa', 'Superfície de giz', 'Bandeja de giz',
                   'Apagador', 'Giz', 'Cabeçalho do desafio')
    movidos = []
    for o in protegidos:
        if o.name.startswith(nomes_lousa):
            o.location.z += elevacao
            movidos.append(o.name)
        elif o.name.startswith('Fundo da estação'):
            o.scale.z *= (1.82 + elevacao) / 1.82
            o.location.z += elevacao / 2
    bpy.context.view_layer.update()
    moldura = next(o for o in protegidos if o.name.startswith('Moldura da lousa'))
    tampo = next(o for o in protegidos if o.name.startswith('Tampo anatômico'))
    inferior = min((moldura.matrix_world @ v.co).z for v in moldura.data.vertices)
    superior = max((tampo.matrix_world @ v.co).z for v in tampo.data.vertices)
    assert abs(inferior - superior) < .001, 'Lousa deve começar no topo branco da bancada'
    objetos=[o for o in CENA.objects if o.type=='MESH']
    for o in objetos:
        o.data.transform(o.matrix_world); o.matrix_world.identity(); o.data.update()
        # O Blender em pt-BR cria cubos com "Mapa UV". A união por material
        # precisa do mesmo nome nos cubos e nas superfícies autoradas dos livros.
        if o.data.uv_layers.active:
            o.data.uv_layers.active.name='UVMap'
            o.data.uv_layers.active.active_render=True
        if o.get('uv_autoral'): continue
        uv=o.data.uv_layers.active or o.data.uv_layers.new(name='UVMap')
        for face in o.data.polygons:
            eixo=max(range(3),key=lambda i:abs(face.normal[i])); a,b=[(1,2),(0,2),(0,1)][eixo]
            for k in face.loop_indices:
                co=o.data.vertices[o.data.loops[k].vertex_index].co
                uv.data[k].uv=(co[a]*2,co[b]*(6 if o.data.materials[0]==papel else 1.3))
    # Bake estático e agrupamento por material; zero luzes adicionais no runtime.
    arquivo=RAIZ/'scripts/refinar-ambientes-duelo.py'
    defs=[n for n in ast.parse(arquivo.read_text(encoding='utf-8')).body if isinstance(n,ast.FunctionDef)]
    RAIOS=12; DIRECOES=[]
    for i in range(RAIOS):
        r=math.sqrt((i+.5)/RAIOS); a=i*2.399963229728653
        DIRECOES.append(Vector((r*math.cos(a),r*math.sin(a),math.sqrt(1-r*r))))
    env={**globals(),'MODO':'escola-revisao'}
    exec(compile(ast.Module(body=defs,type_ignores=[]),str(arquivo),'exec'),env)
    bvh=env['arvore'](objetos); env['acabamento'](objetos,bvh)
    piso=env['piso'](bvh,7.2,8,True)
    ambiente=env['exportar']('escola-medicina-revisao',env['agrupar'](objetos))
    solo=env['exportar']('piso-escola-revisao',[piso])
    result={'ambiente':ambiente,'piso':solo,'objetos_autorados':len(objetos),
            'elevacao_lousa':elevacao,'borda_inferior_lousa':inferior,'topo_tampo':superior,
            'pecas_lousa_elevadas':movidos,
            'elementos_protegidos':len(protegidos),'cena_original_preservada':ANTERIOR.name}
    bpy.data.libraries.write(str(TEMP/'escola-revisao.blend'),{CENA})
    (TEMP/'resumo.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
finally:
    bpy.context.window.scene=ANTERIOR
