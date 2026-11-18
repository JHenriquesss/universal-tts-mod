# -*- coding: utf-8 -*-
"""Estado compartilhado entre o cliente TTS e o jogo.

A classe vivia dentro do ``tts_mod.rpy``, onde so existia dentro do Ren'Py.
Aqui as dependencias chegam pelo construtor: o ``persistent``, a voz padrao e o
``config`` do Ren'Py, de modo que o estado possa ser testado sem abrir o jogo.
"""

import json
import os


DEFAULT_VOICE = "af_heart"
DEFAULT_SPEED = 1.25
MIN_SPEED = 0.5
MAX_SPEED = 2.0


def _clamp_client_speed(raw_speed):
    if raw_speed is None:
        return DEFAULT_SPEED
    try:
        parsed = float(raw_speed)
    except (TypeError, ValueError):
        return DEFAULT_SPEED
    if parsed != parsed:  # NaN check compativel com Python 2 e 3
        return DEFAULT_SPEED
    return min(MAX_SPEED, max(MIN_SPEED, parsed))

# Runtime dedicado do backend: venv leve com Kokoro no ONNX Runtime, criado pelo instalar.bat.
# Fica fora do Python global para evitar dependencias pesadas (~1 GB a mais de RAM).
RUNTIME_DIR_PARTS = ("UniversalKokoroTTS", "runtime")


def find_backend_python(environ, exists, which, os_name="nt"):
    """Escolhe o Python que roda o backend, do mais leve para o mais generico.

    Ordem no Windows: runtime dedicado, ``pythonw``/``python`` do PATH e o
    Python 3.12 instalado pelo ``instalar.bat``. ``exists`` e ``which`` chegam
    por injecao para a regra poder ser testada fora do jogo.
    """
    if os_name != "nt":
        return "python3"
    local_app_data = environ.get("LOCALAPPDATA", "")
    if local_app_data:
        runtime_scripts = os.path.join(local_app_data, *(RUNTIME_DIR_PARTS + ("Scripts",)))
        for name in ("pythonw.exe", "python.exe"):
            candidate = os.path.join(runtime_scripts, name)
            if exists(candidate):
                return candidate
    for name in ("pythonw.exe", "python.exe"):
        if which(name):
            return name
    if local_app_data:
        py312_dir = os.path.join(local_app_data, "Programs", "Python", "Python312")
        for name in ("pythonw.exe", "python.exe"):
            candidate = os.path.join(py312_dir, name)
            if exists(candidate):
                return candidate
    return "pythonw.exe"


class TTSState(object):
    """Estado do cliente: socket, backend, voz, velocidade e auto-advance."""

    # Referencias do jogo. Nao entram no save, mas precisam sobreviver a um
    # load: sem elas o mapa de vozes do jogo sumia depois de carregar um save.
    persistent_ref = None
    config_ref = None
    voice_ref = DEFAULT_VOICE

    def __init__(self, persistent=None, default_voice=DEFAULT_VOICE, config=None):
        TTSState.persistent_ref = persistent
        TTSState.config_ref = config
        TTSState.voice_ref = default_voice

        self._persistent = persistent
        self._default_voice = default_voice
        self._config = config

        self.proc = None
        self.sock = None
        self.connecting = False
        self.owns_backend = False
        self.pending_speech = None
        self.voices = []
        self.last_spoken = None

        saved_auto = getattr(persistent, "tts_auto_forward", False)
        self.auto_forward = bool(saved_auto) if saved_auto is not None else False
        self.auto_advance_flag = False
        self.listening = False
        self.is_playing = False
        self.speak_start_time = 0.0
        self.expected_duration = 0.0

        saved_tts_audio = getattr(persistent, "tts_audio_enabled", True)
        self.tts_audio_enabled = (
            bool(saved_tts_audio) if saved_tts_audio is not None else True
        )
        self.native_voice_detected = False
        self.native_voice_end_time = None
        self.say_start_time = 0.0
        self.playback_done_time = 0.0
        self.current_text = ""
        self.backend_token = None
        self.expected_backend_token = None
        self.stale_backend = False

        # Ultima fala vista pelo jogo, registrada no ponto em que o say e
        # chamado. O callback de personagem do Ren'Py 7 nao entrega o texto.
        self.last_say_who = None
        self.last_say_what = None

        # Garante que speed nunca seja None nem ultrapasse o limite nativo (2.0x)
        saved_speed = getattr(persistent, "tts_speed", DEFAULT_SPEED)
        self.speed = _clamp_client_speed(saved_speed)
        self.current_voice = default_voice
        self.voice_map = {}
        self.voice_map_error = None
        self._last_sent_voice = None
        self._load_voice_map()

    def _load_voice_map(self):
        """Le o voice_map.json do jogo e registra erro diagnostico se estiver corrompido."""
        if getattr(self, "voice_map", None) is None:
            self.voice_map = {}
        self.voice_map_error = None
        config = getattr(self, "_config", None)
        for base in (
            getattr(config, "gamedir", None),
            getattr(config, "basedir", None),
        ):
            if not base:
                continue
            map_path = os.path.join(base, "voice_map.json")
            if not os.path.isfile(map_path):
                continue
            try:
                with open(map_path, "r", encoding="utf-8") as handle:
                    loaded = json.load(handle)
                if not isinstance(loaded, dict):
                    raise ValueError(
                        "esperado objeto JSON {{chave: voz}}, recebido {}".format(type(loaded).__name__)
                    )
                for key, val in loaded.items():
                    if isinstance(key, str) and isinstance(val, str) and val.strip():
                        self.voice_map[key] = val.strip()
            except Exception as err:
                self.voice_map_error = "voice_map.json invalido ({}): {}".format(map_path, err)

    def reload_voice_map(self, notify=None):
        """Recarrega o voice_map.json e avisa o jogador se o JSON estiver invalido."""
        self._load_voice_map()
        if self.voice_map_error and notify is not None:
            notify("TTS: " + self.voice_map_error)
        return self.voice_map

    def __getstate__(self):
        default_voice = getattr(self, "_default_voice", DEFAULT_VOICE)
        return {
            "auto_forward": getattr(self, "auto_forward", False),
            "speed": getattr(self, "speed", DEFAULT_SPEED),
            "current_voice": getattr(self, "current_voice", default_voice),
            "tts_audio_enabled": getattr(self, "tts_audio_enabled", True),
        }

    def __setstate__(self, d):
        default_voice = getattr(self, "_default_voice", None) or TTSState.voice_ref
        self._persistent = TTSState.persistent_ref
        self._config = TTSState.config_ref
        self._default_voice = default_voice
        self.auto_forward = d.get("auto_forward", False)
        self.speed = _clamp_client_speed(d.get("speed", DEFAULT_SPEED))
        self.current_voice = d.get("current_voice", default_voice)
        self.tts_audio_enabled = d.get("tts_audio_enabled", True)
        self.voice_map_error = None
        self.is_playing = False
        self.auto_advance_flag = False
        self.native_voice_detected = False
        self.native_voice_end_time = None
        self.say_start_time = 0.0
        self.playback_done_time = 0.0
        self.current_text = ""
        self.speak_start_time = 0.0
        self.expected_duration = 0.0
        self.last_spoken = None
        self.pending_speech = None
        self.backend_token = None
        self.expected_backend_token = None
        self.stale_backend = False
        self.last_say_who = None
        self.last_say_what = None
        if not hasattr(self, "sock"):
            self.sock = None
        if not hasattr(self, "proc"):
            self.proc = None
        if not hasattr(self, "listening"):
            self.listening = False
        if not hasattr(self, "connecting"):
            self.connecting = False
        if not hasattr(self, "owns_backend"):
            self.owns_backend = False
        self._load_voice_map()
