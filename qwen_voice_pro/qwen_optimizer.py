import os
import sys
import torch
import librosa
import warnings
from transformers import Qwen2AudioForConditionalGeneration, AutoProcessor, BitsAndBytesConfig

# Silencia avisos desnecessários
warnings.filterwarnings("ignore")

class QwenTTSOptimizer:
    def __init__(self, model_id="Qwen/Qwen2-Audio-7B-Instruct"):
        self.model_id = model_id
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        print(f"[*] Inicializando Qwen2-Audio em modo otimizado ({self.device})...")
        
        # Configuração para 4-bit (bitsandbytes) se tiver CUDA
        # Isso permite rodar um modelo de 7B com ~5-6GB de VRAM
        quant_config = None
        if self.device == "cuda":
            quant_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4"
            )

        print("[*] Carregando Processador e Modelo...")
        self.processor = AutoProcessor.from_pretrained(model_id)
        self.model = Qwen2AudioForConditionalGeneration.from_pretrained(
            model_id,
            device_map="auto" if self.device == "cuda" else None,
            quantization_config=quant_config,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            low_cpu_mem_usage=True
        )
        if self.device == "cpu":
            self.model.to("cpu")
            
        print("[+] Modelo pronto!")

    def extract_voice_prompt(self, audio_path):
        if not os.path.exists(audio_path):
            return f"Erro: Arquivo {audio_path} não encontrado."

        print(f"[*] Analisando áudio: {audio_path}")
        
        # Carrega o áudio e ajusta o samplerate para o que o modelo espera
        audio, _ = librosa.load(audio_path, sr=self.processor.feature_extractor.sampling_rate)
        
        # Prompt de Engenharia para extrair a "assinatura" da voz
        # Este prompt foi desenhado para gerar descrições que funcionam bem em modelos como ElevenLabs, Fish Speech, etc.
        text_prompt = (
            "<|audio_bos|><|AUDIO|><|audio_eos|>"
            "Analise esta voz em detalhes para uma tarefa de clonagem de voz. "
            "Forneça uma descrição técnica estruturada incluindo: "
            "1. Gênero e idade estimada. "
            "2. Tom (grave, médio, agudo) e ressonância. "
            "3. Velocidade de fala e ritmo. "
            "4. Emoção predominante e nível de energia. "
            "5. Características únicas (rouquidão, voz sussurrada, vocal fry, clareza). "
            "Ao final, crie um 'Mega-Prompt' denso e curto (em inglês) que resuma toda essa identidade vocal para um sistema TTS."
        )

        # Prepara os inputs
        inputs = self.processor(text=text_prompt, audios=audio, return_tensors="pt")
        
        # Move inputs para o dispositivo correto
        if self.device == "cuda":
            inputs = {k: v.to("cuda") for k, v in inputs.items()}

        print("[*] Gerando perfil de voz...")
        with torch.no_grad():
            generated_ids = self.model.generate(**inputs, max_new_tokens=512)
        
        # Decodifica o resultado ignorando os tokens de entrada
        generated_ids = generated_ids[:, inputs["input_ids"].size(1):]
        response = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        
        return response

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python qwen_optimizer.py <caminho_do_audio>")
        sys.exit(1)

    audio_file = sys.argv[1]
    optimizer = QwenTTSOptimizer()
    resultado = optimizer.extract_voice_prompt(audio_file)
    
    print("\n" + "="*50)
    print("PERFIL DE VOZ GERADO:")
    print("="*50)
    print(resultado)
    print("="*50)
