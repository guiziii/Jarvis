# ChatGPTListener

### Proposta: Assistente virtual com ChatGPT

## 1) Tecnologias utilizadas

- Python
- OpenAI (API Chat)
- WebBrowser
- Speech_recognition
- Pyttsx3
- Os
 - Python-dotenv


## 2) Demonstração

### 2.1) Exemplo de execução GPT

[![N|Solid](https://i.imgur.com/W3Ssygp.jpg)](https://i.imgur.com/W3Ssygp.jpg)

## 3) Funcionalidades

1) "Ronaldo reiniciar computador": Reinicia o computador do usuário (Windows, Linux, macOS).
2) "Ronaldo pode falar": Ativa a leitura por voz das respostas.
3) "Ronaldo não falar"/"Ronaldo nao falar": Desativa a leitura por voz.
4) "Volume médio"/"Volume medio": Ajusta volume para ~50% (Linux via amixer).
5) "Abra o controle": Abre o painel de controle/sistema (depende do SO).
6) "Abra o Google": Abre o Google no navegador padrão.
7) "Documentação do React"/"Documentacao do React": Abre a documentação do React.
8) "Abra o Youtube": Abre o YouTube.
9) "Documentação material"/"Documentacao material": Abre a documentação do Material UI.
10) "Valor do dólar"/"Valor do dolar": Pesquisa o valor do dólar.
11) "Abra a Azure": Abre o Azure DevOps.
12) "Desligar alarme": Finaliza o processo de alarmes (apenas Windows).
13) "Ronaldo": Entra em modo pergunta e resposta via ChatGPT.
14) "Ronaldo sair"/"Ronaldo encerrar": Encerra a aplicação.

Observação: sinônimos sem acento são aceitos para alguns comandos.

## 4) Instalação e configuração

1. Requisitos do sistema:
   - Python 3.9+
   - Microfone operacional
   - Linux: utilitário `amixer` (alsa-utils) para ajuste de volume opcional
   - Dependências de sistema do áudio (ex.: PortAudio) e TTS

2. Instale dependências de sistema (exemplos Ubuntu/Debian):

```bash
sudo apt update
sudo apt install -y portaudio19-dev python3-dev espeak ffmpeg alsa-utils
```

3. Configure o projeto:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edite .env e preencha OPENAI_API_KEY
```

## 5) Execução

```bash
python ChatGptListener.py
```

Fale "Ronaldo" para ativar o modo de perguntas, ou diga um dos comandos listados.

### 5.1) Melhorias de captação (microfone)

Você pode ajustar a qualidade e responsividade da captação via variáveis no `.env`:

- STT_ENGINE: `google` (padrão) ou `openai` (usa Whisper, melhor qualidade, pago)
- MIC_DEVICE_INDEX: índice do microfone (deixe vazio para padrão)
- MIC_SAMPLE_RATE: exemplo `16000` ou `44100`
- MIC_CHUNK_SIZE: tamanho do buffer, ex. `1024`
- LISTEN_TIMEOUT, PHRASE_TIME_LIMIT: controle de tempo na escuta principal
- AMBIENT_DURATION: duração da calibração de ruído ambiente (ex. `0.6` a `1.0`)
- QA_TIMEOUT, QA_PHRASE_TIME_LIMIT: tempos na fase de pergunta
- RECOGNITION_RETRIES: tentativas extras de reconhecimento
- DYNAMIC_ENERGY, ENERGY_THRESHOLD, PAUSE_THRESHOLD, NON_SPEAKING_DURATION: parâmetros do `speech_recognition`


## 6) Possíveis problemas de instalação 

1) `PyAudio` pode exigir `portaudio`/ferramentas de compilação. Veja: `https://stackoverflow.com/questions/73268630/error-could-not-build-wheels-for-pyaudio-which-is-required-to-install-pyprojec`

2) Em algumas distribuições, `pyttsx3` utiliza diferentes mecanismos de voz. Se não houver áudio, instale e configure `espeak` e `ffmpeg` ou escolha outra voz.

3) Em Windows, alguns comandos (como volume/controle) têm comportamento diferente; ajuste conforme seu ambiente.

---

Melhorias recentes:
- Migração para API de Chat da OpenAI (`gpt-4o-mini`) via `openai>=1.40.0`.
- Leitura da chave via variável de ambiente (`.env`).
- Mapeamento de comandos com handlers multiplataforma e sinônimos.
- Reconhecimento de fala mais robusto (ajuste de ruído, timeouts melhores).
- Comandos de saída e alternância de TTS aprimorados.
