# -*- coding: utf-8 -*-
"""Envio da fala do cliente TTS para o backend.

O texto passa por duas transformacoes antes de ir para o socket: a limpeza
das tags e a interpolacao do Ren'Py. A parte que depende da versao do
Python fica aqui, isolada, porque e o unico lugar do cliente que precisa
saber se o jogo roda em Python 2 ou 3.
"""

import sys
import time


def build_payload(text, substitute):
    """Texto final da fala, ja interpolado e pronto para o socket."""
    if sys.version_info[0] == 2:
        # Python 2 (Ren'Py 7)
        if isinstance(text, unicode):  # noqa: F821 - definido apenas em Python 2
            text_value = text.encode("utf-8")
        else:
            text_value = str(text)
        return substitute(text_value)

    # Python 3 (Ren'Py 8)
    text_value = str(text)
    interpolated = substitute(text_value)
    if isinstance(interpolated, str):
        return interpolated.encode("utf-8")
    return interpolated


def speak(state, text, voice, default_voice, substitute, notify):
    """Manda a fala para o backend, trocando a voz antes do texto."""
    if not text:
        return
    if not state.sock:
        state.is_playing = False
        return
    try:
        state.is_playing = True
        state.speak_start_time = time.time()
        clean_length = len(str(text))
        current_speed = float(getattr(state, "speed", 1.25) or 1.25)
        state.expected_duration = max(
            3.0, (clean_length / (10.0 * max(0.5, current_speed))) + 4.0
        )

        payload = build_payload(text, substitute)

        target_voice = voice or getattr(state, "current_voice", None) or default_voice
        state.sock.sendall(b"STOP\n")
        if target_voice:
            state.sock.sendall(("SET_VOICE:" + str(target_voice) + "\n").encode("utf-8"))
            state._last_sent_voice = target_voice
        state.sock.sendall(payload + b"\n")
    except Exception as error:
        notify("TTS falhou: " + str(error))
        state.sock = None
        state.is_playing = False
