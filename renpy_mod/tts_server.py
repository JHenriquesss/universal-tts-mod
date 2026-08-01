# -*- coding: utf-8 -*-
import os
import sys
import io

# 1. SILENCIAMENTO TOTAL E ENCODING
# Redirecionamos TUDO para o log, deixando o stdout livre
here = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))
log_dir = os.environ.get("TTS_LOG_DIR") or here
log_path = os.path.join(log_dir, "tts_server.log")
status_path = os.path.join(log_dir, "tts_ready.txt")

if os.path.exists(status_path):
    try: os.remove(status_path)
    except: pass

def _log(msg):
    try:
        import time, json
        data = {"timestamp": time.time(), "msg": msg}
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(data) + "\n")
    except: pass

# Redirecionamos para o log, mas MANTEMOS o console visível para o usuário
def setup_logger():
    class Logger(object):
        def __init__(self, original_stream):
            self.original_stream = original_stream
            
        def write(self, message):
            if message.strip():
                # Escreve no arquivo de log (JSON)
                _log(f"{message.strip()}")
                # Escreve no console real (se disponível)
                if self.original_stream:
                    try:
                        self.original_stream.write(message)
                        self.original_stream.flush()
                    except: pass
                    
        def flush(self):
            if self.original_stream:
                try: self.original_stream.flush()
                except: pass

    # Salva os streams originais antes de redirecionar
    orig_stdout = sys.stdout
    orig_stderr = sys.stderr
    
    sys.stdout = Logger(sys.__stdout__ if sys.__stdout__ else orig_stdout)
    sys.stderr = Logger(sys.__stderr__ if sys.__stderr__ else orig_stderr)

# Forçar o stdin para UTF-8 de forma muito explícita
if sys.platform == "win32":
    try:
        # Tenta usar sys.stdin.buffer se disponível (via Popen PIPE)
        if hasattr(sys.stdin, 'buffer') and sys.stdin.buffer is not None:
            sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8', errors='replace')
        elif hasattr(sys, '__stdin__') and sys.__stdin__ is not None and hasattr(sys.__stdin__, 'buffer'):
            sys.stdin = io.TextIOWrapper(sys.__stdin__.buffer, encoding='utf-8', errors='replace')
    except Exception as e:
        _log(f"Aviso: Não foi possível reconfigurar stdin: {e}")

try:
    import warnings
    warnings.filterwarnings("ignore")
    import json
    import time
    import queue
    import threading
    import numpy as np
    import re

    if here not in sys.path:
        sys.path.insert(0, here)

    from text_cleaner import TextCleaner
    from tts_engines import KokoroEngine, MockEngine, get_available_voices
    
    # Agora que os imports pesados acabaram, podemos silenciar
    setup_logger()
except Exception as e:
    _log(f"ERRO NOS IMPORTS: {e}")

# Worker for Speech
_speech_queue = queue.Queue(maxsize=10)
DEFAULT_VOICE = "af_heart"

def _normalize_lang(lang):
    aliases = {
        "en": "a",
        "en-us": "a",
        "english": "a",
        "us": "a",
    }
    key = str(lang or "a").strip().lower()
    return aliases.get(key, key or "a")

def _make_engine(lang):
    engine_name = os.environ.get("TTS_ENGINE", "kokoro").lower()
    if engine_name == "mock":
        _log("Usando engine mock para testes.")
        return MockEngine()
    return KokoroEngine(lang=lang)

def _preview_text(text, limit=80):
    text = str(text).replace("\n", " ").replace("\r", " ")
    if len(text) <= limit:
        return text
    return text[:limit] + "..."

def _worker(engine, initial_speed, initial_voice):
    speed = initial_speed
    voice = initial_voice or DEFAULT_VOICE
    while True:
        try:
            task = _speech_queue.get(timeout=1)
            if task is None: break
            
            cmd, data = task
            if cmd == "SET_SPEED":
                speed = data
            elif cmd == "SET_VOICE":
                voice = data or voice
            elif cmd == "SPEAK":
                # LIMPEZA REDUNDANTE PARA APÓSTROFOS (Prevenção Total)
                # Mesmo que o TextCleaner falhe, limpamos aqui novamente
                data = str(data)
                for apo in ['’', '‘', '´', '`', '′', '’']:
                    data = data.replace(apo, "'")
                
                _log(f"Processando: {data}")
                _log(f"speak voice={voice} text_preview={_preview_text(data)}")
                engine.speak(data, voice=voice, speed=speed)
            elif cmd == "STOP":
                engine.stop()
            
            _speech_queue.task_done()
        except queue.Empty:
            continue
        except Exception as e:
            _log(f"Erro no worker thread: {e}")

def main():
    import socket
    requested_lang = sys.argv[1] if len(sys.argv) > 1 else "a"
    lang = _normalize_lang(requested_lang)
    voice = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] not in ("", "None") else DEFAULT_VOICE
    try:
        speed = float(sys.argv[3]) if len(sys.argv) > 3 else 1.25
    except Exception:
        speed = 1.25
    host = '127.0.0.1'
    try:
        port = int(os.environ.get("TTS_PORT", "5050"))
    except Exception:
        port = 5050
    engine_name = os.environ.get("TTS_ENGINE", "kokoro").lower()
    
    _log(f"Iniciando servidor robusto (v2) em {host}:{port}...")
    _log(f"startup_context engine={engine_name} lang={lang} requested_lang={requested_lang} voice={voice} port={port} speed={speed} log_dir={log_dir}")
    print(f"--- SERVIDOR TTS KOKORO ONLINE EM {host}:{port} ---")
    print("Aguardando conexao do jogo...")
    
    try:
        # Socket Server (Bind EARLY to prevent game from spawning duplicate server)
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((host, port))
        server_sock.listen(1)

        engine = _make_engine(lang)
        
        t = threading.Thread(target=_worker, args=(engine, speed, voice), daemon=True)
        t.start()

        # Handshake via arquivo (legado)
        voices_list = ",".join(get_available_voices())
        with open(status_path, "w", encoding="utf-8") as f:
            f.write(f"READY|{voices_list}")
        
        _log(f"Servidor pronto.")
        print("Servidor inicializado com sucesso. Pressione Ctrl+C para encerrar.")

        _response_queue = queue.Queue()
        def on_playback_done():
            _response_queue.put("PLAYBACK_DONE")
        engine.on_playback_done = on_playback_done

        def _response_worker(connection):
            while True:
                msg = _response_queue.get()
                if msg is None: break
                try:
                    connection.sendall((msg + "\n").encode('utf-8'))
                except:
                    break

        while True:
            conn, addr = server_sock.accept()
            _log(f"Conectado por {addr}")
            print(f"[*] Jogo conectado: {addr}")
            
            with conn:
                f = conn.makefile('r', encoding='utf-8')
                
                # Start response worker for this connection
                resp_thread = threading.Thread(target=_response_worker, args=(conn,), daemon=True)
                resp_thread.start()

                try:
                    while True:
                        line = f.readline()
                        if not line: break
                        line = line.strip()
                        if not line: continue


                        if line == "STOP":
                            _log("command=STOP")
                            while not _speech_queue.empty():
                                try: _speech_queue.get_nowait()
                                except: break
                            _speech_queue.put(("STOP", None))
                            continue
                        if line == "QUIT":
                            _log("command=QUIT")
                            _response_queue.put(None) # stop response worker
                            return
                        if line.startswith("SET_SPEED:"):
                            try: speed = float(line[10:].strip())
                            except: pass
                            _log(f"command=SET_SPEED speed={speed}")
                            _speech_queue.put(("SET_SPEED", speed))
                            continue
                        if line.startswith("SET_VOICE:"):
                            requested_voice = line[10:].strip()
                            if requested_voice:
                                voice = requested_voice
                                _log(f"command=SET_VOICE voice={voice}")
                                _speech_queue.put(("SET_VOICE", voice))
                            else:
                                _log("command=SET_VOICE ignored=empty")
                            continue

                        cleaned_text = TextCleaner.clean(line)
                        if cleaned_text:
                            print(f"\n[TEXTO RECEBIDO] {cleaned_text}")
                            _log(f"text_preview={_preview_text(cleaned_text)}")
                            _speech_queue.put(("SPEAK", cleaned_text))
                        else:
                            _log("text_ignored=empty_after_cleaning")
                            print("[!] Texto vazio após limpeza (ignorado)")
                            # Immediately send PLAYBACK_DONE if we ignore
                            _response_queue.put("PLAYBACK_DONE")
                except Exception as ex:
                    _log(f"Connection error: {ex}")
            
            _response_queue.put(None) # stop response worker
            _log("Conexão encerrada pelo cliente.")
            print("[!] Jogo desconectado. Aguardando nova conexao...")

    except Exception as e:
        _log(f"ERRO CRÍTICO: {e}")
        print(f"!!! ERRO CRITICO: {e}")
        with open(status_path, "w", encoding="utf-8") as f:
            f.write("ERROR|" + str(e))

if __name__ == "__main__":
    main()
