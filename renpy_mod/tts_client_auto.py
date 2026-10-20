# -*- coding: utf-8 -*-
"""Regras do avanco automatico do cliente TTS.

As decisoes ficavam dentro da classe de acao do ``tts_mod.rpy``. Aqui elas
sao funcoes puras: o cliente passa o estado e o instante, e o modulo diz o
que precisa acontecer.
"""

import time


# Margem extra sobre o tempo esperado de audio antes de considerar que o
# playback travou, e o piso absoluto dessa espera.
TIMEOUT_EXTRA_SECONDS = 15.0
TIMEOUT_MIN_SECONDS = 40.0

# Tempo minimo antes de o auto-advance considerar que a linha foi lida.
READING_GRACE_SECONDS = 0.35

# Tempo que o audio nativo do jogo precisa ficar em silencio para o
# auto-advance assumir a linha.
NATIVE_VOICE_RELEASE_SECONDS = 0.7


def playback_timed_out(is_playing, speak_start_time, expected_duration, now):
    """O audio passou do tempo esperado e nao terminou."""
    if not is_playing:
        return False
    limit = max(
        float(expected_duration or 0.0) * 2.0 + TIMEOUT_EXTRA_SECONDS,
        TIMEOUT_MIN_SECONDS,
    )
    return (now - float(speak_start_time or 0.0)) > limit


def unvoiced_reading_delay(text):
    """Tempo de leitura de uma linha sem audio nativo."""
    text_length = len(str(text or ""))
    return max(2.0, min(5.0, (text_length * 0.05) + 1.2))


def next_native_voice_state(detected, end_time, native_playing, now):
    """Estado do audio nativo depois deste instante.

    Retorna (detectado, fim_do_audio, finished): ``finished`` diz que o audio
    nativo acabou e que o auto-advance pode assumir a linha.
    """
    if native_playing:
        return True, None, False
    if not detected:
        return False, None, False
    if end_time is None:
        return True, now, False
    if (now - float(end_time)) >= NATIVE_VOICE_RELEASE_SECONDS:
        return False, end_time, True
    return True, end_time, False


def should_end_interaction(auto_advance_flag, auto_active, is_choice, done_time, now):
    """O auto-advance pode encerrar a interacao neste instante."""
    if not auto_advance_flag or not auto_active:
        return False
    if is_choice:
        return False
    return (now - float(done_time or 0.0)) >= READING_GRACE_SECONDS


class AutoAdvanceController(object):
    """Decide, a cada tique, se o jogo pode avancar sozinho.

    A acao do Ren'Py apenas delega para aqui: as regras ficam em funcoes
    puras, testaveis fora do jogo.
    """

    def __init__(self, state, renpy_api, persistent):
        self.state = state
        self.renpy = renpy_api
        self.persistent = persistent

    @property
    def preferences(self):
        return getattr(getattr(self.renpy, "store", None), "_preferences", None)

    def _native_voice_playing(self):
        if not hasattr(self.renpy, "music"):
            return False
        try:
            return bool(
                self.renpy.music.get_playing("voice")
                or self.renpy.music.is_playing("voice")
            )
        except Exception:
            return False

    def tick(self, now=None):
        """Executa um ciclo do auto-advance."""
        state = self.state
        preferences = self.preferences
        moment = time.time() if now is None else now

        pref_auto = getattr(preferences, "afm_enable", False)
        mod_auto = getattr(state, "auto_forward", False)
        if pref_auto != mod_auto:
            state.auto_forward = pref_auto
            try:
                self.persistent.tts_auto_forward = pref_auto
                preferences.afm_after_click = True
                if pref_auto and getattr(preferences, "afm_time", 0) <= 0:
                    preferences.afm_time = 15.0
            except Exception:
                pass
            if pref_auto:
                start = getattr(state, "speak_start_time", 0.0)
                expected = getattr(state, "expected_duration", 5.0)
                if not getattr(state, "is_playing", False) or playback_timed_out(
                    getattr(state, "is_playing", False), start, expected, moment
                ):
                    state.is_playing = False
                    state.playback_done_time = 0.0
                    state.auto_advance_flag = True

        auto_active = getattr(state, "auto_forward", False) or getattr(
            preferences, "afm_enable", False
        )

        # Watchdog: destrava playback se o audio excedeu o tempo esperado.
        start = getattr(state, "speak_start_time", 0.0)
        expected = getattr(state, "expected_duration", 5.0)
        if auto_active and playback_timed_out(
            getattr(state, "is_playing", False), start, expected, moment
        ):
            state.is_playing = False
            state.playback_done_time = moment
            state.auto_advance_flag = True

        # Sincronizacao com o audio nativo do jogo.
        native_playing = self._native_voice_playing()
        was_detected = getattr(state, "native_voice_detected", False)
        detected, end_time, finished = next_native_voice_state(
            was_detected,
            getattr(state, "native_voice_end_time", None),
            native_playing,
            moment,
        )
        state.native_voice_detected = detected
        state.native_voice_end_time = end_time

        if finished:
            state.auto_advance_flag = True
        elif (
            not native_playing
            and not was_detected
            and auto_active
            and not getattr(state, "tts_audio_enabled", True)
        ):
            say_start = getattr(state, "say_start_time", moment)
            elapsed = moment - say_start
            if elapsed >= READING_GRACE_SECONDS:
                delay = unvoiced_reading_delay(getattr(state, "current_text", ""))
                if elapsed >= delay:
                    state.auto_advance_flag = True

        done_time = getattr(state, "playback_done_time", 0.0)
        is_choice = False
        try:
            is_choice = bool(
                self.renpy.get_screen("choice") or self.renpy.get_screen("vibor_in_scene")
            )
        except Exception:
            is_choice = True
        if should_end_interaction(
            getattr(state, "auto_advance_flag", False),
            auto_active,
            is_choice,
            done_time,
            moment,
        ):
            state.auto_advance_flag = False
            self.renpy.end_interaction(True)
