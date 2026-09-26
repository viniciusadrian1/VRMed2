"""Texturas autorais de marcenaria e encadernação, sem imagens externas."""
import io
import math
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont

RAIZ = Path(__file__).resolve().parents[1]
PASTA = RAIZ / 'tmp_escola_revisao'
PASTA.mkdir(exist_ok=True)
fonte = TTFont(RAIZ / 'public/fonts/inter-600.woff')
fonte.flavor = None
buffer = io.BytesIO()
fonte.save(buffer)

def letra(tamanho):
    return ImageFont.truetype(io.BytesIO(buffer.getvalue()), tamanho)

# Cada lombada tem cabeceado, título, coleção e marca de consulta. Não são
# capas de editoras reais; o texto identifica apenas o acervo cenográfico.
titulos = ['ANATOMIA', 'OSTEOLOGIA', 'MORFOLOGIA', 'ATLAS DE ESTUDO',
           'HISTOLOGIA', 'CADERNO DE AULA', 'ESTUDO DO CORPO', 'ACERVO DIDÁTICO']
cores = ['#29463f', '#805343', '#344e5b', '#79715a', '#3b5a4c', '#7c633e', '#4d5155', '#496267']
atlas = Image.new('RGB', (2048, 2048), '#ded8c4')
for i, (titulo, cor) in enumerate(zip(titulos, cores)):
    img = Image.new('RGB', (256, 1024), cor)
    d = ImageDraw.Draw(img)
    for x in (9, 246):
        d.line((x, 0, x, 1023), fill='#24332d', width=4)
    for y in (51, 75, 846, 869):
        d.line((26, y, 229, y), fill='#c6b684', width=3)
    d.text((128, 140), 'VRmed', font=letra(32), fill='#e7dfc5', anchor='mm')
    texto = Image.new('RGBA', (730, 128))
    td = ImageDraw.Draw(texto)
    tamanho = 55
    while td.textlength(titulo, font=letra(tamanho)) > 655:
        tamanho -= 1
    td.text((365, 64), titulo, font=letra(tamanho), fill='#eee6cf', anchor='mm')
    vertical = texto.rotate(90, expand=True)
    img.paste(vertical, (64, 186), vertical)
    d.rectangle((45, 909, 210, 989), fill='#dcd6c4')
    d.text((128, 950), f'A · {i+1:02}', font=letra(35), fill='#34473d', anchor='mm')
    atlas.paste(img, (i*256, 0))

# Livro aberto: roteiro de observação, sem diagramas anatômicos inventados.
paginas = Image.new('RGB', (2048, 1024), '#e4ddc8')
d = ImageDraw.Draw(paginas)
for x, titulo, itens in [(0, 'Caderno de anatomia', ['Observe o modelo', 'Compare as estruturas', 'Registre suas dúvidas']),
                        (1024, 'Anotações de estudo', ['Estrutura observada', 'Relações espaciais', 'Pontos para revisar'])]:
    d.text((x+85, 94), 'VRmed / ACERVO DIDÁTICO', font=letra(25), fill='#617065')
    d.text((x+85, 170), titulo, font=letra(48), fill='#2d453d')
    d.line((x+85, 246, x+939, 246), fill='#a99972', width=4)
    for j, item in enumerate(itens):
        y = 310+j*202
        d.text((x+87, y), item, font=letra(32), fill='#465b51')
        for linha in (74, 112, 150):
            d.line((x+87, y+linha, x+939, y+linha), fill='#c5c0ac', width=2)
    d.text((x+925, 953), str(24+x//1024), font=letra(26), fill='#7b806c')
atlas.paste(paginas, (0, 1024))
atlas.save(PASTA/'encadernacao.png', optimize=True)

random.seed(925)
madeira = Image.new('RGB', (512, 512))
normal = Image.new('RGB', (512, 512))
rough = Image.new('RGB', (512, 512))
for y in range(512):
    for x in range(512):
        onda = math.sin(x*.23 + math.sin(y*.014)*1.7)
        fibra = onda*2 + math.sin(x*.63+y*.008)*.8 + random.uniform(-.4,.4)
        madeira.putpixel((x,y), tuple(max(0,min(255,round(c+fibra))) for c in (161,132,95)))
        normal.putpixel((x,y), (128+round(onda*3),128,255))
        r = 151+round(onda*6)
        rough.putpixel((x,y),(255,r,255))
madeira.save(PASTA/'carvalho.png', optimize=True)
normal.save(PASTA/'carvalho-normal.png', optimize=True)
rough.save(PASTA/'carvalho-rough.png', optimize=True)
papel = Image.new('RGB',(256,256))
for y in range(256):
    cor = (208,203,184) if y%4==0 else (225,220,200)
    for x in range(256):
        papel.putpixel((x,y),cor)
papel.save(PASTA/'folhas.png', optimize=True)
print('Atlas de encadernação 2048², carvalho 512² e folhas 256² prontos.')
