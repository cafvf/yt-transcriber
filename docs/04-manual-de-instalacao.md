# Manual de Instalação

Este documento detalha a instalação do YT Transcriber Bot em **Fedora nativo** e **Ubuntu via WSL2**, dois ambientes oficialmente suportados. Outros sistemas baseados em Linux podem funcionar com adaptações triviais.

A instalação base leva cerca de 30–60 minutos, dominada pelo download dos modelos de IA na primeira execução. Para operação contínua em servidor, use também o [runbook do operador](./11-operator-runbook.md).

---

## 1. Pré-requisitos do sistema

### 1.1 Hardware mínimo
- **CPU**: x86_64, qualquer processador moderno.
- **RAM**: mínimo 8 GB para modelos pequenos (`tiny`, `base`, `small`); 16 GB recomendado para `medium`; 32 GB para `large-v3`.
- **GPU (opcional)**: qualquer NVIDIA com Compute Capability ≥ 6.0 (Pascal/2016+) — Maxwell e anteriores serão tratadas como CPU pelo bot.
- **Disco**: 20 GB livres recomendados (modelos ocupam até 8 GB; cache do Hugging Face e dependências Python somam mais alguns GB).

### 1.2 Sistema operacional
- **Fedora 38+** nativo, ou
- **Ubuntu 22.04+** rodando em **WSL2** (Windows 10/11).

> **Por que não outros?** O projeto foi explicitamente especificado para esses dois ambientes. Distros derivadas (Pop!\_OS, Linux Mint, etc.) provavelmente funcionam, mas não são testadas.

### 1.3 Software de sistema
| Pacote | Por quê | Como instalar (Fedora) | Como instalar (Ubuntu/WSL) |
|---|---|---|---|
| `git` | Clonar o repositório | `sudo dnf install git` | `sudo apt install git` |
| `ffmpeg` | Conversão de áudio | `sudo dnf install ffmpeg` (requer RPM Fusion) | `sudo apt install ffmpeg` |
| `curl` | Instalar `uv` | `sudo dnf install curl` | `sudo apt install curl` |
| `build-essential` / `gcc` | Compilação de wheels nativas | `sudo dnf groupinstall "Development Tools"` | `sudo apt install build-essential` |

> **Fedora e ffmpeg**: ffmpeg requer o repositório RPM Fusion. Se ainda não tiver:
> ```bash
> sudo dnf install https://download1.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm
> sudo dnf install ffmpeg
> ```

### 1.4 (Opcional) GPU NVIDIA
Se for usar GPU:
- Drivers proprietários NVIDIA instalados (`nvidia-smi` deve funcionar).
- CUDA Toolkit **não é necessário** instalar manualmente — o PyTorch traz suas próprias bibliotecas via `pip`.
- Em **WSL2**, GPU funciona desde Windows 11 + WSL2 + drivers NVIDIA específicos para WSL no host Windows. Verifique com `nvidia-smi` rodado **dentro** do WSL.

---

## 2. Instalar o `uv`

[`uv`](https://docs.astral.sh/uv/) é o gerenciador de ambientes Python escolhido para o projeto: rápido, moderno, com suporte nativo a `pyproject.toml` e lockfile reproduzível.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Após a instalação, abra um novo terminal (ou `source ~/.bashrc`) e verifique:

```bash
uv --version
```

---

## 3. Clonar o projeto

```bash
git clone <url-do-repo> ~/yt-transcriber-bot
cd ~/yt-transcriber-bot
```

> O caminho `~/yt-transcriber-bot` é uma sugestão; qualquer caminho do filesystem funciona. Os exemplos a seguir assumem este caminho — ajuste se usar outro.

---

## 4. Criar o ambiente Python e instalar dependências

```bash
cd ~/yt-transcriber-bot
uv sync
```

Esse comando:
1. Lê `pyproject.toml` e `uv.lock`.
2. Cria um ambiente virtual em `.venv/` com Python 3.11 ou 3.12, conforme o interpretador compatível selecionado pelo `uv`.
3. Instala todas as dependências exatamente nas versões travadas, incluindo `torch`, `torchaudio`, `whisperx`, `pyannote.audio` e `faster-whisper`.

Tempo: 3–20 minutos, dependendo da rede e do cache local. O PyTorch é grande e pode baixar pacotes CUDA mesmo quando o processamento final usar CPU.

> Em versões antigas deste projeto era necessário `uv sync --extra ml`. A partir da versão 0.1.2, a stack de ML é dependência principal, porque o fluxo real do bot depende dela. O extra `ml` foi mantido apenas por compatibilidade.

---

## 5. Obter o Bot Token e seu User ID do Telegram

### 5.1 Criar o bot e obter o token
Você já tem; reproduzo aqui o procedimento padrão para referência:
1. No Telegram, fale com [@BotFather](https://t.me/BotFather).
2. Envie `/newbot`.
3. Escolha um nome (livre) e um username (deve terminar com `bot`).
4. O BotFather responde com o **token** (formato `123456789:ABCdef-Ghi...`). **Guarde-o.**

### 5.2 Descobrir seu User ID
1. No Telegram, fale com [@userinfobot](https://t.me/userinfobot).
2. Envie qualquer mensagem; ele responde com seu `Id` numérico (ex.: `123456789`). **Guarde-o.**

---

## 6. Obter o token do Hugging Face e aceitar termos do pyannote

A diarização requer modelos do projeto pyannote, hospedados no Hugging Face com termos de uso. Ações:

### 6.1 Criar conta e gerar token
1. Crie conta gratuita em https://huggingface.co/join (se não tiver).
2. Vá em https://huggingface.co/settings/tokens.
3. Crie um token do tipo **Read** (sem permissões de escrita). Nome livre.
4. Copie o token (formato `hf_xxxxxxxxxxxxxxxxxx`). **Guarde-o.**

### 6.2 Aceitar os termos dos modelos
Em cada uma das páginas abaixo, faça login com sua conta do Hugging Face e clique no botão para aceitar os termos:
1. https://huggingface.co/pyannote/speaker-diarization-community-1
2. Em ambientes antigos/legados, também aceite: https://huggingface.co/pyannote/speaker-diarization-3.1
3. Em ambientes antigos/legados, também pode ser necessário aceitar: https://huggingface.co/pyannote/segmentation-3.0

Sem este passo, o bot pode falhar com erro `401 Unauthorized`, `403 Forbidden` ou mensagem de modelo gated na primeira tentativa de diarização.

---

## 7. Configurar variáveis de ambiente do usuário

> **Princípio**: segredos (tokens, IDs pessoais) **não** ficam em arquivos do projeto. Eles são variáveis de ambiente do **usuário do sistema operacional**.

### 7.1 Para Fedora ou Ubuntu/WSL com Bash
Edite (ou crie) `~/.bashrc` e adicione, ao final:

```bash
# === YT Transcriber Bot — segredos ===
export TELEGRAM_BOT_TOKEN="123456789:SEU_TOKEN_AQUI"
export TELEGRAM_ALLOWED_USER_ID="123456789"
export HF_TOKEN="hf_SEU_TOKEN_AQUI"

# === YT Transcriber Bot — cookies do YouTube (opcional) ===
# Use APENAS UMA das duas linhas abaixo (ou nenhuma se não vai
# acessar vídeos members-only / idade-restritos).
# export YOUTUBE_COOKIES_BROWSER="firefox"
# export YOUTUBE_COOKIES_FILE="$HOME/.config/yt-transcriber-bot/cookies.txt"
```

Recarregue:
```bash
source ~/.bashrc
```

Verifique:
```bash
echo $TELEGRAM_BOT_TOKEN
echo $TELEGRAM_ALLOWED_USER_ID
echo $HF_TOKEN
```

### 7.2 Para Zsh
Mesma coisa, mas em `~/.zshrc`.

### 7.3 Para uso com systemd
O serviço systemd lê as variáveis de um **arquivo separado** (não do `~/.bashrc`, pois systemd não carrega seu shell). Veja seção 11.

---

## 8. (Opcional) Configurar cookies do YouTube

Use cookies se quiser acessar:
- Vídeos members-only de canais aos quais você é assinante.
- Vídeos idade-restritos.
- Algum cenário em que o YouTube esteja exigindo "Sign in to confirm you're not a bot".

Há duas formas:

### 8.1 Forma A — `--cookies-from-browser` (mais simples)
Configure a variável `YOUTUBE_COOKIES_BROWSER` (no seu `~/.bashrc`) com o nome do navegador onde você está logado no YouTube:

```bash
export YOUTUBE_COOKIES_BROWSER="firefox"   # ou "chrome", "chromium", "brave", "edge"
```

O `yt-dlp` lerá os cookies diretamente do perfil do navegador instalado.

**Limitações**:
- O navegador precisa estar instalado **na mesma máquina** onde o bot roda.
- Em **WSL2**, o navegador no Windows host **não** é acessível ao yt-dlp dentro do WSL — você precisaria de um navegador Linux dentro do WSL, ou usar a Forma B.
- Alguns navegadores criptografam cookies (Chrome no Linux usa keyring); a leitura pode falhar silenciosamente.

### 8.2 Forma B — arquivo `cookies.txt`
1. Instale uma extensão de exportação de cookies no seu navegador. Recomendado: **"Get cookies.txt LOCALLY"** (Firefox e Chromium-based, open source).
2. Vá em https://www.youtube.com (logado).
3. Use a extensão para exportar **apenas os cookies do youtube.com** no formato Netscape.
4. Salve o arquivo (ex.: `~/.config/yt-transcriber-bot/cookies.txt`).
5. Configure:
   ```bash
   mkdir -p ~/.config/yt-transcriber-bot
   chmod 700 ~/.config/yt-transcriber-bot
   # mova o cookies.txt para lá e:
   chmod 600 ~/.config/yt-transcriber-bot/cookies.txt
   export YOUTUBE_COOKIES_FILE="$HOME/.config/yt-transcriber-bot/cookies.txt"
   ```

> **Atenção de segurança**: cookies do YouTube logado equivalem a uma sessão ativa da sua conta Google. Trate o arquivo como uma senha. As permissões `700`/`600` acima são essenciais.

### 8.3 Renovação
Cookies expiram. Se o bot começar a rejeitar vídeos com erro de autenticação, reexporte o cookies.txt.

---

## 9. (Opcional) Customizar configurações não-sensíveis

Crie um arquivo `.env` na raiz do projeto (`~/yt-transcriber-bot/.env`) **apenas** se quiser sobrescrever defaults:

```bash
# Modelo Whisper. Use auto para política por idioma.
WHISPER_MODEL=auto
WHISPER_MODEL_PT=large-v3
WHISPER_MODEL_EN=medium
WHISPER_MODEL_DEFAULT=medium

# Execução local
DEVICE=auto
COMPUTE_TYPE=auto
PREFER_YOUTUBE_SUBTITLES=true

# Áudio
AUDIO_BITRATE_KBPS=32
AUDIO_SAMPLE_RATE_HZ=16000

# Limite de duração (minutos)
MAX_VIDEO_DURATION_MIN=180

# Retenção FIFO
RETENTION_COUNT=5

# Paths (relativos ao diretório do projeto ou absolutos)
BASE_DIR=data
DOWNLOADS_DIR_NAME=downloads
PROCESSED_DIR_NAME=processed
TRANSCRIPTS_DIR_NAME=transcripts
LOGS_DIR_NAME=logs
MODELS_DIR=models
DB_PATH=data/jobs.db

# Observabilidade
HEALTHCHECK_MIN_FREE_DISK_MB=500
HEALTHCHECK_LMSTUDIO_TIMEOUT_S=5
LASTERROR_RECENT_LIMIT=50
```

> O `.env` local pode conter secrets para uso pessoal, mas **nunca deve ser versionado**.
> Use `.env.example` apenas com placeholders.
> Antes de commitar, instale os hooks de segurança com `uv run pre-commit install`.

### 9.1 Sumarização com LM Studio

Para usar o comando `/summary [n]`, o bot precisa acessar uma API compatível com OpenAI. No uso local recomendado, essa API é o servidor do LM Studio.

Configuração típica no `.env`:

```env
SUMMARY_BACKEND=openai_compatible
SUMMARY_BASE_URL=http://127.0.0.1:1234/v1
SUMMARY_MODEL=qwen3.5-9b
SUMMARY_API_KEY=
SUMMARY_TEMPERATURE=0.2
SUMMARY_MAX_TOKENS=1024
SUMMARY_MAX_CHARS_PER_CHUNK=4000
SUMMARY_MAX_INPUT_TOKENS=2500
SUMMARY_CHARS_PER_TOKEN=2.0
SUMMARY_TIMEOUT_S=300
SUMMARY_OUTPUT_LANGUAGE=auto
SUMMARY_DISABLE_THINKING=true
SUMMARIES_DIR_NAME=summaries
```

Antes de iniciar o bot, abra o LM Studio, carregue o modelo desejado e ative o servidor local na aba **Developer / Local Server**. Valide no mesmo ambiente em que o bot roda:

```bash
curl http://127.0.0.1:1234/v1/models
```

Use em `SUMMARY_MODEL` o `id` do modelo retornado por esse endpoint.

Para modelos Qwen com reasoning/thinking, mantenha:

```env
SUMMARY_DISABLE_THINKING=true
```

Essa opção não transforma o resumo em uma tarefa de raciocínio: o bot pede resposta direta, envia `enable_thinking=false` e `chat_template_kwargs={"enable_thinking": false}` quando suportado pelo servidor OpenAI-compatible e limpa blocos `<think>...</think>` residuais antes de salvar o Markdown.

Se o log do LM Studio mostrar que a resposta veio com `content` vazio e `reasoning_content` preenchido, o preset/modelo ainda está operando em thinking mode. Desative **Enable Thinking** no LM Studio ou selecione um preset non-thinking. O bot rejeita esse caso de propósito, porque `reasoning_content` não deve ser usado como artefato final.

Para verificar se o `.env` foi carregado corretamente, rode na raiz do projeto:

```bash
uv run python scripts/config/print_effective_settings.py
```

O script mostra as configurações efetivas e mascara segredos.

Para servidores locais com janela de contexto de 4096 tokens, use a configuração conservadora acima. O bot não tem acesso ao tokenizer exato do modelo carregado no LM Studio; por isso, o chunking usa uma estimativa segura com `SUMMARY_MAX_INPUT_TOKENS` e `SUMMARY_CHARS_PER_TOKEN`. Se aparecer no LM Studio um erro como `request (...) exceeds the available context size (4096 tokens)`, reduza:

```env
SUMMARY_MAX_INPUT_TOKENS=2000
SUMMARY_MAX_CHARS_PER_CHUNK=3000
SUMMARY_MAX_TOKENS=768
```

### 9.2 WSL2 + LM Studio no Windows: habilitar Mirrored Mode

Se o bot roda no **Ubuntu/WSL2** e o LM Studio roda no **Windows**, habilite o **Mirrored Mode** do WSL2. Esse modo faz com que o host Windows e a VM WSL2 possam conversar usando `localhost`/`127.0.0.1`, simplificando o acesso ao servidor local do LM Studio.

No Windows, crie ou edite:

```text
%USERPROFILE%\.wslconfig
```

Conteúdo recomendado:

```ini
[wsl2]
networkingMode=mirrored
dnsTunneling=true
autoProxy=true
```

Depois, no PowerShell:

```powershell
wsl --shutdown
```

Reabra o WSL2, inicie o servidor do LM Studio no Windows e teste **dentro do WSL2**:

```bash
curl http://127.0.0.1:1234/v1/models
```

Se funcionar, mantenha:

```env
SUMMARY_BASE_URL=http://127.0.0.1:1234/v1
```

Se ainda houver `Connection refused`, verifique:

1. se o servidor do LM Studio está ativo;
2. se a porta configurada no LM Studio é realmente `1234`;
3. se o firewall do Windows está bloqueando o acesso;
4. se o WSL foi reiniciado com `wsl --shutdown` depois da alteração em `.wslconfig`.



---

## Diagnóstico operacional após instalação

Depois de configurar `.env`, dependências, cookies e LM Studio, use os diagnósticos em duas camadas:

```bash
uv run python scripts/config/print_effective_settings.py
```

Esse script mostra a configuração efetiva no terminal e é útil antes de iniciar o bot. Depois que o bot estiver rodando, use no Telegram:

```text
/healthcheck
```

O `/healthcheck` verifica configuração obrigatória, `.env` efetivo, binários (`ffmpeg`, `ffprobe`, `yt-dlp`), módulos Python, diretórios graváveis, SQLite, espaço em disco, cookies, backend de sumarização e disponibilidade de `SUMMARY_MODEL` em `/v1/models` quando a validação estiver habilitada.

Se uma operação falhar durante o uso, consulte:

```text
/lasterror
```

O `/lasterror` mostra o último erro sanitizado registrado para o usuário autorizado. Ele cobre tanto jobs de transcrição com status `failed` quanto erros derivados, como falhas de `/summary`, exportações e vídeo com legenda selecionável. Para falhas antes da inicialização completa do bot, consulte os logs do terminal ou do serviço systemd.

O registro de erros derivados fica em:

```text
data/logs/operational_errors.jsonl
```

Esse arquivo não deve ser versionado e pode conter caminhos locais e trechos técnicos sanitizados.

---

## Segurança local antes de commitar

Depois da instalação, configure os hooks:

```bash
uv sync --dev
uv run pre-commit install
uv run pre-commit run --all-files
```

O scanner local bloqueia `.env`, cookies, bancos, logs e padrões comuns de tokens. Se `gitleaks` estiver instalado, ele também será executado automaticamente como camada complementar; se não estiver, o hook emitirá aviso e continuará.

Consulte `docs/08-seguranca-e-segredos.md` para a política completa.

---

## 10. Primeira execução (modo manual)

### 10.1 Iniciar
Em um terminal:
```bash
cd ~/yt-transcriber-bot
uv run python -m yt_transcriber_bot
```

Saída esperada nos primeiros segundos:
```
[INFO] Validando configuração...
[INFO] ✓ Configuração válida
[INFO] Validando ffmpeg...
[INFO] ✓ ffmpeg 6.0
[INFO] Detectando hardware...
[INFO] ✓ GPU detectada: NVIDIA Quadro T2000 (CC 7.5, 4GB VRAM) → usando cuda
[INFO] Inicializando banco de dados em data/jobs.db...
[INFO] ✓ Banco pronto (0 jobs em fila)
[INFO] Conectando ao Telegram...
[INFO] ✓ Bot @SeuBot conectado, polling iniciado
[INFO] Aguardando mensagens do user_id=123456789
```

Se aparecer algum `[ERROR]`, leia a mensagem — ela diz exatamente o que falta.

### 10.2 Primeira mensagem
No Telegram, mande `/start`. O bot deve responder.

### 10.3 Primeiro link
Cole um link curto do YouTube em PT ou EN (5–10 minutos é ideal para o primeiro teste). Acompanhe as mensagens de progresso.

> A primeira transcrição vai baixar 2–3 GB de modelos. Isso é normal e só acontece uma vez.

### 10.4 Encerrar
No terminal, `Ctrl+C`. O bot encerra graciosamente, jobs em fila persistem.

---

## 11. (Opcional) Configurar como serviço systemd

Para rodar o bot em background, com auto-start no boot e restart automático em crash. O runbook completo de operação, backup/restore, upgrade/rollback e recovery fica em [`11-operator-runbook.md`](./11-operator-runbook.md).

### 11.1 Criar arquivo de variáveis de ambiente para o serviço
systemd não carrega seu `~/.bashrc`. Crie um arquivo dedicado para segredos e valores que precisam existir no processo do serviço. Configurações não sensíveis também podem permanecer no `.env` da raiz do projeto, porque o serviço roda com `WorkingDirectory` apontando para o repositório.

```bash
sudo mkdir -p /etc/yt-transcriber-bot
sudo nano /etc/yt-transcriber-bot/env
```

Conteúdo (sem `export`, formato `KEY=value`, sem aspas):
```
TELEGRAM_BOT_TOKEN=123456789:SEU_TOKEN_AQUI
TELEGRAM_ALLOWED_USER_ID=123456789
HF_TOKEN=hf_SEU_TOKEN_AQUI
# YOUTUBE_COOKIES_BROWSER=firefox
# YOUTUBE_COOKIES_FILE=/home/SEU_USUARIO/.config/yt-transcriber-bot/cookies.txt
```

Proteja:
```bash
sudo chmod 600 /etc/yt-transcriber-bot/env
sudo chown root:root /etc/yt-transcriber-bot/env
```

### 11.2 Copiar o template de serviço
O projeto fornece um template em `deploy/yt-transcriber-bot.service`. Edite os caminhos e o usuário:

```ini
[Unit]
Description=YT Transcriber Bot (Telegram)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=SEU_USUARIO
Group=SEU_USUARIO
WorkingDirectory=/home/SEU_USUARIO/yt-transcriber-bot
EnvironmentFile=/etc/yt-transcriber-bot/env
ExecStart=/home/SEU_USUARIO/.local/bin/uv run python -m yt_transcriber_bot
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Substitua `SEU_USUARIO` pelo seu username (ex.: `ubuntu`, `fulano`). Confirme o caminho do `uv` com `which uv`.

### 11.3 Instalar e ativar
```bash
sudo cp deploy/yt-transcriber-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable yt-transcriber-bot
sudo systemctl start yt-transcriber-bot
```

### 11.4 Verificar
```bash
sudo systemctl status yt-transcriber-bot
journalctl -u yt-transcriber-bot -f
```

### 11.5 Parar / reiniciar
```bash
sudo systemctl stop yt-transcriber-bot
sudo systemctl restart yt-transcriber-bot
```

### 11.6 systemd em WSL2
WSL2 (versões recentes do Windows 11) suporta systemd nativamente. Habilite editando `/etc/wsl.conf`:
```ini
[boot]
systemd=true
```
E reinicie o WSL: `wsl --shutdown` no PowerShell, depois reabra o WSL.

---

## 12. Verificação final

Cheque que tudo está funcionando:

```bash
# Versão do Python
uv run python --version       # esperado: Python 3.11.x

# Versão do ffmpeg
ffmpeg -version | head -1     # esperado: ffmpeg version 6.x

# Ambiente Python sincronizado com o lockfile
cd ~/yt-transcriber-bot
uv sync --locked --check

# Configuração efetiva, com segredos mascarados
uv run python scripts/config/print_effective_settings.py

# Imports principais sem iniciar o polling do Telegram
uv run python - <<'PY'
import importlib.util
for module in ["telegram", "yt_dlp", "sqlalchemy", "torch", "whisperx", "pyannote.audio"]:
    try:
        present = importlib.util.find_spec(module) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        present = False
    print(module, "OK" if present else "FALTANDO")
PY
```

Se tudo passou, inicie o bot, mande `/start` no Telegram e rode `/healthcheck` antes do primeiro link de teste.

---

## 13. Atualização, backup e rollback

Antes de atualizar uma instalação usada em produção privada, faça backup de
`data/jobs.db`, `data/`, `models/` e arquivos de ambiente conforme o
[runbook do operador](./11-operator-runbook.md#4-backup). Depois atualize:

```bash
cd ~/yt-transcriber-bot
OLD_REV="$(git rev-parse HEAD)"
echo "$OLD_REV" > /tmp/yt-transcriber-old-rev
sudo systemctl stop yt-transcriber-bot   # se estiver usando systemd
git fetch --all --prune
git pull --ff-only
uv sync --locked
uv run python scripts/config/print_effective_settings.py
sudo systemctl start yt-transcriber-bot  # se estiver usando systemd
```

Depois rode no Telegram:

```text
/healthcheck
/status
```

Se a versão nova falhar, pare o serviço, volte para a revisão salva e
sincronize o ambiente:

```bash
cd ~/yt-transcriber-bot
sudo systemctl stop yt-transcriber-bot
git checkout "$(cat /tmp/yt-transcriber-old-rev)"
uv sync --locked
sudo systemctl start yt-transcriber-bot
```

Se houver suspeita de dados incompatíveis ou corrompidos, restaure o backup
completo seguindo [`11-operator-runbook.md`](./11-operator-runbook.md#5-restore).

---

## 14. Desinstalação

```bash
# Parar e remover o serviço
sudo systemctl stop yt-transcriber-bot
sudo systemctl disable yt-transcriber-bot
sudo rm /etc/systemd/system/yt-transcriber-bot.service
sudo systemctl daemon-reload

# Remover arquivos
sudo rm -rf /etc/yt-transcriber-bot
rm -rf ~/yt-transcriber-bot

# Remover variáveis do ~/.bashrc (edite manualmente)

# Remover cache do Hugging Face (opcional, libera GBs)
rm -rf ~/.cache/huggingface
```
