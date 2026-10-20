# -*- coding: utf-8 -*-
"""Comandos do cliente TTS: velocidade, modo automatico e audio.

As funcoes ficavam dentro do ``tts_mod.rpy``. Aqui o estado e as dependencias
chegam por parametro, para que cada comando possa ser testado sozinho.
"""

import time

from tts_client_auto import playback_timed_out


MIN_SPEED = 0.5
MAX_SPEED = 3.0
SPEED_STEP = 0.1


def send_speed(state, notify):
    """Manda a velocidade atual para o backend e avisa o jogador."""
    notify("Velocidade TTS: {:.2f}x".format(state.speed))
    if state.sock:
        try:
            message = "SET_SPEED:{}\n".format(state.speed)
            state.sock.sendall(message.encode("utf-8"))
        except Exception:
            pass


def increase_speed(state, persistent, notify):
    """Acelera a fala em um passo."""
    state.speed = round(min(MAX_SPEED, state.speed + SPEED_STEP), 2)
    try:
        persistent.tts_speed = state.speed
    except Exception:
        pass
    send_speed(state, notify)


def decrease_speed(state, persistent, notify):
    """Desacelera a fala em um passo."""
    state.speed = round(max(MIN_SPEED, state.speed - SPEED_STEP), 2)
    try:
        persistent.tts_speed = state.speed
    except Exception:
        pass
    send_speed(state, notify)


def toggle_auto(state, persistent, preferences, notify, restart_interaction, now=None):
    """Liga ou desliga o avanco automatico.

    Ao ligar, uma fala que ja passou do tempo esperado libera a linha na hora:
    o jogador nao pode ficar preso esperando audio que nunca vai chegar.
    """
    current = bool(
        getattr(state, "auto_forward", False)
        or getattr(preferences, "afm_enable", False)
    )
    new_state = not current
    state.auto_forward = new_state
    try:
        persistent.tts_auto_forward = new_state
    except Exception:
        pass
    try:
        preferences.afm_enable = new_state
        preferences.afm_after_click = True
        if new_state and getattr(preferences, "afm_time", 0) <= 0:
            preferences.afm_time = 15.0
        restart_interaction()
    except Exception:
        pass

    status = "LIGADO" if new_state else "DESLIGADO"
    notify("Modo Automatico: {}".format(status))

    if new_state:
        moment = time.time() if now is None else now
        timed_out = playback_timed_out(
            getattr(state, "is_playing", False),
            getattr(state, "speak_start_time", 0.0),
            getattr(state, "expected_duration", 5.0),
            moment,
        )
        if not getattr(state, "is_playing", False) or timed_out:
            state.is_playing = False
            state.playback_done_time = 0.0
            state.auto_advance_flag = True
    return new_state


def toggle_audio(state, persistent, notify, restart_interaction):
    """Liga ou desliga o audio do TTS."""
    current = bool(getattr(state, "tts_audio_enabled", True))
    new_state = not current
    state.tts_audio_enabled = new_state
    try:
        persistent.tts_audio_enabled = new_state
    except Exception:
        pass

    if not new_state:
        if state.sock:
            try:
                state.sock.sendall(b"STOP\n")
            except Exception:
                pass
        state.is_playing = False

    status = "LIGADO" if new_state else "DESLIGADO"
    notify("Áudio TTS: {}".format(status))
    try:
        restart_interaction()
    except Exception:
        pass
    return new_state
