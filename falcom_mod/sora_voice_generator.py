import argparse
import os
import sys
sys.dont_write_bytecode = True

try:
    from text_cleaner import TextCleaner
except ImportError:
    here = os.path.dirname(os.path.abspath(__file__))
    renpy_dir = os.path.join(os.path.dirname(here), "renpy_mod")
    if os.path.isdir(renpy_dir) and renpy_dir not in sys.path:
        sys.path.insert(0, renpy_dir)
    if here not in sys.path:
        sys.path.insert(0, here)
    from text_cleaner import TextCleaner


def generate_voice_file(text, output_path, voice="af_heart", speed=1.0):
    """
    Gera um arquivo de áudio para uma linha de diálogo do SoraVoice.
    """
    cleaned = TextCleaner.clean(text)
    if not cleaned:
        return False

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    # Exemplo de chamada ao motor TTS (Kokoro ou Mock)
    try:
        from tts_engines import get_tts_engine
        engine = get_tts_engine()
        return engine.speak_to_file(cleaned, output_path, voice=voice, speed=speed)
    except Exception as exc:
        print(f"[ERRO] Falha ao sintetizar áudio: {exc}")
        return False


def main(argv=None):
    parser = argparse.ArgumentParser(description="Gerador de Pacote de Vozes SoraVoice Offline com Kokoro TTS.")
    parser.add_argument("--voice-dir", default="voice/ogg", help="Diretório de saída dos arquivos OGG.")
    parser.add_argument("--voice", default="af_heart", help="Voz Kokoro padrão.")
    args = parser.parse_args(argv)

    print(f"Diretório de saída: {args.voice_dir}")
    print(f"Voz configurada: {args.voice}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
