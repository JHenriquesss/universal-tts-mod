import os
import abc
import numpy as np
import time

# Configurações de vozes padrão
DEFAULT_VOICE_MAP = {
    "af_heart": "en-US-EmmaMultilingualNeural",
    "am_adam": "en-US-AndrewMultilingualNeural",
    "ef_dora": "es-ES-ElviraNeural",
    "pt_br": "pt-BR-FranciscaNeural"
}
DEFAULT_KOKORO_VOICE = "af_heart"

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
                try: sd.play(audio_data, samplerate=samplerate)
                except: pass

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
            self.samplerate = 24000
            
            # Inicializa a thread de playback streaming
            self.play_thread = threading.Thread(target=self._playback_worker, daemon=True)
            self.play_thread.start()
            
            _log_engine("Kokoro Engine v0.19 carregada com sucesso.")
        except Exception as e:
            _log_engine(f"Erro ao carregar Kokoro: {e}")
            self.pipeline = None

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
                        except: pass
                    break
                    
                if isinstance(chunk, str) and chunk == "STOP":
                    if stream is not None:
                        try:
                            stream.stop()
                            stream.close()
                        except: pass
                        stream = None
                    self.audio_queue.task_done()
                    continue

                if isinstance(chunk, str) and chunk == "FINISH_MARKER":
                    if self.on_playback_done:
                        try:
                            self.on_playback_done()
                        except: pass
                    self.audio_queue.task_done()
                    continue
                    
                if not self.stop_flag:
                    try:
                        if stream is None or not stream.active:
                            device_id = self._default_device_id if self._default_device_id >= 0 else None
                            stream = sd.OutputStream(samplerate=self.samplerate, channels=1, dtype='float32', device=device_id)
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
                self.audio_queue.task_done()
            except Exception as e:
                _log_engine(f"Erro no loop do playback_worker: {e}")

    def speak(self, text, voice=None, speed=1.0):
        if not self.pipeline:
            print("[ERRO] Pipeline Kokoro nao inicializado!")
            return False

        # Voz feminina padrão Amy-like se não for especificada
        actual_voice = voice if voice and voice != "None" else DEFAULT_KOKORO_VOICE

        print(f"[*] Gerando audio (Voz: {actual_voice}, Speed: {speed})...")
        _log_engine(f"Kokoro gerando: {text[:30]}...")

        self.stop_flag = False
        self.audio_queue.put("STOP")

        try:
            start_time = time.time()
            count = 0
            for _, _, audio in self.pipeline(text, voice=actual_voice, speed=speed, split_pattern=r'(?<=[.!?])\s+'):
                if self.stop_flag: break
                if hasattr(audio, "detach"):
                    audio = audio.detach().cpu().numpy()
                audio_np = np.asarray(audio, dtype=np.float32).reshape(-1)
                if len(audio_np) > 0:
                    self.audio_queue.put(audio_np)
                count += 1

            self.audio_queue.put("FINISH_MARKER")
            elapsed = time.time() - start_time
            print(f"[OK] Geracao concluida em {elapsed:.2f}s ({count} segmentos)")
            return True
        except Exception as e:
            print(f"[ERRO] Falha na geracao Kokoro: {e}")
            _log_engine(f"Kokoro error: {e}")
        return False

    def stop(self):
        self.stop_flag = True
        try:
            while not self.audio_queue.empty():
                try: self.audio_queue.get_nowait()
                except: break
            self.audio_queue.put("STOP")
        except: pass
        super().stop()

class MockEngine(TTSEngine):
    """Test-only engine selected by TTS_ENGINE=mock."""
    def __init__(self):
        self._player = None
        self._default_device_id = -1

    def speak(self, text, voice=None, speed=1.0): return False
