import os
import glob
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

game_dir = r"C:\Users\joseh_fguhny9\OneDrive\Área de Trabalho\Nova pasta (4)\tts renply\Jogo atual\Cockham-v0.8.1-pc\Cockham-v0.8.1-pc\game"
rpy_files = glob.glob(os.path.join(game_dir, "*.rpy"))

characters = {}
speakers = {}
string_speakers = {}
keywords = {
    'menu', 'play', 'scene', 'show', 'hide', 'with', 'jump', 'call',
    'stop', 'queue', 'voice', 'window', 'pause', 'pass', 'return',
    'translate', 'label', 'init', 'default', 'define', 'transform', 'image',
    'nvl', 'style', 'if', 'elif', 'else', 'while', 'python', 'renpy', '$'
}

for rf in rpy_files:
    if os.path.basename(rf).startswith(('tts_', 'zzz_')):
        continue
    with open(rf, 'r', encoding='utf-8-sig', errors='replace') as f:
        for line in f:
            m_def = re.match(r'^\s*define\s+([a-zA-Z0-9_]+)\s*=\s*Character\s*\(\s*[\'"]([^\'"]*)[\'"]', line)
            if m_def:
                characters[m_def.group(1)] = m_def.group(2).strip()
            m_spk = re.match(r'^\s*([a-zA-Z0-9_]+)\s+[\'"](.*)[\'"]\s*$', line)
            if m_spk:
                spk = m_spk.group(1)
                if spk not in keywords:
                    speakers[spk] = speakers.get(spk, 0) + 1
            m_str_spk = re.match(r'^\s*[\'"]([^\'"]+)[\'"]\s+[\'"](.*)[\'"]\s*$', line)
            if m_str_spk:
                s_spk = m_str_spk.group(1).strip()
                string_speakers[s_spk] = string_speakers.get(s_spk, 0) + 1

print('=== DEFINED CHARACTERS ===')
for k, v in sorted(characters.items()):
    cnt = speakers.get(k, 0)
    print(f'{k:10} -> {v:30} (dialogue lines: {cnt})')

print('\n=== STRING SPEAKERS ("Name" "Line") ===')
for s, cnt in sorted(string_speakers.items(), key=lambda x: -x[1]):
    print(f'{s:25} (lines: {cnt})')
