# Áudios pré-gravados (fallback do TTS)

Coloque aqui arquivos `.mp3` com a narração das descrições dos órgãos.

- O nome do arquivo deve corresponder ao `id` do órgão. Exemplo: `coracao.mp3`.
- Estes áudios são um **fallback**: a narração usa primeiro a síntese de voz
  do navegador (Web Speech API, voz `pt-BR`). O arquivo `.mp3` só é usado
  quando nenhuma voz em português está disponível.
