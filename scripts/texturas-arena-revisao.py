"""Atlas autoral de identificação e microacabamentos; nenhuma imagem externa."""
import io
import json
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont

RAIZ = Path(__file__).resolve().parents[1]
PASTA = RAIZ / 'tmp_revisao'
PASTA.mkdir(exist_ok=True)
fonte = TTFont(RAIZ / 'public/fonts/inter-600.woff')
fonte.flavor = None
buffer = io.BytesIO()
fonte.save(buffer)

rotulos = [
    ('Arena Médica', 'VRmed  /  TREINAMENTO'),
    ('Preparo', '01  /  MATERIAIS'),
    ('Suprimentos', '02  /  ORGANIZAÇÃO'),
    ('Leito de treinamento', 'SIMULAÇÃO EDUCATIVA'),
    ('Apoio e materiais', '03  /  RESERVA'),
    ('Centro de simulação', 'VRmed'),
    ('Higienização', 'ÁREA DE APOIO'),
    ('Posto de apoio', 'TREINAMENTO'),
    ('Compressas', 'MATERIAL DE DEMONSTRAÇÃO'),
    ('Luvas', 'MATERIAL DE DEMONSTRAÇÃO'),
    ('Solução de treino', 'USO CENOGRÁFICO'),
    ('SIMULAÇÃO', 'SEM AQUISIÇÃO CLÍNICA'),
    ('MATERIAIS', 'BANCADA DE PREPARO'),
    ('VRmed', 'ESTAÇÃO DE EXAME'),
    ('ATENÇÃO', 'EQUIPAMENTO DE TREINAMENTO'),
    ('Anatomia', 'ESTUDO • EXPLORAÇÃO • DESCOBERTA'),
]
atlas = Image.new('RGB', (2048, 1024), '#e4e8e2')
d = ImageDraw.Draw(atlas)
for i, (titulo, sub) in enumerate(rotulos):
    x, y = (i % 2) * 1024, (i // 2) * 128
    d.rectangle((x, y, x+1023, y+127), fill='#e4e8e2')
    d.rectangle((x+23, y+21, x+30, y+106), fill='#3b777e')
    size = 57
    f = ImageFont.truetype(io.BytesIO(buffer.getvalue()), size)
    while d.textlength(titulo, font=f) > 906:
        size -= 1
        f = ImageFont.truetype(io.BytesIO(buffer.getvalue()), size)
    d.text((x+512, y+44), titulo, font=f, fill='#18323a', anchor='mm')
    pequeno = ImageFont.truetype(io.BytesIO(buffer.getvalue()), 18)
    d.text((x+512, y+94), sub, font=pequeno, fill='#4c6b70', anchor='mm')
    if i < 8:
        # Autoragem na proporção física evita esticar a fonte para caber no atlas.
        medidas = [(3.666,.276),(1.956,.266),(1.956,.266),(2.506,.336),
                   (2.266,.286),(2.346,.276),(1.586,.266),(1.43,.24)]
        w,h=medidas[i]; img=Image.new('RGB',(round(256*w/h),256),'#e4e8e2')
        pincel=ImageDraw.Draw(img); tamanho=157 if i!=3 else 111
        f=ImageFont.truetype(io.BytesIO(buffer.getvalue()),tamanho)
        while pincel.textlength(titulo,font=f)>img.width-160:
            tamanho-=1; f=ImageFont.truetype(io.BytesIO(buffer.getvalue()),tamanho)
        pincel.text((img.width/2,126 if i!=3 else 91),titulo,font=f,fill='#18323a',anchor='mm')
        if i==3:
            f=ImageFont.truetype(io.BytesIO(buffer.getvalue()),37)
            pincel.text((img.width/2,199),sub,font=f,fill='#4c6b70',anchor='mm')
        atlas.paste(img.resize((1024,128),Image.Resampling.LANCZOS),(x,y))
atlas.save(PASTA/'atlas-arena.png', optimize=True)
(PASTA/'rotulos.json').write_text(json.dumps(rotulos, ensure_ascii=False), encoding='utf-8')

random.seed(921)
for nome, tecido in [('metal', False), ('tecido', True)]:
    n = 256
    rough = Image.new('RGB', (n, n))
    normal = Image.new('RGB', (n, n))
    rp, np = rough.load(), normal.load()
    for y in range(n):
        linha = random.randint(-10, 10)
        for x in range(n):
            r = (231 if tecido else 112) + linha + random.randint(-3, 3)
            rp[x, y] = (255, max(0,min(255,r)), 255)
            np[x, y] = (128+(3 if x%4<2 else -3), 128+(3 if y%4<2 else -3), 255) if tecido else (128, 128+linha//3, 255)
    rough.save(PASTA/f'{nome}-rough.png', optimize=True)
    normal.save(PASTA/f'{nome}-normal.png', optimize=True)
print('Atlas 2048 × 1024 e quatro mapas de microacabamento 256 × 256 criados localmente.')
