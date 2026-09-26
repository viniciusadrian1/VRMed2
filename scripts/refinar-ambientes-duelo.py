"""Acabamento autoral dos cenários. Executar pelo Blender MCP.

Preserva GLBs de origem e a cena aberta. Oclusão de proximidade é calculada
offline por raios na geometria real; não é uma simulação fotométrica clínica.
MODO_ACABAMENTO permite gerar hospital/escola separadamente.
"""
import bpy
import math
import json
import numpy as np
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

RAIZ = Path(__file__).resolve().parents[1]
PASTA = RAIZ / 'public/models/props'
TEMP = RAIZ / 'tmp_acabamento'
TEMP.mkdir(exist_ok=True)
ANTERIOR = bpy.context.window.scene
MODO = globals().get('MODO_ACABAMENTO', 'hospital')
CENA = bpy.data.scenes.new('VRmed_Acabamento_' + MODO)
RAIOS = 24

def p(v):
    return Vector((v[0], -v[2], v[1]))

def selecionar(objetos):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objetos:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objetos[0]

def importar(nome):
    antes = set(CENA.objects)
    bpy.ops.import_scene.gltf(filepath=str(PASTA / (nome + '.glb')))
    objetos = [o for o in CENA.objects if o not in antes and o.type == 'MESH']
    for obj in objetos:
        # Exportações glTF voltam à convenção Z-up do Blender.
        matriz = obj.matrix_world.copy()
        obj.parent = None
        obj.data.transform(matriz)
        obj.matrix_world.identity()
        obj.data.update()
    return objetos

def shader(mat):
    return next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')

def caixa(nome, pos, tamanho, mat, borda=.015):
    bpy.ops.mesh.primitive_cube_add(size=1, location=p(pos))
    o = bpy.context.object
    o.name = nome
    o.dimensions = (tamanho[0], tamanho[2], tamanho[1])
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    o.data.materials.append(mat)
    if borda:
        b = o.modifiers.new('Acabamento', 'BEVEL')
        b.width = min(borda, min(tamanho)*.25)
        b.segments = 3
        bpy.ops.object.modifier_apply(modifier=b.name)
    return o

def tubo(nome, a, b, raio, mat, lados=16):
    a, b = p(a), p(b)
    bpy.ops.mesh.primitive_cylinder_add(vertices=lados, radius=raio, depth=(b-a).length, location=(a+b)/2)
    o = bpy.context.object
    o.name = nome
    o.rotation_euler = (b-a).to_track_quat('Z', 'Y').to_euler()
    o.data.materials.append(mat)
    for face in o.data.polygons:
        face.use_smooth = len(face.vertices) == 4
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return o

def material_do(objetos, trecho):
    return next(m for o in objetos for m in o.data.materials if trecho in m.name)

def textura_madeira(objetos):
    """Lâmina de carvalho discreta, local e pequena; sem dependência de shader procedural."""
    mat = material_do(objetos, 'Carvalho')
    base = np.array(shader(mat).inputs['Base Color'].default_value[:3])
    n = 128
    y, x = np.mgrid[0:n, 0:n]
    fibra = .94 + .045*np.sin(y*.72 + np.sin(x*.075)*1.3) + .012*np.sin(y*2.1+x*.05)
    linear = fibra[:, :, None]*base
    pixels = np.ones((n,n,4), dtype=np.float32)
    pixels[:, :, :3] = np.where(linear <= .0031308, linear*12.92, 1.055*linear**(1/2.4)-.055)
    imagem = bpy.data.images.new('Carvalho laminado', n, n, alpha=False)
    imagem.colorspace_settings.name = 'Non-Color'
    imagem.pixels.foreach_set(pixels.ravel())
    imagem.filepath_raw = str(TEMP / 'carvalho.png')
    imagem.file_format = 'PNG'
    imagem.save()
    imagem = bpy.data.images.load(imagem.filepath_raw, check_existing=False)
    imagem.colorspace_settings.name = 'sRGB'
    tex = mat.node_tree.nodes.new('ShaderNodeTexImage')
    tex.image = imagem
    shader(mat).inputs['Base Color'].default_value = (1,1,1,1)
    mat.node_tree.links.new(tex.outputs['Color'], shader(mat).inputs['Base Color'])
    for obj in objetos:
        if obj.data.materials[0] != mat:
            continue
        uv = obj.data.uv_layers.active or obj.data.uv_layers.new(name='UVMap')
        for face in obj.data.polygons:
            eixo = max(range(3), key=lambda k: abs(face.normal[k]))
            a, b = [(1,2),(0,2),(0,1)][eixo]
            for indice in face.loop_indices:
                pos = obj.data.vertices[obj.data.loops[indice].vertex_index].co
                uv.data[indice].uv = (pos[a]*.7, pos[b]*1.5)

def arvore(objetos):
    vertices, faces = [], []
    for obj in objetos:
        inicio = len(vertices)
        vertices.extend(v.co.copy() for v in obj.data.vertices)
        faces.extend(tuple(inicio+i for i in f.vertices) for f in obj.data.polygons)
    return BVHTree.FromPolygons(vertices, faces)

# Amostragem determinística no hemisfério, ponderada pelo cosseno.
DIRECOES = []
for i in range(RAIOS):
    r = math.sqrt((i+.5)/RAIOS)
    a = i * 2.399963229728653
    DIRECOES.append(Vector((r*math.cos(a), r*math.sin(a), math.sqrt(1-r*r))))

def oclusao(bvh, ponto, normal, alcance=.55):
    q = Vector((0, 0, 1)).rotation_difference(normal)
    origem = ponto + normal*.003
    bloqueio = 0
    for direcao in DIRECOES:
        _, _, _, distancia = bvh.ray_cast(origem, q @ direcao, alcance)
        if distancia is not None:
            bloqueio += (1-distancia/alcance)**.65
    return 1-.62* bloqueio/RAIOS

def acabamento(objetos, bvh):
    for obj in objetos:
        malha = obj.data
        mat = malha.materials[0]
        bsdf = shader(mat)
        nome = mat.name
        # Acabamentos calibrados por classe; não há metal puro sem reflexo ambiente.
        if 'Metal' in nome or 'Latao' in nome:
            bsdf.inputs['Metallic'].default_value = .42
            bsdf.inputs['Roughness'].default_value = .30 if 'Metal' in nome else .38
        elif 'Tecido' in nome:
            bsdf.inputs['Metallic'].default_value = 0
            bsdf.inputs['Roughness'].default_value = .96
        elif 'Esmalte' in nome:
            bsdf.inputs['Metallic'].default_value = .06
            bsdf.inputs['Roughness'].default_value = .37
        elif 'Borracha' in nome or 'Grafite' in nome:
            bsdf.inputs['Roughness'].default_value = .85
        elif 'Carvalho' in nome:
            bsdf.inputs['Roughness'].default_value = .54
        cor = malha.color_attributes.new(name='Contato_e_acabamento', type='BYTE_COLOR', domain='CORNER')
        malha.color_attributes.active_color = cor
        cache = {}
        emissivo = bsdf.inputs['Emission Strength'].default_value > 0
        for face in malha.polygons:
            for indice in face.loop_indices:
                vertice = malha.vertices[malha.loops[indice].vertex_index]
                n = malha.corner_normals[indice].vector
                chave = (vertice.index, *(round(a, 3) for a in n))
                if chave not in cache:
                    fator = 1 if emissivo else oclusao(bvh, vertice.co, n)
                    x, y, z = vertice.co
                    # Veios discretos e variação de tecido são gravados, sem shader extra.
                    if 'Carvalho' in nome:
                        fator *= .94+.055*math.sin(z*91 + math.sin(x*3.2+y*2)*1.7)
                    elif 'Tecido' in nome:
                        fator *= .96+.025*math.sin(x*151+z*91)
                    cache[chave] = (fator, fator, fator, 1)
                cor.data[indice].color = cache[chave]
        # O exportador glTF inclui a cor ativa como COLOR_0. O material-base permanece.

def agrupar(objetos):
    grupos = {}
    for o in objetos:
        grupos.setdefault(o.data.materials[0], []).append(o)
    resultado = []
    for mat, grupo in grupos.items():
        selecionar(grupo)
        bpy.ops.object.join()
        o = bpy.context.object
        o.name = mat.name.split('.')[0] + '_Acabado'
        resultado.append(o)
    return resultado

def exportar(nome, objetos):
    selecionar(objetos)
    destino = PASTA / (nome + '.glb')
    bpy.ops.export_scene.gltf(filepath=str(destino), export_format='GLB', use_selection=True,
        use_active_scene=True, export_animations=False, export_yup=True, export_cameras=False,
        export_lights=False, export_extras=True, export_vertex_color='ACTIVE', export_all_vertex_colors=False)
    tris = 0
    for o in objetos:
        o.data.calc_loop_triangles()
        tris += len(o.data.loop_triangles)
    return {'arquivo': destino.name, 'bytes': destino.stat().st_size, 'triangulos': tris,
            'malhas': len(objetos), 'raios_ao': RAIOS}

def piso(bvh, largura, profundidade, escola=False, cor_hospital=(.145,.225,.245)):
    # Um mapa opaco de 512²: contato de objetos reais e iluminação difusa estilizada.
    # UV igual ao plano glTF; não existe transparência nem shadow map em runtime.
    n = 512
    pixels = np.ones((n, n, 4), dtype=np.float32)
    base = np.array((.59, .60, .53) if escola else cor_hospital)
    normal = Vector((0, 0, 1))
    for j in range(n):
        by = (j/(n-1)-.5)*profundidade
        for i in range(n):
            x = (i/(n-1)-.5)*largura
            ao = oclusao(bvh, Vector((x, by, .009)), normal, .95)
            # Gradiente amplo vindo da janela lateral; não altera luz da anatomia.
            luz = .90 + .16*math.exp(-((x+2.8)/1.9)**2-((by-.3)/3.8)**2)
            junta = min(abs((x+.30) % .60-.30), abs((by+.30) % .60-.30))
            # A Escola já tem juntas geométricas de 1 m; não sobrepor outra malha de linhas.
            fator = .89 if not escola and junta < .008 else 1
            rgb = base * ao * luz * fator
            pixels[j, i, :3] = rgb
    imagem = bpy.data.images.new('Piso_contatos_' + MODO, n, n, alpha=False)
    imagem.colorspace_settings.name = 'Non-Color'
    # Pixels estão em linear; converter explicitamente para sRGB do arquivo final.
    rgb = pixels[:, :, :3]
    pixels[:, :, :3] = np.where(rgb <= .0031308, rgb*12.92, 1.055*np.power(rgb, 1/2.4)-.055)
    imagem.pixels.foreach_set(pixels.ravel())
    imagem.filepath_raw = str(TEMP / ('piso-' + MODO + '.png'))
    imagem.file_format = 'PNG'
    imagem.save()
    # Reabrir como sRGB para o exportador; o arquivo é incorporado ao GLB.
    imagem = bpy.data.images.load(imagem.filepath_raw, check_existing=False)
    imagem.colorspace_settings.name = 'sRGB'
    mat = bpy.data.materials.new('Piso_integrado_' + MODO)
    mat.use_nodes = True
    bsdf = shader(mat)
    bsdf.inputs['Roughness'].default_value = .83
    tex = mat.node_tree.nodes.new('ShaderNodeTexImage')
    tex.image = imagem
    mat.node_tree.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, .001 if escola else 0))
    plano = bpy.context.object
    plano.name = 'Piso_com_contatos_' + MODO
    plano.scale = (largura, profundidade, 1)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    plano.data.materials.append(mat)
    return plano

try:
    bpy.context.window.scene = CENA
    relatorio = []
    if MODO == 'hospital':
        entorno = importar('entorno-arena')
        retaguarda = importar('retaguarda-arena')
        metal = material_do(entorno, 'Metal')
        marfim = material_do(entorno, 'Marfim')
        escuro = material_do(entorno, 'Borracha')
        luz = material_do(retaguarda, 'Difusor')
        # Luminária articulada do leito: fundo médico, fora do campo dos alvos/placas.
        novos = []
        for a, b, r in [((3.18,3.54,-1.85),(3.18,3.01,-1.85),.065),
                         ((3.18,3.01,-1.85),(2.55,2.83,-1.85),.037),
                         ((2.55,2.83,-1.85),(2.72,2.63,-1.85),.034)]:
            novos.append(tubo('Braço de exame', a, b, r, metal))
        novos.append(tubo('Cúpula da luminária', (2.72,2.54,-1.85),(2.72,2.64,-1.85),.29,marfim,32))
        novos.append(tubo('Aro protetor', (2.72,2.52,-1.85),(2.72,2.54,-1.85),.265,escuro,32))
        for i in range(6):
            a = i*math.tau/6
            x, z = 2.72+.175*math.cos(a), -1.85+.175*math.sin(a)
            novos.append(tubo('Lente opaca de exame', (x,2.51,z),(x,2.522,z),.052,luz,12))
        novos.append(tubo('Pegador da luminária', (2.72,2.42,-1.85),(2.72,2.53,-1.85),.031,marfim))
        troca = {metal: material_do(retaguarda, 'Metal'), marfim: material_do(retaguarda, 'Marfim'),
                 escuro: material_do(retaguarda, 'Borracha')}
        for o in novos:
            o.data.materials[0] = troca.get(o.data.materials[0], luz)
            o.data.transform(Matrix.Translation(p((-5.77,0,4.35))))
        retaguarda += novos
        # Cobertura flexível com queda lateral; não deforma o leito original.
        tecido = material_do(retaguarda, 'Tecido')
        vertices, faces = [], []
        nx, nz = 24, 24
        for j in range(nz+1):
            z = 1.54+j/nz*1.32
            for i in range(nx+1):
                dx = (i/nx-.5)*1.20
                queda = max(0, (abs(dx)-.49)/.11)
                altura = .902 + .008*math.sin(j*.85+i*.5) - .14*queda**1.6
                vertices.append(p((-3.05+dx, altura, z)))
        for j in range(nz):
            for i in range(nx):
                k = j*(nx+1)+i
                faces.append((k,k+nx+1,k+nx+2,k+1))
        mesh = bpy.data.meshes.new('Cobertura com caimento')
        mesh.from_pydata(vertices, [], faces)
        mesh.materials.append(tecido)
        cobertura = bpy.data.objects.new('Cobertura com caimento', mesh)
        CENA.collection.objects.link(cobertura)
        for face in mesh.polygons:
            face.use_smooth = True
        retaguarda.append(cobertura)
        # Recorte difuso na janela opaca: mais profundidade, sem vidro/blending.
        janela = caixa('Difusor da janela',(-4.338,2.17,-.15),(.006,1.04,1.93),marfim,0)
        entorno.append(janela)
        objetos = entorno + retaguarda
        # Contexto de oclusão: sala e móveis centrais, não exportados nem alterados.
        contexto = [caixa('Referência piso',(0,-.04,0),(9.2,.08,9.2),marfim,0)]
        for x in (-4.61,4.61): contexto.append(caixa('Referência parede',(x,1.8,0),(.02,3.6,9.2),marfim,0))
        for z in (-4.61,4.61): contexto.append(caixa('Referência parede',(0,1.8,z),(9.2,3.6,.02),marfim,0))
        bancada = importar('bancada-arena')
        for o in bancada: o.data.transform(Matrix.Translation(p((-1.05,0,-.5))))
        contexto += bancada
        cadeira = importar('../hospital/cadeira-rodas')
        vertices = [v.co for o in cadeira for v in o.data.vertices]
        minimo = Vector(tuple(min(v[i] for v in vertices) for i in range(3)))
        maximo = Vector(tuple(max(v[i] for v in vertices) for i in range(3)))
        centro = (minimo+maximo)/2
        matriz = (Matrix.Translation(p((3.78,0,1.12))) @ Matrix.Rotation(-math.pi/2,4,'Z')
                  @ Matrix.Scale(1/(maximo.z-minimo.z),4)
                  @ Matrix.Translation(Vector((-centro.x,-centro.y,-minimo.z))))
        for o in cadeira: o.data.transform(matriz)
        contexto += cadeira
        contexto.append(caixa('Referência console',(.85,.05,-.65),(1.15,.10,.7),marfim,0))
        bvh = arvore(objetos + contexto)
        acabamento(objetos, bvh)
        plano = piso(bvh, 9.2, 9.2)
        relatorio += [exportar('entorno-arena-acabado',agrupar(entorno)),
                      exportar('retaguarda-arena-acabada',agrupar(retaguarda)),
                      exportar('piso-hospital-acabado',[plano])]
    elif MODO == 'escola':
        objetos = importar('escola-medicina')
        textura_madeira(objetos)
        bvh = arvore(objetos)
        acabamento(objetos, bvh)
        plano = piso(bvh, 7.2, 8, True)
        # A nova superfície fica abaixo das juntas, tapete e demarcações existentes.
        relatorio += [exportar('escola-medicina-acabada',objetos), exportar('piso-escola-acabado',[plano])]
    else:
        raise ValueError('Ambiente desconhecido')
    bpy.data.libraries.write(str(TEMP / (MODO+'.blend')), {CENA})
    (TEMP / (MODO+'.json')).write_text(json.dumps(relatorio, ensure_ascii=False, indent=2), encoding='utf-8')
    result = {'ambiente': MODO, 'assets': relatorio, 'cena_original_preservada': ANTERIOR.name}
finally:
    bpy.context.window.scene = ANTERIOR
