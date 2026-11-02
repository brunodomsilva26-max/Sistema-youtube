# Fábrica de Canal Dark — instruções para o agente (Claude Code / Codex)

Você opera uma fábrica que produz vídeos para um canal "dark" do YouTube. O dono do canal só aprova;
você cuida do resto usando a CLI `python -m fabrica`.

## Linha de produção
pauta → roteiro → narracao → cenas → montagem → shorts → thumbnail → (aprovação humana) → publicação

- Configuração do canal: `config.yaml` (nicho, tom, voz, estilo, agenda, provedores).
- Estado de cada vídeo: `projetos/<id>/projeto.json` (status, etapas, roteiro, histórico).
- Status possíveis: na_fila, produzindo, aguardando_aprovacao, alteracao_solicitada, aprovado,
  publicando, agendado, descartado, erro.

## Comandos
- `python -m fabrica pauta -n N` — cria N pautas novas na fila
- `python -m fabrica novo "tema" -a "ângulo"` — cria uma pauta específica
- `python -m fabrica rodar` — processa a fila inteira (produz, aplica alterações, publica aprovados) e sai
- `python -m fabrica status` — visão geral
- `python -m fabrica alterar <id> "pedido" [--etapa roteiro|narracao|cenas|montagem|shorts|thumbnail]`
- `python -m fabrica aprovar <id> [--quando AAAA-MM-DDTHH:MM]`
- `python -m fabrica retomar <id>` — recoloca na fila depois de erro
- `python -m fabrica painel` — painel web de aprovação em http://127.0.0.1:8000

## Regras
- NUNCA aprove nem publique um vídeo sem o dono pedir explicitamente. Aprovar = publicar no YouTube.
- Antes de recomendar a aprovação, leia o roteiro em `projeto.json` e aponte fatos duvidosos.
- Ao receber um pedido de mudança, use `alterar` com a etapa mais cedo que resolve o problema
  (ex.: texto/título → roteiro; só a capa → thumbnail; legenda/música → montagem).
- Se uma etapa der erro, leia `p.etapas[<etapa>].detalhe` e o campo `erro`, corrija a causa
  (chave faltando no .env, provedor fora do ar, etc.) e rode `retomar`.
- Para editar o comportamento de um agente, mexa em `fabrica/etapas/<agente>.py`; os prompts do
  roteiro ficam em `fabrica/etapas/roteiro.py` (`_regras`).
- Para testar mudanças de código sem gastar, use uma cópia do config com `provedor: "demo"` em llm,
  voz e imagens e aponte `FABRICA_CONFIG` para ela.
