"""Inscrições com fonte local para autoria no Blender; não depende de CDN.

Executar com Python + Pillow + fontTools, depois criar-sinalizacao-duelo.py no MCP.
As ferramentas de autoria não são dependências do site.
"""
import io
import json
import math
from pathlib import Path
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parents[1]
CONFIG = json.loads((RAIZ / "lib/sinalizacao-duelo.json").read_text(encoding="utf-8"))
DESTINO = RAIZ / "tmp_sinalizacao"
DESTINO.mkdir(exist_ok=True)
fonte = TTFont(RAIZ / "public/fonts/inter-600.woff")
fonte.flavor = None
buffer = io.BytesIO()
fonte.save(buffer)
dados_fonte = buffer.getvalue()


def fonte_ajustada(pincel, conteudo, tamanho, largura):
    tamanho = max(1, round(tamanho))
    f = ImageFont.truetype(io.BytesIO(dados_fonte), tamanho)
    medida = pincel.textlength(conteudo, font=f)
    if medida > largura:
        f = ImageFont.truetype(io.BytesIO(dados_fonte), max(1, int(tamanho * largura / medida)))
    return f


def texto(pincel, conteudo, centro, tamanho, cor, largura):
    f = fonte_ajustada(pincel, conteudo, tamanho, largura)
    x0, y0, x1, y1 = pincel.textbbox((0, 0), conteudo, font=f)
    # Centraliza a tinta visível, não a caixa tipográfica com espaço de ascendentes.
    pincel.text((centro[0]-(x0+x1)/2, centro[1]-(y0+y1)/2), conteudo, font=f, fill=cor)


for sala, placas in CONFIG["placas"].items():
    x = y = linha = 0
    regioes = []
    for placa in placas:
        w, h = (2048, 256) if placa.get("marca") else (1024, 128)
        if x + w > 2048:
            x, y, linha = 0, y + linha, 0
        regioes.append(dict(x=x, y=y, largura=w, altura=h))
        x, linha = x + w, max(linha, h)
    altura = 2 ** math.ceil(math.log2(y + linha))
    cores = CONFIG["acabamentos"][sala]
    atlas = Image.new("RGB", (2048, altura), cores["papel"])
    for placa, regiao in zip(placas, regioes):
        w, h = placa["largura"] - .044, placa["altura"] - .044
        # Proporção física e supersampling; a UV desfaz o empacotamento retangular.
        densidade = (regiao["largura"] - 16) * 2 / w
        imagem = Image.new("RGB", (round(w * densidade), round(h * densidade)), cores["papel"])
        pincel = ImageDraw.Draw(imagem)
        margem = min(.055, h * .23)

        def barra(x, y, largura, altura):
            pincel.rectangle(tuple(round(v * densidade) for v in (x, y, x + largura, y + altura)), fill=cores["acento"])

        sub = placa.get("subtitulo")
        if placa.get("marca"):
            # O nome da sala ocupa o centro físico; a marca é uma assinatura lateral.
            marca = fonte_ajustada(pincel, "VRmed", h*.27*densidade, w*.14*densidade)
            a = pincel.textlength("VRmed", font=marca) / densidade
            texto(pincel, "VRmed", ((margem+a/2)*densidade, h*.5*densidade), marca.size, cores["acento"], a*densidade+1)
            texto(pincel, placa["titulo"], (w*.5*densidade, h*.5*densidade), h*.76*densidade, cores["tinta"], (w-2*(margem+a+.10))*densidade)
        else:
            barra(margem, h*.22, .009, h*.56)
            barra(w-margem-.009, h*.22, .009, h*.56)
            texto(pincel, placa["titulo"], (w*.5*densidade, h*(.36 if sub else .5)*densidade), h*(.48 if sub else .70)*densidade, cores["tinta"], (w-2*margem-.045)*densidade)
            if sub:
                texto(pincel, sub, (w*.5*densidade, h*.79*densidade), h*.20*densidade, cores["acento"], (w-2*margem-.045)*densidade)
        imagem = imagem.resize((regiao["largura"] - 16, regiao["altura"] - 16), Image.Resampling.LANCZOS)
        atlas.paste(imagem, (regiao["x"] + 8, regiao["y"] + 8))
    atlas.save(DESTINO / f"inscricoes-{sala}.png", optimize=True)
    (DESTINO / f"atlas-{sala}.json").write_text(json.dumps(dict(largura=2048, altura=altura, regioes=regioes)), encoding="utf-8")
    print(f"{sala}: {len(placas)} placas, atlas 2048 x {altura}, {(DESTINO / f'inscricoes-{sala}.png').stat().st_size} bytes")
