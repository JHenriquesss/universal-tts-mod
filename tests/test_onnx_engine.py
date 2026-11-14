"""Kokoro via ONNX Runtime, escolha do motor e Python do backend."""
import ntpath
import os
import sys
import tempfile
import types
import unittest
from unittest import mock

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "renpy_mod"))
import tts_engines  # noqa: E402
from tts_client_state import find_backend_python  # noqa: E402
from tts_protocol import resolve_engine_name  # noqa: E402


class FakeKokoro:
    instances = []

    def __init__(self):
        self.voices = {
            "af_heart": np.full((4,), 1.0, dtype=np.float32),
            "af_bella": np.full((4,), 3.0, dtype=np.float32),
        }
        self.calls = []

    @classmethod
    def from_session(cls, session, voices_path):
        instance = cls()
        instance.session = session
        instance.voices_path = voices_path
        FakeKokoro.instances.append(instance)
        return instance

    def get_voice_style(self, name):
        return self.voices[name]

    def create(self, text, voice, speed=1.0, lang="en-us", is_phonemes=False, trim=True):
        self.calls.append({"text": text, "voice": voice, "speed": speed, "lang": lang,
                           "is_phonemes": is_phonemes, "trim": trim})
        return np.ones(10, dtype=np.float32), 24000


class FakeG2P:
    def __call__(self, text):
        return "/" + text + "/", []


class OnnxPipelineTest(unittest.TestCase):
    def setUp(self):
        FakeKokoro.instances = []
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for name in (tts_engines.ONNX_MODEL_FILES["int8"], tts_engines.ONNX_VOICES_FILE):
            with open(os.path.join(self.tmp.name, name), "wb") as handle:
                handle.write(b"x")

        self.sessions = []
        test = self

        class FakeOptions:
            intra_op_num_threads = 0
            inter_op_num_threads = 0

        def fake_session(path, sess_options=None, providers=None):
            test.sessions.append((path, sess_options, providers))
            return object()

        fake_rt = types.ModuleType("onnxruntime")
        fake_rt.SessionOptions = FakeOptions
        fake_rt.InferenceSession = fake_session
        fake_ko = types.ModuleType("kokoro_onnx")
        fake_ko.Kokoro = FakeKokoro
        patcher = mock.patch.dict(sys.modules, {"onnxruntime": fake_rt, "kokoro_onnx": fake_ko})
        patcher.start()
        self.addCleanup(patcher.stop)
        env = mock.patch.dict(os.environ, {"TTS_THREADS": "2"})
        env.start()
        self.addCleanup(env.stop)

    def _pipeline(self, g2p="misaki", lang="a"):
        import tts_onnx_pipeline
        with mock.patch.object(tts_onnx_pipeline, "_make_misaki_g2p", lambda lang: FakeG2P() if lang in ("a", "b") else None):
            return tts_engines.OnnxPipeline(lang=lang, model="int8", g2p=g2p, onnx_dir=self.tmp.name)

    def test_session_uses_cpu_and_the_backend_thread_limit(self):
        self._pipeline()
        path, options, providers = self.sessions[0]
        self.assertTrue(path.endswith(tts_engines.ONNX_MODEL_FILES["int8"]))
        self.assertEqual(options.intra_op_num_threads, 2)
        self.assertEqual(options.inter_op_num_threads, 1)
        self.assertEqual(providers, ["CPUExecutionProvider"])

    def test_misaki_phonemes_are_sent_per_sentence_with_clamped_speed(self):
        pipe = self._pipeline()
        chunks = list(pipe("Hi there. How are you?", voice="af_heart", speed=5.0))
        calls = FakeKokoro.instances[0].calls

        self.assertEqual(len(chunks), 2)
        self.assertEqual([c["text"] for c in calls], ["/Hi there./", "/How are you?/"])
        self.assertTrue(all(c["is_phonemes"] for c in calls))
        self.assertTrue(all(c["speed"] == 2.0 for c in calls))
        self.assertTrue(all(c["trim"] is False for c in calls))

    def test_espeak_mode_and_non_english_use_espeak_language(self):
        pipe = self._pipeline(g2p="espeak")
        list(pipe("Hello.", voice="af_heart"))
        pipe.set_lang("p")
        list(pipe("Ola.", voice="af_heart"))
        calls = FakeKokoro.instances[0].calls
        self.assertEqual([(c["is_phonemes"], c["lang"]) for c in calls], [(False, "en-us"), (False, "pt-br")])

    def test_blended_and_unknown_voices(self):
        pipe = self._pipeline()
        list(pipe("Hi.", voice="af_heart,af_bella"))
        list(pipe("Hi.", voice="nope"))
        calls = FakeKokoro.instances[0].calls
        np.testing.assert_allclose(calls[0]["voice"], np.full((4,), 2.0))
        np.testing.assert_allclose(calls[1]["voice"], np.full((4,), 1.0))

    def test_missing_model_files_fail_with_clear_path(self):
        os.remove(os.path.join(self.tmp.name, tts_engines.ONNX_VOICES_FILE))
        with self.assertRaises(FileNotFoundError) as ctx:
            self._pipeline()
        self.assertIn(tts_engines.ONNX_VOICES_FILE, str(ctx.exception))


class OnnxOptionsTest(unittest.TestCase):
    def test_defaults_and_invalid_values_fall_back_to_fp32_misaki(self):
        with mock.patch.dict(os.environ, {"TTS_ONNX_MODEL": "", "TTS_ONNX_G2P": ""}):
            self.assertEqual(tts_engines.resolve_onnx_options(), ("fp32", "misaki"))
            self.assertEqual(tts_engines.resolve_onnx_options("FP32", "Espeak"), ("fp32", "espeak"))
            self.assertEqual(tts_engines.resolve_onnx_options("fp64", "x"), ("fp32", "misaki"))

    def test_onnx_dir_defaults_to_local_app_data(self):
        env = {"LOCALAPPDATA": "C:\\Users\\x\\AppData\\Local"}
        self.assertEqual(
            tts_engines.resolve_onnx_dir(env),
            os.path.join("C:\\Users\\x\\AppData\\Local", "UniversalKokoroTTS", "onnx"),
        )
        self.assertEqual(tts_engines.resolve_onnx_dir({"TTS_ONNX_DIR": " D:\\m "}), "D:\\m")


class EngineNameTest(unittest.TestCase):
    def test_only_kokoro_and_mock_exist_and_old_onnx_config_still_works(self):
        self.assertEqual(resolve_engine_name(None, None), "kokoro")
        self.assertEqual(resolve_engine_name("kokoro", "ONNX"), "kokoro")
        self.assertEqual(resolve_engine_name("kokoro", "torch"), "kokoro")
        self.assertEqual(resolve_engine_name(" Mock ", "onnx"), "mock")
        self.assertEqual(resolve_engine_name("kokoro", "mock"), "mock")


class BackendPythonTest(unittest.TestCase):
    LOCAL = "C:\\Users\\x\\AppData\\Local"

    def _find(self, existing=(), on_path=()):
        with mock.patch.object(os, "path", ntpath):
            return find_backend_python(
                {"LOCALAPPDATA": self.LOCAL},
                lambda p: p in existing,
                lambda name: name if name in on_path else None,
                "nt",
            )

    def test_dedicated_runtime_wins_over_global_python(self):
        runtime = ntpath.join(self.LOCAL, "UniversalKokoroTTS", "runtime", "Scripts", "pythonw.exe")
        self.assertEqual(self._find(existing={runtime}, on_path={"pythonw.exe"}), runtime)

    def test_falls_back_to_path_then_python312(self):
        self.assertEqual(self._find(on_path={"python.exe"}), "python.exe")
        py312 = ntpath.join(self.LOCAL, "Programs", "Python", "Python312", "python.exe")
        self.assertEqual(self._find(existing={py312}), py312)
        self.assertEqual(self._find(), "pythonw.exe")

    def test_non_windows_uses_python3(self):
        self.assertEqual(find_backend_python({}, lambda p: False, lambda n: None, "posix"), "python3")


if __name__ == "__main__":
    unittest.main()
