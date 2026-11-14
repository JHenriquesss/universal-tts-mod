"""Valida os artefatos gerados para o CampusConfidential."""
import json
import os
import sys
import textwrap


def main():
    project = sys.argv[1]
    hints_path = os.path.join(project, "samples", "campus_confidential_choice_hints_generated.rpy")
    voice_map_path = os.path.join(project, "samples", "campus_confidential_voice_map.json")

    raw = open(hints_path, "rb").read()
    print("BOM:", raw[:3] == b"\xef\xbb\xbf")
    text = raw.decode("utf-8")
    print("decodifica como UTF-8: OK")

    marker = "Sem altera"
    sample = [line for line in text.splitlines() if marker in line]
    print("linhas com 'Sem altera':", len(sample))
    if sample:
        print("  amostra:", sample[0].strip())

    body = text.split("init -2 python:", 1)[1]
    # Os .rpy do projeto usam CRLF; o dedent so funciona com LF.
    body = textwrap.dedent(body.replace("\r\n", "\n"))
    namespace = {}
    try:
        exec(compile(body, hints_path, "exec"), namespace)
    except SyntaxError as exc:
        print("ERRO DE SINTAXE: linha={} msg={}".format(exc.lineno, exc.msg))
        print("  source:", repr(exc.text))
        raise
    hints = namespace["GENERATED_CHOICE_HINTS"]
    print("sintaxe do .rpy: OK | entradas:", len(hints))

    with open(voice_map_path, "r", encoding="utf-8") as f:
        voice_map = json.load(f)
    print("voice_map entradas:", len(voice_map))
    print("vozes usadas:", ", ".join(sorted(set(voice_map.values()))))

    # O modelo precisa ter todas as vozes referenciadas.
    import numpy as np
    model_dir = os.path.join(os.environ["LOCALAPPDATA"], "UniversalKokoroTTS", "onnx")
    voices_file = os.path.join(model_dir, "voices-v1.0.bin")
    available = set(np.load(voices_file, allow_pickle=True).keys())
    missing = sorted(set(voice_map.values()) - available)
    print("vozes ausentes no modelo:", missing if missing else "nenhuma")


if __name__ == "__main__":
    main()
