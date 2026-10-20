################################################################################
# TTS MOD - VERSÃO FINAL (CARREGAMENTO TARDIO)
################################################################################

# Usamos init 999 para garantir que o GUI do jogo já terminou de carregar
init 999 python: 
    import subprocess
    import os
    import threading
    import time

    from tts_client_state import TTSState
    from tts_client_voice import (
        BF_NAME_KEYS,
        PLAYER_NAME_KEYS,
        clean_speaker_name,
        collect_context_names,
        resolve_voice,
    )

    # --- CONFIGURAÇÕES ---
    TTS_ENGINE = "kokoro"   
    TTS_LANG = "a"        
    TTS_VOICE = "af_heart"
    TTS_PORT = 5050
    # -------------------

    tts_state = TTSState(persistent=persistent, default_voice=TTS_VOICE, config=renpy.config)

    def _tts_backend_instance_token():
        """Le o token de instancia publicado pelo backend no arquivo de prontidao.

        Retorna None quando nao ha token publicado (ex.: backend iniciado
        manualmente em outro diretorio), caso em que nao existe nada a comparar.
        """
        try:
            status_path = os.path.join(renpy.config.gamedir, "tts_ready.txt")
            if not os.path.exists(status_path):
                return None
            with open(status_path, "r", encoding="utf-8") as f:
                status = f.read().strip()
            if not status.startswith("READY|"):
                return None
            parts = status.split("|")
            if len(parts) < 2:
                return None
            token = parts[1].strip()
            return token or None
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

    def _tts_socket_listener(sock):
        try:
            f = sock.makefile('r')
            expected_token = getattr(tts_state, "expected_backend_token", None)
            while tts_state.listening:
                line = f.readline()
                if not line:
                    tts_notify("TTS: Conexão encerrada pelo servidor.")
                    break
                line = line.strip()
                if line.startswith("HELLO:"):
                    remote_token = line[6:].strip()
                    tts_state.backend_token = remote_token
                    if expected_token and remote_token and remote_token != expected_token:
                        # Outra instancia do backend esta respondendo: e o backend
                        # orfao segurando a porta. Reconectar cria um backend novo.
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
            except Exception: pass
            tts_state.proc = None
        
        status_path = os.path.join(renpy.config.gamedir, "tts_ready.txt")
        if os.path.exists(status_path):
            try:
                os.remove(status_path)
            except Exception:
                pass

    def tts_connect(quiet=False):
        import socket
        
        # 1. Se já temos um socket funcional, não faz nada
        if tts_state.sock:
            try:
                # Teste rápido de conexão
                tts_state.sock.sendall(b"\n") 
                if not quiet: tts_notify("TTS já está conectado.")
                return True
            except Exception:
                tts_state.listening = False
                tts_state.sock = None

        if not quiet: tts_notify("Conectando ao servidor TTS...")
        
        # 2. Tentar conectar ao Socket (caso o usuário já tenha aberto o backend manualmente)
        # Tentativas limitadas: um backend que ainda esta bindando nao deve custar
        # o "jogo ficou mudo" na primeira tentativa.
        for attempt in range(3):
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(2.0)
                s.connect(("127.0.0.1", TTS_PORT))
                s.settimeout(None) # Remove timeout para o listener não cair
                tts_state.sock = s
                tts_state.listening = True
                tts_state.stale_backend = False
                # Backend externo: nao ha token autoritativo para comparar.
                tts_state.expected_backend_token = None
                _tts_send_hello(s)
                t = threading.Thread(target=_tts_socket_listener, args=(s,))
                t.daemon = True
                t.start()
                if not quiet: tts_notify("Conectado ao Backend Externo!")
                return True
            except Exception:
                time.sleep(0.4)


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
                for i in range(30):
                    try:
                        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        s.settimeout(2.0)
                        s.connect(("127.0.0.1", TTS_PORT))
                        s.settimeout(None) # Remove timeout para o listener não cair
                        tts_state.sock = s
                        tts_state.listening = True
                        tts_state.stale_backend = False
                        # Token publicado pelo backend que acabamos de iniciar. Se o
                        # HELLO trouxer outro token, outra instancia esta na porta.
                        tts_state.expected_backend_token = _tts_backend_instance_token()
                        _tts_send_hello(s, tts_state.expected_backend_token)
                        t = threading.Thread(target=_tts_socket_listener, args=(s,))
                        t.daemon = True
                        t.start()
                        if not quiet: tts_notify("TTS Online (Auto-start)")
                        try:
                            renpy.restart_interaction()
                        except Exception:
                            pass
                        return
                    except Exception:
                        time.sleep(2)

                if not quiet: tts_notify("Erro: Não foi possível conectar ao servidor TTS.")

            t = threading.Thread(target=_retry_connect)
            t.daemon = True
            t.start()
            return True
        except Exception as e:
            tts_notify("Erro ao iniciar processo TTS: " + str(e))
        return False

    def tts_speak(text, voice=None):
        if not text:
            return
        if not tts_state.sock:
            tts_state.is_playing = False
            return
        try:
            tts_state.is_playing = True
            tts_state.speak_start_time = time.time()
            clean_len = len(str(text))
            cur_speed = float(getattr(tts_state, "speed", 1.25) or 1.25)
            tts_state.expected_duration = max(3.0, (clean_len / (10.0 * max(0.5, cur_speed))) + 4.0)
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

            target_voice = voice or getattr(tts_state, "current_voice", None) or TTS_VOICE
            tts_state.sock.sendall(b"STOP\n")
            if target_voice:
                tts_state.sock.sendall(("SET_VOICE:" + str(target_voice) + "\n").encode('utf-8'))
                tts_state._last_sent_voice = target_voice
            tts_state.sock.sendall(payload + b"\n")
        except Exception as e:
            tts_notify("TTS falhou: " + str(e))
            tts_state.sock = None
            tts_state.is_playing = False

    def _tts_extract_speaker(kwargs=None):
        who = None
        if kwargs and isinstance(kwargs, dict):
            who = kwargs.get("who")
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
            except Exception:
                pass



    def tts_increase_speed():
        tts_state.speed = round(min(3.0, tts_state.speed + 0.1), 2)
        persistent.tts_speed = tts_state.speed
        _send_speed()

    def tts_decrease_speed():
        tts_state.speed = round(max(0.5, tts_state.speed - 0.1), 2)
        persistent.tts_speed = tts_state.speed
        _send_speed()

    def tts_toggle_auto():
        current = bool(getattr(tts_state, "auto_forward", False) or getattr(_preferences, "afm_enable", False))
        new_state = not current
        tts_state.auto_forward = new_state
        try:
            persistent.tts_auto_forward = new_state
        except Exception: pass
        try:
            _preferences.afm_enable = new_state
            _preferences.afm_after_click = True
            if new_state and getattr(_preferences, "afm_time", 0) <= 0:
                _preferences.afm_time = 15.0
            renpy.restart_interaction()
        except Exception: pass
        status = "LIGADO" if new_state else "DESLIGADO"
        tts_notify("Modo Automatico: {}".format(status))
        if new_state:
            now = time.time()
            start = getattr(tts_state, "speak_start_time", 0.0)
            expected = getattr(tts_state, "expected_duration", 5.0)
            if not getattr(tts_state, "is_playing", False) or (now - start > max(expected * 2.0 + 15.0, 40.0)):
                tts_state.is_playing = False
                tts_state.playback_done_time = 0.0
                tts_state.auto_advance_flag = True

    def tts_toggle_audio():
        current = bool(getattr(tts_state, "tts_audio_enabled", True))
        new_state = not current
        tts_state.tts_audio_enabled = new_state
        try:
            persistent.tts_audio_enabled = new_state
        except Exception: pass
        if not new_state:
            if tts_state.sock:
                try:
                    tts_state.sock.sendall(b"STOP\n")
                except Exception: pass
            tts_state.is_playing = False
        status = "LIGADO" if new_state else "DESLIGADO"
        tts_notify("Áudio TTS: {}".format(status))
        try:
            renpy.restart_interaction()
        except Exception: pass
        return new_state

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

    # Injeção segura
    config.all_character_callbacks.append(_tts_callback)
    
    km_dict = {
        'v': tts_connect,
        'V': tts_connect,
        'shift_K_v': tts_connect,
        'a': tts_toggle_auto,
        'A': tts_toggle_auto,
        'shift_K_a': tts_toggle_auto,
        'K_a': tts_toggle_auto,
        't': tts_toggle_audio,
        'T': tts_toggle_audio,
        'shift_K_t': tts_toggle_audio,
        'K_t': tts_toggle_audio,
        'm': tts_toggle_audio,
        'M': tts_toggle_audio,
        'K_EQUALS': tts_increase_speed,
        'K_MINUS': tts_decrease_speed,
        'K_KP_PLUS': tts_increase_speed,
        'K_KP_MINUS': tts_decrease_speed
    }
    config.underlay.append(renpy.Keymap(**km_dict))

    # Sincroniza keymap nativo do Ren'Py para toggle_afm
    try:
        if hasattr(config, "keymap") and isinstance(config.keymap, dict):
            afm_keys = config.keymap.setdefault("toggle_afm", [])
            for k in ('a', 'A', 'shift_K_a', 'K_a'):
                if k not in afm_keys:
                    afm_keys.append(k)
    except Exception:
        pass

    def _tts_install_save_compat_hook():
        """
        Garante compatibilidade reversa para carregar saves antigos criados em versões ou
        builds anteriores do jogo, prevenindo o erro:
        'Exception: Could not load the game. Perhaps the script changed in an incompatible way.'
        Mapeia tuplas de declarações (filename, old_version, serial) para as declarações atuais na namemap.
        """
        try:
            script = getattr(renpy.game, "script", None)
            if not script or not hasattr(script, "namemap"):
                return

            serial_map = {}
            file_serials = {}
            for k in script.namemap.keys():
                if isinstance(k, tuple) and len(k) == 3:
                    fn, ver, serial = k
                    serial_map[(fn, serial)] = k
                    if fn not in file_serials:
                        file_serials[fn] = []
                    file_serials[fn].append(serial)

            for fn in file_serials:
                file_serials[fn].sort()

            orig_has_label = script.has_label
            orig_lookup = script.lookup
            import bisect

            def resolve_compat_statement(label):
                if label in script.namemap:
                    return label
                if isinstance(label, tuple) and len(label) == 3:
                    fn, ver, serial = label
                    if (fn, serial) in serial_map:
                        target = serial_map[(fn, serial)]
                        script.namemap[label] = script.namemap[target]
                        return target
                    if fn in file_serials and file_serials[fn]:
                        serials = file_serials[fn]
                        idx = bisect.bisect_right(serials, serial) - 1
                        if idx >= 0:
                            target = serial_map[(fn, serials[idx])]
                        else:
                            target = serial_map[(fn, serials[0])]
                        script.namemap[label] = script.namemap[target]
                        return target
                return None

            def compat_has_label(label):
                if orig_has_label(label):
                    return True
                return resolve_compat_statement(label) is not None

            def compat_lookup(label):
                if label in script.namemap:
                    return orig_lookup(label)
                target = resolve_compat_statement(label)
                if target:
                    return script.namemap[target]
                return orig_lookup(label)

            script.has_label = compat_has_label
            script.lookup = compat_lookup

            # Fallback seguro para config.load_failed_label caso o jogo não defina
            if not getattr(config, "load_failed_label", None):
                config.load_failed_label = "_after_load"

            # Previne crash do cPickle no Ren'Py 7 (TypeError: expected string, NoneType found)
            if getattr(renpy.store, "save_name", None) is None:
                renpy.store.save_name = ""
        except Exception:
            pass

    def _tts_install_display_hook():
        # Hook no motor de display do Ren'Py para avisar SayBehavior e PauseBehavior
        # que o áudio do TTS está em reprodução, impedindo avanço nativo precoce.
        try:
            import renpy.display.tts as rtts
            if not getattr(rtts, "_tts_mod_hooked", False):
                _orig_is_active = rtts.is_active
                def _hooked_is_active():
                    if getattr(tts_state, "is_playing", False):
                        return True
                    return _orig_is_active()
                rtts.is_active = _hooked_is_active
                rtts._tts_mod_hooked = True
        except Exception:
            pass

    def tts_start_callback():
        _tts_install_display_hook()
        _tts_install_save_compat_hook()
        _tts_install_phone_callback_wrappers()
        if hasattr(tts_state, "_load_voice_map"):
            tts_state._load_voice_map()
        tts_connect(True)

    _tts_install_display_hook()
    _tts_install_save_compat_hook()
    _tts_install_phone_callback_wrappers()
    config.start_callbacks.append(tts_start_callback)
    config.after_load_callbacks.append(tts_start_callback)
    config.overlay_screens.append("tts_auto_forward_checker")
    
    # Auto-start on boot
    tts_start_callback()

init python:
    class TTSAutoAdvanceAction(Action):
        def __call__(self):
            pref_auto = getattr(renpy.store._preferences, "afm_enable", False)
            mod_auto = getattr(tts_state, "auto_forward", False)
            if pref_auto != mod_auto:
                tts_state.auto_forward = pref_auto
                try:
                    persistent.tts_auto_forward = pref_auto
                    renpy.store._preferences.afm_after_click = True
                    if pref_auto and getattr(renpy.store._preferences, "afm_time", 0) <= 0:
                        renpy.store._preferences.afm_time = 15.0
                except Exception:
                    pass
                if pref_auto:
                    now = time.time()
                    start = getattr(tts_state, "speak_start_time", 0.0)
                    expected = getattr(tts_state, "expected_duration", 5.0)
                    if not getattr(tts_state, "is_playing", False) or (now - start > max(expected * 2.0 + 15.0, 40.0)):
                        tts_state.is_playing = False
                        tts_state.playback_done_time = 0.0
                        tts_state.auto_advance_flag = True

            auto_active = getattr(tts_state, "auto_forward", False) or getattr(renpy.store._preferences, "afm_enable", False)

            # Watchdog: destrava playback se auto está ativo e o áudio excedeu o tempo esperado
            if auto_active and getattr(tts_state, "is_playing", False):
                now = time.time()
                start = getattr(tts_state, "speak_start_time", 0.0)
                expected = getattr(tts_state, "expected_duration", 5.0)
                if now - start > max(expected * 2.0 + 15.0, 40.0):
                    tts_state.is_playing = False
                    tts_state.playback_done_time = now
                    tts_state.auto_advance_flag = True

            # Sincronização com áudio nativo do jogo quando TTS está desligado ou o jogo possui dublagem
            native_playing = False
            if hasattr(renpy, "music"):
                try:
                    if bool(renpy.music.get_playing("voice")) or bool(renpy.music.is_playing("voice")):
                        native_playing = True
                except Exception:
                    pass

            if native_playing:
                tts_state.native_voice_detected = True
                tts_state.native_voice_end_time = None
            elif getattr(tts_state, "native_voice_detected", False):
                now = time.time()
                if getattr(tts_state, "native_voice_end_time", None) is None:
                    tts_state.native_voice_end_time = now
                elif now - tts_state.native_voice_end_time >= 0.7:
                    tts_state.native_voice_detected = False
                    tts_state.auto_advance_flag = True
            elif auto_active and not getattr(tts_state, "tts_audio_enabled", True):
                now = time.time()
                start = getattr(tts_state, "say_start_time", now)
                elapsed = now - start
                if elapsed >= 0.35:
                    text_len = len(getattr(tts_state, "current_text", ""))
                    delay = max(2.0, min(5.0, (text_len * 0.05) + 1.2))
                    if elapsed >= delay:
                        tts_state.auto_advance_flag = True

            now = time.time()
            done_time = getattr(tts_state, "playback_done_time", 0.0)
            is_choice = bool(renpy.get_screen("choice") or renpy.get_screen("vibor_in_scene"))
            if getattr(tts_state, "auto_advance_flag", False) and auto_active and not is_choice:
                if now - done_time >= 0.35:
                    tts_state.auto_advance_flag = False
                    renpy.end_interaction(True)

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
