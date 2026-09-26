"""Arena Médica: versão de estudo isolada, sem alterar a base nem a anatomia.

Autoria Blender métrica. Arquitetura e equipamentos são um conjunto; detalhes
construtivos, tecido e inscrições fazem parte dos assets, não da interface.
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
TEMP = RAIZ/'tmp_revisao'
PASTA = RAIZ/'public/models/props'
ANTERIOR = bpy.context.window.scene
CENA = bpy.data.scenes.new('VRmed_Arena_Revisao')
materiais = []

def p(v): return Vector((v[0], -v[2], v[1]))

def material(nome, hexadecimal, rough=.65, metal=0, emissao=0):
    m=bpy.data.materials.new('Revisao_'+nome); m.use_nodes=True
    c=[int(hexadecimal[i:i+2],16)/255 for i in (0,2,4)]
    c=[x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4 for x in c]
    sh=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    sh.inputs['Base Color'].default_value=(*c,1)
    sh.inputs['Roughness'].default_value=rough
    sh.inputs['Metallic'].default_value=metal
    sh.inputs['Emission Color'].default_value=(*c,1)
    sh.inputs['Emission Strength'].default_value=emissao
    materiais.append(m)
    return m

parede=material('Pintura_mineral','b9c4be',.92)
forro=material('Forro_difuso','c6cfca',.92,0,.14)
branco=material('Polimero_ceramica','dfe3dc',.34)
verde=material('Esmalte_satinado','527b7e',.46,.06)
azul=material('Revestimento_petroleo','233e47',.65)
metal=material('Inox_escovado','9da9aa',.46,.72)
preto=material('Borracha','1b2428',.91)
tecido=material('Tecido','93b3b0',.97)
linho=material('Linho','dee0d0',.99)
luz=material('Luz_difusa','fff2d5',.5,0,.65)
visor=material('Visor','172d36',.24,.15)
coral=material('Identificacao_coral','c57354',.66)
tinta=material('Inscricoes','ffffff',.75)
sh=next(n for n in tinta.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
tex=tinta.node_tree.nodes.new('ShaderNodeTexImage')
tex.image=bpy.data.images.load(str(TEMP/'atlas-arena.png'),check_existing=False)
tinta.node_tree.links.new(tex.outputs['Color'],sh.inputs['Base Color'])

def caixa(nome, pos, tam, mat, borda=.015):
    bpy.ops.mesh.primitive_cube_add(size=1,location=p(pos))
    o=bpy.context.object; o.name=nome; o.dimensions=(tam[0],tam[2],tam[1])
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.data.materials.append(mat)
    if borda:
        b=o.modifiers.new('Raio construtivo','BEVEL'); b.width=min(borda,min(tam)*.28); b.segments=3
        bpy.ops.object.modifier_apply(modifier=b.name)
    return o

def tubo(nome,a,b,r,mat,lados=16):
    a,b=p(a),p(b)
    bpy.ops.mesh.primitive_cylinder_add(vertices=lados,radius=r,depth=(b-a).length,location=(a+b)/2)
    o=bpy.context.object; o.name=nome; o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler()
    o.data.materials.append(mat)
    for f in o.data.polygons: f.use_smooth=len(f.vertices)==4
    return o

def malha(nome,vs,fs,mat,suave=False):
    m=bpy.data.meshes.new(nome); m.from_pydata([p(v) for v in vs],[],fs); m.materials.append(mat)
    bm=bmesh.new(); bm.from_mesh(m); bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.to_mesh(m); bm.free()
    for f in m.polygons: f.use_smooth=suave
    o=bpy.data.objects.new(nome,m); CENA.collection.objects.link(o)
    return o

def curva(nome,pontos,r,mat):
    c=bpy.data.curves.new(nome,'CURVE'); c.dimensions='3D'; c.resolution_u=8; c.bevel_depth=r; c.bevel_resolution=2
    s=c.splines.new('BEZIER'); s.bezier_points.add(len(pontos)-1)
    for v,pos in zip(s.bezier_points,pontos): v.co=p(pos); v.handle_left_type=v.handle_right_type='AUTO'
    o=bpy.data.objects.new(nome,c); CENA.collection.objects.link(o); c.materials.append(mat)
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active=o
    bpy.ops.object.convert(target='MESH'); return bpy.context.object

def girar(objetos,centro,angulo):
    tr=Matrix.Translation(p(centro)); m=tr @ Matrix.Rotation(angulo,4,'Z') @ tr.inverted()
    for o in objetos: o.matrix_world=m@o.matrix_world

def inscricao(indice,centro,w,h,giro=0):
    x,y,z=centro
    o=malha('Inscrição impressa',[(x-w/2,y-h/2,z),(x+w/2,y-h/2,z),(x+w/2,y+h/2,z),(x-w/2,y+h/2,z)],[(0,1,2,3)],tinta)
    uv=o.data.uv_layers.new(name='UVMap')
    u=(indice%2)*.5; v=1-(indice//2+1)*.125
    # Pequena margem no atlas elimina mistura entre etiquetas nos mipmaps.
    # BMesh pode reorganizar loops ao recalcular as normais. A inscrição depende
    # da posição física, nunca da ordem interna dos vértices.
    for loop in o.data.loops:
        co=o.data.vertices[loop.vertex_index].co
        fu=(co.x-(x-w/2))/w; fv=(co.z-(y-h/2))/h
        uv.data[loop.index].uv=(u+.003+fu*.494,v+.003+fv*.119)
    if giro: girar([o],centro,giro)
    return o

def placa(indice,pos,w,h,giro=0):
    x,y,z=pos; antes=set(CENA.objects)
    caixa('Perfil fino de sinalização',(x,y,z-.021),(w+.026,h+.026,.042),azul,.01)
    caixa('Alumínio pintado',(x,y,z),(w,h,.015),branco,.004)
    inscricao(indice,(x,y,z+.0085),w-.014,h-.014)
    if giro: girar(set(CENA.objects)-antes,pos,giro)

def roda(x,z):
    for dx in (-.026,.026):
        tubo('Roda dupla',(x+dx-.015,.095,z),(x+dx+.015,.095,z),.073,preto,20)
    tubo('Eixo',(x-.055,.095,z),(x+.055,.095,z),.027,metal)
    caixa('Garfo do rodízio',(x,.161,z),(.045,.11,.092),metal,.008)
    tubo('Pino giratório',(x,.18,z),(x,.245,z),.027,metal)
    caixa('Pedal de trava',(x,.154,z+.079),(.073,.018,.081),coral,.005)

def frasco(x,y,z,indice=10):
    tubo('Frasco de treino',(x,y+.018,z),(x,y+.205,z),.061,branco,24)
    tubo('Ombro do frasco',(x,y+.205,z),(x,y+.230,z),.049,branco,24)
    tubo('Tampa estriada',(x,y+.225,z),(x,y+.26,z),.041,verde,24)
    for i in range(12):
        a=i*math.tau/12
        tubo('Estria da tampa',(x+.041*math.cos(a),y+.23,z+.041*math.sin(a)),(x+.041*math.cos(a),y+.255,z+.041*math.sin(a)),.0028,verde,6)
    inscricao(indice,(x,y+.12,z+.0615),.085,.053)

def estojo(x,y,z,indice):
    caixa('Embalagem de apoio',(x,y+.105,z),(.36,.21,.25),branco,.01)
    caixa('Dobra da tampa',(x,y+.202,z),(.368,.023,.257),verde,.005)
    inscricao(indice,(x,y+.118,z+.126),.30,.09)

def puxador(x,y,z,w=.26):
    for dx in (-w/2,w/2): tubo('Fixação de alça',(x+dx,y,z),(x+dx,y,z+.032),.012,metal)
    curva('Alça dobrada',[(x-w/2,y,z+.023),(x-w/2+.02,y,z+.048),(x+w/2-.02,y,z+.048),(x+w/2,y,z+.023)],.012,metal)

def gabinete(x,z,w=2.1):
    caixa('Base recuada',(x,.065,z),(w-.16,.13,.53),preto,.012)
    caixa('Gabinete modular',(x,.49,z),(w,.78,.64),branco,.018)
    for i in range(3):
        a=x-w/3+i*w/3
        caixa('Junta de porta',(a,.49,z+.329),(w/3-.014,.744,.015),azul,.006)
        caixa('Frente laminada',(a,.49,z+.340),(w/3-.038,.722,.022),verde,.008)
        puxador(a,.76,z+.354,w*.14)
    caixa('Tampo de bancada',(x,.908,z),(w+.075,.068,.74),branco,.019)
    caixa('Espelho de bancada',(x,1.025,z-.314),(w+.06,.20,.025),branco,.004)

try:
    bpy.context.window.scene=CENA
    # Métodos de seção servem apenas à geometria, sem executar qualquer gerador antigo.
    arquivo=RAIZ/'scripts/dirigir-arte-arena.py'; arvore=ast.parse(arquivo.read_text(encoding='utf-8'))
    defs=[n for n in arvore.body if isinstance(n,ast.FunctionDef) and n.name=='arco_retangulo']
    etapa=next(n for n in arvore.body if isinstance(n,ast.Try))
    defs += [n for n in etapa.body if isinstance(n,ast.FunctionDef) and n.name in ('casca','painel')]
    escopo={**globals(),'cena':CENA}; exec(compile(ast.Module(body=defs,type_ignores=[]),str(arquivo),'exec'),escopo)
    casca,painel=escopo['casca'],escopo['painel']
    # Arquitetura: revestimento contínuo, juntas de instalação e rodapé sanitário.
    for lado in (-1,1):
        caixa('Parede lateral',(lado*4.59,1.8,0),(.10,3.6,9.2),parede,0)
        caixa('Rodapé sanitário',(lado*4.50,.11,0),(.10,.22,9.15),azul,.035)
        caixa('Proteção de parede',(lado*4.507,.94,.7),(.065,.18,7.3),verde,.028)
        for z in (-3.75,-2.25,-.75,.75,2.25,3.75):
            caixa('Junta vertical',(lado*4.531,2.16,z),(.012,2.60,.014),azul,0)
        caixa('Canal de luz indireta',(lado*4.37,3.28,0),(.22,.18,8.9),azul,.02)
        caixa('Difusor embutido',(lado*4.335,3.24,0),(.12,.018,8.6),luz,.004)
    for z in (-4.59,4.59): caixa('Parede de fechamento',(0,1.8,z),(9.2,3.6,.10),parede,0)
    # Teto modular: silhueta e ritmo de um espaço construído, não uma nave.
    caixa('Forro contínuo',(0,3.57,0),(9.2,.06,9.2),azul,0)
    for x in (-3.6,-2.4,-1.2,0,1.2,2.4,3.6):
        for z in (-3.6,-2.4,-1.2,0,1.2,2.4,3.6):
            caixa('Placa acústica',(x,3.526,z),(1.17,.028,1.17),forro,.008)
    for x in (-2.4,2.4):
        for z in (-2.4,0,2.4):
            caixa('Caixilho de luminária',(x,3.483,z),(1.19,.06,1.19),metal,.012)
            caixa('Difusor de luminária',(x,3.447,z),(1.09,.012,1.09),luz,.008)
    # Frente: painéis completos, marcenaria e bancada com espessuras consistentes.
    caixa('Parede protagonista',(0,1.93,-4.47),(4.10,3.24,.16),azul,.06)
    for x in (-1.95,1.95):
        caixa('Montante do pórtico',(x,1.74,-3.25),(.16,3.48,.26),verde,.03)
    caixa('Travessa do pórtico',(0,3.415,-3.25),(4.04,.32,.26),verde,.035)
    placa(0,(0,3.415,-3.105),3.68,.29)
    for x,indice in ((-3.30,1),(3.30,2)):
        caixa('Painel técnico da bancada',(x,1.87,-4.445),(2.14,3.05,.12),verde,.03)
        gabinete(x,-4.04)
        caixa('Fundo do nicho',(x,2.23,-4.37),(2.09,1.22,.045),azul,.006)
        for dx in (-1.015,1.015): caixa('Lateral superior',(x+dx,2.24,-4.16),(.06,1.26,.46),branco,.008)
        for y in (1.62,2.23,2.85): caixa('Prateleira embutida',(x,y,-4.14),(2.10,.045,.48),branco,.009)
        caixa('Perfil de iluminação',(x,1.58,-4.1),(1.98,.025,.22),luz,.003)
        if x<0:
            for dx in (-.70,-.27,.21,.68): estojo(x+dx,1.645,-4.11,8 if dx<0 else 9)
            for dx in (-.63,-.20,.23,.66): frasco(x+dx,2.252,-4.09)
            estojo(x-.61,.944,-4.05,8); frasco(x+.62,.944,-4.13)
        else:
            for dx in (-.51,.51):
                painel('Porta superior',(x+dx,2.24,-3.875),.977,1.19,.036,branco,.028)
                # Visores opacos evitam transparência ordenada e custo estéreo.
                painel('Vidro acetinado',(x+dx,2.33,-3.850),.71,.72,.010,visor,.035)
                puxador(x+dx,1.80,-3.84,.24)
            estojo(x-.64,.944,-4.04,9)
        placa(indice,(x,3.13,-4.355),1.97,.28)
        for dx in (-.52,.52):
            caixa('Tomada de bancada',(x+dx,1.28,-4.351),(.14,.14,.020),branco,.012)
            for f in (-.031,.031): tubo('Encaixe elétrico',(x+dx+f,1.28,-4.338),(x+dx+f,1.28,-4.333),.008,preto,8)
    # Janela de observação: caixilho, persianas e peitoril de verdade.
    caixa('Nicho da janela',(-4.48,2.05,-.15),(.13,1.53,2.63),azul,.025)
    caixa('Vidro difusor',(-4.402,2.05,-.15),(.016,1.36,2.45),luz,.005)
    for y in np.linspace(1.47,2.63,10): caixa('Lâmina de persiana',(-4.36,float(y),-.15),(.11,.026,2.40),branco,.004)
    for z in (-1.3,1.0): tubo('Guia de persiana',(-4.29,1.42,z),(-4.29,2.7,z),.006,metal,8)
    caixa('Peitoril',(-4.34,1.31,-.15),(.35,.065,2.73),branco,.02)

    # Carrinho técnico: gavetas com folga, perfil de puxada e guias, não riscos pintados.
    x,z=-2.91,-1.43
    for dx in (-.41,.41):
        for dz in (-.30,.30): roda(x+dx,z+dz)
    casca('Para-choque do carrinho',(x,0,z),[(.245,1.10,.89,0,0),(.31,1.14,.91,0,0),(.35,1.06,.82,0,0)],preto,raio=.11)
    casca('Estrutura do carrinho',(x,0,z),[(.32,1.01,.78,0,0),(.94,1.01,.78,0,0)],branco,raio=.06)
    for i,y in enumerate((.39,.50,.61,.72,.85)):
        h=.09 if i<4 else .13
        painel('Gaveta com junta',(x,y,z+.398),.84,h,.025,verde,.016)
        caixa('Canal de puxada',(x,y+h/2-.012,z+.422),(.68,.017,.015),azul,.004)
        caixa('Lábio metálico',(x,y+h/2-.004,z+.436),(.70,.012,.025),metal,.004)
        inscricao(8 if i<2 else 9,(x-.31,y-.005,z+.413),.13,.035)
    casca('Tampo bandeja',(x,0,z),[(.951,1.10,.87,0,0),(.998,1.12,.89,0,0),(1.025,1.04,.81,0,0)],metal,raio=.08)
    caixa('Tapete removível',(x,1.028,z),(.88,.013,.64),azul,.04)
    for dx in (-.47,.47):
        curva('Guarda contínua',[(x+dx,1.015,z-.33),(x+dx,1.13,z-.28),(x+dx,1.13,z+.28),(x+dx,1.015,z+.33)],.013,metal)
    curva('Pega de transporte',[(x-.49,.85,z-.24),(x-.64,.99,z-.24),(x-.64,.99,z+.24),(x-.49,.85,z+.24)],.021,verde)
    # Cuba reniforme estilizada: parede e rebaixo modelados.
    vs=[]; n=40
    for altura,escala in ((1.044,.82),(1.080,1),(1.090,1.01),(1.080,.92),(1.050,.72)):
        for i in range(n):
            a=i*math.tau/n; rr=.14*(1-.29*math.cos(a))
            vs.append((x-.18+rr*math.cos(a)*escala,altura,z+rr*math.sin(a)*.67*escala))
    fs=[(k*n+i,k*n+(i+1)%n,(k+1)*n+(i+1)%n,(k+1)*n+i) for k in range(4) for i in range(n)]
    fs.append(tuple(4*n+i for i in reversed(range(n))))
    malha('Cuba de instrumental',vs,fs,metal,True)
    for dz in (-.10,.015,.13):
        curva('Pinça de demonstração',[(x+.03,1.050,z+dz),(x+.20,1.050,z+dz+.016),(x+.32,1.050,z+dz+.033)],.005,metal)
        curva('Outra haste da pinça',[(x+.03,1.05,z+dz),(x+.20,1.05,z+dz+.046),(x+.32,1.05,z+dz+.036)],.005,metal)
    # Estação de exame com braços articulados, console inclinado e sonda encaixada.
    x,z=3.08,-1.84
    for dx in (-.36,.36):
        for dz in (-.30,.30): roda(x+dx,z+dz)
    casca('Base moldada da estação',(x,0,z),[(.23,1.02,.86,0,0),(.30,1.05,.88,0,0),(.37,.70,.56,0,-.05)],verde,raio=.16)
    casca('Corpo inclinado',(x,0,z),[(.34,.46,.44,0,-.06),(.48,.47,.39,0,-.07),(.88,.40,.37,0,.015),(1.03,.57,.49,0,.08)],branco,raio=.13)
    casca('Console com rebaixo',(x,0,z),[(1.00,.75,.59,0,.06),(1.075,.96,.71,0,.06),(1.14,.91,.64,0,.025)],branco,raio=.10)
    caixa('Teclado de membrana',(x,1.148,z+.02),(.76,.016,.43),azul,.013)
    for j in range(3):
        for i in range(7): caixa('Tecla côncava',(x-.30+i*.069,1.163,z-.11+j*.074),(.051,.016,.048),branco,.007)
    for dx in (.20,.30): tubo('Seletor giratório',(x+dx,1.162,z+.15),(x+dx,1.19,z+.15),.025,metal,20)
    tubo('Aro trackball',(x+.25,1.16,z-.09),(x+.25,1.18,z-.09),.058,metal,24)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20,ring_count=10,radius=.048,location=p((x+.25,1.178,z-.09)))
    bpy.context.object.data.materials.append(branco)
    curva('Braço articulado',[(x,1.08,z-.22),(x,1.38,z-.40),(x,1.60,z-.32)],.038,metal)
    for y,zz in ((1.37,z-.40),(1.60,z-.32)): tubo('Articulação',(x-.052,y,zz),(x+.052,y,zz),.068,verde,20)
    painel('Carcaça do monitor',(x,1.80,z-.29),1.00,.66,.12,branco,.055)
    painel('Moldura da tela',(x,1.80,z-.22),.94,.60,.023,preto,.045)
    painel('Tela escura',(x,1.81,z-.202),.85,.48,.009,visor,.035)
    inscricao(11,(x,1.80,z-.195),.70,.125)
    for i in range(14): caixa('Dissipador traseiro',(x-.29+i*.044,1.74,z-.356),(.012,.25,.012),azul,.002)
    for i in range(6): caixa('Respiro inferior',(x,.49+i*.047,z+.163),(.25,.014,.012),azul,.003)
    curva('Cabo da sonda',[(x+.32,1.0,z),(x+.49,.55,z+.1),(x+.66,.66,z+.12),(x+.59,1.20,z+.08)],.011,preto)
    casca('Sonda com empunhadura',(x+.59,0,z+.08),[(1.16,.074,.08,0,0),(1.31,.10,.10,0,0),(1.36,.16,.065,0,0)],branco,raio=.03)
    caixa('Apoio da sonda',(x+.58,1.18,z+.03),(.18,.08,.20),verde,.023)
    inscricao(13,(x,.76,z+.212),.30,.092)

    # Leito: cinemática visual, cabeceiras vazadas e tecido com caimento.
    x,z=-3.02,2.50
    for dx in (-.47,.47):
        for dz in (-.85,.85): roda(x+dx,z+dz)
    caixa('Chassi inferior',(x,.29,z),(1.12,.12,1.98),verde,.03)
    for dx in (-.31,.31):
        tubo('Tesoura de elevação',(x+dx,.33,z-.6),(x+dx,.60,z+.6),.038,metal)
        tubo('Tesoura cruzada',(x+dx,.33,z+.6),(x+dx,.60,z-.6),.038,metal)
    casca('Estrado do leito',(x,0,z),[(.60,1.19,2.23,0,0),(.70,1.19,2.23,0,0)],azul,raio=.12)
    casca('Colchão com borda',(x,0,z),[(.71,1.10,2.10,0,0),(.77,1.14,2.14,0,0),(.86,1.07,2.08,0,0)],linho,raio=.14)
    for lado in (-1,1):
        curva('Grade de segurança',[(x+lado*.63,.68,z-.77),(x+lado*.63,1.02,z-.65),(x+lado*.63,1.02,z+.61),(x+lado*.63,.68,z+.76)],.022,metal)
        tubo('Travessa da grade',(x+lado*.63,.86,z-.65),(x+lado*.63,.86,z+.65),.016,metal)
        for dz in (-.56,.56): caixa('Trava da grade',(x+lado*.63,.70,z+dz),(.07,.12,.1),verde,.02)
    for dz in (-1.16,1.16):
        for dx in (-.46,.46): tubo('Haste cabeceira',(x+dx,.60,z+dz),(x+dx,1.12,z+dz),.022,metal)
        # Moldura aberta: pega atravessável, não retângulo colado.
        for dx in (-.48,.48): caixa('Lateral cabeceira',(x+dx,1.0,z+dz),(.13,.34,.073),branco,.03)
        for y in (.86,1.14): caixa('Travessa cabeceira',(x,y,z+dz),(1.06,.11,.077),branco,.025)
        caixa('Inserto da cabeceira',(x,.93,z+dz),(.86,.16,.062),verde,.025)
    vs=[]; fs=[]; nx,nz=30,30
    for j in range(nz+1):
        zz=z-.87+j/nz*1.48
        for i in range(nx+1):
            dx=(i/nx-.5)*1.38; queda=max(0,(abs(dx)-.56)/.13)
            # O caimento começa fora da borda do colchão; não o atravessa.
            yy=.90-.25*queda**1.2+.012*math.sin(j*.64+i*.39)+.007*math.sin(i*.9-j*.45)
            vs.append((x+dx,yy,zz))
    for j in range(nz):
        for i in range(nx):
            k=j*(nx+1)+i; fs.append((k,k+1,k+nx+2,k+nx+1))
    cobertura=malha('Cobertura com costura e queda',vs,fs,tecido,True)
    sol=cobertura.modifiers.new('Espessura da cobertura','SOLIDIFY'); sol.thickness=.004
    bpy.context.view_layer.objects.active=cobertura; bpy.ops.object.modifier_apply(modifier=sol.name)
    for lado in (-1,1): curva('Costura da cobertura',[(x+lado*.668,.64+.012*math.sin(j*.7),z-.85+j*.12) for j in range(13)],.0025,linho)
    # Travesseiro abaulado por seções, mantendo borda costurada.
    casca('Travesseiro',(x,0,z+.75),[(.864,.61,.31,0,0),(.89,.78,.43,0,0),(.98,.66,.34,0,0),(1.00,.42,.20,0,0)],linho,raio=.09)
    # Cabeceira técnica e apoio posterior.
    caixa('Painel do leito',(-2.95,1.75,4.44),(2.79,2.95,.12),verde,.04)
    caixa('Calha técnica',(-2.95,1.55,4.30),(2.5,.24,.18),branco,.025)
    for i in range(4):
        xx=-3.72+i*.33
        caixa('Módulo de conexão',(xx,1.55,4.19),(.19,.17,.034),azul,.012)
        tubo('Conector de demonstração',(xx,1.55,4.171),(xx,1.55,4.153),.035,metal)
    placa(3,(-2.95,2.58,4.362),2.52,.35,math.pi)
    caixa('Luz de cabeceira',(-2.95,2.08,4.24),(2.31,.08,.12),branco,.013)
    caixa('Difusor de cabeceira',(-2.95,2.045,4.19),(2.19,.014,.08),luz,.003)
    # Cortina com pregas variáveis e barra: tecido opaco, não múltiplos planos.
    curva('Trilho de cortina',[(-4.3,2.99,1.13),(-1.86,2.99,1.13),(-1.78,2.99,1.23),(-1.78,2.99,3.9)],.018,metal)
    vs=[]; fs=[]
    for j in range(18):
        y=.27+j/17*2.56
        for i in range(61):
            xx=-4.27+i/60*.60
            zz=1.13+.045*math.cos(i*.73)+.008*math.sin(j*.7+i*.4)
            vs.append((xx,y,zz))
    for j in range(17):
        for i in range(60):
            k=j*61+i; fs.append((k,k+1,k+62,k+61))
    cortina=malha('Cortina hospitalar pregueada',vs,fs,tecido,True)
    sol=cortina.modifiers.new('Espessura do tecido','SOLIDIFY'); sol.thickness=.004
    bpy.context.view_layer.objects.active=cortina; bpy.ops.object.modifier_apply(modifier=sol.name)
    for i in range(7): tubo('Suspensor de cortina',(-4.23+i*.08,2.83,1.13),(-4.23+i*.08,2.99,1.13),.007,metal,8)
    # Apoio do fundo: mesmo sistema construtivo, orientação oposta.
    antes=set(CENA.objects); gabinete(2.98,4.06,2.34)
    for dx in (-.75,0,.75): estojo(2.98+dx,.944,4.02,8 if dx<0 else 9)
    girar(set(CENA.objects)-antes,(2.98,0,4.06),math.pi)
    placa(4,(2.98,2.64,4.34),2.28,.30,math.pi)
    for y in (1.51,2.08):
        caixa('Prateleira do apoio',(2.98,y,4.17),(2.37,.05,.55),branco,.012)
        for dx in (-.8,0,.8):
            for dy in (.065,.145): caixa('Tecido dobrado',(2.98+dx,y+dy,4.10),(.57,.066,.38),linho,.027)
    # Entrada: portas, guarnições e vidro fosco sólido (sem transparência).
    for x in (-.46,.46):
        caixa('Folha da porta',(x,1.22,4.43),(.90,2.43,.09),verde,.012)
        caixa('Visor fosco',(x,1.64,4.375),(.41,.64,.023),visor,.03)
        caixa('Proteção inferior',(x,.3,4.372),(.78,.38,.018),metal,.008)
        tubo('Puxador vertical',(x+(.26 if x<0 else -.26),.98,4.33),(x+(.26 if x<0 else -.26),1.39,4.33),.018,metal)
    for x in (-.96,.96): caixa('Batente',(x,1.24,4.405),(.07,2.48,.15),branco,.013)
    caixa('Batente superior',(0,2.49,4.405),(1.99,.085,.15),branco,.01)
    placa(5,(0,2.78,4.29),2.36,.29,math.pi)
    # Posto lateral: cuba com interior, torneira curva e dispensadores.
    antes=set(CENA.objects); x,z=0,0
    gabinete(0,0,1.45)
    # Anel da cuba com parede interior, sem tampo atravessando a abertura.
    # A cuba é de sobrepor; seu fundo fica acima do tampo existente.
    vs=[]; fs=[]; n=40
    for y,w,d in ((.944,.72,.48),(1.055,.76,.50),(1.069,.73,.47),(1.046,.63,.37),(.959,.57,.31)):
        for i in range(n):
            a=math.tau*i/n; vs.append((w*.5*math.copysign(abs(math.cos(a))**.5,math.cos(a)),y,d*.5*math.copysign(abs(math.sin(a))**.5,math.sin(a))))
    for k in range(4):
        for i in range(n): fs.append((k*n+i,k*n+(i+1)%n,(k+1)*n+(i+1)%n,(k+1)*n+i))
    fs.append(tuple(4*n+i for i in reversed(range(n))))
    malha('Cuba de sobrepor',vs,fs,metal,True)
    curva('Torneira monocomando',[(.22,.945,-.23),(.22,1.30,-.23),(.10,1.35,-.19),(0,1.28,-.09)],.018,metal)
    tubo('Ralo',(0,.961,0),(0,.964,0),.026,preto)
    caixa('Dispensador',(-.5,1.62,-.25),(.24,.34,.16),branco,.035)
    caixa('Janela do dispensador',(-.5,1.63,-.163),(.09,.17,.012),visor,.009)
    caixa('Toalheiro',(.45,1.70,-.23),(.37,.29,.16),branco,.025)
    caixa('Papel',(.45,1.49,-.15),(.24,.20,.012),linho,.003)
    objetos=set(CENA.objects)-antes
    for o in objetos: o.matrix_world=Matrix.Translation(p((4.12,0,2.45))) @ Matrix.Rotation(-math.pi/2,4,'Z') @ o.matrix_world
    placa(6,(4.34,2.32,2.45),1.6,.28,-math.pi/2)
    # Monitor de treino do leito: estado dinâmico fica na camada web, mesma posição.
    caixa('Braço do monitor',(-4.335,1.73,2.65),(.41,.085,.085),metal,.012)
    antes=set(CENA.objects)
    painel('Monitor do leito',(0,0,0),.84,.58,.13,branco,.05)
    painel('Borda do visor',(0,0,.073),.77,.50,.018,preto,.03)
    for o in set(CENA.objects)-antes: o.matrix_world=Matrix.Translation(p((-4.07,1.76,2.65))) @ Matrix.Rotation(math.pi/2,4,'Z') @ o.matrix_world

    # Transforma tudo para coordenadas mundiais e aplica UV métrica aos microacabamentos.
    objetos=[o for o in CENA.objects if o.type=='MESH']
    for o in objetos:
        o.data.transform(o.matrix_world); o.matrix_world.identity(); o.data.update()
        if o.data.materials[0] != tinta:
            uv=o.data.uv_layers.active or o.data.uv_layers.new(name='UVMap')
            for face in o.data.polygons:
                eixo=max(range(3),key=lambda i:abs(face.normal[i])); a,b=[(1,2),(0,2),(0,1)][eixo]
                for k in face.loop_indices:
                    v=o.data.vertices[o.data.loops[k].vertex_index].co
                    uv.data[k].uv=(v[a]*4,v[b]*4)
    for mat,nome in ((metal,'metal'),(tecido,'tecido'),(linho,'tecido')):
        sh=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED'); nos=mat.node_tree.nodes; links=mat.node_tree.links
        t=nos.new('ShaderNodeTexImage'); t.image=bpy.data.images.load(str(TEMP/f'{nome}-rough.png'),check_existing=True); t.image.colorspace_settings.name='Non-Color'
        sep=nos.new('ShaderNodeSeparateColor'); links.new(t.outputs['Color'],sep.inputs['Color']); links.new(sep.outputs['Green'],sh.inputs['Roughness'])
        t=nos.new('ShaderNodeTexImage'); t.image=bpy.data.images.load(str(TEMP/f'{nome}-normal.png'),check_existing=True); t.image.colorspace_settings.name='Non-Color'
        norm=nos.new('ShaderNodeNormalMap'); norm.inputs['Strength'].default_value=.35
        links.new(t.outputs['Color'],norm.inputs['Color']); links.new(norm.outputs['Normal'],sh.inputs['Normal'])
    # Oclusão estática, sem sombra dinâmica. Funções de acabamento não executam outros geradores.
    caminho=RAIZ/'scripts/refinar-ambientes-duelo.py'; mod=ast.parse(caminho.read_text(encoding='utf-8'))
    defs=[n for n in mod.body if isinstance(n,ast.FunctionDef)]
    RAIOS=12; DIRECOES=[]
    for i in range(RAIOS):
        r=math.sqrt((i+.5)/RAIOS); a=i*2.399963229728653
        DIRECOES.append(Vector((r*math.cos(a),r*math.sin(a),math.sqrt(1-r*r))))
    env={**globals(),'MODO':'arena-revisao'}; exec(compile(ast.Module(body=defs,type_ignores=[]),str(caminho),'exec'),env)
    bvh=env['arvore'](objetos)
    # Mantém os materiais autorados; só grava oclusão nos vértices.
    for o in objetos:
        m=o.data; cor=m.color_attributes.new(name='Contato',type='BYTE_COLOR',domain='CORNER'); m.color_attributes.active_color=cor; cache={}
        emissivo=o.data.materials[0]==luz
        for f in m.polygons:
            for k in f.loop_indices:
                vi=m.loops[k].vertex_index; n=m.corner_normals[k].vector; key=(vi,*(round(a,3) for a in n))
                if key not in cache:
                    ao=1 if emissivo else env['oclusao'](bvh,m.vertices[vi].co,n)
                    cache[key]=(ao,ao,ao,1)
                cor.data[k].color=cache[key]
    piso=env['piso'](bvh,9.2,9.2,escola=True,cor_hospital=(.34,.40,.39))
    # Piso contínuo de vinil: função usa base Escola sem juntas, mais clara que o anterior.
    ambiente=env['exportar']('arena-medica-revisao',env['agrupar'](objetos))
    solo=env['exportar']('piso-arena-revisao',[piso])
    result={'ambiente':ambiente,'piso':solo,'objetos_autorados':len(objetos),'cena_original':ANTERIOR.name,'anatomia_modificada':False}
    bpy.data.libraries.write(str(TEMP/'arena-revisao.blend'),{CENA})
    (TEMP/'resumo-arena.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
finally:
    bpy.context.window.scene=ANTERIOR
