# Créditos de modelos (props)

- `monitor.glb` — "Office Monitor / Workstation Monitor" por
  [DatSketch](https://sketchfab.com/DatSketch), licença
  [CC-BY-4.0](http://creativecommons.org/licenses/by/4.0/).
  Fonte: https://sketchfab.com/3d-models/office-monitor-workstation-monitor-6a7b0147890242418a49f6db26657ab4
- `mesa.glb` — "Office Table 1600x800 mm Nova U dark" por
  [alex_ko](https://sketchfab.com/alex_ko), licença
  [CC-BY-4.0](http://creativecommons.org/licenses/by/4.0/).
  Fonte: https://sketchfab.com/3d-models/office-table-1600x800-mm-nova-u-dark-3aa915f97d1c4a5c986f5beedbd64172
- `cadeira.glb` — "Office Chair Modern" por
  [thethieme](https://sketchfab.com/thethieme), licença
  [CC-BY-4.0](http://creativecommons.org/licenses/by/4.0/).
  Fonte: https://sketchfab.com/3d-models/office-chair-modern-675f34f7304e4d92812a41e9750539aa
- `teclado-mouse.glb` — "Keyboard Mouse" por
  [arsenif5690](https://sketchfab.com/arsenif5690), licença
  [CC-BY-4.0](http://creativecommons.org/licenses/by/4.0/).
  Fonte: https://sketchfab.com/3d-models/keyboard-mouse-b6644ed405f8489091be482d34cb7195
- `livro.glb` — "Book - Encyclopedia" por
  [Maxence Rouillet](https://sketchfab.com/maxencerouillet), licença
  [CC-BY-4.0](http://creativecommons.org/licenses/by/4.0/).
  Fonte: https://sketchfab.com/3d-models/book-encyclopedia-0487cb088c244d02a736cb337e65778c
- `radio.glb` — "Philips Radio" por
  [Lassi Kaukonen](https://sketchfab.com/thesidekick), licença
  [CC-BY-4.0](http://creativecommons.org/licenses/by/4.0/).
  Fonte: https://sketchfab.com/3d-models/philips-radio-46bdaf3fb5cc47b2a7c3f273433dc0dd

## Ambiente Hospital do Duelo (`public/models/hospital/`)

Todos do Sketchfab, licença CC-BY-4.0, com dieta simplify/resize/webp/draco:

- `trolley.glb` — "Hospital Trolley" por creative_beast
- `monitor-hr.glb` — "Monitor with heart rate" por Sousinho
- `cortina-monitor.glb` — "Bed Curtain and Vital Signs Monitor" por Ethan Cragun
- `ultrassom.glb` — "Ultrasound Machine" por Liuuzaki
- `cadeira-rodas.glb` — "WheelChair" por Loïc
- `props-medicos.glb` — "Medical Props" por coa white (reserva, ainda não em cena)

Fora do projeto por decisão: "Surgical/Instrument table collection" (CC-BY-NC,
não-comercial) e "Hospital Stuff" (1,67M triângulos — inviável em VR).

## Arena médica — incremento de setembro de 2026

- `bancada-arena.glb`: bancada e luminária autorais do projeto, geradas
  proceduralmente por `scripts/criar-bancada-arena.py`. Sem assets externos.
  1.728 triângulos, 5 materiais, unidades em metros, 125.028 bytes.
- `dr-caloni-arena.glb`, `dra-reis-arena.glb`, `dr-chefe-arena.glb`:
  variantes de apresentação dos personagens já fornecidos pelo projeto.
  Derivadas dos arquivos homônimos sem `-arena`, que permanecem intactos.
  Redução de geometria apenas nesses personagens decorativos, texturas de até
  1.024 pixels e compressão Draco. Nenhum órgão foi simplificado.
  A variante não altera nem concede novos direitos sobre o personagem original.
- A referência a Surgeon Simulator é de composição e apresentação, sem uso de
  seus modelos, texturas, personagens, marcas ou arquivos.
- `entorno-arena.glb`: arquitetura e equipamentos de apoio autorais, gerados
  no Blender por `scripts/criar-entorno-arena.py`: armários, cuba/torneira,
  carrinho de instrumentos, equipamento de treinamento, janela técnica,
  porta e ventilação. Oito materiais, sem texturas externas. O visor é uma
  representação abstrata de simulação, não um exame ou sinal clínico.
- `retaguarda-arena.glb`: apoio hospitalar autoral produzido no Blender por
  `scripts/criar-retaguarda-arena.py`: leito vazio de treinamento, cortina,
  cabeceira técnica, armário de materiais, higienização, posto de apoio e
  acabamento da entrada. 18.423 triângulos, oito malhas/materiais, sem texturas
  ou animações, 1.321.600 bytes, unidades em metros. Sem assets externos ou
  anatomia gerada. Substitui a instância antiga de cortina/monitor; seu arquivo
  de origem permanece no acervo. Telas e equipamentos são cenográficos.

## Escola de medicina — 2026-09-23

- `escola-medicina.glb`: sala autoral gerada no Blender por
  `scripts/criar-escola-medicina.py`. Arquitetura, bancada, lousa, vitrine,
  microscópios estilizados, atlas, carteiras e luminárias sem assets externos.
  Revisão de acabamento/orientação: 21.694 triângulos, 11 malhas/materiais,
  sem texturas, 1.530.688 bytes. Cadeiras removidas; carteiras alinhadas aos
  competidores, pranchetas, lâminas e microscópios mais detalhados. Demarcações
  e zona dos postos rente ao piso, sem plataforma elevada.
- `esqueleto-estudo.glb`: exposição de ossos e dentes extraída do arquivo
  `public/models/systems/arthrology.glb` já presente no acervo. Três malhas,
  158.090 triângulos preservados, materiais de apresentação e compressão Draco;
  sem decimação e sem modificar o original. Não representa a camada completa
  de ligamentos/cartilagens do arquivo de artrologia.
- `esqueleto-prancha.png`: renderização frontal das mesmas malhas originais,
  feita no Blender (512 × 1.024). Não é anatomia gerada por IA. Serve como
  alternativa leve na vitrine durante a partida.
- As duas apresentações do esqueleto são reproduzidas por
  `scripts/preparar-esqueleto-escola.py`. A derivação não altera nem concede
  novos direitos sobre o acervo original; mantém-se a responsabilidade de
  documentar a licença de origem antes de redistribuí-lo fora do projeto.
