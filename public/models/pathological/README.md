# Modelos patológicos (.glb)

Coloque aqui os arquivos `.glb` das versões patológicas dos órgãos, usados no
modo de comparação (`/compare`).

- O nome do arquivo deve ser **idêntico** ao do modelo saudável correspondente
  em `../healthy/`. Exemplo: `coracao.glb` (coração hipertrofiado),
  `pulmao.glb` (enfisema), `figado.glb` (cirrose).
- O órgão precisa ter `pathologicalPath` definido em `lib/organs.ts`.
- Sem o arquivo, o modo de comparação exibe um modelo de demonstração com o
  selo "Modelo de demonstração" e o aviso "Modelo patológico real em preparação"
  — sem quebrar a interface nem passar o placeholder por modelo real.
