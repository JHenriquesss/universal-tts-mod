################################################################################
# MOD DE CONTINUAR AUTOMATICO (SEM TTS)
# Especialmente adaptado para jogos com dublagem/audio nativo (ex: Summertime Saga Remake)
################################################################################

init -10 python:
    import sys
    import os
    if hasattr(renpy.config, "gamedir") and renpy.config.gamedir not in sys.path:
        sys.path.insert(0, renpy.config.gamedir)

init 999 python:
    import time
    from auto_advance_core import AutoAdvanceManager

    # Instância do gerenciador de avanço automático
    saved_pause = getattr(persistent, "mod_auto_pause", None)
    if saved_pause is None:
        saved_pause = 0.7
    saved_enabled = bool(getattr(persistent, "mod_auto_advance_enabled", False) or False)
    auto_advance_mgr = AutoAdvanceManager(renpy_api=renpy, pause_after_voice=saved_pause)
    auto_advance_mgr.enabled = saved_enabled

    def auto_toggle_action():
        """Alterna o modo continuar automático e salva no persistent."""
        new_val = auto_advance_mgr.toggle()
        persistent.mod_auto_advance_enabled = new_val
        try:
            renpy.restart_interaction()
        except Exception:
            pass

    def auto_increase_pause_action():
        """Aumenta o tempo de pausa apos finalizado o audio."""
        val = auto_advance_mgr.increase_pause()
        persistent.mod_auto_pause = val
        try:
            renpy.restart_interaction()
        except Exception:
            pass

    def auto_decrease_pause_action():
        """Diminui o tempo de pausa apos finalizado o audio."""
        val = auto_advance_mgr.decrease_pause()
        persistent.mod_auto_pause = val
        try:
            renpy.restart_interaction()
        except Exception:
            pass

    def _auto_dialogue_callback(event, **kwargs):
        """Monitora o ciclo de vida do dialogo (inicio e fim)."""
        if event == "begin":
            try:
                if renpy.get_screen("town_map"):
                    renpy.hide_screen("town_map")
            except Exception:
                pass
            auto_advance_mgr.on_say_begin(kwargs)
        elif event == "end":
            auto_advance_mgr.on_say_end()

    # Registra callback de personagens para sincronia exata de fala
    config.all_character_callbacks.append(_auto_dialogue_callback)

    # Teclas de atalho: 'A' para ligar/desligar, '+' e '-' para ajustar pausa
    km_dict = {
        'a': auto_toggle_action,
        'A': auto_toggle_action,
        'shift_K_a': auto_toggle_action,
        'K_a': auto_toggle_action,
        'K_EQUALS': auto_increase_pause_action,
        'K_MINUS': auto_decrease_pause_action,
        'K_KP_PLUS': auto_increase_pause_action,
        'K_KP_MINUS': auto_decrease_pause_action
    }
    config.underlay.append(renpy.Keymap(**km_dict))

    # Previne que pulos (Jumps) de mapas deixem a tela town_map presa no stack de telas
    if hasattr(renpy, "jump") and not getattr(renpy, "_mod_jump_patched", False):
        _orig_jump = renpy.jump
        def _safe_jump(label, *args, **kwargs):
            try:
                if renpy.get_screen("town_map"):
                    renpy.hide_screen("town_map")
            except Exception:
                pass
            return _orig_jump(label, *args, **kwargs)
        renpy.jump = _safe_jump
        renpy._mod_jump_patched = True

    def _auto_on_load_reset():
        """Reseta estados transientes apos carregar jogo salvo e fecha telas presas."""
        auto_advance_mgr.say_active = False
        auto_advance_mgr.advanced = False
        auto_advance_mgr.voice_detected = False
        auto_advance_mgr.voice_end_time = None
        auto_advance_mgr.line_start_time = time.time()
        auto_advance_mgr.enabled = bool(getattr(persistent, "mod_auto_advance_enabled", False) or False)
        saved_pause = getattr(persistent, "mod_auto_pause", None)
        try:
            auto_advance_mgr.pause_after_voice = float(saved_pause) if saved_pause is not None else 0.7
        except (ValueError, TypeError):
            auto_advance_mgr.pause_after_voice = 0.7

        try:
            if renpy.get_screen("town_map"):
                renpy.hide_screen("town_map")
        except Exception:
            pass

    config.start_callbacks.append(_auto_on_load_reset)
    config.after_load_callbacks.append(_auto_on_load_reset)

    def _auto_interact_cleanup():
        """Garante que town_map nao fique ativo em segundo plano durante nenhum dialogo."""
        try:
            if renpy.get_screen("say") and renpy.get_screen("town_map"):
                renpy.hide_screen("town_map")
        except Exception:
            pass

    if _auto_interact_cleanup not in config.interact_callbacks:
        config.interact_callbacks.append(_auto_interact_cleanup)

    if "auto_continue_overlay" not in config.overlay_screens:
        config.overlay_screens.append("auto_continue_overlay")

    # Garante que AFM nativo do RenPy nao gere eventos concorrentes
    try:
        _preferences.afm_enable = False
    except Exception:
        pass

screen auto_continue_overlay():
    zorder 95

    # O timer e o botao SO EXISTEM DURANTE DIALOGO ATIVO (screen say)
    # NUNCA no mapa, nunca no free roam, nunca durante escolhas de menu
    if renpy.get_screen("say") and not renpy.get_screen("choice"):
        if renpy.get_screen("town_map"):
            timer 0.01 action Hide("town_map")

        timer 0.05 repeat True action Function(auto_advance_mgr.tick)

        frame:
            xpos 20
            ypos 20
            background "#000000a0"
            padding (10, 6)
            if auto_advance_mgr.enabled:
                textbutton "▶ Continuar: AUTO" action Function(auto_toggle_action) text_color "#55ff55" text_size 15 text_outlines [(1, "#000", 0, 0)]
            else:
                textbutton "⏸ Continuar: MANUAL" action Function(auto_toggle_action) text_color "#ffffff" text_size 15 text_outlines [(1, "#000", 0, 0)]
