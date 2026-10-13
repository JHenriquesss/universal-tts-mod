import ctypes
import io
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.dont_write_bytecode = True

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FALCOM_MOD_DIR = os.path.join(ROOT_DIR, "falcom_mod")
RENPY_MOD_DIR = os.path.join(ROOT_DIR, "renpy_mod")

for p in (FALCOM_MOD_DIR, RENPY_MOD_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)


class TestFalcomTextHook(unittest.TestCase):
    """
    Testes para o hook e processador de texto da Falcom.
    """

    def test_hook_cleans_and_formats_dialogue(self):
        from falcom_text_hook import FalcomTextHook

        hook = FalcomTextHook(host="127.0.0.1", port=5050)
        raw_text = "#0CEstelle#0C\n#1KJoshua, are we ready to leave for Bose?"
        processed = hook.process_raw_text(raw_text)

        self.assertNotIn("#0C", processed)
        self.assertNotIn("#1K", processed)
        self.assertIn("Estelle", processed)
        self.assertIn("Joshua, are we ready to leave for Bose?", processed)

    def test_hook_cleans_textractor_control_markers_and_restores_sentence_gap(self):
        from falcom_text_hook import FalcomTextHook

        hook = FalcomTextHook(host="127.0.0.1", port=5050)
        raw_text = "##Ahh, ka-zing. Read like a book!A children's book, at that!"

        self.assertEqual(
            hook.process_raw_text(raw_text),
            "Ahh, ka-zing. Read like a book! A children's book, at that!",
        )

    def test_hook_collapses_textractor_suffix_replays_from_full_string_hook(self):
        from falcom_text_hook import FalcomTextHook

        hook = FalcomTextHook(host="127.0.0.1", port=5050)
        raw_text = (
            "#1061F#4PPerfect, perfect. Thanks!#1060FSo anyway, the thing "
            "we discussed earlier.Mind showing it to me? It's down here, right?"
            "#4PPerfect, perfect. Thanks!#1060FSo anyway, the thing we discussed "
            "earlier.Mind showing it to me? It's down here, right?"
            "#1060FSo anyway, the thing we discussed earlier.Mind showing it to me? "
            "It's down here, right?"
        )

        self.assertEqual(
            hook.process_raw_text(raw_text),
            "Perfect, perfect. Thanks!",
        )

    def test_hook_keeps_only_current_page_before_future_portrait_tag(self):
        from falcom_text_hook import FalcomTextHook

        hook = FalcomTextHook(host="127.0.0.1", port=5050)
        raw_text = (
            "#5P#1060FPhewwwww! Being on an airship for over half a day is tiring, huh?"
            "#1061FI know how to stretch our legs, though."
            "#1062FLet's go report the completion of our training!"
        )

        self.assertEqual(
            hook.process_raw_text(raw_text),
            "Phewwwww! Being on an airship for over half a day is tiring, huh?",
        )

    def test_textractor_burst_emits_first_page_then_waits_for_next_idle_gap(self):
        from falcom_text_hook import FalcomTextHook

        hook = FalcomTextHook(
            host="127.0.0.1",
            port=5050,
            textractor_burst_gap=0.4,
        )
        first_block = (
            "#1060FCurrent box.#1061FFuture box that has not appeared yet."
        )

        self.assertEqual(
            hook.observe_textractor_capture(first_block, now=1.0),
            "Current box.",
        )
        self.assertIsNone(
            hook.observe_textractor_capture(
                "#1061FFuture box that has not appeared yet.",
                now=1.05,
            )
        )
        self.assertIsNone(
            hook.observe_textractor_capture(
                "box that has not appeared yet.",
                now=1.10,
            )
        )
        self.assertEqual(
            hook.observe_textractor_capture(
                "#1061FFuture box that has not appeared yet.",
                now=1.60,
            ),
            "Future box that has not appeared yet.",
        )

    def test_new_burst_skips_previous_page_and_releases_next_page(self):
        from falcom_text_hook import FalcomTextHook

        hook = FalcomTextHook(
            host="127.0.0.1",
            port=5050,
            textractor_burst_gap=0.4,
        )
        hook.last_sent_text = "Current box."
        hook.history.append("Current box.")

        self.assertIsNone(
            hook.observe_textractor_capture(
                "#1060FCurrent box.#1061FNext box.",
                now=2.0,
            )
        )
        self.assertIsNone(
            hook.observe_textractor_capture("rent box.", now=2.01)
        )
        self.assertEqual(
            hook.observe_textractor_capture("#1061FNext box.", now=2.02),
            "Next box.",
        )

    def test_hook_ignores_repetitive_typewriter_chunks(self):
        from falcom_text_hook import FalcomTextHook

        hook = FalcomTextHook(host="127.0.0.1", port=5050)
        step1 = hook.should_send("Joshua, are we")
        step2 = hook.should_send("Joshua, are we ready")
        step3 = "Joshua, are we ready to leave for Bose?"
        self.assertTrue(step1)
        self.assertTrue(step2)
        self.assertTrue(hook.should_send(step3))

        # Ao enviar a frase completa
        hook.last_sent_text = step3
        hook.history.append(step3)

        # Repetição idêntica imediata deve ser ignorada
        self.assertFalse(hook.should_send(step3))

    def test_hook_ignores_empty_or_system_strings(self):
        from falcom_text_hook import FalcomTextHook

        hook = FalcomTextHook(host="127.0.0.1", port=5050)
        self.assertFalse(hook.is_valid_dialogue(""))
        self.assertFalse(hook.is_valid_dialogue("   "))
        self.assertFalse(hook.is_valid_dialogue("12345"))
        self.assertFalse(hook.is_valid_dialogue("Save"))
        self.assertFalse(hook.is_valid_dialogue("Load"))
        self.assertTrue(hook.is_valid_dialogue("Estelle: We need to hurry!"))

    def test_hook_rejects_resource_and_win32_noise_seen_in_live_sc(self):
        from falcom_text_hook import FalcomTextHook

        hook = FalcomTextHook(host="127.0.0.1", port=5050)
        observed_noise = (
            "#32772",
            "Static",
            "ComboLBox",
            r"\\?\USBID_046D&PID_0AB1&MI_00#7&154E9B5D&0&0000#\GLOBAL",
            "CH20000 ._CH",
            "BATTLE ._CH",
            "Frame_SCENE_ROOT",
            "DDS |",
        )

        for text in observed_noise:
            self.assertFalse(hook.is_valid_dialogue(text), text)

        self.assertTrue(hook.is_valid_dialogue("Agate: What are you doing here?"))

    def test_hook_sends_payload_over_socket(self):
        from falcom_text_hook import FalcomTextHook

        hook = FalcomTextHook(host="127.0.0.1", port=5050)
        mock_socket = MagicMock()
        hook.socket = mock_socket

        hook.send_text("Estelle: Let's go!")

        # Deve enviar comando STOP seguido do texto
        calls = [c[0][0] for c in mock_socket.sendall.call_args_list]
        combined = b"".join(calls).decode("utf-8")
        self.assertIn("STOP\n", combined)
        self.assertIn("Estelle: Let's go!\n", combined)

    def test_extract_dialogue_from_raw_memory_buffer(self):
        from falcom_text_hook import FalcomTextHook

        hook = FalcomTextHook(host="127.0.0.1", port=5050)
        # Buffer de memória simulando a área de diálogo do jogo
        memory_chunk = (
            b"\x00\x00\x00\x00"
            b"#0CFather Kevin#0C\x00\x00\x00"
            b"#1KAi-diiios, that was one heck of a trip!#1K\x00"
            b"\x00\x00\x00\x00"
        )
        dialogues = hook.extract_dialogues_from_buffer(memory_chunk)
        self.assertGreaterEqual(len(dialogues), 1)
        combined = " ".join(dialogues)
        self.assertIn("Ai-diiios, that was one heck of a trip!", combined)

    def test_process_names_filter(self):
        from falcom_text_hook import FalcomTextHook

        hook = FalcomTextHook(host="127.0.0.1", port=5050)
        self.assertTrue(hook.is_target_process("ed6_win2_DX9.exe"))
        self.assertTrue(hook.is_target_process("ed6_win2.exe"))
        self.assertTrue(hook.is_target_process("ED6_WIN.EXE"))
        self.assertFalse(hook.is_target_process("notepad.exe"))

    @unittest.skipUnless(os.name == "nt", "Win32 API contract")
    def test_hook_configures_pointer_sized_win32_handles(self):
        from ctypes import wintypes
        from falcom_text_hook import FalcomTextHook

        hook = FalcomTextHook(host="127.0.0.1", port=5050)

        self.assertIs(hook.k32.CreateToolhelp32Snapshot.restype, wintypes.HANDLE)
        self.assertIs(hook.k32.OpenProcess.restype, wintypes.HANDLE)
        self.assertIs(hook.u32.GetClipboardData.restype, wintypes.HANDLE)
        self.assertIs(hook.k32.GlobalLock.restype, wintypes.LPVOID)

    def test_clipboard_reader_locks_and_unlocks_global_memory(self):
        from falcom_text_hook import FalcomTextHook

        class FakeUser32:
            def __init__(self, clipboard_handle):
                self.clipboard_handle = clipboard_handle
                self.closed = False

            def OpenClipboard(self, _owner):
                return True

            def GetClipboardData(self, _format):
                return self.clipboard_handle

            def CloseClipboard(self):
                self.closed = True

        class FakeKernel32:
            def __init__(self, text_buffer):
                self.text_buffer = text_buffer
                self.locked = []
                self.unlocked = []

            def GlobalLock(self, handle):
                self.locked.append(handle)
                return ctypes.addressof(self.text_buffer)

            def GlobalUnlock(self, handle):
                self.unlocked.append(handle)
                return True

        text_buffer = ctypes.create_unicode_buffer("Estelle: We should hurry!")
        clipboard_handle = ctypes.addressof(text_buffer)
        user32 = FakeUser32(clipboard_handle)
        kernel32 = FakeKernel32(text_buffer)
        hook = FalcomTextHook(host="127.0.0.1", port=5050)
        hook.u32 = user32
        hook.k32 = kernel32
        hook.should_send = lambda _text: False

        hook.check_clipboard()

        self.assertEqual(kernel32.locked, [clipboard_handle])
        self.assertEqual(kernel32.unlocked, [clipboard_handle])
        self.assertTrue(user32.closed)
        self.assertEqual(hook.last_clipboard_text, "Estelle: We should hurry!")

    def test_clipboard_only_loop_never_scans_or_opens_game_memory(self):
        from falcom_text_hook import FalcomTextHook

        hook = FalcomTextHook(host="127.0.0.1", port=5050)
        hook.connect = MagicMock(return_value=True)
        hook.check_clipboard = MagicMock(return_value=None)
        hook.find_target_process = MagicMock(
            side_effect=AssertionError("clipboard-only must not inspect game processes")
        )

        with patch("falcom_text_hook.time.sleep"):
            hook.monitor_clipboard_loop(poll_interval=0, max_cycles=2)

        self.assertEqual(
            hook.check_clipboard.call_args_list,
            [unittest.mock.call(send=False), unittest.mock.call(), unittest.mock.call()],
        )
        hook.find_target_process.assert_not_called()

    def test_cli_accepts_clipboard_only_mode(self):
        from falcom_text_hook import build_arg_parser

        args = build_arg_parser().parse_args(["--clipboard-only"])

        self.assertTrue(args.clipboard_only)

    def test_cli_accepts_private_textractor_pipe_mode(self):
        from falcom_text_hook import build_arg_parser

        args = build_arg_parser().parse_args(
            [
                "--textractor-cli", r"C:\\TTS\\TextractorCLI.exe",
                "--pid", "4321",
                "--hook-code", "HSFN932#4@12F4E0:ed6_win2_DX9.exe",
            ]
        )

        self.assertEqual(args.pid, 4321)
        self.assertIn("TextractorCLI.exe", args.textractor_cli)
        self.assertTrue(args.hook_code.startswith("HSFN932#4@"))

    def test_private_textractor_pipe_ignores_clipboard_and_other_threads(self):
        from falcom_text_hook import FalcomTextHook

        expected_hook = "HSFN932#4@12F4E0:ed6_win2_DX9.exe"
        cli_output = (
            "Usage: {'attach'|'detach'|hookcode} -Pprocessid\n"
            "[0:5B00:0:0:0:Console:HB0@0] Textractor: pipe connected\n"
            "[2:5B00:52FA8C:0:0:Wrong:HSN932#-20@12FA8C:ed6_win2_DX9.exe] browser text\n"
            f"[3:5B00:52F4E0:0:0:Dialogue:{expected_hook}] "
            "#1060FCurrent box.#1061FFuture box that is not visible.\n"
            f"[3:5B00:52F4E0:0:0:Dialogue:{expected_hook}] "
            "#1061FFuture box that is not visible.\n"
            f"[3:5B00:52F4E0:0:0:Dialogue:{expected_hook}] "
            "box that is not visible.\n"
        ).encode("utf-16-le")

        process = MagicMock()
        process.stdin = io.BytesIO()
        process.stdout = io.BytesIO(cli_output)
        process.poll.return_value = None
        hook = FalcomTextHook(host="127.0.0.1", port=5050)
        tts_socket = MagicMock()
        hook.socket = tts_socket
        hook.is_connected = True
        hook.check_clipboard = MagicMock(
            side_effect=AssertionError("private pipe must never read the global clipboard")
        )

        hook.monitor_textractor_cli(
            r"C:\\TTS\\TextractorCLI.exe",
            23296,
            expected_hook,
            popen_factory=MagicMock(return_value=process),
        )

        payload = b"".join(
            call.args[0] for call in tts_socket.sendall.call_args_list
        ).decode("utf-8")
        commands = process.stdin.getvalue().decode("utf-16-le")
        self.assertIn("attach -P23296", commands)
        self.assertIn(f"{expected_hook} -P23296", commands)
        self.assertIn("Current box.", payload)
        self.assertNotIn("Future box", payload)
        self.assertNotIn("browser text", payload)
        hook.check_clipboard.assert_not_called()

    def test_large_memory_region_is_split_without_skipping_the_tail(self):
        from falcom_text_hook import FalcomTextHook

        hook = FalcomTextHook(host="127.0.0.1", port=5050)
        chunks = list(hook.iter_region_chunks(0x1000, 600 * 1024, 256 * 1024))

        self.assertEqual(
            chunks,
            [
                (0x1000, 256 * 1024),
                (0x41000, 256 * 1024),
                (0x81000, 88 * 1024),
            ],
        )

    def test_memory_tracker_ignores_baseline_and_returns_only_changed_dialogue(self):
        from falcom_text_hook import FalcomTextHook

        hook = FalcomTextHook(host="127.0.0.1", port=5050)
        address = 0x81000
        baseline = b"Static\x00BATTLE ._CH\x00"
        changed = b"#0CAgate#0C\x00What are you doing here?#1K\x00"

        self.assertEqual(hook.dialogues_from_changed_chunk(address, baseline), [])
        self.assertEqual(hook.dialogues_from_changed_chunk(address, baseline), [])
        self.assertIn(
            "What are you doing here?",
            " ".join(hook.dialogues_from_changed_chunk(address, changed)),
        )

    def test_candidate_waits_for_typewriter_text_to_stabilize(self):
        from falcom_text_hook import FalcomTextHook

        hook = FalcomTextHook(host="127.0.0.1", port=5050, settle_seconds=0.35)

        self.assertIsNone(hook.observe_dialogue_candidate("Agate: What are you", now=1.0))
        self.assertIsNone(hook.observe_dialogue_candidate("Agate: What are you doing here?", now=1.2))
        self.assertIsNone(hook.observe_dialogue_candidate(None, now=1.4))
        self.assertEqual(
            hook.observe_dialogue_candidate(None, now=1.56),
            "Agate: What are you doing here?",
        )

    def test_resolve_falcom_voice_by_name_and_portrait(self):
        from falcom_text_hook import resolve_falcom_voice

        # Nome entre tags Falcom #0C
        self.assertEqual(resolve_falcom_voice("#0CEstelle#0C\nWait for me!"), "af_heart")
        self.assertEqual(resolve_falcom_voice("#0CFather Kevin#0C\nAi-diiios!"), "am_michael")
        self.assertEqual(resolve_falcom_voice("#0CAnelace#0C\nLet's train!"), "af_nicole")
        self.assertEqual(resolve_falcom_voice("#0CScherazard#0C\nListen up!"), "af_sarah")

        # Nome entre colchetes [Nome]
        self.assertEqual(resolve_falcom_voice("[Joshua]\nReady when you are."), "am_adam")
        self.assertEqual(resolve_falcom_voice("[Cassius]\nStay sharp, Estelle."), "am_eric")

        # Prefixo de fala Nome:
        self.assertEqual(resolve_falcom_voice("Agate: What are you doing here?"), "am_onyx")
        self.assertEqual(resolve_falcom_voice("Olivier: Ah, my sweet muse!"), "am_fenrir")
        self.assertEqual(resolve_falcom_voice("Kloe: It's good to see you."), "af_sky")
        self.assertEqual(resolve_falcom_voice("Tita: Estelle! Joshua!"), "af_bella")

        # Auto-apresentação (original e fonética gerada pelo text_cleaner)
        self.assertEqual(
            resolve_falcom_voice("I, Estelle Bright, hereby recognize you as my rival!"),
            "af_heart",
        )
        self.assertEqual(
            resolve_falcom_voice("I, Eh-stell Bright, hereby recognize you as my rival!"),
            "af_heart",
        )

        # Retrato #...F
        self.assertEqual(resolve_falcom_voice("#1060FCurrent box."), "af_bella")

        # Sem tags nem nome: fallback padrão seguro, nunca None
        self.assertEqual(
            resolve_falcom_voice("This is the final boarding call for the Cecilia, bound for Rolent."),
            "af_heart",
        )

    def test_keep_current_textractor_page_preserves_mid_sentence_expression_and_ellipses(self):
        from falcom_text_hook import FalcomTextHook

        hook = FalcomTextHook(host="127.0.0.1", port=5050)

        # Mudança de expressão facial no meio de uma oração sem pontuação não deve ser cortada
        mid_expr = "#0FI was thinking about that #2Fyesterday evening."
        self.assertEqual(
            hook.process_raw_text(mid_expr),
            "I was thinking about that yesterday evening.",
        )

        # Pausa com reticências (...) seguida de expressão não deve ser cortada prematuramente
        ellipsis_expr = "#0Fhas not been severed... #2Fyet."
        self.assertEqual(
            hook.process_raw_text(ellipsis_expr),
            "has not been severed... yet.",
        )

        # Pausa antes de exclamativa
        pause_shout = "#0FWait... #2FAre you serious?!"
        self.assertEqual(
            hook.process_raw_text(pause_shout),
            "Wait... Are you serious?!",
        )

    def test_send_text_always_sends_set_voice(self):
        from falcom_text_hook import FalcomTextHook

        hook = FalcomTextHook(host="127.0.0.1", port=5050)
        mock_socket = MagicMock()
        hook.socket = mock_socket

        # Sem voz especificada: deve resolver e enviar SET_VOICE automaticamente
        hook.send_text("Agate: What are you doing here?")
        calls = [c[0][0] for c in mock_socket.sendall.call_args_list]
        combined = b"".join(calls).decode("utf-8")
        self.assertIn("SET_VOICE:am_onyx\n", combined)
        self.assertIn("STOP\n", combined)

        # Texto neutro sem locutor: deve enviar SET_VOICE:af_heart para nunca herdar voz anterior
        mock_socket.reset_mock()
        hook.send_text("This is the airport announcement.")
        calls = [c[0][0] for c in mock_socket.sendall.call_args_list]
        combined = b"".join(calls).decode("utf-8")
        self.assertIn("SET_VOICE:af_heart\n", combined)
        self.assertIn("STOP\n", combined)

    def test_speed_control_increase_decrease_and_clamping(self):
        import tempfile
        from falcom_text_hook import FalcomTextHook

        with tempfile.TemporaryDirectory() as tmpdir:
            hook = FalcomTextHook(host="127.0.0.1", port=5050, speed=1.25, base_dir=tmpdir)
            mock_socket = MagicMock()
            hook.socket = mock_socket
            hook.is_connected = True

            # Aumentar velocidade
            new_speed = hook.increase_speed(0.1)
            self.assertEqual(new_speed, 1.35)
            self.assertEqual(hook.speed, 1.35)
            mock_socket.sendall.assert_called_with(b"SET_SPEED:1.35\n")

            # Diminuir velocidade
            mock_socket.reset_mock()
            new_speed = hook.decrease_speed(0.2)
            self.assertEqual(new_speed, 1.15)
            self.assertEqual(hook.speed, 1.15)
            mock_socket.sendall.assert_called_with(b"SET_SPEED:1.15\n")

            # Limite máximo (3.0x)
            hook.set_speed(2.95)
            self.assertEqual(hook.increase_speed(0.2), 3.0)

            # Limite mínimo (0.5x)
            hook.set_speed(0.55)
            self.assertEqual(hook.decrease_speed(0.2), 0.5)

    def test_speed_persists_in_config_file(self):
        import tempfile
        from falcom_text_hook import FalcomTextHook

        with tempfile.TemporaryDirectory() as tmpdir:
            hook1 = FalcomTextHook(host="127.0.0.1", port=5050, base_dir=tmpdir)
            hook1.set_speed(1.4)

            # Novo hook na mesma pasta deve carregar velocidade automaticamente
            hook2 = FalcomTextHook(host="127.0.0.1", port=5050, base_dir=tmpdir)
            self.assertEqual(hook2.speed, 1.4)

    def test_cli_accepts_speed_argument(self):
        from falcom_text_hook import build_arg_parser

        args = build_arg_parser().parse_args(["--speed", "1.45"])
        self.assertEqual(args.speed, 1.45)

    def test_hook_loads_port_from_config_file(self):
        import json
        import tempfile
        from falcom_text_hook import FalcomTextHook

        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_path = os.path.join(tmpdir, "tts_config.json")
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump({"port": 5055}, f)
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("TTS_PORT", None)
                hook = FalcomTextHook(base_dir=tmpdir)
                self.assertEqual(hook.port, 5055)

    def test_hook_cli_accepts_port_argument(self):
        from falcom_text_hook import build_arg_parser

        args = build_arg_parser().parse_args(["--port", "5055"])
        self.assertEqual(args.port, 5055)

    def test_hook_preserves_port_and_custom_keys_on_set_speed(self):
        import json
        import tempfile
        from falcom_text_hook import FalcomTextHook

        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_path = os.path.join(tmpdir, "tts_config.json")
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump({"port": 5055, "custom_setting": True}, f)

            hook = FalcomTextHook(base_dir=tmpdir)
            hook.set_speed(1.35)

            with open(cfg_path, "r", encoding="utf-8") as f:
                saved = json.load(f)
            self.assertEqual(saved.get("port"), 5055)
            self.assertEqual(saved.get("custom_setting"), True)
            self.assertEqual(saved.get("speed"), 1.35)

    def test_voice_for_face_id_and_modular_voice_map(self):
        from falcom_voice_map import (
            CHARACTER_NAME_VOICE_MAP,
            PORTRAIT_VOICE_MAP,
            resolve_falcom_voice,
            voice_for_face_id,
        )

        self.assertIsNone(voice_for_face_id(None))
        self.assertEqual(voice_for_face_id(0), "af_heart")
        self.assertEqual(voice_for_face_id(1005), "af_heart")
        self.assertEqual(voice_for_face_id(1035), "am_fenrir")
        self.assertEqual(voice_for_face_id(1042), "af_sky")
        self.assertEqual(voice_for_face_id(1065), "af_bella")
        self.assertEqual(voice_for_face_id(552), "am_onyx")
        self.assertEqual(voice_for_face_id(495), "am_adam")
        self.assertEqual(voice_for_face_id(152), "af_bella")
        self.assertEqual(voice_for_face_id(215), "af_sarah")
        self.assertEqual(voice_for_face_id(705), "af_sarah")
        self.assertIn("estelle", CHARACTER_NAME_VOICE_MAP)
        self.assertIn(0, PORTRAIT_VOICE_MAP)


if __name__ == "__main__":
    unittest.main()


