################################################################################
# TTS MOD - VERSÃO FINAL (CARREGAMENTO TARDIO)
################################################################################

# Usamos init 999 para garantir que o GUI do jogo já terminou de carregar
init 999 python:
    import atexit
    import os
    import subprocess
    import sys
    import threading
    import time

    # Os modulos do cliente ficam ao lado do tts_mod.rpy na pasta game/. O
    # Ren'Py nem sempre coloca essa pasta no sys.path, entao ela e adicionada
    # aqui antes dos imports.
    _tts_client_dir = getattr(renpy.config, "gamedir", None)
    if _tts_client_dir and _tts_client_dir not in sys.path:
        sys.path.insert(0, _tts_client_dir)

    from tts_client_state import TTSState, find_backend_python
    from tts_client_voice import BF_NAME_KEYS, PLAYER_NAME_KEYS, clean_speaker_name, collect_context_names, resolve_voice
    from tts_client_hooks import extract_callback_text, install_display_hook, install_phone_callback_wrappers, install_save_compat_hook
    from tts_client_auto import AutoAdvanceController
    from tts_client_speech import speak
    from tts_client_commands import decrease_speed, increase_speed, send_speed, toggle_audio, toggle_auto

    TTS_ENGINE = "kokoro"
    TTS_LANG = "a"
    TTS_VOICE = "af_heart"
    TTS_PORT = 5050

    tts_state = TTSState(persistent=persistent, default_voice=TTS_VOICE, config=renpy.config)
    _tts_connect_lock = threading.Lock()

    def _tts_backend_instance_token():
        """Le o token de instancia publicado pelo backend no arquivo de prontidao."""
        try:
            status_path = os.path.join(renpy.config.gamedir, "tts_ready.txt")
            if not os.path.exists(status_path):
                return None
            with open(status_path, "r", encoding="utf-8") as f:
                status = f.read().strip()
            if not status.startswith("READY|"):
                return None
            parts = status.split("|")
            return (parts[1].strip() or None) if len(parts) >= 2 else None
        except Exception:
            return None

    def _tts_send_hello(sock, expected_token=None):
        """Pede ao backend o token da instancia corrente (comando HELLO)."""
        try:
            payload = "HELLO:" + expected_token if expected_token else "HELLO"
            sock.sendall((payload + "\n").encode("utf-8"))
        except Exception:
            pass
        return expected_token

    def _tts_flush_pending_speech():
        pending = getattr(tts_state, "pending_speech", None)
        if pending and tts_state.sock and getattr(tts_state, "tts_audio_enabled", True):
            tts_state.pending_speech = None
            speak(tts_state, pending[0], pending[1], TTS_VOICE, renpy.substitute, tts_notify)

    def _tts_socket_listener(sock):
        try:
            f = sock.makefile('r')
            expected_token = getattr(tts_state, "expected_backend_token", None)
            while tts_state.listening:
                line = f.readline()
                if not line:
                    if tts_state.listening and getattr(tts_state, "tts_audio_enabled", True):
                        tts_notify("TTS: Conexão encerrada pelo servidor.")
                    break
                line = line.strip()
                if line.startswith("HELLO:"):
                    remote_token = line[6:].strip()
                    tts_state.backend_token = remote_token
                    if expected_token and remote_token and remote_token != expected_token:
                        tts_notify("TTS: outra instancia do backend esta na porta. Pressione v para reconectar.")
                        tts_state.stale_backend = True
                        tts_state.sock = None
                        tts_state.listening = False
                        try:
                            sock.close()
                        except Exception:
                            pass
                        return
                    continue
                if line == "PLAYBACK_DONE":
                    tts_state.is_playing = False
                    tts_state.playback_done_time = time.time()
                    auto_active = getattr(tts_state, "auto_forward", False) or getattr(renpy.store._preferences, "afm_enable", False)
                    if auto_active:
                        tts_state.auto_advance_flag = True
        except Exception as e:
            tts_notify("TTS Listener Erro: " + str(e))
        tts_state.listening = False
        tts_state.sock = None
        tts_state.is_playing = False

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
        tts_state.connecting = False
        tts_state.owns_backend = False
        if tts_state.sock:
            try:
                tts_state.sock.sendall(b"QUIT\n")
            except Exception:
                pass
            try:
                tts_state.sock.close()
            except Exception:
                pass
            tts_state.sock = None

        if tts_state.proc:
            try:
                tts_state.proc.terminate()
                try:
                    tts_state.proc.wait(timeout=0.5)
                except Exception:
                    tts_state.proc.kill()
            except Exception:
                pass
            tts_state.proc = None

        status_path = os.path.join(renpy.config.gamedir, "tts_ready.txt")
        if os.path.exists(status_path):
            try:
                os.remove(status_path)
            except Exception:
                pass

    def tts_shutdown():
        """Encerra o backend proprio ao fechar o jogo; se externo, so desconecta."""
        if getattr(tts_state, "owns_backend", False) or tts_state.proc is not None:
            tts_kill()
            return
        tts_state.listening = False
        tts_state.connecting = False
        if tts_state.sock:
            try:
                tts_state.sock.close()
            except Exception:
                pass
            tts_state.sock = None

    def tts_connect(quiet=False):
        import socket

        with _tts_connect_lock:
            if tts_state.sock:
                try:
                    tts_state.sock.sendall(b"\n")
                    if not quiet:
                        tts_notify("TTS já está conectado.")
                    return True
                except Exception:
                    tts_state.listening = False
                    tts_state.sock = None

            if getattr(tts_state, "connecting", False) or (tts_state.proc and tts_state.proc.poll() is None):
                if not quiet:
                    tts_notify("TTS inicializando...")
                return True
            tts_state.connecting = True

        if not quiet:
            tts_notify("Conectando ao servidor TTS...")

        # 2. Tentar conectar ao Socket (caso o usuário já tenha aberto o backend manualmente)
        for attempt in range(3):
            s = None
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(2.0)
                s.connect(("127.0.0.1", TTS_PORT))
                s.settimeout(None)
                tts_state.sock = s
                tts_state.listening = True
                tts_state.stale_backend = False
                tts_state.owns_backend = False
                tts_state.connecting = False
                tts_state.expected_backend_token = None
                _tts_send_hello(s)
                t = threading.Thread(target=_tts_socket_listener, args=(s,))
                t.daemon = True
                t.start()
                _tts_flush_pending_speech()
                if not quiet:
                    tts_notify("Conectado ao Backend Externo!")
                return True
            except Exception:
                if s is not None:
                    try:
                        s.close()
                    except Exception:
                        pass
                time.sleep(0.4)

        # 3. Abrir o processo se não estiver rodando
        tts_kill()
        tts_state.connecting = True

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

            import shutil
            py_path = find_backend_python(os.environ, os.path.exists, shutil.which, os.name)

            server_script = os.path.join(renpy.config.gamedir, "tts_server.py")

            tts_state.proc = subprocess.Popen(
                [py_path, "-u", server_script, TTS_LANG, TTS_VOICE, str(tts_state.speed), "--parent-pid", str(os.getpid())],
                env=env,
                startupinfo=startupinfo,
                creationflags=0x08000000 if os.name == 'nt' else 0
            )
            tts_state.owns_backend = True

            def _retry_connect():
                try:
                    time.sleep(2)
                    for i in range(60):
                        if tts_state.proc and tts_state.proc.poll() is not None:
                            break
                        token = _tts_backend_instance_token()
                        if tts_state.proc and not token:
                            time.sleep(1.5)
                            continue
                        s = None
                        try:
                            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            s.settimeout(2.0)
                            s.connect(("127.0.0.1", TTS_PORT))
                            s.settimeout(None)
                            tts_state.sock = s
                            tts_state.listening = True
                            tts_state.stale_backend = False
                            tts_state.expected_backend_token = token or _tts_backend_instance_token()
                            _tts_send_hello(s, tts_state.expected_backend_token)
                            t = threading.Thread(target=_tts_socket_listener, args=(s,))
                            t.daemon = True
                            t.start()
                            _tts_flush_pending_speech()
                            if not quiet:
                                tts_notify("TTS Online (Auto-start)")
                            try:
                                renpy.restart_interaction()
                            except Exception:
                                pass
                            return
                        except Exception:
                            if s is not None:
                                try:
                                    s.close()
                                except Exception:
                                    pass
                            time.sleep(2)
                    if not quiet:
                        tts_notify("Erro: Não foi possível conectar ao servidor TTS.")
                finally:
                    tts_state.connecting = False

            t = threading.Thread(target=_retry_connect)
            t.daemon = True
            t.start()
            return True
        except Exception as e:
            tts_state.connecting = False
            tts_state.owns_backend = False
            tts_notify("Erro ao iniciar processo TTS: " + str(e))
        return False

    def tts_speak(text, voice=None):
        if not text or not getattr(tts_state, "tts_audio_enabled", True):
            return
        if not tts_state.sock:
            tts_state.pending_speech = (text, voice)
            if not getattr(tts_state, "connecting", False):
                t = threading.Thread(target=tts_connect, args=(True,))
                t.daemon = True
                t.start()
            return
        speak(tts_state, text, voice, TTS_VOICE, renpy.substitute, tts_notify)

    def _tts_extract_speaker(kwargs=None):
        who = kwargs.get("who") if (kwargs and isinstance(kwargs, dict)) else None
        if not who:
            who = getattr(renpy.store, "_last_say_who", None)
        if who:
            if isinstance(who, str):
                who_str = who.strip()
                char_obj = getattr(renpy.store, who_str, None)
                if char_obj and hasattr(char_obj, "name"):
                    cleaned = clean_speaker_name(getattr(char_obj, "name", None), renpy.substitute)
                    if cleaned:
                        return cleaned
                return who_str
            if hasattr(who, "name"):
                cleaned = clean_speaker_name(who.name, renpy.substitute)
                if cleaned:
                    return cleaned
            return str(who).strip()
        return None

    def _tts_resolve_voice(speaker=None):
        voice_map = getattr(tts_state, "voice_map", {})
        context_sources = (getattr(renpy, "store", None), getattr(renpy, "persistent", None))
        return resolve_voice(
            speaker=speaker,
            voice_map=voice_map,
            player_names=collect_context_names(PLAYER_NAME_KEYS, context_sources),
            bf_names=collect_context_names(BF_NAME_KEYS, context_sources),
            current_voice=getattr(tts_state, "current_voice", None),
            default_voice=TTS_VOICE,
            last_speaker=getattr(renpy.store, "_last_say_who", ""),
        )

    def tts_speak_once(text, voice=None):
        if not text:
            return
        if text != getattr(tts_state, "last_spoken", None):
            tts_state.last_spoken = text
            actual_voice = voice or _tts_resolve_voice(_tts_extract_speaker())
            tts_speak(text, voice=actual_voice)

    def _tts_extract_callback_text(kwargs):
        return extract_callback_text(kwargs)

    def _tts_install_phone_callback_wrappers():
        install_phone_callback_wrappers(renpy.store, lambda text: tts_speak_once(text), ("Phone_SendSound", "Phone_ReceiveSound"))

    def _send_speed():
        send_speed(tts_state, tts_notify)

    def tts_increase_speed():
        increase_speed(tts_state, persistent, tts_notify)

    def tts_decrease_speed():
        decrease_speed(tts_state, persistent, tts_notify)

    def tts_toggle_auto():
        toggle_auto(tts_state, persistent, _preferences, tts_notify, lambda: renpy.restart_interaction())

    def _tts_wake_audio():
        cur = getattr(tts_state, "current_text", "")
        if cur:
            tts_state.pending_speech = (cur, _tts_resolve_voice(_tts_extract_speaker()))
        t = threading.Thread(target=tts_connect, args=(True,))
        t.daemon = True
        t.start()

    def tts_toggle_audio():
        return toggle_audio(tts_state, persistent, tts_notify, lambda: renpy.restart_interaction(), on_disable=tts_kill, on_enable=_tts_wake_audio)

    def _tts_callback(event, **kwargs):
        if event == "begin":
            tts_state.auto_advance_flag = False
            tts_state.native_voice_detected = False
            tts_state.native_voice_end_time = None
            tts_state.say_start_time = time.time()
            what = _tts_extract_callback_text(kwargs)
            tts_state.current_text = str(what or "")
            speaker = _tts_extract_speaker(kwargs)
            voice = _tts_resolve_voice(speaker)
            if what and getattr(tts_state, "tts_audio_enabled", True):
                tts_speak_once(what, voice=voice)
            else:
                tts_state.last_spoken = what
                tts_state.is_playing = False

    config.all_character_callbacks.append(_tts_callback)

    km_dict = {
        'v': tts_connect, 'V': tts_connect, 'shift_K_v': tts_connect,
        'a': tts_toggle_auto, 'A': tts_toggle_auto, 'shift_K_a': tts_toggle_auto, 'K_a': tts_toggle_auto,
        't': tts_toggle_audio, 'T': tts_toggle_audio, 'shift_K_t': tts_toggle_audio, 'K_t': tts_toggle_audio,
        'm': tts_toggle_audio, 'M': tts_toggle_audio,
        'K_EQUALS': tts_increase_speed, 'K_MINUS': tts_decrease_speed,
        'K_KP_PLUS': tts_increase_speed, 'K_KP_MINUS': tts_decrease_speed,
    }
    config.underlay.append(renpy.Keymap(**km_dict))

    try:
        if hasattr(config, "keymap") and isinstance(config.keymap, dict):
            afm_keys = config.keymap.setdefault("toggle_afm", [])
            for k in ('a', 'A', 'shift_K_a', 'K_a'):
                if k not in afm_keys:
                    afm_keys.append(k)
    except Exception:
        pass

    def _tts_install_save_compat_hook():
        install_save_compat_hook(getattr(renpy.game, "script", None), config, renpy.store)

    def _tts_install_display_hook():
        try:
            import renpy.display.tts as rtts
        except Exception:
            return
        install_display_hook(rtts, lambda: getattr(tts_state, "is_playing", False))

    def tts_start_callback():
        _tts_install_display_hook()
        _tts_install_save_compat_hook()
        _tts_install_phone_callback_wrappers()
        if hasattr(tts_state, "_load_voice_map"):
            tts_state._load_voice_map()
        if getattr(tts_state, "tts_audio_enabled", True):
            tts_connect(True)

    _tts_install_display_hook()
    _tts_install_save_compat_hook()
    _tts_install_phone_callback_wrappers()
    config.start_callbacks.append(tts_start_callback)
    config.after_load_callbacks.append(tts_start_callback)
    if hasattr(config, "quit_callbacks"):
        config.quit_callbacks.append(tts_shutdown)
    atexit.register(tts_shutdown)
    config.overlay_screens.append("tts_auto_forward_checker")

    # Auto-start on boot
    tts_start_callback()

init python:
    class TTSAutoAdvanceAction(Action):
        def __call__(self):
            AutoAdvanceController(tts_state, renpy, persistent).tick()

screen tts_auto_forward_checker():
    zorder 100
    timer 0.1 repeat True action TTSAutoAdvanceAction()

    $ current_auto = getattr(tts_state, "auto_forward", False) or getattr(_preferences, "afm_enable", False)
    $ current_tts_audio = getattr(tts_state, "tts_audio_enabled", True)
    vbox:
        xalign 0.99
        yalign 0.01
        spacing 4
        if current_auto:
            textbutton "Parar Modo Automático" action Function(tts_toggle_auto) text_size 14 text_color "#ff5555" text_outlines [(1, "#000", 0, 0)]
        else:
            textbutton "Iniciar Modo Automático" action Function(tts_toggle_auto) text_size 14 text_color "#55ff55" text_outlines [(1, "#000", 0, 0)]

        if current_tts_audio:
            textbutton "Áudio TTS: Ligado" action Function(tts_toggle_audio) text_size 14 text_color "#55ccff" text_outlines [(1, "#000", 0, 0)]
        else:
            textbutton "Áudio TTS: Desligado" action Function(tts_toggle_audio) text_size 14 text_color "#ffaa55" text_outlines [(1, "#000", 0, 0)]
