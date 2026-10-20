import pickle
import zlib
import sys
import re
import os

sys.stdout.reconfigure(encoding='utf-8')

game_root = r"D:\Games\Much_Bigger_Than_my_Boyfriend\Much Bigger Than my Boyfriend"
game_dir = os.path.join(game_root, "game")
rpa_path = os.path.join(game_dir, "archive.rpa")

with open(rpa_path, 'rb') as f:
    header = f.read(40)
    parts = header.strip().split()
    offset = int(parts[1], 16)
    key = int(parts[2], 16)
    f.seek(offset)
    index = pickle.loads(zlib.decompress(f.read()))

    def get_file(name):
        chunks = []
        for entry in index[name]:
            f.seek(entry[0] ^ key)
            prefix = entry[2] if len(entry) > 2 else b''
            data = f.read(entry[1] ^ key)
            chunks.append(prefix + data)
        return b''.join(chunks)

    total_voice_lines = 0
    total_dialogues = 0
    voice_by_folder = {}

    rpy_files = sorted([k for k in index if k.endswith('.rpy') and not k.startswith('tl/')])
    print(f"Scanning {len(rpy_files)} non-tl rpy files...")

    voice_re = re.compile(r'^\s*voice\s+["\']([^"\']+)["\']')
    dialogue_re = re.compile(r'^\s*([a-zA-Z0-9_]+)\s+["\']')

    keywords = {
        'menu', 'play', 'scene', 'show', 'hide', 'with', 'jump', 'call',
        'stop', 'queue', 'voice', 'window', 'pause', 'pass', 'return',
        'translate', 'label', 'init', 'default', 'define', 'transform', 'image',
        'nvl', 'style', 'if', 'elif', 'else', 'while', 'python', 'renpy', '$'
    }

    voice_per_char = {}
    total_per_char = {}

    last_voice = None
    for k in rpy_files:
        content = get_file(k).decode('utf-8-sig', 'replace')
        for line in content.splitlines():
            mv = voice_re.match(line)
            if mv:
                vpath = mv.group(1)
                total_voice_lines += 1
                parts = vpath.split('/')
                folder = parts[1] if len(parts) > 1 else 'root'
                voice_by_folder[folder] = voice_by_folder.get(folder, 0) + 1
                last_voice = vpath
                continue

            md = dialogue_re.match(line)
            if md:
                tag = md.group(1)
                if tag not in keywords:
                    total_dialogues += 1
                    total_per_char[tag] = total_per_char.get(tag, 0) + 1
                    if last_voice:
                        voice_per_char[tag] = voice_per_char.get(tag, 0) + 1
            last_voice = None

    print(f"Total dialogue statements: {total_dialogues}")
    print(f"Total voice statements: {total_voice_lines}")
    print("Voice statements by folder:", voice_by_folder)
    print("\nVoice statements vs total dialogues per character tag:")
    for tag, tot in sorted(total_per_char.items(), key=lambda x: -x[1]):
        v_cnt = voice_per_char.get(tag, 0)
        pct = (v_cnt / tot * 100) if tot else 0
        print(f"  {tag:10}: {v_cnt:4} voiced / {tot:4} total ({pct:5.1f}%)")
