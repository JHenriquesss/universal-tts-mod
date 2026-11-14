import os
import sys

from tts_protocol import append_bounded_log, resolve_cpu_threads

DEFAULT_KOKORO_VOICE = "af_heart"

# O modelo roda no ONNX Runtime, sem PyTorch no processo: carrega mais rapido e
# usa bem menos memoria. A pronuncia em ingles vem do misaki.
ONNX_DIR_PARTS = ("UniversalKokoroTTS", "onnx")
ONNX_MODEL_FILES = {"int8": "kokoro-v1.0.int8.onnx", "fp32": "kokoro-v1.0.onnx"}
ONNX_VOICES_FILE = "voices-v1.0.bin"
ONNX_G2P_MODES = ("misaki", "espeak")
ONNX_SPEED_RANGE = (0.5, 2.0)
# Lang code do kokoro -> idioma do espeak-ng (fallback quando nao ha misaki).
ESPEAK_LANGS = {
    "a": "en-us", "b": "en-gb", "e": "es", "f": "fr-fr", "h": "hi",
    "i": "it", "p": "pt-br", "j": "ja", "z": "cmn",
}


def _log_engine(msg):
    tld = os.environ.get("TTS_LOG_DIR") or os.path.dirname(os.path.abspath(__file__))
    append_bounded_log(os.path.join(tld, "tts_server.log"), f"[ENGINE] {msg}")


def resolve_onnx_dir(environ=None):
    env = os.environ if environ is None else environ
    custom = str(env.get("TTS_ONNX_DIR", "")).strip()
    if custom:
        return custom
    return os.path.join(env.get("LOCALAPPDATA", os.path.expanduser("~")), *ONNX_DIR_PARTS)


def resolve_onnx_options(model=None, g2p=None):
    """Variante do modelo e modo de pronuncia."""
    model_key = str(model or os.environ.get("TTS_ONNX_MODEL") or "fp32").strip().lower()
    if model_key not in ONNX_MODEL_FILES:
        model_key = "fp32"
    g2p_key = str(g2p or os.environ.get("TTS_ONNX_G2P") or "misaki").strip().lower()
    if g2p_key not in ONNX_G2P_MODES:
        g2p_key = "misaki"
    return model_key, g2p_key


def _import_misaki():
    """Importa o misaki mantendo o torch fora do processo quando possivel."""
    blocked = "torch" not in sys.modules
    if blocked:
        sys.modules["torch"] = None
    try:
        from misaki import en, espeak
        return en, espeak
    except ImportError:
        if not blocked:
            raise
    finally:
        if blocked and sys.modules.get("torch", 0) is None:
            del sys.modules["torch"]
    for name in [n for n in sys.modules if n == "spacy" or n.startswith(("spacy.", "spacy_", "thinc", "misaki"))]:
        del sys.modules[name]
    _log_engine("spacy exigiu o torch: misaki carregado com o torch no processo.")
    from misaki import en, espeak
    return en, espeak


def _make_misaki_g2p(lang):
    if lang not in ("a", "b"):
        return None
    en, espeak = _import_misaki()
    british = lang == "b"
    try:
        fallback = espeak.EspeakFallback(british=british)
    except Exception as exc:
        _log_engine(f"EspeakFallback indisponivel: {exc}")
        fallback = None
    return en.G2P(trf=False, british=british, fallback=fallback, unk="")


class OnnxPipeline(object):
    """Gera o audio frase a frase: ``pipeline(text, voice, speed, split_pattern)``."""

    def __init__(self, lang="a", model="fp32", g2p="misaki", onnx_dir=None):
        import re
        import numpy as np
        import onnxruntime as rt
        from kokoro_onnx import Kokoro

        self._re = re
        self._np = np
        onnx_dir = onnx_dir or resolve_onnx_dir()
        model_path = os.path.join(onnx_dir, ONNX_MODEL_FILES[model])
        voices_path = os.path.join(onnx_dir, ONNX_VOICES_FILE)
        for path in (model_path, voices_path):
            if not os.path.isfile(path):
                raise FileNotFoundError(
                    f"Arquivo do modelo Kokoro ausente: {path}. Rode o instalar.bat para baixar o modelo."
                )

        options = rt.SessionOptions()
        options.intra_op_num_threads = resolve_cpu_threads(os.environ.get("TTS_THREADS"))
        options.inter_op_num_threads = 1
        session = rt.InferenceSession(model_path, sess_options=options, providers=["CPUExecutionProvider"])
        self.kokoro = Kokoro.from_session(session, voices_path)
        self.model = model
        self.g2p_mode = g2p
        self.lang = None
        self.g2p = None
        self._voice_cache = {}
        self.set_lang(lang)

    def set_lang(self, lang):
        self.lang = lang
        self.g2p = _make_misaki_g2p(lang) if self.g2p_mode == "misaki" else None

    def _voice_style(self, voice):
        style = self._voice_cache.get(voice)
        if style is None:
            names = [name.strip() for name in str(voice).split(",") if name.strip()]
            available = [name for name in names if name in self.kokoro.voices]
            if not available:
                available = [DEFAULT_KOKORO_VOICE]
            # Voz composta ("af_heart,af_bella") e a media dos estilos.
            style = self._np.mean([self.kokoro.get_voice_style(name) for name in available], axis=0)
            self._voice_cache[voice] = style
        return style

    def _sentence_audio(self, sentence, style, speed):
        if self.g2p is not None:
            phonemes, _tokens = self.g2p(sentence)
            if not phonemes or not phonemes.strip():
                return None
            audio, _sr = self.kokoro.create(phonemes, voice=style, speed=speed, is_phonemes=True, trim=False)
        else:
            lang = ESPEAK_LANGS.get(self.lang, "en-us")
            audio, _sr = self.kokoro.create(sentence, voice=style, speed=speed, lang=lang, trim=False)
        return audio

    def __call__(self, text, voice=None, speed=1.0, split_pattern=r"(?<=[.!?])\s+"):
        style = self._voice_style(voice or DEFAULT_KOKORO_VOICE)
        low, high = ONNX_SPEED_RANGE
        speed = min(high, max(low, float(speed)))
        parts = self._re.split(split_pattern, text) if split_pattern else [text]
        for sentence in parts:
            sentence = sentence.strip()
            if not sentence:
                continue
            audio = self._sentence_audio(sentence, style, speed)
            if audio is not None and len(audio):
                yield sentence, None, audio
