"""
Auto-Advance Core Controller for Ren'Py games with native voice acting.
Provides safe, dialogue-gated auto-forwarding that respects audio playback,
prevents map/free-roam interruptions, and manages clean screen transitions.
"""

import time


class AutoAdvanceManager(object):
    """
    Coordinates automatic dialogue advancement during Say interactions.
    Strictly isolated from non-dialogue screens (Map, Free Roam, Menus, Minigames).
    """

    def __init__(self, renpy_api=None, pause_after_voice=0.7):
        self.renpy = renpy_api
        self.enabled = False
        try:
            self.pause_after_voice = float(pause_after_voice) if pause_after_voice is not None else 0.7
        except (ValueError, TypeError):
            self.pause_after_voice = 0.7

        # Transient lifecycle state (reset per line & not pickled)
        self.say_active = False
        self.advanced = False
        self.voice_detected = False
        self.voice_end_time = None
        self.line_start_time = 0.0
        self.current_text = ""
        self.current_speaker = None

    def __getstate__(self):
        return {
            "enabled": getattr(self, "enabled", False),
            "pause_after_voice": getattr(self, "pause_after_voice", 0.7),
        }

    def __setstate__(self, state):
        self.enabled = bool(state.get("enabled", False) or False)
        raw_pause = state.get("pause_after_voice", 0.7)
        try:
            self.pause_after_voice = float(raw_pause) if raw_pause is not None else 0.7
        except (ValueError, TypeError):
            self.pause_after_voice = 0.7
        self.say_active = False
        self.advanced = True
        self.voice_detected = False
        self.voice_end_time = None
        self.line_start_time = 0.0
        self.current_text = ""
        self.current_speaker = None
        if not hasattr(self, "renpy"):
            self.renpy = None

    def can_advance(self) -> bool:
        """
        Airtight safety gate ensuring auto-advance only executes when dialogue is active.
        Guarantees that Map, Free Roam, Choices, and Menus are NEVER interrupted.
        """
        if not getattr(self, "enabled", False):
            return False

        if not getattr(self, "say_active", False):
            return False

        if getattr(self, "advanced", False):
            return False

        if not self.renpy:
            return False

        # Dialogue say screen MUST be present
        try:
            if self.renpy.get_screen("say") is None:
                return False
        except Exception:
            return False

        # Menu choices require player decision - do not auto-advance
        try:
            if self.renpy.get_screen("choice") is not None:
                return False
        except Exception:
            pass

        # Navigation screens: MUST NOT advance or end interaction
        for blocked_screen in ("town_map", "free_roam", "roam_hud", "main_menu", "game_menu"):
            try:
                if self.renpy.get_screen(blocked_screen) is not None:
                    if blocked_screen == "town_map" and hasattr(self.renpy, "hide_screen"):
                        self.renpy.hide_screen("town_map")
                    return False
            except Exception:
                pass

        # If Ren'Py is already skipping or fast-forwarding, let engine handle it
        try:
            if getattr(self.renpy.config, "skipping", False):
                return False
        except Exception:
            pass

        return True

    def calculate_unvoiced_delay(self, text: str) -> float:
        """
        Calculates comfortable reading time for unvoiced dialogue lines.
        Scales with character count, clamped between 2.0s and 6.0s.
        """
        length = len(str(text or "").strip())
        return max(2.0, min(6.0, (length * 0.05) + 1.5))

    def on_say_begin(self, kwargs=None):
        """Called when a dialogue line starts (via config.all_character_callbacks)."""
        self.say_active = True
        self.advanced = False
        self.voice_detected = False
        self.voice_end_time = None
        self.line_start_time = time.time()

        # Clean up any lingering modal navigation screens (like town_map) that would block dialogue
        if self.renpy and hasattr(self.renpy, "hide_screen"):
            try:
                if self.renpy.get_screen("town_map") is not None:
                    self.renpy.hide_screen("town_map")
            except Exception:
                pass

        raw_text = ""
        if kwargs and isinstance(kwargs, dict):
            for k in ("what", "text", "message"):
                val = kwargs.get(k)
                if val:
                    raw_text = val
                    break
        self.current_text = str(raw_text)

    def on_say_end(self):
        """Called when a dialogue line ends (via config.all_character_callbacks)."""
        self.say_active = False
        self.advanced = True
        self.voice_detected = False
        self.voice_end_time = None

    def toggle(self) -> bool:
        """Toggles Auto-Advance on/off with on-screen notification."""
        self.enabled = not self.enabled
        if self.enabled and self.renpy and hasattr(self.renpy, "get_screen"):
            try:
                if self.renpy.get_screen("say") is not None:
                    self.say_active = True
                    self.advanced = False
                    self.line_start_time = time.time()
                    if hasattr(self.renpy, "store") and hasattr(self.renpy.store, "_last_say_what"):
                        val = self.renpy.store._last_say_what
                        if val is not None:
                            self.current_text = str(val)
            except Exception:
                pass

        status_str = "LIGADO" if self.enabled else "DESLIGADO"
        if self.renpy and hasattr(self.renpy, "notify"):
            try:
                self.renpy.notify(f"Modo Automático: {status_str}")
            except Exception:
                pass
        return self.enabled

    def increase_pause(self, step=0.1):
        """Increases breathing pause after voice audio finishes."""
        self.pause_after_voice = round(min(3.0, self.pause_after_voice + step), 2)
        if self.renpy and hasattr(self.renpy, "notify"):
            try:
                self.renpy.notify(f"Pausa após áudio: {self.pause_after_voice:.1f}s")
            except Exception:
                pass
        return self.pause_after_voice

    def decrease_pause(self, step=0.1):
        """Decreases breathing pause after voice audio finishes."""
        self.pause_after_voice = round(max(0.1, self.pause_after_voice - step), 2)
        if self.renpy and hasattr(self.renpy, "notify"):
            try:
                self.renpy.notify(f"Pausa após áudio: {self.pause_after_voice:.1f}s")
            except Exception:
                pass
        return self.pause_after_voice

    def is_voice_playing(self) -> bool:
        """Checks if voice audio is actively playing."""
        if not self.renpy:
            return False

        # 1. Authoritative helper if defined by the game (e.g. remake_voice_playing in Summertime Saga)
        try:
            if hasattr(self.renpy, "store") and hasattr(self.renpy.store, "remake_voice_playing"):
                fn = self.renpy.store.remake_voice_playing
                if callable(fn):
                    return bool(fn())
        except Exception:
            pass

        # 2. Ren'Py music channel checking
        if hasattr(self.renpy, "music"):
            try:
                if bool(self.renpy.music.get_playing("voice")):
                    return True
            except Exception:
                pass
            try:
                if bool(self.renpy.music.is_playing("voice")):
                    return True
            except Exception:
                pass

        return False

    def trigger_advance(self):
        """Fires dialogue advance strictly within dialogue context."""
        if not self.can_advance():
            return
        self.advanced = True

        dismissed = False
        if self.renpy and hasattr(self.renpy, "queue_event"):
            try:
                self.renpy.queue_event("dismiss", up=False)
                dismissed = True
            except Exception:
                pass

        if self.renpy and hasattr(self.renpy, "restart_interaction"):
            try:
                self.renpy.restart_interaction()
            except Exception:
                pass

        if not dismissed and self.renpy and hasattr(self.renpy, "end_interaction"):
            try:
                self.renpy.end_interaction(True)
            except Exception as e:
                # If e is EndInteraction, let it bubble up to terminate interact_core
                if type(e).__name__ == "EndInteraction":
                    raise

    def tick(self, now=None):
        """
        Periodic evaluation loop (called by overlay screen timer).
        Checks voice channel playback and natural reading pauses.
        """
        if not getattr(self, "enabled", False) or not self.renpy:
            return

        current_time = time.time() if now is None else float(now)

        # Dialogue recovery: if say screen is visible, recover say_active and detect new lines
        if hasattr(self.renpy, "get_screen"):
            try:
                if self.renpy.get_screen("say") is not None:
                    # Check if line text changed in Ren'Py store
                    last_what = None
                    if hasattr(self.renpy, "store"):
                        last_what = getattr(self.renpy.store, "_last_say_what", None)

                    if last_what is not None:
                        str_what = str(last_what)
                        if str_what != self.current_text:
                            self.current_text = str_what
                            self.say_active = True
                            self.advanced = False
                            self.voice_detected = False
                            self.voice_end_time = None
                            self.line_start_time = current_time

                    if not self.say_active:
                        self.say_active = True
                        self.advanced = False
                        self.voice_detected = False
                        self.voice_end_time = None
                        self.line_start_time = current_time
                        if last_what is not None:
                            self.current_text = str(last_what)
                else:
                    self.say_active = False
                    self.voice_detected = False
                    self.voice_end_time = None
            except Exception:
                pass

        if not self.can_advance():
            return

        is_voice = self.is_voice_playing()
        if is_voice:
            self.voice_detected = True
            self.voice_end_time = None
            return

        if self.voice_detected:
            # Voice finished playing
            if self.voice_end_time is None:
                self.voice_end_time = current_time
                return

            if (current_time - self.voice_end_time) >= self.pause_after_voice:
                self.trigger_advance()
        else:
            # Unvoiced line: allow 0.35s grace for audio to begin loading
            elapsed = current_time - self.line_start_time
            if elapsed < 0.35:
                return

            delay = self.calculate_unvoiced_delay(self.current_text)
            if elapsed >= delay:
                self.trigger_advance()

