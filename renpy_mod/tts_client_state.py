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

        # Garante que speed nunca seja None, mesmo se o persistent salvou como None
        saved_speed = getattr(persistent, "tts_speed", DEFAULT_SPEED)
        self.speed = float(saved_speed) if saved_speed is not None else DEFAULT_SPEED
        self.current_voice = default_voice
        self.voice_map = {}
        self._last_sent_voice = None
        self._load_voice_map()

    def _load_voice_map(self):
        """Le o voice_map.json do jogo. Um save antigo nao pode impedir a leitura."""
        try:
            if getattr(self, "voice_map", None) is None:
                self.voice_map = {}
            config = getattr(self, "_config", None)
            for base in (
                getattr(config, "gamedir", None),
                getattr(config, "basedir", None),
            ):
                if not base:
                    continue
                map_path = os.path.join(base, "voice_map.json")
                if os.path.isfile(map_path):
                    with open(map_path, "r", encoding="utf-8") as handle:
                        self.voice_map.update(json.load(handle))
        except Exception:
            pass

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
        self.speed = d.get("speed", DEFAULT_SPEED)
        self.current_voice = d.get("current_voice", default_voice)
        self.tts_audio_enabled = d.get("tts_audio_enabled", True)
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
        self.backend_token = None
        self.expected_backend_token = None
        self.stale_backend = False
        if not hasattr(self, "sock"):
            self.sock = None
        if not hasattr(self, "proc"):
            self.proc = None
        if not hasattr(self, "listening"):
            self.listening = False
        self._load_voice_map()
