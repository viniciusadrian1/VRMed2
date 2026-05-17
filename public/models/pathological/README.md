# Modelos patológicos (.glb)

Coloque aqui os arquivos `.glb` das versões patológicas dos órgãos, usados no
modo de comparação (`/compare`).

- O nome do arquivo deve ser **idêntico** ao do modelo saudável correspondente
  em `../healthy/`. Exemplo: `coracao.glb` (coração hipertrofiado),
  `pulmao.glb` (enfisema), `figado.glb` (cirrose).
- O órgão precisa ter `pathologicalPath` definido em `lib/organs.ts`.
- Sem o arquivo, o modo de comparação exibe um modelo de demonstração e um
  aviso de "modelo em breve" — sem quebrar a interface.
