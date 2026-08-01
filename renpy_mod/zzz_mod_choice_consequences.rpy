# Mod: consequências de escolhas + painel de variáveis (Ren'Py)
#
# ÂMBITO (define-scope):
# - Com "Mod: dicas" ligado: à direita de cada botão aparece um painel com efeitos ($)
#   ou aviso se não houver entrada no mapa. Lookup: normalização Unicode das legendas, aliases,
#   fallback por legenda e label; curados para menus com if antes dos $.
# - Painel "Stats": valores actuais de um subconjunto de variáveis (quando existem).
#
# COBERTURA (coverage):
# - Isto aplica-se a blocos menu: do jogo.
# - Dicas: zzz_mod_choice_hints_generated.rpy (extract_menu_hints.py) + CURATED_CHOICE_HINTS.
#
# Atalhos / UI: botões no quick menu - "Mod: dicas" e "Mod: stats".

default persistent.show_choice_consequences = True
default persistent.show_stats_overlay = False

init python:
    import re
    from choice_hints_core import (
        build_choice_hints,
        display_choice_caption,
        format_hint_for_display,
        lookup_choice_hint,
        normalize_caption_unicode,
    )

    def mod_norm_caption_unicode(s):
        """Alinha legendas do motor com chaves dos .rpy (apóstrofos '' → ', aspas "" → ")."""
        return normalize_caption_unicode(s)

    # Variáveis mostradas no painel (getattr seguro se ainda não existirem).
    MOD_DEBUG_VAR_NAMES = []

    # Entradas curadas; sobrescrevem o dicionário gerado quando a chave coincide.
    # Dicas automáticas: zzz_mod_choice_hints_generated.rpy (init -2).
    CURATED_CHOICE_HINTS = {}

    try:


        _gen_hints = GENERATED_CHOICE_HINTS


    except Exception:


        _gen_hints = {}


    CHOICE_HINTS = build_choice_hints(_gen_hints, CURATED_CHOICE_HINTS)





    def mod_choice_hints_register_unicode_aliases(store_dict):


        extra = {}


        for k, v in list(store_dict.items()):


            if isinstance(k, tuple) and len(k) == 2:


                lab, c = k


                nc = mod_norm_caption_unicode(c)


                if nc != c:


                    extra[(lab, nc)] = v


            elif isinstance(k, str):


                nk = mod_norm_caption_unicode(k)


                if nk != k:


                    extra[nk] = v


        store_dict.update(extra)





    mod_choice_hints_register_unicode_aliases(CHOICE_HINTS)





    def mod_normalize_menu_caption(caption):


        if caption is None:


            return ""


        if isinstance(caption, str):


            return caption


        try:


            from renpy.text.text import Text





            if isinstance(caption, Text):


                return str(caption)


        except Exception:


            pass


        return str(caption)





    def mod_choice_hints_current_label_name():


        """Nome do label (string) do script onde corre o menu. context().current é tuple na maior parte dos nós."""


        try:


            import renpy.ast as ast_mod





            ctx = renpy.game.context()


            for n in reversed(ctx.call_location_stack):


                if isinstance(n, str) and renpy.game.script.has_label(n):


                    return n


            cur = ctx.current


            if isinstance(cur, str) and renpy.game.script.has_label(cur):


                return cur


            try:


                cur_node = renpy.game.script.lookup(cur)


            except Exception:


                return None





            def block_contains_node(block, target):


                for s in block:


                    if s is target:


                        return True


                    if isinstance(s, ast_mod.Menu):


                        for _lb, _cond, blk in s.items:


                            if blk and block_contains_node(blk, target):


                                return True


                    elif getattr(s, "block", None):


                        if block_contains_node(s.block, target):


                            return True


                return False





            for k, node in renpy.game.script.namemap.items():


                if not isinstance(k, str) or not isinstance(node, ast_mod.Label):


                    continue


                if block_contains_node(node.block, cur_node):


                    return k


        except Exception:


            pass


        return None





    def mod_consequences_lookup(caption):


        """Resolve texto de consequÃªncias (não depende de persistent)."""


        try:


            cap = mod_norm_caption_unicode(mod_normalize_menu_caption(caption))


            if not cap:


                return None


            lab = mod_choice_hints_current_label_name()
            return lookup_choice_hint(CHOICE_HINTS, lab, cap)


        except Exception:


            return None





    def mod_consequences_get_hint(caption):


        if not persistent.show_choice_consequences:


            return None


        return mod_consequences_lookup(caption)





    MOD_HINT_GREEN = "#4ade80"


    MOD_HINT_RED = "#f87171"


    MOD_HINT_NEUTRAL = "#c8c8c8"





    def mod_choice_button_display_caption(caption):
        """Legenda visível no botão: remove prefixos '(Charisma: ...)', '(REQUIRED)', etc.; lookup usa caption completo."""
        return display_choice_caption(mod_normalize_menu_caption(caption))






    def _legacy_strip_requirement_segments(s):


        if not s:


            return s


        kept = []


        for seg in s.split(";"):


            seg = seg.strip()


            if not seg:


                continue


            low = seg.lower()


            if low.startswith("requer"):


                continue


            kept.append(seg)


        return "; ".join(kept) if kept else s





    def _legacy_hint_chunk_color(chunk):


        ch = chunk.strip()


        if not ch:


            return MOD_HINT_NEUTRAL


        low = ch.lower()


        if low.startswith("ramo ") or "sem vari" in low:


            return MOD_HINT_NEUTRAL


        if "-=" in ch:


            return MOD_HINT_RED


        if "+=" in ch:


            return MOD_HINT_GREEN


        if re.search(r"\s-\d+", ch) and "level" not in low:


            return MOD_HINT_RED


        if re.search(r"\s\+\d+", ch) or re.search(r"^\+\d", ch.strip()):


            return MOD_HINT_GREEN


        if "poss" in low and ("mc_exp" in low or "bonus_xp" in low):


            return MOD_HINT_GREEN


        if "bónus" in low or "bonus" in low:


            return MOD_HINT_GREEN


        if re.search(r"[=\s]-\d+\s*$", ch):


            return MOD_HINT_RED


        if re.search(r"[=\s]\+\d+\s*$", ch):


            return MOD_HINT_GREEN


        return MOD_HINT_NEUTRAL





    def mod_hint_format_for_display(raw):


        """Remove requisitos; aplica tags Ren'Py {color} verde/vermelho/neutro por fragmento."""


        return format_hint_for_display(raw)





    def mod_consequences_stats_lines():


        lines = []


        st = renpy.store


        for name in MOD_DEBUG_VAR_NAMES:


            if hasattr(st, name):


                v = getattr(st, name)


                lines.append("{} = {}".format(name, v))


        if not lines:


            lines.append("(nenhuma variável da lista ainda definida)")


        return lines





    if "consequences_stats_overlay" not in config.overlay_screens:
        config.overlay_screens.append("consequences_stats_overlay")
    if "mod_toolbar" not in config.overlay_screens:
        config.overlay_screens.append("mod_toolbar")

style consequence_hint_text is default:
    size max(15, int(gui.text_size * 0.72))
    color "#e8e8e8"
    text_align 0.0
    layout "tex"
    xmaximum 540

screen mod_choice_row(i):
    hbox:
        spacing 14
        xalign 0.5
        python:
            _caption = i.caption
            if getattr(persistent, "hintsEnabled", False) and "hint" in i.kwargs:
                _caption += " " + i.kwargs["hint"]
            
            _mod_btn_label = mod_choice_button_display_caption(_caption)
            
            _outlines = None
            if getattr(persistent, "dialogueTextOutlines", False):
                _outlines = [(2, "#000000", 0, 0)]

        textbutton "[_mod_btn_label]":
            action i.action
            style "choice_button"
            text_style "choice_button_text"
            if _outlines:
                text_outlines _outlines

        if persistent.show_choice_consequences:
            frame:
                padding (10, 8)
                xminimum 260
                xmaximum 560
                yminimum 36
                background Solid("#000000e0")
                vbox:
                    yalign 0.5
                    $ _lk = mod_consequences_lookup(i.caption)
                    if _lk:
                        $ _hint_fmt = mod_hint_format_for_display(_lk)
                        text "[_hint_fmt]":
                            style "consequence_hint_text"
                            substitute True
                    else:
                        text _("Sem dados (sem mapeamento para esta legenda)."):
                            style "consequence_hint_text"
                            color "#ffcc66"

screen choice(items):
    fixed:
        xfill True
        yfill True
        vbox:
            xalign 0.5
            yalign 0.88
            spacing gui.choice_spacing
            for i in items:
                use mod_choice_row(i)

screen consequences_stats_overlay():
    zorder 95
    if persistent.show_stats_overlay:
        frame:
            xpos 12
            ypos 12
            xmaximum 420
            ymaximum 340
            padding (12, 12)
            background Solid("#000000cc")
            vbox:
                spacing 6
                text _("Mod: variáveis (referência)") size gui.label_text_size
                viewport:
                    scrollbars "vertical"
                    mousewheel True
                    draggable True
                    vbox:
                        spacing 4
                        for _line in mod_consequences_stats_lines():
                            text "[_line!q]" size int(gui.text_size * 0.78)

screen mod_toolbar():
    zorder 101
    hbox:
        xalign 0.98
        yalign 0.02
        spacing 10
        textbutton _("Mod: dicas"):
            action [ToggleField(persistent, "show_choice_consequences"), Function(renpy.restart_interaction)]
            selected persistent.show_choice_consequences
            text_size 14
            background Solid("#33333399")
            hover_background Solid("#66666699")
            selected_background Solid("#22882299")
            padding (8, 4)
        textbutton _("Mod: stats"):
            action [ToggleField(persistent, "show_stats_overlay"), Function(renpy.restart_interaction)]
            selected persistent.show_stats_overlay
            text_size 14
            background Solid("#33333399")
            hover_background Solid("#66666699")
            selected_background Solid("#22882299")
            padding (8, 4)


