import os
import abc
import time

# Configurações de vozes padrão
DEFAULT_VOICE_MAP = {
    "af_heart": "en-US-EmmaMultilingualNeural",
    "am_adam": "en-US-AndrewMultilingualNeural",
    "ef_dora": "es-ES-ElviraNeural",
    "pt_br": "pt-BR-FranciscaNeural"
}
DEFAULT_KOKORO_VOICE = "af_heart"

# Versao do modelo de sintese. Entra na chave do cache em disco: sem isso, uma
# troca de modelo continuaria servindo o audio antigo sem nenhum aviso.
MODEL_VERSION = "kokoro-v0.19"

def get_available_voices():
    return list(DEFAULT_VOICE_MAP.keys())

def _log_engine(msg):
    tld = os.environ.get("TTS_LOG_DIR") or os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(tld, "tts_server.log")
    try:
        import json
        data = {"timestamp": time.time(), "msg": f"[ENGINE] {msg}"}
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(data) + "\n")
    except Exception:
        pass

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
                    try: sd.play(audio_data, samplerate=samplerate)
                    except Exception: pass

    @abc.abstractmethod
    def speak(self, text, voice=None, speed=1.0):
        pass

    def stop(self):
        try:
            import sounddevice as sd
            sd.stop()
        except Exception: pass




class KokoroEngine(TTSEngine):
    def __init__(self, lang="a"):
        super().__init__()
        import queue
        import threading
        self.audio_queue = queue.Queue()
        self.stop_flag = False
        self.on_playback_done = None
        
        try:
            _log_engine("Importando KPipeline do pacote kokoro...")
            from kokoro import KPipeline
            _log_engine(f"Inicializando KPipeline(lang_code={lang})...")
            # Carrega o Pipeline com o modelo Kokoro 82M padrão
            # O parâmetro lang_code="a" é para inglês americano
            self.pipeline = KPipeline(lang_code=lang)
            self.lang = lang
            self.samplerate = 24000

            # Inicializa diretorio de cache de audio
            cache_base = os.environ.get("TTS_CACHE_DIR") or os.environ.get("TTS_LOG_DIR") or os.path.dirname(os.path.abspath(__file__))
            self.cache_dir = os.path.join(cache_base, ".tts_cache")
            try:
                os.makedirs(self.cache_dir, exist_ok=True)
                self.clean_cache()
            except Exception:
                pass
            
            # Inicializa a thread de playback streaming
            self.play_thread = threading.Thread(target=self._playback_worker, daemon=True)
            self.play_thread.start()
            
            _log_engine("Kokoro Engine v0.19 carregada com sucesso.")
        except Exception as e:
            _log_engine(f"Erro ao carregar Kokoro: {e}")
            self.pipeline = None

    def set_lang(self, lang):
        self.lang = lang
        _log_engine(f"KokoroEngine alterando lang_code para: {lang}")
        try:
            from kokoro import KPipeline
            self.pipeline = KPipeline(lang_code=lang)
            _log_engine(f"KokoroEngine KPipeline atualizado com sucesso: {lang}")
            return True
        except Exception as e:
            _log_engine(f"Erro ao alterar idioma no KokoroEngine: {e}")
            return False

    def clean_cache(self, max_files=2000, max_size_mb=500):
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
                            except Exception: pass
                            stream = None
                self.audio_queue.task_done()
            except Exception as e:
                _log_engine(f"Erro no loop do playback_worker: {e}")
                if stream is not None:
                    try:
                        stream.stop()
                        stream.close()
                    except Exception: pass
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
        return hashlib.md5(f"{MODEL_VERSION}_{actual_voice}_{speed:.2f}_{text}".encode("utf-8")).hexdigest()

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
            import numpy as np
            np.save(cache_file, audio_data)
        except Exception as ex:
            _log_engine(f"Erro ao salvar cache: {ex}")
            return
        # Poda durante a sessao: a cota so era reavaliada no boot, e uma sessao longa
        # ultrapassava o limite de arquivos e de tamanho sem parar. A varredura do
        # diretorio e barata ao lado do custo de sintetizar a fala.
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
            start_time = time.time()
            count = 0
            collected_chunks = []
            for _, _, audio in self.pipeline(text, voice=actual_voice, speed=speed, split_pattern=r'(?<=[.!?])\s+'):
                if self.stop_flag: break
                if hasattr(audio, "detach"):
                    audio = audio.detach().cpu().numpy()
                import numpy as np
                audio_np = np.asarray(audio, dtype=np.float32).reshape(-1)
                if len(audio_np) > 0:
                    self.audio_queue.put(audio_np)
                    collected_chunks.append(audio_np)
                count += 1

            self.audio_queue.put("FINISH_MARKER")
            elapsed = time.time() - start_time
            print(f"[OK] Geracao concluida em {elapsed:.2f}s ({count} segmentos)")

            # Salvar no cache se geração concluiu com sucesso
            if not self.stop_flag and collected_chunks:
                import numpy as np
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
            collected = []
            for _, _, audio in self.pipeline(text, voice=actual_voice, speed=speed):
                if hasattr(audio, "detach"):
                    audio = audio.detach().cpu().numpy()
                import numpy as np
                collected.append(np.asarray(audio, dtype=np.float32).reshape(-1))
            if collected:
                import numpy as np
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

