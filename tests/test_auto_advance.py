"""
Unit tests for the Auto-Advance (Continuar Automático) system.
Tests voice detection, unvoiced duration calculations, screen gating (map/free roam isolation),
and advance trigger safety.
"""

import time
import pytest
from unittest.mock import MagicMock, patch


class FakeStore:
    def __init__(self):
        self._last_say_what = None
        self._last_say_who = None


class FakeRenpy:
    def __init__(self):
        self._screens = {}
        self.music = MagicMock()
        self.music.is_playing.return_value = False
        self.music.get_playing.return_value = None
        self.config = MagicMock()
        self.config.skipping = False
        self.end_interaction_called = 0
        self.notifications = []
        self.events_queued = []
        self.restart_interaction_called = 0
        self.store = FakeStore()

    def get_screen(self, name):
        return self._screens.get(name)

    def set_screen(self, name, val):
        self._screens[name] = val

    def clear_screen(self, name):
        self._screens.pop(name, None)

    def hide_screen(self, name):
        self._screens.pop(name, None)

    def end_interaction(self, val):
        self.end_interaction_called += 1

    def queue_event(self, name, up=False):
        self.events_queued.append((name, up))

    def restart_interaction(self):
        self.restart_interaction_called += 1

    def notify(self, msg):
        self.notifications.append(msg)


@pytest.fixture
def fake_renpy():
    return FakeRenpy()



def test_can_auto_advance_gates(fake_renpy):
    from renpy_mod.auto_advance_core import AutoAdvanceManager

    mgr = AutoAdvanceManager(renpy_api=fake_renpy)

    # 1. Disabled by default
    mgr.enabled = False
    mgr.say_active = True
    fake_renpy.set_screen("say", object())
    assert not mgr.can_advance()

    # 2. Enabled, but not in say
    mgr.enabled = True
    mgr.say_active = False
    assert not mgr.can_advance()

    # 3. In say, say screen active -> should allow
    mgr.say_active = True
    assert mgr.can_advance()

    # 4. On town map -> MUST NOT advance
    fake_renpy.set_screen("town_map", object())
    assert not mgr.can_advance()
    fake_renpy.clear_screen("town_map")

    # 5. In free roam -> MUST NOT advance
    fake_renpy.set_screen("free_roam", object())
    assert not mgr.can_advance()
    fake_renpy.clear_screen("free_roam")

    # 6. Choice menu showing -> MUST NOT advance
    fake_renpy.set_screen("choice", object())
    assert not mgr.can_advance()
    fake_renpy.clear_screen("choice")

    # 7. Already advanced for this line -> MUST NOT advance again
    mgr.advanced = True
    assert not mgr.can_advance()


def test_voiced_dialogue_lifecycle(fake_renpy):
    from renpy_mod.auto_advance_core import AutoAdvanceManager

    mgr = AutoAdvanceManager(renpy_api=fake_renpy)
    mgr.enabled = True
    mgr.pause_after_voice = 0.5  # 500ms pause

    # Dialogue begins
    fake_renpy.set_screen("say", object())
    mgr.on_say_begin({"what": "Hello, good morning!"})

    assert mgr.say_active is True
    assert mgr.advanced is False
    assert mgr.voice_detected is False

    # First tick: voice is playing
    fake_renpy.music.is_playing.return_value = True
    mgr.tick(now=100.0)

    assert mgr.voice_detected is True
    assert mgr.voice_end_time is None
    assert fake_renpy.end_interaction_called == 0

    # Still playing at 102.0s
    mgr.tick(now=102.0)
    assert fake_renpy.end_interaction_called == 0

    # Voice stops at 103.0s
    fake_renpy.music.is_playing.return_value = False
    mgr.tick(now=103.0)
    assert mgr.voice_end_time == 103.0
    assert fake_renpy.end_interaction_called == 0

    # Pause has not elapsed yet (only 300ms elapsed)
    mgr.tick(now=103.3)
    assert fake_renpy.end_interaction_called == 0

    # Pause elapses at 103.5s (500ms elapsed)
    mgr.tick(now=103.5)
    assert mgr.advanced is True
    assert ("dismiss", False) in fake_renpy.events_queued or fake_renpy.end_interaction_called >= 1

    # Subsequent ticks on same line MUST NOT advance again
    prev_events = len(fake_renpy.events_queued)
    mgr.tick(now=103.6)
    mgr.tick(now=104.0)
    assert len(fake_renpy.events_queued) == prev_events


def test_unvoiced_dialogue_lifecycle(fake_renpy):
    from renpy_mod.auto_advance_core import AutoAdvanceManager

    mgr = AutoAdvanceManager(renpy_api=fake_renpy)
    mgr.enabled = True

    fake_renpy.set_screen("say", object())
    mgr.on_say_begin({"what": "A short thought."})  # 15 chars -> ~2.25s duration
    start = 50.0
    mgr.line_start_time = start

    fake_renpy.music.is_playing.return_value = False

    # Within grace period (< 0.35s)
    mgr.tick(now=50.2)
    assert len(fake_renpy.events_queued) == 0

    # Halfway through text duration
    mgr.tick(now=51.0)
    assert len(fake_renpy.events_queued) == 0

    # Duration elapsed
    duration = mgr.calculate_unvoiced_delay("A short thought.")
    mgr.tick(now=start + duration + 0.1)
    assert mgr.advanced is True
    assert ("dismiss", False) in fake_renpy.events_queued or fake_renpy.end_interaction_called >= 1



def test_map_navigation_is_never_interrupted(fake_renpy):
    from renpy_mod.auto_advance_core import AutoAdvanceManager

    mgr = AutoAdvanceManager(renpy_api=fake_renpy)
    mgr.enabled = True

    # Dialogue ends and player is sent to town map
    mgr.on_say_end()
    fake_renpy.clear_screen("say")
    fake_renpy.set_screen("town_map", object())

    # Ticks should do absolutely nothing
    for t in [100.0, 105.0, 110.0, 150.0]:
        mgr.tick(now=t)

    assert fake_renpy.end_interaction_called == 0
    assert fake_renpy.notifications == []


def test_toggle_auto_mode(fake_renpy):
    from renpy_mod.auto_advance_core import AutoAdvanceManager

    mgr = AutoAdvanceManager(renpy_api=fake_renpy)
    assert mgr.enabled is False

    mgr.toggle()
    assert mgr.enabled is True
    assert any("LIGADO" in n for n in fake_renpy.notifications)

    mgr.toggle()
    assert mgr.enabled is False
    assert any("DESLIGADO" in n for n in fake_renpy.notifications)


def test_exception_resilience_and_negative_inputs(fake_renpy):
    from renpy_mod.auto_advance_core import AutoAdvanceManager
    import pickle

    mgr = AutoAdvanceManager(renpy_api=fake_renpy)
    mgr.enabled = True
    mgr.say_active = True

    # Malformed kwargs on say_begin
    mgr.on_say_begin(None)
    assert mgr.current_text == ""
    mgr.on_say_begin("not a dict")
    assert mgr.current_text == ""

    # Exception in get_screen
    fake_renpy.get_screen = MagicMock(side_effect=RuntimeError("Screen engine busy"))
    assert mgr.can_advance() is False

    # Exception in music.is_playing
    fake_renpy.get_screen = lambda name: object() if name == "say" else None
    fake_renpy.music.is_playing.side_effect = RuntimeError("Audio device busy")
    # Should not raise exception
    mgr.tick(now=10.0)

    # Exception in end_interaction
    fake_renpy.music.is_playing = MagicMock(return_value=False)
    fake_renpy.end_interaction = MagicMock(side_effect=RuntimeError("Cannot end interaction"))
    mgr.line_start_time = 0.0
    mgr.tick(now=10.0)
    assert mgr.advanced is True

    # Serialization test: transient fields MUST NOT leak into unpickled state
    mgr.say_active = True
    mgr.voice_detected = True
    mgr.voice_end_time = 123.45
    pickled = pickle.dumps(mgr)
    restored = pickle.loads(pickled)

    assert restored.enabled is True
    assert restored.say_active is False
    assert restored.voice_detected is False
    assert restored.voice_end_time is None
    assert restored.advanced is True


def test_pause_adjustments(fake_renpy):
    from renpy_mod.auto_advance_core import AutoAdvanceManager

    mgr = AutoAdvanceManager(renpy_api=fake_renpy, pause_after_voice=0.7)
    mgr.increase_pause(0.2)
    assert mgr.pause_after_voice == 0.9
    assert any("0.9s" in n for n in fake_renpy.notifications)

    mgr.decrease_pause(0.5)
    assert mgr.pause_after_voice == 0.4
    assert any("0.4s" in n for n in fake_renpy.notifications)

    # Test clamping
    mgr.decrease_pause(2.0)
    assert mgr.pause_after_voice == 0.1
    mgr.increase_pause(5.0)
    assert mgr.pause_after_voice == 3.0


def test_none_and_malformed_pause_defaults(fake_renpy):
    from renpy_mod.auto_advance_core import AutoAdvanceManager
    import pickle

    # Ren'Py persistent attribute returns None if unset!
    mgr_none = AutoAdvanceManager(renpy_api=fake_renpy, pause_after_voice=None)
    assert mgr_none.pause_after_voice == 0.7

    mgr_str = AutoAdvanceManager(renpy_api=fake_renpy, pause_after_voice="invalid")
    assert mgr_str.pause_after_voice == 0.7

    # Pickle restore with None state
    state = {"enabled": None, "pause_after_voice": None}
    mgr_restored = AutoAdvanceManager(renpy_api=fake_renpy)
    mgr_restored.__setstate__(state)
    assert mgr_restored.enabled is False
    assert mgr_restored.pause_after_voice == 0.7


def test_stray_town_map_cleanup_on_say_begin(fake_renpy):
    from renpy_mod.auto_advance_core import AutoAdvanceManager

    mgr = AutoAdvanceManager(renpy_api=fake_renpy)
    mgr.enabled = True

    # Simulate town_map stuck in screen stack from a previous jump/save
    fake_renpy.set_screen("town_map", object())
    fake_renpy.set_screen("say", object())

    # Dialogue begins
    mgr.on_say_begin({"what": "Hey there, Miss Dewitt."})

    # town_map MUST be hidden by the manager to unblock cutscene and mouse clicks
    assert fake_renpy.get_screen("town_map") is None


def test_stray_town_map_cleanup_in_can_advance(fake_renpy):
    from renpy_mod.auto_advance_core import AutoAdvanceManager

    mgr = AutoAdvanceManager(renpy_api=fake_renpy)
    mgr.enabled = True
    mgr.say_active = True

    # Say screen active, but stray town_map also present
    fake_renpy.set_screen("say", object())
    fake_renpy.set_screen("town_map", object())

    # First call detects stray town_map and requests hide_screen
    assert mgr.can_advance() is False
    assert fake_renpy.get_screen("town_map") is None

    # Subsequent call now succeeds because town_map is gone
    assert mgr.can_advance() is True


def test_advance_uses_queue_event_dismiss(fake_renpy):
    from renpy_mod.auto_advance_core import AutoAdvanceManager

    mgr = AutoAdvanceManager(renpy_api=fake_renpy)
    mgr.enabled = True
    fake_renpy.set_screen("say", object())
    mgr.say_active = True
    mgr.advanced = False

    mgr.trigger_advance()

    assert mgr.advanced is True
    # queue_event("dismiss") must be called
    assert ("dismiss", False) in fake_renpy.events_queued
    # restart_interaction must be called
    assert fake_renpy.restart_interaction_called >= 1


def test_advance_reraises_end_interaction_when_no_queue_event():
    from renpy_mod.auto_advance_core import AutoAdvanceManager

    class EndInteraction(Exception):
        pass

    class MinimalRenpy:
        def __init__(self):
            self._screens = {"say": object()}
            self.config = MagicMock(skipping=False)

        def get_screen(self, name):
            return self._screens.get(name)

        def end_interaction(self, val):
            raise EndInteraction("ended")

    mini = MinimalRenpy()
    mgr = AutoAdvanceManager(renpy_api=mini)
    mgr.enabled = True
    mgr.say_active = True
    mgr.advanced = False

    # EndInteraction MUST bubble up so Ren'Py interact_core can handle it!
    with pytest.raises(EndInteraction):
        mgr.trigger_advance()


def test_say_active_recovery_from_screen_and_last_say_what(fake_renpy):
    from renpy_mod.auto_advance_core import AutoAdvanceManager

    mgr = AutoAdvanceManager(renpy_api=fake_renpy)
    mgr.enabled = True
    # Simulate loading game directly into a say statement without on_say_begin firing
    mgr.say_active = False
    mgr.advanced = True
    fake_renpy.set_screen("say", object())
    fake_renpy.store._last_say_what = "Hello after loading save."

    # Tick should detect say screen and recover state
    mgr.tick(now=10.0)

    assert mgr.say_active is True
    assert mgr.advanced is False
    assert mgr.current_text == "Hello after loading save."


def test_next_line_auto_detection_when_text_changes(fake_renpy):
    from renpy_mod.auto_advance_core import AutoAdvanceManager

    mgr = AutoAdvanceManager(renpy_api=fake_renpy)
    mgr.enabled = True
    fake_renpy.set_screen("say", object())
    fake_renpy.store._last_say_what = "Line 1"
    mgr.on_say_begin({"what": "Line 1"})
    mgr.trigger_advance()
    assert mgr.advanced is True

    # Next dialogue line appears in Ren'Py store
    fake_renpy.store._last_say_what = "Line 2 - new line!"
    mgr.tick(now=20.0)

    # Must have reset advanced state for the new line
    assert mgr.advanced is False
    assert mgr.current_text == "Line 2 - new line!"


def test_voice_detection_with_remake_voice_playing(fake_renpy):
    from renpy_mod.auto_advance_core import AutoAdvanceManager

    mgr = AutoAdvanceManager(renpy_api=fake_renpy)
    mgr.enabled = True
    fake_renpy.set_screen("say", object())
    mgr.say_active = True
    mgr.advanced = False

    # Game defines remake_voice_playing() helper
    fake_renpy.store.remake_voice_playing = MagicMock(return_value=True)

    mgr.tick(now=5.0)
    assert mgr.voice_detected is True
    assert mgr.is_voice_playing() is True


def test_toggle_during_active_say_screen(fake_renpy):
    from renpy_mod.auto_advance_core import AutoAdvanceManager

    mgr = AutoAdvanceManager(renpy_api=fake_renpy)
    mgr.enabled = False
    mgr.say_active = False
    mgr.advanced = True
    fake_renpy.set_screen("say", object())
    fake_renpy.store._last_say_what = "Currently paused line."

    # User toggles AUTO on during active dialogue
    mgr.toggle()

    assert mgr.enabled is True
    assert mgr.say_active is True
    assert mgr.advanced is False
