import os
import sys
import unittest
import numpy as np

sys.dont_write_bytecode = True

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RENPY_MOD_DIR = os.path.join(ROOT_DIR, "renpy_mod")
FALCOM_MOD_DIR = os.path.join(ROOT_DIR, "falcom_mod")

for p in (FALCOM_MOD_DIR, RENPY_MOD_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from text_cleaner import TextCleaner
from falcom_text_hook import FalcomTextHook, voice_for_face_id, PORTRAIT_VOICE_MAP
from tts_engines import KokoroEngine, get_tts_engine


class TestTtsCacheAndMultiVoice(unittest.TestCase):
    def test_extract_face_id(self):
        self.assertEqual(TextCleaner.extract_face_id("#0FEstelle"), 0)
        self.assertEqual(TextCleaner.extract_face_id("#1060FSome dialogue"), 1060)
        self.assertEqual(TextCleaner.extract_face_id("#15FJoshua"), 15)
        self.assertIsNone(TextCleaner.extract_face_id("Plain dialogue without face"))

    def test_voice_for_face_id_mapping(self):
        self.assertEqual(voice_for_face_id(0), "af_heart")      # Estelle FC
        self.assertEqual(voice_for_face_id(1001), "af_heart")   # Estelle SC
        self.assertEqual(voice_for_face_id(1015), "af_heart")   # Estelle SC expression (previously misidentified as male)
        self.assertEqual(voice_for_face_id(1025), "af_heart")   # Estelle SC expression
        self.assertEqual(voice_for_face_id(10), "am_adam")      # Joshua FC
        self.assertEqual(voice_for_face_id(594), "am_adam")     # Joshua SC
        self.assertEqual(voice_for_face_id(30), "am_fenrir")    # Olivier
        self.assertEqual(voice_for_face_id(1035), "am_fenrir")  # Olivier SC
        self.assertEqual(voice_for_face_id(50), "am_onyx")      # Agate
        self.assertEqual(voice_for_face_id(551), "am_onyx")     # Agate SC
        self.assertEqual(voice_for_face_id(60), "af_bella")     # Tita
        self.assertEqual(voice_for_face_id(1060), "af_bella")   # Tita SC
        self.assertIsNone(voice_for_face_id(None))   # None preserves default/narrator voice

    def test_duplicate_or_fragment_detection(self):
        hook = FalcomTextHook(host="127.0.0.1", port=5050)
        hook.last_sent_text = "We should hurry to the Rolent branch right now."
        hook.history.append("We should hurry to the Rolent branch right now.")

        # Exact match is duplicate
        self.assertTrue(hook.is_duplicate_or_fragment("We should hurry to the Rolent branch right now."))
        # Substring / slice is duplicate
        self.assertTrue(hook.is_duplicate_or_fragment("hurry to the Rolent branch right now."))
        # Suffix is duplicate
        self.assertTrue(hook.is_duplicate_or_fragment("branch right now."))
        # Different dialogue is not duplicate
        self.assertFalse(hook.is_duplicate_or_fragment("Joshua, are you ready?"))

    def test_kokoro_cache_key_and_storage(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Instantiate dummy engine without calling KPipeline
            original_init = KokoroEngine.__init__
            KokoroEngine.__init__ = lambda self: setattr(self, 'cache_dir', tmp_dir) or None
            try:
                engine = KokoroEngine()
                key = engine._get_cache_key("Testing dialogue cache.", voice="af_heart", speed=1.0)
                self.assertIsInstance(key, str)
                self.assertEqual(len(key), 32)

                # Not yet cached
                self.assertIsNone(engine._get_from_cache(key))

                # Save audio array
                fake_audio = np.array([0.1, 0.2, 0.3], dtype=np.float32)
                engine._save_to_cache(key, fake_audio)

                # Retrieve from cache
                cached = engine._get_from_cache(key)
                self.assertIsNotNone(cached)
                self.assertTrue(np.allclose(fake_audio, cached))
            finally:
                KokoroEngine.__init__ = original_init

    def test_kokoro_clean_cache(self):
        import tempfile
        import time
        with tempfile.TemporaryDirectory() as tmp_dir:
            original_init = KokoroEngine.__init__
            KokoroEngine.__init__ = lambda self: setattr(self, 'cache_dir', tmp_dir) or None
            try:
                engine = KokoroEngine()
                # Create 5 cache files with staged timestamps
                for i in range(5):
                    fpath = os.path.join(tmp_dir, f"file_{i}.npy")
                    with open(fpath, "wb") as f:
                        f.write(b"0" * 1024)
                    os.utime(fpath, (time.time() - (5 - i) * 10, time.time() - (5 - i) * 10))

                # Create a non-cache file that should not be touched
                keep_path = os.path.join(tmp_dir, "notes.txt")
                with open(keep_path, "w") as f:
                    f.write("important notes")

                # Clean cache to max 3 files
                removed = engine.clean_cache(max_files=3, max_size_mb=100)
                self.assertEqual(removed, 2)
                self.assertTrue(os.path.exists(keep_path))
                self.assertTrue(os.path.exists(os.path.join(tmp_dir, "file_4.npy")))
                self.assertTrue(os.path.exists(os.path.join(tmp_dir, "file_3.npy")))
                self.assertTrue(os.path.exists(os.path.join(tmp_dir, "file_2.npy")))
                self.assertFalse(os.path.exists(os.path.join(tmp_dir, "file_0.npy")))
                self.assertFalse(os.path.exists(os.path.join(tmp_dir, "file_1.npy")))
            finally:
                KokoroEngine.__init__ = original_init

    def test_get_tts_engine_factory_function(self):
        import tts_engines
        self.assertTrue(callable(tts_engines.get_tts_engine))

    def test_kokoro_engine_single_stop_method_and_queue_drain(self):
        import queue
        import re
        with open(os.path.join(RENPY_MOD_DIR, "tts_engines.py"), "r", encoding="utf-8") as f:
            source = f.read()
        kokoro_body = source.split("class KokoroEngine", 1)[1].split("def get_tts_engine", 1)[0]
        stop_defs = re.findall(r"(?m)^\s{4}def stop\(self\):", kokoro_body)
        self.assertEqual(len(stop_defs), 1, "KokoroEngine must not define duplicate stop(self) methods")

        original_init = KokoroEngine.__init__
        KokoroEngine.__init__ = lambda self: None
        try:
            engine = KokoroEngine()
            engine.audio_queue = queue.Queue()
            engine.stop_flag = False
            engine.audio_queue.put("chunk1")
            engine.audio_queue.put("chunk2")

            engine.stop()

            self.assertTrue(engine.stop_flag)
            # Only the single "STOP" sentinel should remain as an unfinished task
            self.assertEqual(engine.audio_queue.unfinished_tasks, 1)
            self.assertEqual(engine.audio_queue.get_nowait(), "STOP")
        finally:
            KokoroEngine.__init__ = original_init

    def test_falcom_speedhack_toggle_logic(self):
        from falcom_mod.falcom_text_hook import FalcomTextHook
        hook = FalcomTextHook()
        self.assertFalse(hook.speedhack_enabled)
        self.assertIn((0x4cb009, b"\x74\x33", b"\x90\x90"), hook.TURBO_PATCHES)
        self.assertIn((0x42366e, b"\x74\x41", b"\x90\x90"), hook.TURBO_PATCHES)

        fake_memory = {addr: bytearray(orig) for addr, orig, _ in hook.TURBO_PATCHES}
        class MockK32:
            def OpenProcess(self, access, inherit, pid):
                return 1234
            def CloseHandle(self, handle):
                return 1
            def VirtualProtectEx(self, handle, addr, size, prot, old_prot):
                return 1
            def ReadProcessMemory(self, handle, addr, buf, size, n_read):
                addr_int = addr.value if hasattr(addr, 'value') else addr
                val = fake_memory.get(addr_int, b"")
                for i in range(min(size, len(val))):
                    buf[i] = val[i]
                return 1
            def WriteProcessMemory(self, handle, addr, buf, size, n_written):
                addr_int = addr.value if hasattr(addr, 'value') else addr
                fake_memory[addr_int] = bytearray(buf[:size])
                return 1

        hook.k32 = MockK32()
        hook.target_pid = 9999

        # Toggle ON
        res = hook.toggle_speedhack()
        self.assertTrue(res)
        self.assertTrue(hook.speedhack_enabled)
        for addr, _, rep in hook.TURBO_PATCHES:
            self.assertEqual(bytes(fake_memory[addr]), rep)

        # Toggle OFF
        res = hook.toggle_speedhack()
        self.assertFalse(res)
        self.assertFalse(hook.speedhack_enabled)
        for addr, orig, _ in hook.TURBO_PATCHES:
            self.assertEqual(bytes(fake_memory[addr]), orig)

    def test_falcom_tts_toggle_logic(self):
        from falcom_mod.falcom_text_hook import FalcomTextHook
        hook = FalcomTextHook()
        self.assertTrue(hook.tts_enabled)

        # Toggle OFF (Mute)
        res = hook.toggle_tts()
        self.assertFalse(res)
        self.assertFalse(hook.tts_enabled)
        # In silent mode, send_text returns False without sending
        self.assertFalse(hook.send_text("This should not be voiced."))

        # Toggle ON (Unmute)
        res = hook.toggle_tts()
        self.assertTrue(res)
        self.assertTrue(hook.tts_enabled)

    def test_renpy_gender_aware_voice_resolution(self):
        import re
        with open(os.path.join(RENPY_MOD_DIR, "tts_mod.rpy"), "r", encoding="utf-8") as f:
            source = f.read()

        match = re.search(r"(?ms)^    def _tts_resolve_voice\(speaker=None\):\n(.*?)(?=^    def |\Z)", source)
        self.assertIsNotNone(match)
        code = "def _tts_resolve_voice(speaker=None):\n" + match.group(1)

        fake_scope = {
            "re": re,
            "TTS_VOICE": "af_heart",
            "tts_state": type("State", (), {"voice_map": {
                "player": "am_adam",
                "narrator": "am_adam",
                "default": "am_adam",
                "mia": "af_heart",
                "ava": "af_bella",
            }, "current_voice": "am_adam"}),
            "renpy": type("Renpy", (), {"store": type("Store", (), {"povname": "Carlos", "_last_say_who": "player"})}),
        }
        exec(code, fake_scope)
        resolve_func = fake_scope["_tts_resolve_voice"]

        # Protagonist / Narration tests
        self.assertEqual(resolve_func(None), "am_adam")
        self.assertEqual(resolve_func("player"), "am_adam")
        self.assertEqual(resolve_func("Player"), "am_adam")
        self.assertEqual(resolve_func("Carlos"), "am_adam")
        self.assertEqual(resolve_func("Anon"), "am_adam")
        self.assertEqual(resolve_func("MC"), "am_adam")
        self.assertEqual(resolve_func("narrator"), "am_adam")
        self.assertEqual(resolve_func("[player_name]"), "am_adam")

        # Support for player_name attribute in store
        fake_scope["renpy"].store.player_name = "Liam"
        self.assertEqual(resolve_func("Liam"), "am_adam")
        self.assertEqual(resolve_func("liam"), "am_adam")

        # Support for mcN and mcname in store / persistent
        fake_scope["renpy"].store.mcN = "Marcus"
        self.assertEqual(resolve_func("Marcus"), "am_adam")
        self.assertEqual(resolve_func("marcus"), "am_adam")

        fake_scope["renpy"].store.mcname = "Arthur"
        self.assertEqual(resolve_func("Arthur"), "am_adam")


        # Female characters test
        self.assertEqual(resolve_func("Mia"), "af_heart")
        self.assertEqual(resolve_func("mia"), "af_heart")
        self.assertEqual(resolve_func("Ava"), "af_bella")

        # Thoughts suffix resolution (should resolve to character's base voice)
        self.assertEqual(resolve_func("Mia's thoughts"), "af_heart")
        self.assertEqual(resolve_func("Mia’s thoughts"), "af_heart")
        self.assertEqual(resolve_func("Ava's thought"), "af_bella")
        self.assertEqual(resolve_func("Ava’s thought"), "af_bella")

        # Unknown female character fallback must always return a female voice
        unknown_female_voice = resolve_func("SomeGirl")
        self.assertTrue(unknown_female_voice.startswith("af_") or unknown_female_voice.startswith("bf_"))

        # Unknown male character fallback must always return a male voice
        unknown_male_voice = resolve_func("Police Officer")
        self.assertTrue(unknown_male_voice.startswith("am_") or unknown_male_voice.startswith("bm_"))
        for male_role in ("Mechanic", "Waiter", "Dentist", "Landlord", "Husband", "Bodyguard"):
            role_voice = resolve_func(male_role)
            self.assertTrue(
                role_voice.startswith("am_") or role_voice.startswith("bm_"),
                f"{male_role} should resolve to a male voice but got {role_voice}"
            )

    def test_origin_story_s2_voice_map_and_resolution(self):
        game_map_path = r"D:\Games\OriginStoryS2-0.10.1-pc\OriginStoryS2-0.10.1-pc\game\voice_map.json"
        if not os.path.exists(game_map_path):
            self.skipTest("Origin Story S2 voice_map.json not found on disk.")

        import json
        with open(game_map_path, "r", encoding="utf-8") as f:
            vmap = json.load(f)

        # Protagonist / Narrator mapped to am_onyx
        for key in ("default", "narrator", "mc", "jack", "[mc_name]", "player"):
            self.assertEqual(vmap.get(key), "am_onyx")

        # Wolf companion mapped to am_fenrir
        self.assertEqual(vmap.get("wolf"), "am_fenrir")
        self.assertEqual(vmap.get("midnight"), "am_fenrir")

        # Key female heroines / characters
        self.assertEqual(vmap.get("moonsong"), "af_nicole")
        self.assertEqual(vmap.get("amber"), "af_heart")
        self.assertEqual(vmap.get("evelyn"), "af_bella")
        self.assertEqual(vmap.get("lady steel"), "af_alloy")
        self.assertEqual(vmap.get("lake"), "af_jessica")
        self.assertEqual(vmap.get("parker"), "af_sarah")

        # Key male characters
        self.assertEqual(vmap.get("fraser"), "am_adam")
        self.assertEqual(vmap.get("miles"), "am_fenrir")
        self.assertEqual(vmap.get("todd"), "am_eric")
        self.assertEqual(vmap.get("elijah"), "am_michael")


if __name__ == "__main__":
    unittest.main()
