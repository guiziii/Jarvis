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

# Inicializa TTS e OpenAI client
engine = pyttsx3.init()
client = OpenAI()

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
    recognizer = sr.Recognizer()
    with sr.AudioFile(filename) as source:
        audio = recognizer.record(source)
    try:
        return recognizer.recognize_google(audio, language='pt-BR')
    except Exception:
        print('Falha ao transcrever o áudio')
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

def main() -> None:
    tts_enabled = True
    activation_word = 'ronaldo'

    recognizer = sr.Recognizer()
    microphone = sr.Microphone()

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

    while True:
        try:
            with microphone as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = recognizer.listen(source, phrase_time_limit=5, timeout=10)

            try:
                transcription = recognizer.recognize_google(audio, language='pt-BR')
            except sr.UnknownValueError:
                continue

            if not transcription:
                continue

            normalized = transcription.strip().lower()
            print(normalized)

            # Executa comandos diretos
            if normalized in command_map:
                command_map[normalized]()
                continue

            # Suporta comandos no formato "ronaldo <comando>"
            if normalized.startswith(activation_word + ' '):
                possible_cmd = normalized
                if possible_cmd in command_map:
                    command_map[possible_cmd]()
                    continue

            # Ativa modo pergunta/resposta
            if normalized == activation_word:
                filename = 'input.wav'
                speak_text('Pergunte qualquer coisa.', tts_enabled)
                with microphone as source:
                    recognizer.adjust_for_ambient_noise(source, duration=0.3)
                    audio = recognizer.listen(source, phrase_time_limit=10, timeout=10)
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
