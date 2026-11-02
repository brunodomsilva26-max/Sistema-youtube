---
description: Pede uma alteração em um vídeo
argument-hint: <id> <o que mudar>
---
Pedido do dono do canal: $ARGUMENTS

1. Identifique o id do projeto (primeira palavra; se faltar, use `python -m fabrica status` e pergunte).
2. Escolha a etapa mais cedo que resolve: roteiro, narracao, cenas, montagem, shorts ou thumbnail.
3. Rode `python -m fabrica alterar <id> "<pedido>" --etapa <etapa>` e depois `python -m fabrica rodar`.
4. Informe quando o vídeo voltar para "Aguardando aprovação".
