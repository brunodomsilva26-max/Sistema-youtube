# 🏭 Fábrica de Canal Dark no YouTube

Sistema que produz o canal inteiro sozinho: **pauta → roteiro → narração → cenas → montagem → shorts → thumbnail → agendamento no YouTube** (API oficial).
Você só abre o painel, assiste e **aprova**. Se quiser mudar algo, escreve o pedido e o agente certo refaz só aquela parte.

```
 1 Pauta ─▶ 2 Roteiro ─▶ 3 Narração ─▶ 4 Cenas ─▶ 5 Montagem ─▶ 6 Shorts ─▶ 7 Thumbnail
                                                                                  │
                                         VOCÊ: ✓ aprovar  /  ✏️ pedir alteração ◀─┘
                                                     │
                                          8 Publicação: sobe no YouTube como
                                            privado + estreia programada
```

## O que cada agente faz

| # | Agente | Como faz | Custo |
|---|--------|----------|-------|
| 1 | **Pauta** | Claude sugere temas novos do seu nicho sem repetir os anteriores | centavos |
| 2 | **Roteiro** | Claude escreve o roteiro em blocos, título, descrição, tags, conceito da thumb e 3 roteiros de Shorts | centavos |
| 3 | **Narração** | TTS por bloco: Edge TTS (grátis, voz neural pt-BR) ou ElevenLabs | grátis / pago |
| 4 | **Cenas** | Uma imagem por bloco: Pollinations (grátis) ou OpenAI gpt-image-1 | grátis / pago |
| 5 | **Montagem** | ffmpeg: movimento de câmera (Ken Burns), legendas queimadas, música de fundo, 1080p | grátis |
| 6 | **Shorts** | Vídeos 1080x1920 até 59s, fundo desfocado, legenda grande | grátis |
| 7 | **Thumbnail** | Imagem IA + texto gigante com contorno e palavra em amarelo | grátis |
| 8 | **Publicação** | YouTube Data API v3: upload, thumbnail, `publishAt` nos próximos horários livres | grátis |

## Instalação (uma vez)

Precisa de **Python 3.10+** e **ffmpeg**.

```bash
git clone https://github.com/brunodomsilva26-max/Sistema-youtube.git
cd Sistema-youtube
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                  # coloque sua ANTHROPIC_API_KEY
```

ffmpeg: `brew install ffmpeg` (Mac) · `sudo apt install ffmpeg` (Linux) · `winget install ffmpeg` (Windows).

Depois edite o **`config.yaml`**: nome do canal, nicho, público, tom, duração, voz, estilo das imagens e os dias/horários de publicação.

## Testar sem gastar nada (modo demo)

No `config.yaml`, coloque `provedor: "demo"` em `llm`, `voz` e `imagens`. Depois:

```bash
python -m fabrica pauta -n 1
python -m fabrica painel          # abre http://127.0.0.1:8000
```

## Uso no dia a dia

```bash
python -m fabrica painel          # painel + fábrica ligada
```

- **Aprovação** — a fila de vídeos prontos. Abra, assista o vídeo e os shorts, veja a thumb e:
  - **✓ Aprovar e agendar** → sobe tudo no YouTube programado (vídeo + shorts em horários seguintes);
  - **✏️ Pedir alteração** → ex.: *"a thumbnail precisa dizer SUMIU SEM RASTRO"*. A IA descobre qual agente
    resolve e refaz só ele e o que depende dele (mudar thumb não refaz o vídeo; mudar roteiro refaz tudo).
- **Fábrica** — o escritório: cada agente mostra o que está fazendo em tempo real.
- **Agenda** — tudo que está programado no YouTube.
- **Nova pauta** (barra lateral) — digite um tema, ou deixe vazio para o agente sugerir 3.

### Linha de comando

```bash
python -m fabrica pauta -n 5                      # agente de pauta cria 5 vídeos na fila
python -m fabrica novo "O mistério do voo 370" -a "a última mensagem do piloto"
python -m fabrica status                          # lista tudo com o progresso de cada etapa
python -m fabrica rodar                           # produz toda a fila e sai (bom para cron)
python -m fabrica aprovar <id> [--quando 2026-11-20T18:00]
python -m fabrica alterar <id> "deixa a narração mais lenta" [--etapa narracao]
python -m fabrica retomar <id>                    # depois de um erro
```

## Conectar o YouTube (API oficial)

1. Em <https://console.cloud.google.com>, crie um projeto e ative a **YouTube Data API v3**.
2. **Tela de consentimento OAuth** → tipo *Externo* → adicione seu e-mail em *Usuários de teste*.
3. **Credenciais → Criar → ID do cliente OAuth → App para computador** → baixe o JSON e salve como
   `credenciais/client_secret.json`.
4. Rode `python -m fabrica youtube-login` e autorize **com a conta do canal**.
5. No `config.yaml`, troque `youtube.modo` para `"real"`.

Os vídeos sobem como **privados com estreia programada** (`publishAt`) e com a flag de conteúdo
sintético (IA) declarada. Observações:

- A cota padrão é de 10.000 unidades/dia e upload é a operação mais cara da API (cada vídeo aprovado
  faz 1 upload do longo + 1 por short). Confira o consumo em *APIs e serviços → Cotas* e peça aumento se precisar.
- Projetos do Google Cloud **não verificados** podem ter os uploads travados como privados. Para estreias
  automáticas, faça a verificação/auditoria do app no Google (formulário de *YouTube API Services Audit*).
- Thumbnail personalizada exige canal verificado por telefone.

## Usar com o Claude Code / Codex

O repositório já vem com `CLAUDE.md` / `AGENTS.md` e comandos prontos. Abra a pasta no Claude Code e use:

| Comando | O que faz |
|---|---|
| `/pauta 5` | gera 5 pautas e coloca na fila |
| `/produzir` | roda a fábrica até esvaziar a fila |
| `/status` | resumo do que está em cada etapa |
| `/revisar <id> <pedido>` | pede uma alteração |
| `/aprovar <id>` | aprova e agenda |

Sem chave da API Anthropic? Use `llm.provedor: "claude_code"` — o roteiro passa a ser escrito pelo
`claude -p` da sua própria assinatura do Claude Code.

## Rodar 24h

Deixe `python -m fabrica painel --host 0.0.0.0` rodando num PC/VPS, ou agende `python -m fabrica pauta -n 3 && python -m fabrica rodar`
no cron. Você aprova pelo celular acessando o painel (use uma VPN/Tailscale; o painel não tem login).

## Estrutura

```
config.yaml              ← SEU canal (nicho, voz, estilo, agenda)
fabrica/
  pipeline.py            ← orquestrador / worker
  estado.py              ← status de cada projeto (projetos/<id>/projeto.json)
  llm.py                 ← Claude (API, CLI do Claude Code ou demo)
  etapas/                ← um arquivo por agente
  youtube.py, agenda.py  ← upload e horários livres
  painel/                ← painel web (Flask)
projetos/<id>/           ← tudo que foi gerado: audio/, cenas/, video.mp4, shorts/, thumbnail.jpg
```

## Boas práticas (para o canal não ser desmonetizado)

O YouTube desmonetiza "conteúdo repetitivo/produzido em massa". Por isso a fábrica **sempre** passa por
você antes de publicar. Use a aprovação para garantir que cada vídeo tem valor real, revise os fatos,
varie formatos e mantenha a declaração de conteúdo sintético ligada.
