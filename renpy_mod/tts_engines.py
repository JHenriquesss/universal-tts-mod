import abc
import atexit
import os
import sys
import time

from tts_protocol import append_bounded_log, resolve_cpu_threads, trim_working_set

# Configurações de vozes padrão
DEFAULT_VOICE_MAP = {
    "af_heart": "en-US-EmmaMultilingualNeural",
    "am_adam": "en-US-AndrewMultilingualNeural",
    "ef_dora": "es-ES-ElviraNeural",
    "pt_br": "pt-BR-FranciscaNeural"
}
DEFAULT_KOKORO_VOICE = "af_heart"

# Versao do modelo de sintese. Entra na chave do cache em disco (junto com a
# variante e a pronuncia): sem isso, uma troca de modelo continuaria servindo o
# audio antigo sem nenhum aviso.
MODEL_VERSION = "kokoro-v1.0-onnx"

# Cache efemero da sessao ativa: enxuto durante o jogo (para rollback imediato)
# e zerado automaticamente a cada inicializacao e encerramento limpo do processo.
SESSION_CACHE_MAX_FILES = 100
SESSION_CACHE_MAX_MB = 50
_REGISTERED_CACHE_DIRS = set()


def get_available_voices():
    return list(DEFAULT_VOICE_MAP.keys())


def _log_engine(msg):
    tld = os.environ.get("TTS_LOG_DIR") or os.path.dirname(os.path.abspath(__file__))
    append_bounded_log(os.path.join(tld, "tts_server.log"), f"[ENGINE] {msg}")


def clear_cache_dir(cache_dir, remove_dir_if_empty=False):
    """Remove todos os artefatos de audio (.npy/.wav) de ``cache_dir`` sem tocar outros arquivos."""
    if not cache_dir or not os.path.isdir(cache_dir):
        return 0
    removed_count = 0
    try:
        for name in os.listdir(cache_dir):
            if name.endswith(".npy") or name.endswith(".wav"):
                try:
                    os.remove(os.path.join(cache_dir, name))
                    removed_count += 1
                except OSError:
                    pass
        if remove_dir_if_empty and not os.listdir(cache_dir):
            try:
                os.rmdir(cache_dir)
            except OSError:
                pass
    except Exception as exc:
        _log_engine(f"Erro ao limpar cache efemero: {exc}")
    return removed_count


def _register_ephemeral_cache_cleanup(cache_dir):
    if not cache_dir:
        return
    normalized = os.path.normcase(os.path.abspath(cache_dir))
    if normalized in _REGISTERED_CACHE_DIRS:
        return
    _REGISTERED_CACHE_DIRS.add(normalized)
    atexit.register(clear_cache_dir, cache_dir, True)


class TTSEngine(abc.ABC):
    def __init__(self):
        self._player = None
        self._default_device_id = None
        self._cache_device()

    def _cache_device(self):
        try:
            import sounddevice as sd
            self._default_device_id = sd.default.device[1]
            _log_engine(f"Dispositivo de saída cacheado: {self._default_device_id}")
        except Exception as e:
            _log_engine(f"Erro ao cachear dispositivo: {e}")
            self._default_device_id = -1

    def set_player(self, player):
        self._player = player

    def _play(self, audio_data, samplerate):
        if self._player:
            self._player(audio_data, samplerate)
        else:
            try:
                import sounddevice as sd
                sd.stop()
                sd.play(audio_data, samplerate=samplerate, device=self._default_device_id if self._default_device_id >= 0 else None)
            except Exception as e:
                _log_engine(f"Erro na reprodução: {e}")
                try:
                    self._cache_device()
                    sd.play(audio_data, samplerate=samplerate, device=self._default_device_id if self._default_device_id >= 0 else None)
                except Exception:
                    try:
                        sd.play(audio_data, samplerate=samplerate)
                    except Exception:
                        pass

    @abc.abstractmethod
    def speak(self, text, voice=None, speed=1.0):
        pass

    def stop(self):
        try:
            import sounddevice as sd
            sd.stop()
        except Exception:
            pass


# --- Kokoro-82M no ONNX Runtime -----------------------------------------------
# O modelo roda no ONNX Runtime, sem PyTorch no processo: o backend carrega mais
# rapido e usa bem menos memoria. A pronuncia em ingles vem do misaki, o mesmo
# conversor do pacote kokoro original.

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


def resolve_onnx_dir(environ=None):
    env = os.environ if environ is None else environ
    custom = str(env.get("TTS_ONNX_DIR", "")).strip()
    if custom:
        return custom
    return os.path.join(env.get("LOCALAPPDATA", os.path.expanduser("~")), *ONNX_DIR_PARTS)


def resolve_onnx_options(model=None, g2p=None):
    """Variante do modelo e modo de pronuncia.

    fp32 por padrao porque e o peso original do modelo. O int8 usa ~200 MB a
    menos de RAM, mas perde um pouco de fidelidade.
    """
    model_key = str(model or os.environ.get("TTS_ONNX_MODEL") or "fp32").strip().lower()
    if model_key not in ONNX_MODEL_FILES:
        model_key = "fp32"
    g2p_key = str(g2p or os.environ.get("TTS_ONNX_G2P") or "misaki").strip().lower()
    if g2p_key not in ONNX_G2P_MODES:
        g2p_key = "misaki"
    return model_key, g2p_key


def _import_misaki():
    """Importa o misaki mantendo o torch fora do processo.

    Quando o backend cai num Python global que tem o torch, o spacy (usado pelo
    misaki) o puxaria sem uso (~200 MB). Se algum plugin do spacy exigir o torch
    de verdade, o import e refeito com o torch liberado.
    """
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


class KokoroEngine(TTSEngine):
    """Kokoro-82M no ONNX Runtime, com fila de playback em streaming e cache de sessao."""

    ENGINE_LABEL = "Kokoro ONNX Engine"

    def __init__(self, lang="a", model=None, g2p=None):
        super().__init__()
        import queue
        import threading
        self.audio_queue = queue.Queue()
        self.stop_flag = False
        self.on_playback_done = None
        self.onnx_model, self.onnx_g2p = resolve_onnx_options(model, g2p)

        try:
            _log_engine(f"Inicializando Kokoro ONNX (modelo={self.onnx_model}, pronuncia={self.onnx_g2p}, lang={lang})...")
            self.pipeline = OnnxPipeline(lang=lang, model=self.onnx_model, g2p=self.onnx_g2p)
            self.lang = lang
            self.samplerate = 24000

            # Cache efemero: zera restos de sessoes anteriores no boot para nao
            # acumular GBs em disco entre execucoes e registra limpeza na saida.
            cache_base = os.environ.get("TTS_CACHE_DIR") or os.environ.get("TTS_LOG_DIR") or os.path.dirname(os.path.abspath(__file__))
            self.cache_dir = os.path.join(cache_base, ".tts_cache")
            try:
                os.makedirs(self.cache_dir, exist_ok=True)
                removed = self.clear_cache()
                if removed:
                    _log_engine(f"Cache de sessao anterior limpo no boot ({removed} arquivos).")
                _register_ephemeral_cache_cleanup(self.cache_dir)
            except Exception:
                pass

            # Inicializa a thread de playback streaming
            self.play_thread = threading.Thread(target=self._playback_worker, daemon=True)
            self.play_thread.start()

            # Descarta os buffers mortos do carregamento antes do jogo precisar da RAM.
            trim_working_set()
            _log_engine(f"{self.ENGINE_LABEL} carregada com sucesso.")
        except Exception as e:
            _log_engine(f"Erro ao carregar Kokoro: {e}")
            self.pipeline = None

    def set_lang(self, lang):
        if not self.pipeline:
            return False
        if lang == getattr(self, "lang", None):
            return True
        _log_engine(f"KokoroEngine alterando idioma para: {lang}")
        try:
            # Troca so a pronuncia: a sessao do modelo e as vozes continuam carregadas.
            self.pipeline.set_lang(lang)
            self.lang = lang
            return True
        except Exception as e:
            _log_engine(f"Erro ao alterar idioma no KokoroEngine: {e}")
            return False

    def clear_cache(self, remove_dir_if_empty=False):
        return clear_cache_dir(getattr(self, "cache_dir", None), remove_dir_if_empty=remove_dir_if_empty)

    def clean_cache(self, max_files=SESSION_CACHE_MAX_FILES, max_size_mb=SESSION_CACHE_MAX_MB):
        try:
            if not getattr(self, "cache_dir", None) or not os.path.isdir(self.cache_dir):
                return 0
            entries = []
            total_size = 0
            for name in os.listdir(self.cache_dir):
                if name.endswith(".npy") or name.endswith(".wav"):
                    p = os.path.join(self.cache_dir, name)
                    try:
                        st = os.stat(p)
                        entries.append((st.st_mtime, st.st_size, p))
                        total_size += st.st_size
                    except OSError:
                        pass
            max_bytes = max_size_mb * 1024 * 1024
            removed_count = 0
            if len(entries) > max_files or total_size > max_bytes:
                entries.sort(key=lambda x: x[0])
                for mtime, size, p in entries:
                    if len(entries) - removed_count <= max_files and total_size <= max_bytes:
                        break
                    try:
                        os.remove(p)
                        total_size -= size
                        removed_count += 1
                    except OSError:
                        pass
            return removed_count
        except Exception as e:
            _log_engine(f"Erro na limpeza de cache: {e}")
            return 0

    def _playback_worker(self):
        import sounddevice as sd
        stream = None
        while True:
            try:
                chunk = self.audio_queue.get()
                if chunk is None:
                    if stream is not None:
                        try:
                            stream.stop()
                            stream.close()
                        except Exception:
                            pass
                    break

                if isinstance(chunk, str) and chunk == "STOP":
                    if stream is not None:
                        try:
                            stream.stop()
                            stream.close()
                        except Exception:
                            pass
                        stream = None
                    self.audio_queue.task_done()
                    continue

                if isinstance(chunk, str) and chunk == "FINISH_MARKER":
                    time.sleep(0.15)
                    if self.on_playback_done:
                        try:
                            self.on_playback_done()
                        except Exception:
                            pass

                    self.audio_queue.task_done()
                    continue

                if not self.stop_flag:
                    try:
                        if stream is None or not stream.active:
                            device_id = self._default_device_id if self._default_device_id >= 0 else None
                            try:
                                stream = sd.OutputStream(samplerate=self.samplerate, channels=1, dtype='float32', device=device_id)
                                stream.start()
                            except Exception as dev_err:
                                _log_engine(f"Dispositivo padrão falhou ({dev_err}), tentando atualizar dispositivo...")
                                self._cache_device()
                                stream = sd.OutputStream(samplerate=self.samplerate, channels=1, dtype='float32', device=None)
                                stream.start()

                        # Escreve o chunk em blocos menores para permitir interrupcao rapida
                        chunk_2d = chunk.reshape(-1, 1)
                        block_size = 2400  # 100ms em 24000Hz
                        for i in range(0, len(chunk_2d), block_size):
                            if self.stop_flag:
                                break
                            stream.write(chunk_2d[i:i+block_size])
                    except Exception as e:
                        _log_engine(f"Erro no playback_worker: {e}")
                        if stream is not None:
                            try:
                                stream.stop()
                                stream.close()
                            except Exception:
                                pass
                            stream = None
                self.audio_queue.task_done()
            except Exception as e:
                _log_engine(f"Erro no loop do playback_worker: {e}")
                if stream is not None:
                    try:
                        stream.stop()
                        stream.close()
                    except Exception:
                        pass
                    stream = None

    def stop(self):
        self.stop_flag = True
        try:
            while not self.audio_queue.empty():
                try:
                    self.audio_queue.get_nowait()
                    self.audio_queue.task_done()
                except Exception:
                    break
            self.audio_queue.put("STOP")
        except Exception:
            pass
        super().stop()

    def _get_cache_key(self, text, voice=None, speed=1.0):
        import hashlib
        actual_voice = voice if voice and voice != "None" else DEFAULT_KOKORO_VOICE
        model_version = "{}-{}-{}".format(
            MODEL_VERSION, getattr(self, "onnx_model", "fp32"), getattr(self, "onnx_g2p", "misaki")
        )
        return hashlib.md5(f"{model_version}_{actual_voice}_{speed:.2f}_{text}".encode("utf-8")).hexdigest()

    def _get_from_cache(self, cache_key):
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.npy")
        if os.path.isfile(cache_file):
            try:
                import numpy as np
                cached = np.load(cache_file)
                if len(cached) > 0:
                    return cached
            except Exception as e:
                _log_engine(f"Erro ao ler cache: {e}")
        return None

    def _save_to_cache(self, cache_key, audio_data):
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.npy")
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
            import numpy as np
            np.save(cache_file, audio_data)
        except Exception as ex:
            _log_engine(f"Erro ao salvar cache: {ex}")
            return
        # Poda durante a sessao: mantem apenas a janela recente para rollback sem
        # crescer em disco durante sessoes longas.
        self.clean_cache()

    def speak(self, text, voice=None, speed=1.0):
        if not self.pipeline:
            print("[ERRO] Pipeline Kokoro nao inicializado!")
            return False

        # Voz padrão se não for especificada
        actual_voice = voice if voice and voice != "None" else DEFAULT_KOKORO_VOICE

        self.stop_flag = False
        self.audio_queue.put("STOP")

        # 1. Checagem de Cache em Disco (.tts_cache)
        cache_key = self._get_cache_key(text, actual_voice, speed)
        cached_audio = self._get_from_cache(cache_key)
        if cached_audio is not None:
            self.audio_queue.put(cached_audio)
            self.audio_queue.put("FINISH_MARKER")
            print(f"[CACHE HIT] Audio carregado instantaneamente ({actual_voice})")
            _log_engine(f"[CACHE HIT] {text[:30]}... ({cache_key})")
            return True

        print(f"[*] Gerando audio (Voz: {actual_voice}, Speed: {speed})...")
        _log_engine(f"Kokoro gerando: {text[:30]}...")

        try:
            import numpy as np
            start_time = time.time()
            count = 0
            collected_chunks = []
            for _, _, audio in self.pipeline(text, voice=actual_voice, speed=speed, split_pattern=r'(?<=[.!?])\s+'):
                if self.stop_flag:
                    break
                audio_np = np.asarray(audio, dtype=np.float32).reshape(-1)
                del audio
                if len(audio_np) > 0:
                    self.audio_queue.put(audio_np)
                    collected_chunks.append(audio_np)
                count += 1

            self.audio_queue.put("FINISH_MARKER")
            elapsed = time.time() - start_time
            print(f"[OK] Geracao concluida em {elapsed:.2f}s ({count} segmentos)")

            # Salvar no cache se geração concluiu com sucesso
            if not self.stop_flag and collected_chunks:
                full_audio = np.concatenate(collected_chunks)
                self._save_to_cache(cache_key, full_audio)

            return True
        except Exception as e:
            print(f"[ERRO] Falha na geracao Kokoro: {e}")
            _log_engine(f"Kokoro error: {e}")
        return False

    def speak_to_file(self, text, output_path, voice=None, speed=1.0):
        """Sintetiza áudio e salva diretamente em arquivo (ex: OGG/WAV)."""
        if not self.pipeline:
            return False
        actual_voice = voice if voice and voice != "None" else DEFAULT_KOKORO_VOICE
        try:
            import numpy as np
            collected = [
                np.asarray(audio, dtype=np.float32).reshape(-1)
                for _, _, audio in self.pipeline(text, voice=actual_voice, speed=speed)
            ]
            if collected:
                import soundfile as sf
                full_audio = np.concatenate(collected)
                os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
                sf.write(output_path, full_audio, self.samplerate)
                return True
        except Exception as e:
            _log_engine(f"speak_to_file error: {e}")
        return False


def get_tts_engine(lang="a"):
    """Factory method para obter a engine Kokoro inicializada."""
    return KokoroEngine(lang=lang)


class MockEngine(TTSEngine):
    """Test-only engine selected by TTS_ENGINE=mock."""
    def __init__(self):
        self._player = None
        self._default_device_id = -1
        self.on_playback_done = None

    def speak(self, text, voice=None, speed=1.0):
        if self.on_playback_done:
            try:
                self.on_playback_done()
            except Exception:
                pass
        return True

    def set_lang(self, lang):
        self.lang = lang
        _log_engine(f"MockEngine lang set to {lang}")
        return True
