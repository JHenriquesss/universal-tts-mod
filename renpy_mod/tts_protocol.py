# -*- coding: utf-8 -*-
"""Protocolo do socket TTS: comandos e regras de fila.

Fica em um modulo proprio, sem efeitos de import, para que as regras de fila
possam ser testadas de forma deterministica sem subir um backend, e para que
exista uma unica fonte de verdade do protocolo usada pelo backend, pelos
clientes e pelas guardas de documentacao.
"""

# Comandos enviados pelo cliente ao backend.
CMD_STOP = "STOP"
CMD_SET_SPEED = "SET_SPEED"
CMD_SET_VOICE = "SET_VOICE"
CMD_SET_LANG = "SET_LANG"
CMD_HELLO = "HELLO"
CMD_QUIT = "QUIT"

# Comando enviado pelo backend ao cliente.
CMD_PLAYBACK_DONE = "PLAYBACK_DONE"

# Protocolo aceito pelo backend.
CLIENT_COMMANDS = (
    CMD_STOP,
    CMD_SET_SPEED,
    CMD_SET_VOICE,
    CMD_SET_LANG,
    CMD_HELLO,
    CMD_QUIT,
)

# Comandos enviados pelo backend ao cliente.
SERVER_COMMANDS = (CMD_PLAYBACK_DONE,)

# Comandos que o STOP preserva: o STOP cancela a fala pendente, nao a configuracao.
PRESERVED_ON_STOP = (CMD_SET_VOICE, CMD_SET_SPEED, CMD_SET_LANG)


def drain_preserving(queue_obj, preserved_commands=PRESERVED_ON_STOP):
    """Esvazia a fila de falas e devolve os itens de configuracao que sobrevivem a um STOP.

    Descarta a fala pendente e preserva a configuracao (voz, velocidade, idioma).
    Cada item descartado e liberado com task_done, senao o contador de tarefas
    pendentes da fila cresce a cada STOP.
    """
    import queue as queue_module

    preserved = []
    while not queue_obj.empty():
        try:
            item = queue_obj.get_nowait()
        except queue_module.Empty:
            break
        if item[0] in preserved_commands:
            preserved.append(item)
        try:
            queue_obj.task_done()
        except ValueError:
            pass
    return preserved
