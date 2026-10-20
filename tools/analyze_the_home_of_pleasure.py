import pickle
import zlib
import sys
import re
import os

sys.stdout.reconfigure(encoding='utf-8')

game_root = r"D:\Games\TheHomeOfPleasure-0.3.3-pc"
game_dir = os.path.join(game_root, "game")
rpa_path = os.path.join(game_dir, "scripts.rpa")

if not os.path.exists(rpa_path):
    print(f"Error: {rpa_path} not found.")
    sys.exit(1)

with open(rpa_path, 'rb') as f:
    header = f.read(40)
    parts = header.strip().split()
    offset = int(parts[1], 16)
    key = int(parts[2], 16)
    f.seek(offset)
    index = pickle.loads(zlib.decompress(f.read()))

def get_file(name):
    with open(rpa_path, 'rb') as f:
        chunks = []
        for entry in index[name]:
            f.seek(entry[0] ^ key)
            prefix = entry[2] if len(entry) > 2 else b''
            data = f.read(entry[1] ^ key)
            chunks.append(prefix + data)
        return b''.join(chunks)

tag_counts = {}
string_speakers = {}
menus = []
choices_list = []
flags_or_vars = set()

dialogue_re = re.compile(r'^\s*([a-zA-Z0-9_]+)\s+["\']')
str_spk_re = re.compile(r'^\s*["\']([^"\']+)["\']\s+["\'](.*)["\']\s*$')
menu_re = re.compile(r'^\s*menu(?:\s+\w+)?\s*:')
choice_re = re.compile(r'^\s*["\']([^"\']+)["\'](?:\s+if\s+([^:]+))?\s*:\s*$')

keywords = {
    'menu', 'play', 'scene', 'show', 'hide', 'with', 'jump', 'call',
    'stop', 'queue', 'voice', 'window', 'pause', 'pass', 'return',
    'translate', 'label', 'init', 'default', 'define', 'transform', 'image',
    'nvl', 'style', 'if', 'elif', 'else', 'while', 'python', 'renpy', '$'
}

rpy_files = sorted([k for k in index if k.endswith('.rpy')])
print(f"Scanning {len(rpy_files)} rpy files in scripts.rpa...")

in_menu = False
current_menu_file = ""
current_menu_line = 0

for rf in rpy_files:
    content = get_file(rf).decode('utf-8-sig', 'replace')
    lines = content.splitlines()
    in_menu = False
    for i, line in enumerate(lines):
        line_num = i + 1
        
        # Check string speaker
        ms = str_spk_re.match(line)
        if ms:
            spk = ms.group(1).strip()
            if len(spk) < 30 and not any(c in spk for c in ['{', '[', 'http', '.png', '.jpg', '.webp']):
                string_speakers[spk] = string_speakers.get(spk, 0) + 1

        # Check dialogue tag
        md = dialogue_re.match(line)
        if md:
            tag = md.group(1)
            if tag not in keywords:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        # Check menu
        if menu_re.match(line):
            menus.append((rf, line_num, line.strip()))
            in_menu = True
            current_menu_file = rf
            current_menu_line = line_num
            continue

        if in_menu:
            indent = len(line) - len(line.lstrip())
            if line.strip() and indent <= 4 and not line.strip().startswith('#'):
                in_menu = False
            else:
                mc_choice = choice_re.match(line)
                if mc_choice:
                    c_text = mc_choice.group(1).strip()
                    c_cond = mc_choice.group(2).strip() if mc_choice.group(2) else ""
                    choices_list.append((rf, line_num, c_text, c_cond))

        # Check vars
        m_var = re.match(r'^\s*\$?\s*([a-zA-Z0-9_]+)\s*(\+=|-=|=)\s*', line)
        if m_var:
            flags_or_vars.add(m_var.group(1))

        # Check aa1_name assignment
        m_aa1 = re.search(r'aa1_name\s*=\s*["\']([^"\']+)["\']', line)
        if m_aa1:
            flags_or_vars.add(f"AA1:{m_aa1.group(1)}")

print("\n=== DIALOGUE TAGS ===")
for t, cnt in sorted(tag_counts.items(), key=lambda x: -x[1]):
    print(f"  {t:15}: {cnt}")

print("\n=== AA1_NAME VALUES ===")
aa1_values = sorted([x[4:] for x in flags_or_vars if x.startswith("AA1:")])
for v in aa1_values:
    print(f"  {v}")

print("\n=== STRING SPEAKERS ===")
for s, cnt in sorted(string_speakers.items(), key=lambda x: -x[1]):
    print(f"  {s:25}: {cnt}")

print(f"\n=== MENUS AND CHOICES ===")
print(f"Total menus: {len(menus)}")
print(f"Total choices: {len(choices_list)}")
print("Sample choices (first 25):")
for ch in choices_list[:25]:
    cond_str = f" [if {ch[3]}]" if ch[3] else ""
    print(f"  {ch[0]}:{ch[1]} -> \"{ch[2]}\"{cond_str}")
