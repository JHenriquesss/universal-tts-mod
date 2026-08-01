# Qwen2-Audio Voice Prompt Optimizer (Standalone)

Este projeto é uma implementação otimizada do **Qwen2-Audio-7B-Instruct** focada em extrair perfis de voz detalhados para serem usados em outros sistemas de TTS.

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
- `requirements.txt`: Lista de bibliotecas necessárias.
- `models/`: Onde o cache do modelo será armazenado (opcional).
