"""Regressao de carga, troca de idioma e ciclo efemero de cache da KokoroEngine."""
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "renpy_mod"))
import tts_engines  # noqa: E402


class FakePipeline:
    created = []

    def __init__(self, lang="a", model="fp32", g2p="misaki", onnx_dir=None):
        self.lang = lang
        self.model = model
        self.g2p_mode = g2p
        self.lang_changes = []
        self.calls = []
        FakePipeline.created.append(self)

    def set_lang(self, lang):
        self.lang_changes.append(lang)
        self.lang = lang

    def __call__(self, text, voice=None, speed=1.0, split_pattern=None):
        self.calls.append((text, voice, speed))
        yield ("gs", None, [0.1, -0.1, 0.05])


class EngineTestBase(unittest.TestCase):
    def setUp(self):
        FakePipeline.created = []
        patcher = mock.patch.object(tts_engines, "OnnxPipeline", FakePipeline)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.cache_tmp = tempfile.TemporaryDirectory()
        self.log_tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.cache_tmp.cleanup)
        self.addCleanup(self.log_tmp.cleanup)
        env = mock.patch.dict(
            os.environ,
            {
                "TTS_CACHE_DIR": self.cache_tmp.name,
                "TTS_LOG_DIR": self.log_tmp.name,
                "TTS_ONNX_MODEL": "",
                "TTS_ONNX_G2P": "",
            },
        )
        env.start()
        self.addCleanup(env.stop)

    def _make(self, **kwargs):
        with mock.patch.object(tts_engines.TTSEngine, "_cache_device"), \
                mock.patch.object(tts_engines, "trim_working_set") as trim, \
                mock.patch("threading.Thread"):
            engine = tts_engines.KokoroEngine(lang="a", **kwargs)
        return engine, trim


class EngineLoadTest(EngineTestBase):
    def test_engine_builds_one_onnx_pipeline_with_default_options_and_trims_ram(self):
        engine, trim = self._make()
        self.assertEqual(len(FakePipeline.created), 1)
        pipe = engine.pipeline
        self.assertEqual((pipe.lang, pipe.model, pipe.g2p_mode), ("a", "fp32", "misaki"))
        trim.assert_called_once()

    def test_config_options_reach_the_pipeline(self):
        engine, _ = self._make(model="int8", g2p="espeak")
        self.assertEqual((engine.pipeline.model, engine.pipeline.g2p_mode), ("int8", "espeak"))

    def test_failed_load_leaves_engine_without_pipeline_and_speak_refuses(self):
        def broken(*args, **kwargs):
            raise FileNotFoundError("Arquivo do modelo Kokoro ausente: x")

        with mock.patch.object(tts_engines, "OnnxPipeline", broken):
            engine, _ = self._make()
        self.assertIsNone(engine.pipeline)
        self.assertFalse(engine.speak("Hello."))
        self.assertFalse(engine.set_lang("p"))

    def test_module_has_no_pytorch_path(self):
        with open(tts_engines.__file__, "r", encoding="utf-8") as f:
            source = f.read()
        for leftover in ("KPipeline", "KModel", "import kokoro", "inference_mode", "TTS_DEVICE", "cuda"):
            self.assertNotIn(leftover, source)


class SetLangTest(EngineTestBase):
    def test_same_lang_is_a_no_op(self):
        engine, _ = self._make()
        self.assertTrue(engine.set_lang("a"))
        self.assertEqual(engine.pipeline.lang_changes, [])

    def test_new_lang_keeps_the_loaded_model(self):
        engine, _ = self._make()
        pipe = engine.pipeline
        self.assertTrue(engine.set_lang("p"))
        self.assertIs(engine.pipeline, pipe)
        self.assertEqual(pipe.lang_changes, ["p"])
        self.assertEqual(len(FakePipeline.created), 1)

    def test_speak_queues_float_audio_and_finish_marker(self):
        engine, _ = self._make()
        self.assertTrue(engine.speak("Hello there.", voice="af_heart", speed=1.0))
        items = []
        while not engine.audio_queue.empty():
            items.append(engine.audio_queue.get_nowait())
        self.assertEqual(items[0], "STOP")
        self.assertEqual(str(items[1].dtype), "float32")
        self.assertEqual(items[-1], "FINISH_MARKER")


class LightnessHelpersTest(unittest.TestCase):
    def test_cpu_threads_default_to_a_quarter_of_logical_cores_capped(self):
        from tts_protocol import resolve_cpu_threads

        self.assertEqual(resolve_cpu_threads(None, cpu_count=12), 3)
        self.assertEqual(resolve_cpu_threads(None, cpu_count=32), 4)
        self.assertEqual(resolve_cpu_threads(None, cpu_count=2), 1)
        self.assertEqual(resolve_cpu_threads(" 6 ", cpu_count=12), 6)
        self.assertEqual(resolve_cpu_threads("zero", cpu_count=12), 3)
        self.assertEqual(resolve_cpu_threads("0", cpu_count=12), 3)

    def test_thread_env_limits_do_not_override_user_values(self):
        from tts_protocol import apply_thread_env_limits

        env = {"MKL_NUM_THREADS": "8"}
        apply_thread_env_limits(3, environ=env)
        self.assertEqual(env["OMP_NUM_THREADS"], "3")
        self.assertEqual(env["OPENBLAS_NUM_THREADS"], "3")
        self.assertEqual(env["MKL_NUM_THREADS"], "8")

    def test_priority_can_be_kept_normal(self):
        from tts_protocol import lower_process_priority

        self.assertFalse(lower_process_priority(" Normal "))


class EphemeralCacheLifecycleTest(EngineTestBase):
    def test_kokoro_startup_deletes_existing_cache_files_and_preserves_non_cache_files(self):
        cache_dir = os.path.join(self.cache_tmp.name, ".tts_cache")
        os.makedirs(cache_dir, exist_ok=True)
        stale_npy = os.path.join(cache_dir, "stale_line.npy")
        stale_wav = os.path.join(cache_dir, "stale_line.wav")
        keep_txt = os.path.join(cache_dir, "notes.txt")
        for path in (stale_npy, stale_wav, keep_txt):
            with open(path, "wb") as handle:
                handle.write(b"payload")

        engine, _ = self._make()

        self.assertFalse(os.path.exists(stale_npy))
        self.assertFalse(os.path.exists(stale_wav))
        self.assertTrue(os.path.exists(keep_txt))
        self.assertEqual(engine.cache_dir, cache_dir)

    def test_clear_cache_dir_removes_cache_files_and_empty_folder_on_shutdown(self):
        cache_dir = os.path.join(self.cache_tmp.name, ".tts_cache")
        os.makedirs(cache_dir, exist_ok=True)
        for name in ("a.npy", "b.wav"):
            with open(os.path.join(cache_dir, name), "wb") as handle:
                handle.write(b"audio")

        removed = tts_engines.clear_cache_dir(cache_dir, remove_dir_if_empty=True)
        self.assertEqual(removed, 2)
        self.assertFalse(os.path.exists(cache_dir))

        os.makedirs(cache_dir, exist_ok=True)
        with open(os.path.join(cache_dir, "c.npy"), "wb") as handle:
            handle.write(b"audio")
        keep_txt = os.path.join(cache_dir, "keep.txt")
        with open(keep_txt, "w", encoding="utf-8") as handle:
            handle.write("do not delete")

        removed_mixed = tts_engines.clear_cache_dir(cache_dir, remove_dir_if_empty=True)
        self.assertEqual(removed_mixed, 1)
        self.assertTrue(os.path.isdir(cache_dir))
        self.assertTrue(os.path.isfile(keep_txt))

    def test_kokoro_startup_registers_atexit_cleanup_with_path_not_engine_self(self):
        cache_dir = os.path.join(self.cache_tmp.name, ".tts_cache")
        with mock.patch("atexit.register") as reg_mock, \
                mock.patch.object(tts_engines, "_REGISTERED_CACHE_DIRS", set(), create=True):
            first, _ = self._make()
            second, _ = self._make()

        self.assertEqual(reg_mock.call_count, 1)
        args, _kwargs = reg_mock.call_args
        self.assertIs(args[0], tts_engines.clear_cache_dir)
        self.assertEqual(args[1], cache_dir)
        self.assertIs(args[2], True)
        self.assertNotIn(first, args)
        self.assertNotIn(second, args)

    def test_cache_key_depends_on_model_variant_and_pronunciation(self):
        fp32, _ = self._make()
        int8, _ = self._make(model="int8")
        espeak, _ = self._make(g2p="espeak")
        keys = {e._get_cache_key("Same line.", "af_heart", 1.0) for e in (fp32, int8, espeak)}
        self.assertEqual(len(keys), 3)


if __name__ == "__main__":
    unittest.main()
