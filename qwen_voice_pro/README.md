# Qwen2-Audio Voice Prompt Optimizer (Standalone)

> **Spike — experimento sem consumidor no mod.** Nada neste repositório chama
> este script: ele não é instalado pelo `instalar.bat`, não entra no
> `requirements.txt` do mod e não roda no CI. Fica aqui como registro da
> ideia, não como parte do produto.

Este projeto é uma implementação otimizada do **Qwen2-Audio-7B-Instruct** focada em extrair perfis de voz detalhados para serem usados em outros sistemas de TTS.

## Por que continua como spike
- O modelo tem **7B parâmetros**: ~28 GB de VRAM em precisão normal e ~5 GB em
  quantização 4-bit.
- A saída é uma **descrição textual** de voz. O motor do mod é o Kokoro, que não
  expõe clonagem de voz: a descrição só aproveita em sistemas como ElevenLabs ou
  Fish Speech, que o projeto não integra.
- Como nada no projeto consome o resultado, mover esse peso para o payload do
  mod seria carregar gigabytes sem uso.

## Como Usar
1. Mova esta pasta `qwen_voice_pro` para onde desejar no seu PC.
2. Certifique-se de ter o Python instalado.
3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
4. Coloque um arquivo de áudio (ex: `voz_referencia.wav`) na pasta raiz.
5. Execute o script:
   ```bash
   python qwen_optimizer.py voz_referencia.wav
   ```

## Otimizações Incluídas
- **4-bit Quantization**: Reduz o uso de VRAM de ~28GB para apenas ~5GB.
- **Float16 Inference**: Acelera a geração em GPUs modernas.
- **Prompt Engineering**: Configurado especificamente para extrair paralinguística (vocal fry, respiração, emoção).

## Arquivos
- `qwen_optimizer.py`: Script principal de inferência.
- `requirements.txt`: Lista de bibliotecas necessárias, exclusiva deste spike.
- `models/`: Onde o cache do modelo será armazenado (opcional).
- `outputs/`: Onde a descrição da voz é gravada (opcional).
