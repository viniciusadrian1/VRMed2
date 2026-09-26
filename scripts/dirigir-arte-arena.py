"""Segunda direção de arte do Hospital, pelo Blender MCP.

Reaproveita a autoria anterior antes da união das peças. Exporta uma variante;
não sobrescreve os originais, a cena aberta, os órgãos ou as placas aprovadas.
"""
import ast
import math
import bpy
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

RAIZ = Path(__file__).resolve().parents[1]
anterior = bpy.context.window.scene


def fonte_antes_da_exportacao():
    caminho = RAIZ / 'scripts/criar-entorno-arena.py'
    arvore = ast.parse(caminho.read_text(encoding='utf-8'))
    etapa = next(n for n in arvore.body if isinstance(n, ast.Try))
    prefixo = arvore.body[:arvore.body.index(etapa)]
    corpo = []
    for n in etapa.body:
        if isinstance(n, ast.For) and isinstance(n.target, ast.Name) and n.target.id == 'mat':
            break
        corpo.append(n)
    escopo = {'__file__': str(caminho)}
    exec(compile(ast.Module(body=prefixo+corpo, type_ignores=[]), str(caminho), 'exec'), escopo)
    return escopo


def arco_retangulo(largura, altura, raio, passos=5):
    raio = min(raio, largura*.45, altura*.45)
    pontos = []
    for x,y,a in [(largura/2-raio,altura/2-raio,0),
                  (-largura/2+raio,altura/2-raio,90),
                  (-largura/2+raio,-altura/2+raio,180),
                  (largura/2-raio,-altura/2+raio,270)]:
        for i in range(passos+1):
            t = math.radians(a+i*90/passos)
            pontos.append((x+raio*math.cos(t), y+raio*math.sin(t)))
    return pontos


try:
    base = fonte_antes_da_exportacao()
    cena = base['cena']
    cena.name = 'VRmed_Direcao_Arena'
    caixa, tubo, cabo = (base[n] for n in ('caixa','tubo','cabo'))
    p = base['ponto']
    marfim, esmalte, petroleo, metal, escuro, ciano, ambar, vidro = (
        base[n] for n in ('marfim','esmalte','petroleo','metal','escuro','ciano','ambar','vidro'))
    materiais = base['materiais']
    # Oito famílias PBR: cerâmica clara, polímero teal, metal, borracha e difusores.
    paleta = [(marfim,(.77,.79,.73),.38,.03), (esmalte,(.22,.38,.39),.42,.10),
              (petroleo,(.016,.037,.044),.52,.12), (metal,(.43,.49,.50),.30,.65),
              (escuro,(.012,.020,.023),.82,0), (vidro,(.007,.024,.031),.25,.10)]
    for mat, cor, rugosidade, metalicidade in paleta:
        sh = next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
        sh.inputs['Base Color'].default_value = (*cor,1)
        sh.inputs['Roughness'].default_value = rugosidade
        sh.inputs['Metallic'].default_value = metalicidade
    # Âmbar vira luz de trabalho quente, distinta do ciano de estado da partida.
    sh = next(n for n in ambar.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    sh.inputs['Base Color'].default_value = (.72,.57,.31,1)
    sh.inputs['Emission Color'].default_value = (.72,.57,.31,1)
    sh.inputs['Emission Strength'].default_value = .65

    # Remoção limitada às peças reconstruídas nesta NOVA cena de autoria.
    for o in list(cena.objects):
        if o.type != 'MESH':
            continue
        centro = sum((o.matrix_world @ Vector(c) for c in o.bound_box),Vector())/8
        x,y,z = centro.x,centro.z,-centro.y
        carrinho = -3.6 < x < -2.2 and -1.95 < z < -.75 and y < 1.3
        exame = 2.35 < x < 3.75 and -2.45 < z < -1.00 and y < 1.96
        superior = o.name.startswith(('Armário superior','Porta superior','Visor acetinado',
                                      'Reflexo do visor','Alça vertical','Iluminação sob armário'))
        if carrinho or exame or superior:
            bpy.data.objects.remove(o, do_unlink=True)

    def casca(nome, centro, perfis, mat, eixo='Y', raio=.10):
        """Carcaça por seções arredondadas, com variação de forma e não só cubos."""
        vs, fs = [], []
        for t,w,h,dx,dy in perfis:
            for a,b in arco_retangulo(w,h,raio):
                local = (a+dx,t,b+dy) if eixo=='Y' else (a+dx,b+dy,t)
                vs.append(p(tuple(centro[i]+local[i] for i in range(3))))
        n = len(vs)//len(perfis)
        for j in range(len(perfis)-1):
            for i in range(n):
                k = j*n+i; q = j*n+(i+1)%n
                fs.append((k,q,q+n,k+n))
        fs += [tuple(reversed(range(n))),tuple((len(perfis)-1)*n+i for i in range(n))]
        malha = bpy.data.meshes.new(nome)
        malha.from_pydata(vs,[],fs); malha.materials.append(mat)
        obj = bpy.data.objects.new(nome,malha); cena.collection.objects.link(obj)
        # Normais exteriores recalculadas em todas as carcaças fechadas.
        import bmesh
        bm=bmesh.new(); bm.from_mesh(malha)
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.to_mesh(malha); bm.free()
        for face in malha.polygons:
            face.use_smooth = len(face.vertices)==4
        return obj

    def painel(nome, centro, w,h,d,mat,raio=.055):
        return casca(nome,centro,[(-d/2,w-.025,h-.025,0,0),(-d*.25,w,h,0,0),
                                 (d*.25,w,h,0,0),(d/2,w-.025,h-.025,0,0)],mat,'Z',raio)

    def rodas(x,z,largura,prof):
        for dx in (-largura/2,largura/2):
            for dz in (-prof/2,prof/2):
                tubo('Rodízio com banda',(x+dx-.048,.115,z+dz),(x+dx+.048,.115,z+dz),.105,escuro,20)
                tubo('Cubo do rodízio',(x+dx-.051,.115,z+dz),(x+dx+.051,.115,z+dz),.049,metal,16)
                caixa('Garfo curvo',(x+dx,.215,z+dz),(.055,.16,.15),esmalte,.02)

    # Carrinho: volume arredondado, rodas reais, três gavetas e instrumentos contidos.
    x,z=-2.88,-1.40
    rodas(x,z,.78,.61)
    casca('Para-choque carrinho',(x,0,z),[(.23,1.08,.88,0,0),(.29,1.12,.90,0,0),(.34,1.03,.82,0,0)],escuro)
    casca('Corpo cerâmico carrinho',(x,0,z),[(.31,.88,.70,0,0),(.37,.99,.77,0,0),(.88,.99,.77,0,0),(.94,.91,.69,0,0)],marfim)
    for y in (.45,.63,.81):
        painel('Frente de gaveta',(x,y,z+.391),.79,.155,.025,esmalte,.033)
        cabo('Puxador contínuo',[(x-.23,y+.025,z+.414),(x-.20,y+.025,z+.46),
                              (x+.20,y+.025,z+.46),(x+.23,y+.025,z+.414)],.014,metal)
    casca('Bandeja afundada',(x,0,z),[(.935,1.05,.83,0,0),(.98,1.07,.85,0,0),(1.01,1.00,.78,0,0)],metal)
    caixa('Fundo da bandeja',(x,1.016,z),(.84,.012,.57),escuro,.004)
    for dx in (-.18,0,.18):
        cabo('Instrumento esterilizável',[(x+dx,1.032,z-.16),(x+dx,1.04,z+.12),
                                         (x+dx+.04,1.04,z+.17)],.01,metal)
    for dx in (-.46,.46):
        cabo('Guarda da bandeja',[(x+dx,1.00,z-.32),(x+dx,1.12,z-.30),
                                  (x+dx,1.12,z+.30),(x+dx,1.00,z+.32)],.014,metal)
    cabo('Alça lateral',[(x-.46,.85,z-.25),(x-.62,.94,z-.25),(x-.62,.94,z+.25),(x-.46,.85,z+.25)],.021,esmalte)

    # Estação de exame: coluna orgânica inclinada, console e monitor articulados.
    x,z=3.02,-1.87
    rodas(x,z,.76,.66)
    casca('Base da estação',(x,0,z),[(.22,1.10,.94,0,0),(.31,1.15,.94,0,0),(.39,.84,.69,0,-.04)],esmalte)
    casca('Coluna moldada',(x,0,z),[(.35,.58,.55,0,-.10),(.56,.56,.46,0,-.09),
                                 (.87,.42,.39,0,.02),(1.10,.69,.53,0,.06)],marfim,raio=.14)
    # Painel frontal inclinado e conjunto de comando com trackball.
    casca('Console anatômico',(x,0,z),[(1.05,.86,.59,0,.08),(1.14,1.04,.69,0,.08),
                                    (1.21,1.00,.62,0,.04)],marfim)
    caixa('Superfície de comando',(x,1.215,z+.08),(.83,.014,.42),petroleo,.004)
    for j in range(3):
        for i in range(6):
            caixa('Tecla de console',(x-.33+i*.074,1.23,z-.06+j*.072),(.050,.018,.047),esmalte,.005)
    tubo('Anel trackball',(x+.27,1.22,z+.15),(x+.27,1.239,z+.15),.065,metal,24)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8,radius=.052,location=p((x+.27,1.238,z+.15)))
    bola=bpy.context.object; bola.name='Trackball'; bola.data.materials.append(marfim)
    for f in bola.data.polygons: f.use_smooth=True
    tubo('Braço do monitor',(x,1.14,z-.18),(x,1.56,z-.31),.048,metal,16)
    painel('Carcaça do monitor',(x,1.79,z-.25),1.04,.71,.15,marfim,.095)
    painel('Moldura do monitor',(x,1.79,z-.163),.96,.62,.025,escuro,.065)
    painel('Vidro da estação',(x,1.80,z-.145),.88,.53,.010,vidro,.04)
    # Esquema abstrato de aquisição, não uma imagem diagnóstica fabricada.
    for i in range(7):
        y=1.65+i*.043
        caixa('Barras do visor',(x-.12,y,z-.132),(.26+i*.038,.012,.005),ciano,0)
    for dx in (-.25,0,.25):
        caixa('Indicador inferior',(x+dx,1.51,z-.158),(.11,.018,.006),ciano,0)
    cabo('Cabo flexível da sonda',[(x+.36,1.08,z),(x+.56,.50,z+.07),
                                 (x+.66,.64,z+.14),(x+.60,1.30,z+.06)],.015,escuro)
    casca('Sonda de estudo',(x+.59,0,z+.06),[(1.15,.08,.09,0,0),(1.32,.11,.11,0,0),
                                          (1.40,.17,.07,0,0)],marfim,raio=.035)
    for i in range(5):
        caixa('Ventilação da estação',(x, .48+i*.046,z+.185),(.26,.014,.009),escuro,0)

    # Assimetria funcional: nicho aberto no preparo; portas curvas nos suprimentos.
    for x in (-3.32,3.32):
        painel('Casulo do armário',(x,2.37,-4.14),1.89,1.00,.48,marfim,.10)
        painel('Rebaixo do armário',(x,2.37,-3.887),1.70,.83,.022,petroleo,.07)
        if x < 0:
            for y in (2.04,2.40):
                caixa('Prateleira inox',(x,y,-3.84),(1.63,.038,.38),metal,.008)
                for dx in (-.57,-.20,.20,.57):
                    casca('Recipiente de preparo',(x+dx,y,-3.89),[(.025,.21,.22,0,0),(.23,.21,.22,0,0),
                          (.25,.18,.19,0,0)],marfim,raio=.045)
                    caixa('Faixa do recipiente',(x+dx,y+.14,-3.772),(.14,.048,.008),esmalte,.002)
            caixa('Luz do nicho',(x,2.72,-3.85),(1.53,.018,.14),ambar,.003)
        else:
            for dx in (-.44,.44):
                painel('Porta arredondada',(x+dx,2.37,-3.84),.79,.80,.06,esmalte,.085)
                painel('Janela opaca da porta',(x+dx,2.43,-3.799),.60,.53,.012,vidro,.065)
                cabo('Pega embutida',[(x+dx-.15,2.11,-3.80),(x+dx-.15,2.11,-3.75),
                                     (x+dx+.15,2.11,-3.75),(x+dx+.15,2.11,-3.80)],.012,metal)
        caixa('Luz de bancada',(x,1.84,-4.03),(1.70,.028,.24),ambar,.005)

    # Nervuras laterais e forro flutuante emolduram o campo visual, sem novo teto baixo.
    for lado in (-1,1):
        for z in (-2.75,.25,3.10):
            # Perfil esculpido: montante, ombro inclinado e retorno ao forro.
            pontos=[(lado*4.42,.12,z),(lado*4.42,2.92,z),
                    (lado*4.13,3.30,z),(lado*3.54,3.47,z)]
            for a,b in zip(pontos,pontos[1:]):
                tubo('Nervura arquitetônica',a,b,.085,marfim,8)
            tubo('Inserto da nervura',(lado*4.319,1.60,z),(lado*4.319,2.86,z),.018,ciano,8)
        casca('Nuvem acústica',(lado*2.87,0,.25),[(3.37,.98,5.70,0,0),(3.46,1.20,5.86,0,0),
                                              (3.50,1.16,5.82,0,0)],petroleo,raio=.25)
        caixa('Difusor longitudinal',(lado*2.87,3.359,.25),(.73,.016,5.22),ambar,.005)
        for z in (-1.9,-.8,.3,1.4,2.5):
            caixa('Junta do difusor',(lado*2.87,3.342,z),(.78,.012,.024),metal,0)
        # Revestimento modular recuado atrás das estações: separa os setores da parede.
        for z in (-3.75,-2.22,-.69,.84,2.37,3.84):
            painel_lateral=painel('Módulo de parede',(0,0,0),1.47,2.34,.085,marfim,.10)
            from mathutils import Matrix
            giro=Matrix.Rotation(-lado*math.pi/2,4,'Z')
            painel_lateral.data.transform(Matrix.Translation(p((lado*4.535,1.83,z))) @ giro)
            # Borda fria abaixo e faixa quente acima; superfícies físicas, não luzes novas.
            caixa('Junta de parede',(lado*4.474,3.05,z),(.018,.028,1.29),metal,.003)
            caixa('Luz rasante',(lado*4.465,2.98,z),(.014,.026,1.22),ambar,.003)
    # Janela iluminada com venezianas finas, não mais um retângulo escuro.
    caixa('Difusor da janela',(-4.338,2.17,-.15),(.006,1.04,1.93),marfim,0)
    for y in (1.79,1.98,2.17,2.36,2.55):
        caixa('Veneziana da janela',(-4.30,y,-.15),(.13,.035,1.90),esmalte,.007)

    # Oclusão real por raios e gradação ampla nas superfícies, calculadas offline.
    objetos=[o for o in cena.objects if o.type=='MESH']
    for o in objetos:
        o.data.transform(o.matrix_world); o.matrix_world.identity(); o.data.update()
    vertices,faces=[],[]
    for o in objetos:
        k=len(vertices); vertices.extend(v.co.copy() for v in o.data.vertices)
        faces.extend(tuple(k+i for i in f.vertices) for f in o.data.polygons)
    bvh=BVHTree.FromPolygons(vertices,faces)
    direcoes=[]
    for i in range(12):
        r=math.sqrt((i+.5)/12); a=i*2.39996323
        direcoes.append(Vector((r*math.cos(a),r*math.sin(a),math.sqrt(1-r*r))))
    for o in objetos:
        m=o.data
        cor=m.color_attributes.new(name='Luz_de_ambiente',type='BYTE_COLOR',domain='CORNER')
        m.color_attributes.active_color=cor
        cache={}
        for face in m.polygons:
            for k in face.loop_indices:
                v=m.vertices[m.loops[k].vertex_index]; n=m.corner_normals[k].vector
                chave=(v.index,*(round(c,3) for c in n))
                if chave not in cache:
                    q=Vector((0,0,1)).rotation_difference(n); ao=0
                    for d in direcoes:
                        _,_,_,dist=bvh.ray_cast(v.co+n*.004,q@d,.55)
                        if dist is not None: ao+=(1-dist/.55)**.65
                    fator=1-.52*ao/12
                    cache[chave]=(fator,fator,fator,1)
                cor.data[k].color=cache[chave]
    # União por material: custo de submissão limitado, sem luz ou sombra dinâmica.
    unidos=[]
    grupos={mat:[o for o in objetos if o.data.materials[0]==mat] for mat in materiais}
    for mat,grupo in grupos.items():
        if not grupo: continue
        bpy.ops.object.select_all(action='DESELECT')
        for o in grupo: o.select_set(True)
        bpy.context.view_layer.objects.active=grupo[0]
        bpy.ops.object.join(); o=bpy.context.object; o.name=mat.name.split('.')[0]+'_Direcao'
        unidos.append(o)
    bpy.ops.object.select_all(action='DESELECT')
    for o in unidos: o.select_set(True)
    destino=RAIZ/'public/models/props/entorno-arena-direcao.glb'
    bpy.ops.export_scene.gltf(filepath=str(destino),export_format='GLB',use_selection=True,
        use_active_scene=True,export_animations=False,export_cameras=False,export_lights=False,
        export_vertex_color='ACTIVE',export_all_vertex_colors=False)
    tris=0
    for o in unidos:
        o.data.calc_loop_triangles(); tris+=len(o.data.loop_triangles)
    result={'arquivo':str(destino),'bytes':destino.stat().st_size,'malhas':len(unidos),'triangulos':tris,
            'cena_original_preservada':anterior.name}
    # Recalcula o contato no piso para as novas rodas/carcaças, sem sombras antigas.
    import numpy as np
    contextos=[s for s in bpy.data.scenes if s.name.startswith('VRmed_Acabamento_hospital')
               and any(o.name.startswith('defaultMaterial') for o in s.objects)]
    if not contextos:
        origem=RAIZ/'tmp_acabamento/hospital.blend'
        if not origem.exists():
            raise RuntimeError('Execute primeiro refinar-ambientes-duelo.py para obter o contexto do piso.')
        with bpy.data.libraries.load(str(origem),link=False) as (dados,alvos):
            alvos.scenes=[n for n in dados.scenes if n.startswith('VRmed_Acabamento_hospital')]
        contextos=[s for s in alvos.scenes if s]
    contexto=contextos[-1]
    vs,fs=[],[]
    apoio=[o for o in contexto.objects if o.type=='MESH' and not o.name.startswith(('Entorno_','Piso_'))]
    for o in unidos+apoio:
        k=len(vs); vs.extend(o.matrix_world @ v.co for v in o.data.vertices)
        fs.extend(tuple(k+i for i in f.vertices) for f in o.data.polygons)
    contexto_piso=BVHTree.FromPolygons(vs,fs)
    caminho=RAIZ/'scripts/refinar-ambientes-duelo.py'
    defs=ast.parse(caminho.read_text(encoding='utf-8'))
    defs=[n for n in defs.body if isinstance(n,ast.FunctionDef) and n.name in ('shader','oclusao','piso','selecionar','exportar')]
    temp=RAIZ/'tmp_acabamento'; temp.mkdir(exist_ok=True)
    env={**globals(),'CENA':cena,'PASTA':RAIZ/'public/models/props','TEMP':temp,
         'MODO':'hospital-direcao','RAIOS':12,'DIRECOES':direcoes}
    exec(compile(ast.Module(body=defs,type_ignores=[]),str(caminho),'exec'),env)
    plano=env['piso'](contexto_piso,9.2,9.2,cor_hospital=(.21,.26,.25))
    result['piso']=env['exportar']('piso-hospital-direcao',[plano])
    bpy.data.libraries.write(str(temp/'hospital-direcao.blend'),{cena})
finally:
    bpy.context.window.scene=anterior
