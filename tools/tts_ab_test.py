# -*- coding: utf-8 -*-
"""Compara as variantes do Kokoro ONNX: atraso, memoria e qualidade.

Cada variante roda em um processo proprio, pelo mesmo caminho de codigo que o
backend usa no jogo (``renpy_mod/tts_engines.py``). O resultado fica em
``samples/ab_test/``: um WAV por fala e variante e um ``index.html`` com os
numeros e os players lado a lado para ouvir.

Uso (com o runtime leve):
    "%LOCALAPPDATA%\\UniversalKokoroTTS\\runtime\\Scripts\\python.exe" tools\\tts_ab_test.py
"""

import argparse
import html
import json
import os
import subprocess
import sys
import time

# Importa os modulos de renpy_mod/: sem isso sobra __pycache__ na pasta do mod.
sys.dont_write_bytecode = True

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RENPY_MOD_DIR = os.path.join(ROOT_DIR, "renpy_mod")
DEFAULT_OUT_DIR = os.path.join(ROOT_DIR, "samples", "ab_test")
SPEED = 1.25

VARIANTS = {
    "onnx-fp32-misaki": "ONNX fp32 + misaki (padrao)",
    "onnx-fp32-espeak": "ONNX fp32 + espeak",
    "onnx-int8-misaki": "ONNX int8 + misaki",
}

LINES = [
    ("af_heart", "Hey, you're finally awake. I was starting to get worried about you."),
    ("am_adam", "Listen carefully. We have exactly 3 hours before the 9:45 train leaves the station."),
    ("af_heart", "Wait... are you serious? You actually remembered my birthday?!"),
    ("am_adam", "I don't think that's a good idea, Jessica. Mr. Thompson won't like it."),
    ("af_heart", "Hmm. Maybe we could grab some coffee first, and then go to the mall together?"),
    ("am_adam", "Okay."),
    ("af_heart", "It's been a long day. The meeting dragged on forever, my boss kept yelling, and honestly, I just want to lie down and forget about everything for a while."),
    ("am_adam", "Oh wow, that's amazing! Let's celebrate tonight!"),
]


def _memory_mb():
    if os.name != "nt":
        return None, None
    import ctypes
    from ctypes import wintypes

    class Counters(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
            ("PrivateUsage", ctypes.c_size_t),
        ]

    kernel32 = ctypes.windll.kernel32
    psapi = ctypes.windll.psapi
    kernel32.GetCurrentProcess.restype = ctypes.c_void_p
    psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD]
    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    psapi.GetProcessMemoryInfo(kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb)
    return counters.WorkingSetSize / 2 ** 20, counters.PrivateUsage / 2 ** 20


def _build_pipeline(variant):
    sys.path.insert(0, RENPY_MOD_DIR)
    from tts_protocol import apply_thread_env_limits, resolve_cpu_threads, trim_working_set

    apply_thread_env_limits(resolve_cpu_threads(os.environ.get("TTS_THREADS")))
    import tts_engines

    _engine, model, g2p = variant.split("-")
    pipeline = tts_engines.OnnxPipeline(lang="a", model=model, g2p=g2p)
    trim_working_set()  # o backend faz o mesmo depois de carregar
    return pipeline


def run_variant(variant, out_dir):
    os.environ["TTS_LOG_DIR"] = out_dir  # nao suja renpy_mod/ com tts_server.log
    import numpy as np
    import soundfile as sf

    started = time.perf_counter()
    pipeline = _build_pipeline(variant)
    load_s = time.perf_counter() - started
    ws_load, commit_load = _memory_mb()

    variant_dir = os.path.join(out_dir, variant)
    os.makedirs(variant_dir, exist_ok=True)

    def synth(text, voice):
        t0 = time.perf_counter()
        first = None
        chunks = []
        for _, _, audio in pipeline(text, voice=voice, speed=SPEED, split_pattern=r"(?<=[.!?])\s+"):
            if hasattr(audio, "detach"):
                audio = audio.detach().cpu().numpy()
            if first is None:
                first = time.perf_counter() - t0
            chunks.append(np.asarray(audio, dtype=np.float32).reshape(-1))
        total = time.perf_counter() - t0
        audio = np.concatenate(chunks) if chunks else np.zeros(1, dtype=np.float32)
        return first or total, total, audio

    warm_first, warm_total, _ = synth("Hello there.", "af_heart")

    lines = []
    for index, (voice, text) in enumerate(LINES, start=1):
        first, total, audio = synth(text, voice)
        name = "{:02d}.wav".format(index)
        sf.write(os.path.join(variant_dir, name), audio, 24000, subtype="PCM_16")
        duration = len(audio) / 24000.0
        lines.append({"file": name, "first_s": first, "total_s": total, "audio_s": duration})

    ws_end, commit_end = _memory_mb()
    return {
        "variant": variant,
        "load_s": load_s,
        "warmup_first_s": warm_first,
        "ws_after_load_mb": ws_load,
        "commit_after_load_mb": commit_load,
        "ws_end_mb": ws_end,
        "commit_end_mb": commit_end,
        "lines": lines,
    }


def _fmt(value, digits=2, unit="s"):
    return "—" if value is None else "{:.{}f}{}".format(value, digits, unit)


def write_report(results, out_dir):
    rows = []
    for res in results:
        if "error" in res:
            rows.append("<tr><th>{}</th><td colspan='6' class='err'>{}</td></tr>".format(
                html.escape(VARIANTS[res["variant"]]), html.escape(res["error"])))
            continue
        lines = res["lines"]
        avg_first = sum(item["first_s"] for item in lines) / len(lines)
        max_first = max(item["first_s"] for item in lines)
        rtf = sum(item["total_s"] for item in lines) / sum(item["audio_s"] for item in lines)
        rows.append(
            "<tr><th>{}</th><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
                html.escape(VARIANTS[res["variant"]]),
                _fmt(res["load_s"], 1),
                _fmt(avg_first), _fmt(max_first), _fmt(rtf, 2, "x"),
                _fmt(res["ws_end_mb"], 0, " MB"), _fmt(res["commit_end_mb"], 0, " MB"),
            )
        )

    ok_results = [res for res in results if "error" not in res]
    players = []
    for index, (voice, text) in enumerate(LINES, start=1):
        cells = []
        for res in ok_results:
            item = res["lines"][index - 1]
            cells.append(
                "<div class='cell'><div class='lbl'>{}<span>início {} · total {}</span></div>"
                "<audio controls preload='none' src='{}/{}'></audio></div>".format(
                    html.escape(VARIANTS[res["variant"]]), _fmt(item["first_s"]), _fmt(item["total_s"]),
                    res["variant"], item["file"],
                )
            )
        players.append(
            "<section><p class='line'><b>{:02d}</b> <code>{}</code> {}</p><div class='grid'>{}</div></section>".format(
                index, html.escape(voice), html.escape(text), "".join(cells)
            )
        )

    page = """<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kokoro A/B</title>
<style>
:root {{ --bg:#fafaf9; --fg:#1c1917; --muted:#78716c; --card:#fff; --line:#e7e5e4; --err:#b91c1c; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#1c1917; --fg:#f5f5f4; --muted:#a8a29e; --card:#292524; --line:#44403c; --err:#f87171; }} }}
body {{ background:var(--bg); color:var(--fg); font:15px/1.5 system-ui,sans-serif; margin:0 auto; max-width:1100px; padding:24px 16px; }}
h1 {{ font-size:22px; margin:0 0 4px; }} p.sub {{ color:var(--muted); margin:0 0 20px; }}
table {{ border-collapse:collapse; width:100%; background:var(--card); margin-bottom:28px; font-variant-numeric:tabular-nums; }}
th, td {{ border-bottom:1px solid var(--line); padding:8px 10px; text-align:right; }}
th:first-child, thead th {{ text-align:left; }} thead th {{ color:var(--muted); font-weight:600; font-size:13px; }}
td.err {{ color:var(--err); text-align:left; }}
section {{ background:var(--card); border:1px solid var(--line); border-radius:8px; padding:12px 14px; margin-bottom:12px; }}
.line {{ margin:0 0 10px; }} .line code {{ color:var(--muted); }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:10px; }}
.lbl {{ font-size:13px; font-weight:600; margin-bottom:4px; display:flex; justify-content:space-between; gap:8px; }}
.lbl span {{ color:var(--muted); font-weight:400; }}
audio {{ width:100%; }}
.wrap {{ overflow-x:auto; }}
</style></head><body>
<h1>Kokoro ONNX: variantes</h1>
<p class="sub">Velocidade {speed}x, CPU com as mesmas threads do backend. "Início" = tempo até o primeiro trecho de áudio ficar pronto (o atraso que você sente no jogo).</p>
<div class="wrap"><table><thead><tr><th>Variante</th><th>Carregar</th><th>Início médio</th><th>Início pior</th><th>Tempo/áudio</th><th>RAM</th><th>Memória reservada</th></tr></thead>
<tbody>{rows}</tbody></table></div>
{players}
</body></html>
""".format(speed=SPEED, rows="".join(rows), players="".join(players))
    path = os.path.join(out_dir, "index.html")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(page)
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--variant", choices=sorted(VARIANTS), help="(interno) roda uma variante e imprime JSON")
    parser.add_argument("--only", nargs="*", choices=sorted(VARIANTS), help="variantes a comparar")
    parser.add_argument("--out", default=DEFAULT_OUT_DIR)
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    if args.variant:
        print("AB_RESULT " + json.dumps(run_variant(args.variant, args.out)))
        return 0

    os.makedirs(args.out, exist_ok=True)
    results = []
    for variant in args.only or list(VARIANTS):
        print("[*] {} ...".format(VARIANTS[variant]), flush=True)
        proc = subprocess.run(
            [sys.executable, os.path.abspath(__file__), "--variant", variant, "--out", args.out],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        payload = [line for line in proc.stdout.splitlines() if line.startswith("AB_RESULT ")]
        if proc.returncode != 0 or not payload:
            tail = (proc.stderr or proc.stdout).strip().splitlines()[-3:]
            results.append({"variant": variant, "error": " | ".join(tail) or "falhou"})
            print("    falhou: {}".format(results[-1]["error"]), flush=True)
            continue
        res = json.loads(payload[-1][len("AB_RESULT "):])
        results.append(res)
        avg_first = sum(item["first_s"] for item in res["lines"]) / len(res["lines"])
        print("    carregar {:.1f}s | início médio {:.2f}s | RAM {:.0f} MB | reservada {:.0f} MB".format(
            res["load_s"], avg_first, res["ws_end_mb"] or 0, res["commit_end_mb"] or 0), flush=True)

    with open(os.path.join(args.out, "results.json"), "w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2)
    print("[OK] Relatorio: {}".format(write_report(results, args.out)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
