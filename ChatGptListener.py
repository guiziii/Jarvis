import os
import platform
import webbrowser
from typing import Callable, Dict

import speech_recognition as sr
import pyttsx3
from dotenv import load_dotenv
from openai import OpenAI

# Carrega variáveis do .env, caso exista
load_dotenv()


def get_env_bool(var_name: str, default: bool) -> bool:
    val = os.getenv(var_name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


def get_env_int(var_name: str, default: int | None) -> int | None:
    val = os.getenv(var_name)
    if val is None or val.strip() == "":
        return default
    try:
        return int(val)
    except ValueError:
        return default

# Inicializa TTS e OpenAI client
engine = pyttsx3.init()
client = OpenAI()

# Configuração de captação via variáveis de ambiente
STT_ENGINE = os.getenv('STT_ENGINE', 'google').strip().lower()  # 'google' | 'openai'
MIC_DEVICE_INDEX = get_env_int('MIC_DEVICE_INDEX', None)
MIC_SAMPLE_RATE = get_env_int('MIC_SAMPLE_RATE', None)
MIC_CHUNK_SIZE = get_env_int('MIC_CHUNK_SIZE', 1024)

LISTEN_TIMEOUT = get_env_int('LISTEN_TIMEOUT', 10) or 10
PHRASE_TIME_LIMIT = get_env_int('PHRASE_TIME_LIMIT', 6) or 6
AMBIENT_DURATION = float(os.getenv('AMBIENT_DURATION', '0.6'))
QA_TIMEOUT = get_env_int('QA_TIMEOUT', 15) or 15
QA_PHRASE_TIME_LIMIT = get_env_int('QA_PHRASE_TIME_LIMIT', 12) or 12
RECOGNITION_RETRIES = get_env_int('RECOGNITION_RETRIES', 1) or 1

# Parâmetros do recognizer
DYNAMIC_ENERGY = get_env_bool('DYNAMIC_ENERGY', True)
ENERGY_THRESHOLD = get_env_int('ENERGY_THRESHOLD', None)
PAUSE_THRESHOLD = float(os.getenv('PAUSE_THRESHOLD', '0.8'))
NON_SPEAKING_DURATION = float(os.getenv('NON_SPEAKING_DURATION', '0.5'))

# URLs úteis
url = 'https://www.google.com'
urlY = 'https://www.youtube.com'
urlDevAzure = 'https://dev.azure.com/'
urlDocReact = 'https://react.dev/'
urldolar = 'https://www.google.com/search?q=valor%20do%20d%C3%B3lar'
urlMui = 'https://mui.com/material-ui/getting-started/overview/'

def set_volume_medium_linux() -> None:
    os.system('amixer -D pulse sset Master 50%')

def transcribe_audio_to_text(filename: str) -> str:
    """Transcreve áudio usando o mecanismo definido em STT_ENGINE.

    - google: usa SpeechRecognition + Google Web Speech API (gratuito, sujeito a limites)
    - openai: usa Whisper API (requer OPENAI_API_KEY)
    """
    if STT_ENGINE == 'openai':
        try:
            with open(filename, 'rb') as audio_file:
                result = client.audio.transcriptions.create(
                    model='whisper-1',
                    file=audio_file,
                    language='pt',
                )
            text = getattr(result, 'text', None)
            return (text or '').strip()
        except Exception as e:
            print(f'Falha ao transcrever com OpenAI Whisper: {e}')
            return ''
    else:
        try:
            recognizer = sr.Recognizer()
            with sr.AudioFile(filename) as source:
                audio = recognizer.record(source)
            return recognizer.recognize_google(audio, language='pt-BR')
        except Exception as e:
            print(f'Falha ao transcrever com Google: {e}')
            return ''

def generate_response(prompt: str) -> str:
    """Gera resposta usando a API de chat da OpenAI.

    Requer variável de ambiente OPENAI_API_KEY.
    """
    try:
        chat = client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[
                {"role": "system", "content": "Você é um assistente útil e conciso."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=400,
        )
        return (chat.choices[0].message.content or '').strip()
    except Exception as e:
        print(f'Erro ao gerar resposta: {e}')
        return 'Desculpe, ocorreu um erro ao gerar a resposta.'


def speak_text(text: str, tts_enabled: bool) -> None:
    if tts_enabled:
        engine.setProperty('rate', 220)
        engine.say(text)
        engine.runAndWait()


def restart_computer() -> None:
    """Tenta reiniciar o computador de forma multiplataforma (pode exigir privilégios)."""
    system_name = platform.system().lower()
    try:
        if 'windows' in system_name:
            os.system('shutdown /r /t 0')
        elif 'linux' in system_name:
            # Pode requerer sudo; o usuário verá a mensagem do sistema
            os.system('shutdown -r now')
        elif 'darwin' in system_name:
            os.system('sudo shutdown -r now')
        else:
            print('SO não suportado para reinicialização automática.')
    except Exception as e:
        print(f'Falha ao reiniciar: {e}')


def open_url(url_to_open: str) -> None:
    try:
        webbrowser.open(url_to_open)
    except Exception as e:
        print(f'Não foi possível abrir o navegador: {e}')


def open_control_panel() -> None:
    system_name = platform.system().lower()
    try:
        if 'windows' in system_name:
            os.system('control')
        elif 'linux' in system_name:
            # Tenta centros de controle comuns
            if os.system('which gnome-control-center >/dev/null 2>&1') == 0:
                os.system('gnome-control-center')
            elif os.system('which systemsettings5 >/dev/null 2>&1') == 0:
                os.system('systemsettings5')
            else:
                print('Nenhum painel de controle padrão encontrado no Linux.')
        elif 'darwin' in system_name:
            os.system('open "/System/Library/PreferencePanes"')
        else:
            print('SO não suportado para painel de controle.')
    except Exception as e:
        print(f'Falha ao abrir o painel de controle: {e}')


def kill_alarms_windows() -> None:
    system_name = platform.system().lower()
    if 'windows' in system_name:
        os.system('Taskkill /F /IM AlarmsNotificationTask.exe')
    else:
        print('O comando "Desligar alarme" está disponível apenas no Windows.')

def _contains_activation(text: str, activation_word: str) -> bool:
    text = text.lower()
    activation_word = activation_word.lower()
    return activation_word in text


def _extract_after_activation(text: str, activation_word: str) -> str:
    text = text.lower().strip()
    activation_word = activation_word.lower().strip()
    if activation_word not in text:
        return ''
    # Pega substring após a primeira ocorrência de 'activation_word'
    idx = text.find(activation_word)
    after = text[idx + len(activation_word):].strip()
    return after


def main() -> None:
    tts_enabled = True
    activation_word = 'ronaldo'

    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = DYNAMIC_ENERGY
    if ENERGY_THRESHOLD is not None:
        recognizer.energy_threshold = ENERGY_THRESHOLD
    recognizer.pause_threshold = PAUSE_THRESHOLD
    recognizer.non_speaking_duration = NON_SPEAKING_DURATION

    microphone = sr.Microphone(
        device_index=MIC_DEVICE_INDEX,
        sample_rate=MIC_SAMPLE_RATE,
        chunk_size=MIC_CHUNK_SIZE,
    )

    def set_tts_on() -> None:
        nonlocal tts_enabled
        tts_enabled = True
        speak_text('Vou falar as respostas.', tts_enabled)

    def set_tts_off() -> None:
        nonlocal tts_enabled
        tts_enabled = False
        print('Voz desativada.')

    def set_medium_volume() -> None:
        print(' -> Ajustando volume para médio (50%)')
        if platform.system().lower() == 'linux':
            set_volume_medium_linux()
        else:
            print('Ajuste de volume automático não suportado neste sistema.')

    def open_sublime() -> None:
        # Tenta diferentes nomes do binário
        for cmd in ['subl', 'sublime_text', 'sublime']:
            if os.system(f'which {cmd} >/dev/null 2>&1') == 0:
                os.system(cmd)
                return
        print('Sublime Text não encontrado no PATH.')

    def open_with_feedback(url_to_open: str, message: str) -> None:
        speak_text(message, tts_enabled)
        print(' -> Abrindo navegador')
        open_url(url_to_open)

    def exit_program() -> None:
        speak_text('Encerrando. Até logo!', tts_enabled)
        raise KeyboardInterrupt()

    # Mapa de comandos por frase completa (em minúsculas)
    command_map: Dict[str, Callable[[], None]] = {
        'ronaldo reiniciar computador': restart_computer,
        'ronaldo pode falar': set_tts_on,
        'ronaldo não falar': set_tts_off,
        'ronaldo nao falar': set_tts_off,
        'volume médio': set_medium_volume,
        'volume medio': set_medium_volume,
        'abra o controle': open_control_panel,
        'abra o sublime': open_sublime,
        'abra o google': lambda: open_with_feedback(url, 'Abrindo o Google'),
        'documentação do react': lambda: open_with_feedback(urlDocReact, 'Abrindo documentação do React'),
        'documentacao do react': lambda: open_with_feedback(urlDocReact, 'Abrindo documentação do React'),
        'abra o youtube': lambda: open_with_feedback(urlY, 'Abrindo YouTube'),
        'documentação material': lambda: open_with_feedback(urlMui, 'Abrindo documentação do Material-UI'),
        'documentacao material': lambda: open_with_feedback(urlMui, 'Abrindo documentação do Material-UI'),
        'valor do dólar': lambda: open_with_feedback(urldolar, 'Abrindo pesquisa do dólar'),
        'valor do dolar': lambda: open_with_feedback(urldolar, 'Abrindo pesquisa do dólar'),
        'abra a azure': lambda: open_with_feedback(urlDevAzure, 'Abrindo Azure DevOps'),
        'desligar alarme': kill_alarms_windows,
        'ronaldo sair': exit_program,
        'ronaldo encerrar': exit_program,
    }

    print("\nDiga 'Ronaldo' para conversar com o ChatGPT ou diga um comando.")
    # Calibração inicial mais longa
    try:
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source, duration=max(1.0, AMBIENT_DURATION))
    except Exception as e:
        print(f'Falha na calibração inicial do microfone: {e}')

    while True:
        try:
            with microphone as source:
                # Recalibração breve a cada iteração para adaptar a ruído ambiente
                recognizer.adjust_for_ambient_noise(source, duration=AMBIENT_DURATION)
                audio = recognizer.listen(
                    source,
                    phrase_time_limit=PHRASE_TIME_LIMIT,
                    timeout=LISTEN_TIMEOUT,
                )

            # Tentativas de reconhecimento
            transcription = ''
            for _ in range(max(1, RECOGNITION_RETRIES + 1)):
                try:
                    if STT_ENGINE == 'google':
                        transcription = recognizer.recognize_google(audio, language='pt-BR')
                    else:
                        # grava temporariamente e usa Whisper
                        tmpfile = 'tmp_listen.wav'
                        with open(tmpfile, 'wb') as f:
                            f.write(audio.get_wav_data())
                        transcription = transcribe_audio_to_text(tmpfile)
                    break
                except sr.UnknownValueError:
                    transcription = ''
                    continue
                except Exception:
                    transcription = ''
                    continue

            if not transcription:
                continue

            normalized = transcription.strip().lower()
            print(normalized)

            # Executa comandos diretos
            if normalized in command_map:
                command_map[normalized]()
                continue

            # Suporta comandos com palavra de ativação na frase
            if _contains_activation(normalized, activation_word):
                after = _extract_after_activation(normalized, activation_word)
                if after:
                    # Tenta com e sem o prefixo 'ronaldo '
                    prefixed = f'{activation_word} {after}'
                    if prefixed in command_map:
                        command_map[prefixed]()
                        continue
                    if after in command_map:
                        command_map[after]()
                        continue

            # Ativa modo pergunta/resposta
            if normalized == activation_word or (_contains_activation(normalized, activation_word) and not _extract_after_activation(normalized, activation_word)):
                filename = 'input.wav'
                speak_text('Pergunte qualquer coisa.', tts_enabled)
                with microphone as source:
                    recognizer.adjust_for_ambient_noise(source, duration=max(0.3, AMBIENT_DURATION))
                    audio = recognizer.listen(
                        source,
                        phrase_time_limit=QA_PHRASE_TIME_LIMIT,
                        timeout=QA_TIMEOUT,
                    )
                    with open(filename, 'wb') as f:
                        f.write(audio.get_wav_data())

                text = transcribe_audio_to_text(filename)
                if text:
                    print(f'Você disse: {text}')
                    if text.strip().lower() in {'esquece', 'cancelar', 'cancelar comando'}:
                        print('Comando cancelado')
                        speak_text('Comando cancelado.', tts_enabled)
                        continue

                    response = generate_response(text)
                    print(f'ChatGPT: {response}')
                    speak_text(response, tts_enabled)

        except sr.WaitTimeoutError:
            # Sem fala detectada dentro do timeout; continua ouvindo
            continue
        except KeyboardInterrupt:
            print('Encerrado pelo usuário.')
            break
        except Exception as e:
            print(f'Ocorreu um erro: {e}')


if __name__ == "__main__":
    # Verifica se a chave foi configurada
    if not os.getenv('OPENAI_API_KEY'):
        print('ATENÇÃO: Defina a variável de ambiente OPENAI_API_KEY (veja .env.example).')
    main()
