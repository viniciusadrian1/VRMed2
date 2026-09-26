"""Revisão autoral da Escola pelo Blender MCP, sem substituir os originais.

Reutiliza os geradores antes da união das peças e as carcaças da Arena Médica.
Preserva geometria/posições da lousa, palco, postos e qualquer asset anatômico.
"""
import ast
import json
import math
import bpy
import numpy as np
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

RAIZ = Path(__file__).resolve().parents[1]
anterior = bpy.context.window.scene


def autoria_original():
    caminho = RAIZ/'scripts/criar-escola-medicina.py'
    arvore = ast.parse(caminho.read_text(encoding='utf-8'))
    etapa = next(n for n in arvore.body if isinstance(n,ast.Try))
    corpo=[]
    for n in etapa.body:
        if isinstance(n,ast.For) and isinstance(n.target,ast.Name) and n.target.id=='mat':
            break
        corpo.append(n)
    escopo={'__file__':str(caminho)}
    exec(compile(ast.Module(body=arvore.body[:arvore.body.index(etapa)]+corpo,type_ignores=[]),str(caminho),'exec'),escopo)
    # Somente definições geométricas: não executa a autoria/exportação do Hospital.
    helper=RAIZ/'scripts/dirigir-arte-arena.py'
    modulo=ast.parse(helper.read_text(encoding='utf-8'))
    defs=[n for n in modulo.body if isinstance(n,ast.FunctionDef) and n.name=='arco_retangulo']
    etapa=next(n for n in modulo.body if isinstance(n,ast.Try))
    defs += [n for n in etapa.body if isinstance(n,ast.FunctionDef) and n.name in ('casca','painel')]
    assert len(defs)==3, 'As três funções de carcaça precisam continuar disponíveis.'
    exec(compile(ast.Module(body=defs,type_ignores=[]),str(helper),'exec'),escopo)
    return escopo


try:
    base=autoria_original()
    cena=base['cena']; cena.name='VRmed_Direcao_Escola'
    caixa,tubo,casca,painel,p=(base[n] for n in ('caixa','tubo','casca','painel','p'))
    parede,marfim,madeira,escuro,verde,metal,latao,luz,tecido,ambar,azul=base['materiais']
    # Carvalho claro, verde profundo e cerâmica quente; nenhuma mudança de cor nos órgãos.
    for mat,cor,rugosidade,metalicidade in [
        (madeira,(.38,.235,.115),.52,0),(marfim,(.77,.75,.68),.40,0),
        (parede,(.58,.63,.57),.96,0),(verde,(.023,.059,.043),.87,0),
        (metal,(.41,.43,.40),.31,.60),(latao,(.40,.29,.12),.37,.58)]:
        sh=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
        sh.inputs['Base Color'].default_value=(*cor,1)
        sh.inputs['Roughness'].default_value=rugosidade
        sh.inputs['Metallic'].default_value=metalicidade
    sh=next(n for n in luz.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    sh.inputs['Base Color'].default_value=(.84,.78,.61,1)
    sh.inputs['Emission Color'].default_value=(.84,.78,.61,1)
    sh.inputs['Emission Strength'].default_value=.55

    def vertices_mundo(o):
        return sorted(tuple(round(v,5) for v in o.matrix_world @ x.co) for x in o.data.vertices)

    # Guardas antes/depois da autoria: não remodelar os elementos aprovados.
    nomes_protegidos=('Tampo de estudo','Pé tubular','Área de trabalho','Prancheta',
        'Ficha de estudo','Demarcação do posto','Zona dos postos','Fundo da estação',
        'Moldura da lousa','Superfície de giz','Bandeja de giz','Cabeçalho do desafio',
        'Rodapé bancada','Bancada de demonstração','Tampo anatômico','Área de demonstração')
    protegidos={o:vertices_mundo(o) for o in cena.objects if o.type=='MESH' and o.name.startswith(nomes_protegidos)}
    substituir=('Armário de laboratório','Tampo laboratório','Porta de apoio','Puxador de apoio',
        'Base microscópio','Braço microscópio','Cabeça microscópio','Ocular','Platina microscópio',
        'Revólver das objetivas','Objetiva','Anel da objetiva','Ajuste de foco','Botão de foco',
        'Lâmina de estudo','Iluminador','Biblioteca de atlas','Prateleira','Capa de atlas',
        'Lombada do atlas','Painel acústico','Montante vitrine','Vitrine base e topo',
        'Luminária','Difusor')
    for o in list(cena.objects):
        # A luminária do palco é preservada, inclusive seu difusor específico.
        if o.name.startswith('Difusor de estudo'):
            continue
        if o.name.startswith(substituir):
            assert o not in protegidos
            bpy.data.objects.remove(o,do_unlink=True)

    def cabo(nome,pontos,raio,mat):
        curva=bpy.data.curves.new(nome,'CURVE'); curva.dimensions='3D'
        curva.resolution_u=5; curva.bevel_depth=raio; curva.bevel_resolution=1
        spline=curva.splines.new('BEZIER'); spline.bezier_points.add(len(pontos)-1)
        for v,pos in zip(spline.bezier_points,pontos):
            v.co=p(pos); v.handle_left_type=v.handle_right_type='AUTO'
        o=bpy.data.objects.new(nome,curva); cena.collection.objects.link(o)
        curva.materials.append(mat)
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
        bpy.context.view_layer.objects.active=o; bpy.ops.object.convert(target='MESH')
        return bpy.context.object

    def painel_lateral(nome,centro,w,h,d,mat,giro=-math.pi/2,raio=.045):
        o=painel(nome,(0,0,0),w,h,d,mat,raio)
        o.data.transform(Matrix.Translation(p(centro)) @ Matrix.Rotation(giro,4,'Z'))
        return o

    def atlas(x,y,z,w,h,mat,inclinacao=0):
        objetos=[caixa('Miolo do atlas',(x,y+h/2,z),(w-.012,h-.016,.215),marfim,.004)]
        for dx in (-w/2,w/2):
            objetos.append(caixa('Capa rígida',(x+dx,y+h/2,z),(.012,h,.23),mat,.003))
        objetos.append(caixa('Lombada costurada',(x,y+h/2,z+.118),(w,h,.022),mat,.006))
        for dh in (.06,h-.055):
            objetos.append(caixa('Marcação da lombada',(x,y+dh,z+.133),(w*.70,.008,.004),latao,0))
        for o in objetos:
            # Giro pequeno e coerente no conjunto inteiro, sem livros flutuando.
            m=Matrix.Translation(p((x,y,z))) @ Matrix.Rotation(inclinacao,4,'Y') @ Matrix.Translation(-p((x,y,z)))
            o.matrix_world=m@o.matrix_world

    # Biblioteca de largura única com base fechada, em vez de duas torres finas.
    x,z=-2.42,-3.44
    casca('Base da biblioteca',(x,0,z),[(.06,1.27,.56,0,0),(.16,1.34,.59,0,0),(.72,1.34,.59,0,0)],madeira,raio=.065)
    for dx in (-.31,.31):
        painel('Porta da biblioteca',(x+dx,.43,z+.31),.59,.47,.035,tecido,.045)
        tubo('Puxador da biblioteca',(x+dx-.095,.56,z+.337),(x+dx+.095,.56,z+.337),.012,latao)
    painel('Nicho de atlas',(x,1.42,z-.24),1.34,1.44,.085,verde,.075)
    for dx in (-.64,.64):
        casca('Lateral da biblioteca',(x+dx,0,z),[(.70,.072,.58,0,0),(2.10,.072,.58,0,0)],madeira,raio=.024)
    for y in (.75,1.20,1.65,2.10):
        casca('Prateleira laminada',(x,0,z),[(y-.025,1.33,.59,0,0),(y+.025,1.33,.59,0,0)],madeira,raio=.05)
        caixa('Filete da estante',(x,y+.015,z+.301),(1.20,.015,.009),latao,.003)
    for linha,y in enumerate((.78,1.23,1.68)):
        for i in range(7):
            h=.27+(i%3)*.045
            atlas(x-.49+i*.143,y,z+.035,.098,h,[tecido,ambar,azul][(i+linha)%3],.035 if i==6 else 0)
    caixa('Luz interna da biblioteca',(x,2.066,z+.09),(1.13,.014,.17),luz,.004)

    # Vitrine curva: mesmo vão e suporte anatômico, sem uma lâmina de vidro à frente.
    x,z=1.82,-2.44
    for dx in (-.59,.59):
        casca('Montante laminado da vitrine',(x+dx,0,z),[(.08,.10,.54,0,0),(.18,.12,.56,0,0),
                   (2.06,.12,.56,0,0),(2.20,.10,.52,0,0)],madeira,raio=.04)
        tubo('Inserto de vitrine',(x+dx, .26,z+.287),(x+dx,2.03,z+.287),.007,latao,8)
    for y in (.10,2.18):
        casca('Moldura orgânica da vitrine',(x,0,z),[(y-.06,1.26,.59,0,0),(y,1.35,.64,0,0),
                   (y+.055,1.26,.59,0,0)],madeira,raio=.11)
    caixa('Difusor da vitrine',(x,2.109,z+.02),(.98,.018,.28),luz,.005)

    # Bancada de microscopia com tampo racetrack e portas voltadas para o aluno.
    x,z=2.73,.15
    casca('Base recuada de microscopia',(x,0,z),[(.04,.91,1.71,0,0),(.15,.91,1.71,0,0)],escuro)
    casca('Corpo da bancada',(x,0,z),[(.12,1.01,1.82,0,0),(.23,1.11,1.91,0,0),
                                    (.82,1.11,1.91,0,0),(.91,1.04,1.84,0,0)],madeira,raio=.12)
    casca('Tampo cerâmico',(x,0,z),[(.91,1.18,2.00,0,0),(.965,1.23,2.04,0,0),
                                   (.999,1.17,1.99,0,0)],marfim,raio=.18)
    for dz in (-.63,0,.63):
        painel_lateral('Porta de laboratório',(2.156,.52,z+dz),.54,.64,.032,tecido)
        cabo('Pega de laboratório',[(2.126,.74,z+dz-.12),(2.092,.74,z+dz-.095),
                                   (2.092,.74,z+dz+.095),(2.126,.74,z+dz+.12)],.012,latao)
    # Dois microscópios binoculares estilizados, com platina e conjunto óptico separados.
    for z in (-.37,.56):
        x=2.64
        casca('Base moldada do microscópio',(x,0,z),[(1.002,.43,.35,0,0),(1.04,.49,.37,0,0),
                                                    (1.07,.40,.31,.02,0)],marfim,raio=.10)
        casca('Arco do microscópio',(x,0,z),[(1.055,.15,.23,.13,0),(1.17,.13,.19,.21,0),
                   (1.40,.12,.17,.22,0),(1.50,.16,.20,.12,0),(1.55,.22,.21,0,0)],marfim,raio=.06)
        for dz in (-.10,.10):
            tubo('Binóculo óptico',(x-.02,1.51,z+dz),(x-.17,1.62,z+dz),.035,escuro,16)
            tubo('Borda de ocular',(x-.17,1.62,z+dz),(x-.19,1.635,z+dz),.042,metal,16)
            tubo('Lente opaca',(x-.19,1.635,z+dz),(x-.194,1.638,z+dz),.027,verde,16)
        tubo('Revólver inclinado',(x,1.45,z),(x,1.40,z),.072,metal,20)
        for dx,dz in ((-.04,0),(.022,-.036),(.022,.036)):
            tubo('Objetiva cromada',(x+dx,1.40,z+dz),(x+dx,1.315,z+dz),.018,metal,12)
            tubo('Anel de identificação',(x+dx,1.355,z+dz),(x+dx,1.345,z+dz),.020,latao,12)
        casca('Platina mecânica',(x-.025,0,z),[(1.235,.31,.29,0,0),(1.263,.31,.29,0,0)],escuro,raio=.025)
        tubo('Condensador',(x-.03,1.14,z),(x-.03,1.23,z),.056,metal,16)
        tubo('Luz de campo',(x-.03,1.074,z),(x-.03,1.089,z),.061,luz,16)
        caixa('Lâmina no estágio',(x-.025,1.27,z),(.18,.006,.075),azul,.001)
        for dz in (-.065,.065):
            tubo('Grampo da lâmina',(x+.03,1.274,z+dz),(x-.04,1.274,z+dz),.007,metal,8)
        for lado in (-1,1):
            tubo('Foco macrométrico',(x+.18,1.245,z+lado*.08),(x+.18,1.245,z+lado*.145),.056,escuro,20)
            tubo('Foco micrométrico',(x+.18,1.245,z+lado*.145),(x+.18,1.245,z+lado*.163),.026,metal,16)
        cabo('Cabo de alimentação',[(x+.23,1.05,z),(x+.45,1.022,z+.03),(3.23,1.025,z+.13)],.008,escuro)

    # Parede de fundo com painéis amplos e moldura contínua, sem listras soltas.
    for x,w in ((-2.65,1.48),(-.83,1.95),(1.49,2.45)):
        painel('Painel acústico enquadrado',(x,1.84,-3.825),w,1.61,.062,tecido,.08)
    for x in (-3.23,3.23):
        casca('Pilastra de carvalho',(x,0,-3.76),[(.08,.15,.12,0,0),(2.54,.15,.12,0,0),
                                                  (3.06,.19,.16,0,0)],madeira,raio=.032)
        caixa('Luz de borda',(x+(.10 if x<0 else -.10),2.03,-3.705),(.016,1.80,.014),luz,.003)
    caixa('Cornija do departamento',(0,3.035,-3.74),(6.62,.12,.23),madeira,.025)
    caixa('Iluminação da cornija',(0,2.966,-3.695),(6.27,.016,.12),luz,.004)
    # Forro acústico em carvalho com luminárias contínuas de cantos curvos.
    for x in (-1.94,1.94):
        casca('Forro flutuante',(x,0,.10),[(2.99,.77,5.15,0,0),(3.045,.94,5.32,0,0),
                                         (3.12,.92,5.30,0,0)],madeira,raio=.24)
        casca('Difusor do forro',(x,0,.10),[(2.975,.57,4.90,0,0),(2.99,.60,4.93,0,0)],luz,raio=.20)
        for z in (-1.62,-.51,.60,1.71):
            caixa('Junta de luminária',(x,2.967,z),(.62,.012,.019),latao,0)
    # Venezianas preservam a janela e acrescentam profundidade sem transparência.
    for z in (-1.8,1.35):
        for y in (1.50,1.71,1.92,2.13,2.34,2.55):
            caixa('Veneziana clara',(-3.274,y,z),(.09,.027,1.95),marfim,.006)

    # Retaguarda: armazenamento de material didático, fora dos postos e do corredor.
    x,z=2.34,3.39
    casca('Credenza de apoio',(x,0,z),[(.08,1.43,.65,0,0),(.18,1.53,.69,0,0),(.94,1.53,.69,0,0)],madeira,raio=.10)
    casca('Tampo do apoio',(x,0,z),[(.94,1.60,.75,0,0),(1.00,1.64,.78,0,0)],marfim,raio=.12)
    for dx in (-.38,.38):
        o=painel('Frente do apoio',(0,0,0),.69,.65,.034,tecido)
        o.data.transform(Matrix.Translation(p((x+dx,.55,z-.362))) @ Matrix.Rotation(math.pi,4,'Z'))
        tubo('Puxador posterior',(x+dx-.10,.78,z-.387),(x+dx+.10,.78,z-.387),.012,latao)
    for dx in (-.43,.03):
        casca('Estojo de lâminas',(x+dx,0,z),[(1.003,.36,.34,0,0),(1.17,.36,.34,0,0)],tecido,raio=.04)
        casca('Tampa de estojo',(x+dx,0,z),[(1.17,.39,.36,0,0),(1.20,.39,.36,0,0)],marfim,raio=.04)
    # Nicho posterior de atlas fechado por laterais, sem criar anatomia fictícia.
    x,z=-2.37,3.48
    painel('Painel de acervo posterior',(x,1.73,z+.22),1.55,1.49,.08,tecido,.08)
    for dx in (-.76,.76):
        casca('Lateral do acervo',(x+dx,0,z),[(.97,.08,.54,0,0),(2.47,.08,.54,0,0)],madeira,raio=.025)
    for y in (1.02,1.69,2.44):
        caixa('Prateleira do acervo',(x,y,z),(1.58,.055,.56),madeira,.018)
    for y in (1.053,1.723):
        for i in range(7):
            # Livros virados para a sala, não para a parede.
            anteriores=set(cena.objects)
            atlas(x-.53+i*.165,y,z-.02,.11,.35+(i%2)*.06,[tecido,ambar,azul][i%3])
            giro=Matrix.Translation(p((x-.53+i*.165,y,z-.02))) @ Matrix.Rotation(math.pi,4,'Z') @ Matrix.Translation(-p((x-.53+i*.165,y,z-.02)))
            for o in set(cena.objects)-anteriores: o.matrix_world=giro@o.matrix_world

    for o,antes in protegidos.items():
        assert vertices_mundo(o)==antes, f'Elemento protegido alterado: {o.name}'
    # Achatar transformações, texturizar e gravar contatos com os mesmos métodos do Hospital.
    objetos=[o for o in cena.objects if o.type=='MESH']
    for o in objetos:
        o.data.transform(o.matrix_world); o.matrix_world.identity(); o.data.update()
    origem=RAIZ/'scripts/refinar-ambientes-duelo.py'
    modulo=ast.parse(origem.read_text(encoding='utf-8'))
    defs=[n for n in modulo.body if isinstance(n,ast.FunctionDef)]
    temp=RAIZ/'tmp_acabamento'; temp.mkdir(exist_ok=True)
    raios=12
    direcoes=[]
    for i in range(raios):
        r=math.sqrt((i+.5)/raios); a=i*2.399963229728653
        direcoes.append(Vector((r*math.cos(a),r*math.sin(a),math.sqrt(1-r*r))))
    env={**globals(),'CENA':cena,'PASTA':RAIZ/'public/models/props','TEMP':temp,
         'MODO':'escola-direcao','RAIOS':raios,'DIRECOES':direcoes}
    exec(compile(ast.Module(body=defs,type_ignores=[]),str(origem),'exec'),env)
    env['textura_madeira'](objetos)
    bvh=env['arvore'](objetos)
    env['acabamento'](objetos,bvh)
    piso=env['piso'](bvh,7.2,8,True)
    ambiente=env['exportar']('escola-medicina-direcao',env['agrupar'](objetos))
    contato=env['exportar']('piso-escola-direcao',[piso])
    result={'ambiente':ambiente,'piso':contato,'elementos_protegidos':len(protegidos),
            'cena_original_preservada':anterior.name}
    bpy.data.libraries.write(str(temp/'escola-direcao.blend'),{cena})
    (temp/'escola-direcao.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
finally:
    bpy.context.window.scene=anterior
