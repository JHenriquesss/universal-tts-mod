################################################################################
# TTS MOD - VERSÃO FINAL (CARREGAMENTO TARDIO)
################################################################################

# Usamos init 1000 para garantir que o GUI do jogo já terminou de carregar
init 1000 python: 
    import subprocess
    import os
    import threading
    import time
    import re

    # --- CONFIGURAÇÕES ---
    TTS_ENGINE = "kokoro"   
    TTS_LANG = "a"        
    TTS_VOICE = "af_heart"
    TTS_PORT = 5050
    # -------------------

    class TTSState(object):
        def __init__(self):
            self.proc = None
            self.sock = None
            self.voices = []
            self.last_spoken = None
            self.auto_forward = False
            self.auto_advance_flag = False
            self.listening = False
            
            # Garante que speed nunca seja None, mesmo se o persistent salvou como None
            saved_speed = getattr(persistent, "tts_speed", 1.25)
            self.speed = float(saved_speed) if saved_speed is not None else 1.25

        def __getstate__(self):
            d = dict(self.__dict__)
            d["proc"] = None
            d["sock"] = None
            d["listening"] = False
            return d

        def __setstate__(self, d):
            self.__dict__.update(d)

    tts_state = TTSState()

    def _tts_socket_listener(sock):
        try:
            f = sock.makefile('r')
            while tts_state.listening:
                line = f.readline()
                if not line:
                    tts_notify("TTS: Conexão encerrada pelo servidor.")
                    break
                line = line.strip()
                if line == "PLAYBACK_DONE":
                    if getattr(tts_state, "auto_forward", False):
                        tts_state.auto_advance_flag = True
        except Exception as e:
            tts_notify("TTS Listener Erro: " + str(e))
        tts_state.listening = False
        tts_state.sock = None

    def tts_notify(message):
        try:
            getattr(renpy, "notify")(message)
        except Exception:
            pass

    def tts_status_message():
        socket_status = "connected" if tts_state.sock else "disconnected"
        process_status = "running" if tts_state.proc and tts_state.proc.poll() is None else "stopped"
        auto_status = "ON" if tts_state.auto_forward else "OFF"
        return "socket={} process={} speed={:.2f} auto={}".format(socket_status, process_status, tts_state.speed, auto_status)

    def tts_kill():
        tts_state.listening = False
        if tts_state.sock:
            try:
                tts_state.sock.sendall(b"QUIT\n")
            except: pass
            try:
                tts_state.sock.close()
            except: pass
            tts_state.sock = None
            
        if tts_state.proc:
            try:
                tts_state.proc.terminate()
                try:
                    import time
                    time.sleep(0.5)
                    tts_state.proc.kill()
                except: pass
            except: pass
            tts_state.proc = None
        
        status_path = os.path.join(renpy.config.gamedir, "tts_ready.txt")
        if os.path.exists(status_path):
            try: os.remove(status_path)
            except: pass

    def tts_connect(quiet=False):
        import socket
        
        # 1. Se já temos um socket funcional, não faz nada
        if tts_state.sock:
            try:
                # Teste rápido de conexão
                tts_state.sock.sendall(b"\n") 
                if not quiet: tts_notify("TTS já está conectado.")
                return True
            except:
                tts_state.listening = False
                tts_state.sock = None

        if not quiet: tts_notify("Conectando ao servidor TTS...")
        
        # 2. Tentar conectar ao Socket (caso o usuário já tenha aberto o backend manualmente)
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2.0)
            s.connect(("127.0.0.1", TTS_PORT))
            s.settimeout(None) # Remove timeout para o listener não cair
            tts_state.sock = s
            tts_state.listening = True
            t = threading.Thread(target=_tts_socket_listener, args=(s,))
            t.daemon = True
            t.start()
            if not quiet: tts_notify("Conectado ao Backend Externo!")
            return True
        except:
            pass # Falhou conexão externa, tenta abrir o processo local

        # 3. Abrir o processo se não estiver rodando
        tts_kill()
        
        env = os.environ.copy()
        env["TTS_ENGINE"] = TTS_ENGINE
        env["TTS_LOG_DIR"] = renpy.config.gamedir
        env["TTS_PORT"] = str(TTS_PORT)
        
        try:
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0 

            py_path = "pythonw.exe" if os.name == 'nt' else "python3"
            if os.name == 'nt':
                import shutil
                if not shutil.which(py_path):
                    if shutil.which("python.exe"):
                        py_path = "python.exe"
                    else:
                        local_app_data = os.environ.get("LOCALAPPDATA", "")
                        py312 = os.path.join(local_app_data, "Programs", "Python", "Python312", "pythonw.exe")
                        if os.path.exists(py312):
                            py_path = py312
                        else:
                            py312_console = os.path.join(local_app_data, "Programs", "Python", "Python312", "python.exe")
                            if os.path.exists(py312_console):
                                py_path = py312_console

            server_script = os.path.join(renpy.config.gamedir, "tts_server.py")
            
            tts_state.proc = subprocess.Popen(
                [py_path, "-u", server_script, TTS_LANG, TTS_VOICE, str(tts_state.speed)],
                env=env,
                startupinfo=startupinfo,
                creationflags=0x08000000 if os.name == 'nt' else 0
            )

            
            # Aguardar o servidor subir e tentar conectar via socket (retry loop)
            def _retry_connect():
                time.sleep(2) # Espera inicial
                for i in range(10):
                    try:
                        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        s.settimeout(2.0)
                        s.connect(("127.0.0.1", TTS_PORT))
                        s.settimeout(None) # Remove timeout para o listener não cair
                        tts_state.sock = s
                        tts_state.listening = True
                        t = threading.Thread(target=_tts_socket_listener, args=(s,))
                        t.daemon = True
                        t.start()
                        if not quiet: tts_notify("TTS Online (Auto-start)")
                        return
                    except:
                        time.sleep(2)
                if not quiet: tts_notify("Erro: Não foi possível conectar ao servidor TTS.")

            t = threading.Thread(target=_retry_connect)
            t.daemon = True
            t.start()
            return True
        except Exception as e:
            tts_notify("Erro ao iniciar processo TTS: " + str(e))
        return False

    def tts_speak(text):
        if not text or not tts_state.sock:
            return
        try:
            import sys
            if sys.version_info[0] == 2:
                # Python 2 (Ren'Py 7)
                if isinstance(text, unicode):
                    text_val = text.encode('utf-8')
                else:
                    text_val = str(text)
                interpolated_text = renpy.substitute(text_val)
                payload = interpolated_text
            else:
                # Python 3 (Ren'Py 8)
                text_val = str(text)
                interpolated_text = renpy.substitute(text_val)
                if isinstance(interpolated_text, str):
                    payload = interpolated_text.encode('utf-8')
                else:
                    payload = interpolated_text

            tts_state.sock.sendall(b"STOP\n")
            tts_state.sock.sendall(payload + b"\n")
        except Exception as e:
            tts_notify("TTS falhou: " + str(e))
            tts_state.sock = None

    def tts_speak_once(text):
        if not text:
            return
        if text != getattr(tts_state, "last_spoken", None):
            tts_state.last_spoken = text
            tts_speak(text)

    def _tts_extract_callback_text(kwargs):
        for key in ("what", "text", "message"):
            value = kwargs.get(key)
            if value:
                return value
        return getattr(renpy.store, "_last_say_what", None)

    def _tts_wrap_phone_callback(original):
        def wrapped(event, interact=True, **kwargs):
            try:
                original(event, interact=interact, **kwargs)
            except TypeError:
                original(event, **kwargs)

            if event in ("begin", "show_done"):
                tts_speak_once(_tts_extract_callback_text(kwargs))

        wrapped._tts_wrapped = True
        return wrapped

    def _tts_patch_phone_callback_function(original):
        if getattr(original, "_tts_wrapped", False):
            return original
        try:
            import types
            original_copy = types.FunctionType(
                original.__code__,
                original.__globals__,
                original.__name__,
                original.__defaults__,
                original.__closure__,
            )
            original_copy.__kwdefaults__ = getattr(original, "__kwdefaults__", None)

            def patched(event, interact=True, _tts_original=original_copy, **kwargs):
                try:
                    _tts_original(event, interact=interact, **kwargs)
                except TypeError:
                    _tts_original(event, **kwargs)

                if event in ("begin", "show_done"):
                    tts_speak_once(_tts_extract_callback_text(kwargs))

            original.__code__ = patched.__code__
            original.__defaults__ = patched.__defaults__
            original.__kwdefaults__ = patched.__kwdefaults__
            original._tts_wrapped = True
            return original
        except Exception:
            return _tts_wrap_phone_callback(original)

    def _tts_install_phone_callback_wrappers():
        # Some games render phone/NVL texts through custom Character callbacks,
        # which can bypass the global all_character_callbacks hook.
        for name in ("Phone_SendSound", "Phone_ReceiveSound"):
            original = getattr(renpy.store, name, None)
            if original and not getattr(original, "_tts_wrapped", False):
                setattr(renpy.store, name, _tts_patch_phone_callback_function(original))

    def _send_speed():
        tts_notify("Velocidade TTS: {:.2f}x".format(tts_state.speed))
        if tts_state.sock:
            try:
                msg = "SET_SPEED:{}\n".format(tts_state.speed)
                tts_state.sock.sendall(msg.encode('utf-8'))
            except: pass


    def tts_increase_speed():
        tts_state.speed = round(min(3.0, tts_state.speed + 0.1), 2)
        persistent.tts_speed = tts_state.speed
        _send_speed()

    def tts_decrease_speed():
        tts_state.speed = round(max(0.5, tts_state.speed - 0.1), 2)
        persistent.tts_speed = tts_state.speed
        _send_speed()

    def tts_toggle_auto():
        tts_state.auto_forward = not tts_state.auto_forward
        status = "LIGADO" if tts_state.auto_forward else "DESLIGADO"
        tts_notify("TTS Modo Automatico: {}".format(status))

    def _tts_callback(event, **kwargs):
        if event == "begin":
            # what é o texto que está sendo exibido agora
            what = _tts_extract_callback_text(kwargs)
            
            if what:
                # Evitar falar o mesmo texto repetidamente se for um redraw de tela
                tts_speak_once(what)

    # Injeção segura
    config.all_character_callbacks.append(_tts_callback)
    
    km_dict = {
        'v': tts_connect,
        'a': tts_toggle_auto,
        'K_EQUALS': tts_increase_speed,
        'K_MINUS': tts_decrease_speed,
        'K_KP_PLUS': tts_increase_speed,
        'K_KP_MINUS': tts_decrease_speed
    }
    config.underlay.append(renpy.Keymap(**km_dict))

    def tts_start_callback():
        _tts_install_phone_callback_wrappers()
        tts_connect(True)

    _tts_install_phone_callback_wrappers()
    config.start_callbacks.append(tts_start_callback)
    config.after_load_callbacks.append(tts_start_callback)
    config.overlay_screens.append("tts_auto_forward_checker")
    
    # Auto-start on boot
    tts_start_callback()

init python:
    class TTSAutoAdvanceAction(Action):
        def __call__(self):
            if getattr(tts_state, "auto_advance_flag", False) and not renpy.get_screen("choice"):
                tts_state.auto_advance_flag = False
                renpy.end_interaction(True)

screen tts_auto_forward_checker():
    zorder 100
    timer 0.1 repeat True action TTSAutoAdvanceAction()

    if tts_state.sock:
        vbox:
            xalign 0.99
            yalign 0.01
            if tts_state.auto_forward:
                textbutton "Parar TTS Automático" action Function(tts_toggle_auto) text_size 14 text_color "#ff5555" text_outlines [(1, "#000", 0, 0)]
            else:
                textbutton "Iniciar TTS Automático" action Function(tts_toggle_auto) text_size 14 text_color "#55ff55" text_outlines [(1, "#000", 0, 0)]
