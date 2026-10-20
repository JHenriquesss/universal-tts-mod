# -*- coding: utf-8 -*-
"""Hooks que ligam o cliente TTS ao motor do Ren'Py.

O comportamento vivia dentro do ``tts_mod.rpy``, onde so podia ser testado
abrindo o jogo. Aqui cada hook recebe o objeto que ele vai alterar, o que
permite exercitar a logica com dublês.
"""

import bisect
import types


def extract_callback_text(kwargs):
    """Texto da fala dentro do callback de personagem."""
    for key in ("what", "text", "message"):
        value = (kwargs or {}).get(key)
        if value:
            return value
    return None


def wrap_phone_callback(original, on_text):
    """Envolve um callback de personagem para que ele fale o texto."""

    def wrapped(event, interact=True, **kwargs):
        try:
            original(event, interact=interact, **kwargs)
        except TypeError:
            original(event, **kwargs)

        if event in ("begin", "show_done"):
            on_text(extract_callback_text(kwargs))

    wrapped._tts_wrapped = True
    return wrapped


def patch_phone_callback_function(original, on_text):
    """Reescreve o codigo do callback preservando a assinatura original."""
    if getattr(original, "_tts_wrapped", False):
        return original
    try:
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
                on_text(extract_callback_text(kwargs))

        original.__code__ = patched.__code__
        original.__defaults__ = patched.__defaults__
        original.__kwdefaults__ = patched.__kwdefaults__
        original._tts_wrapped = True
        return original
    except Exception:
        return wrap_phone_callback(original, on_text)


def install_phone_callback_wrappers(store, on_text, names=("Phone_SendSound", "Phone_ReceiveSound")):
    """Alguns jogos desenham o telefone por callbacks proprios.

    Esses callbacks passam pelo hook global de personagem, entao precisam ser
   involucrados um a um.
    """
    for name in names:
        original = getattr(store, name, None)
        if original and not getattr(original, "_tts_wrapped", False):
            setattr(store, name, patch_phone_callback_function(original, on_text))


def install_save_compat_hook(script, config=None, store=None):
    """Compatibilidade reversa para carregar saves de versoes antigas.

    Mapeia as declaracoes com (arquivo, versao, serial) para as declaracoes
    atuais da namemap, evitando o erro "the script changed in an incompatible
    way" ao carregar um save antigo.
    """
    try:
        if not script or not hasattr(script, "namemap"):
            return

        serial_map = {}
        file_serials = {}
        for key in script.namemap.keys():
            if isinstance(key, tuple) and len(key) == 3:
                filename, _version, serial = key
                serial_map[(filename, serial)] = key
                if filename not in file_serials:
                    file_serials[filename] = []
                file_serials[filename].append(serial)

        for filename in file_serials:
            file_serials[filename].sort()

        original_has_label = script.has_label
        original_lookup = script.lookup

        def resolve_compat_statement(label):
            if label in script.namemap:
                return label
            if isinstance(label, tuple) and len(label) == 3:
                filename, _version, serial = label
                if (filename, serial) in serial_map:
                    target = serial_map[(filename, serial)]
                    script.namemap[label] = script.namemap[target]
                    return target
                if filename in file_serials and file_serials[filename]:
                    serials = file_serials[filename]
                    index = bisect.bisect_right(serials, serial) - 1
                    if index >= 0:
                        target = serial_map[(filename, serials[index])]
                    else:
                        target = serial_map[(filename, serials[0])]
                    script.namemap[label] = script.namemap[target]
                    return target
            return None

        def compat_has_label(label):
            if original_has_label(label):
                return True
            return resolve_compat_statement(label) is not None

        def compat_lookup(label):
            if label in script.namemap:
                return original_lookup(label)
            target = resolve_compat_statement(label)
            if target:
                return script.namemap[target]
            return original_lookup(label)

        script.has_label = compat_has_label
        script.lookup = compat_lookup

        # Fallback seguro para config.load_failed_label caso o jogo nao defina
        if config is not None and not getattr(config, "load_failed_label", None):
            config.load_failed_label = "_after_load"

        # Previne crash do cPickle no Ren'Py 7 (TypeError: expected string, NoneType found)
        if store is not None and getattr(store, "save_name", None) is None:
            store.save_name = ""
    except Exception:
        pass


def install_display_hook(display_tts, is_playing):
    """Avisa o motor de display que o audio do TTS esta em reproducao.

    Sem isso o SayBehavior e o PauseBehavior encerram a fala antes do audio.
    """
    try:
        if display_tts is None:
            return
        if not getattr(display_tts, "_tts_mod_hooked", False):
            original_is_active = display_tts.is_active

            def hooked_is_active():
                if is_playing():
                    return True
                return original_is_active()

            display_tts.is_active = hooked_is_active
            display_tts._tts_mod_hooked = True
    except Exception:
        pass
