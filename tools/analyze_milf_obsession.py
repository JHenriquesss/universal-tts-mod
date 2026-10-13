import pickle
import zlib
import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

rpa_path = r'D:\Games\MILF_Obsession-0.5.0-pc\MILF_Obsession-0.5.0-pc\game\archive.rpa'

with open(rpa_path, 'rb') as f:
    l = f.read(40)
    offset = int(l[8:24], 16)
    key = int(l[25:33], 16)
    f.seek(offset)
    index = pickle.loads(zlib.decompress(f.read()))

    def get_file(name):
        entry = index[name][0]
        f_offset, f_len = entry[0] ^ key, entry[1] ^ key
        prefix = entry[2] if len(entry) > 2 else b''
        f.seek(f_offset)
        return prefix + f.read(f_len)

    characters = {}
    speakers = {}
    rpy_files = sorted([k for k in index.keys() if k.endswith('.rpy')])
    keywords = {
        'menu', 'play', 'scene', 'show', 'hide', 'with', 'jump', 'call',
        'stop', 'queue', 'voice', 'window', 'pause', 'pass', 'return',
        'translate', 'label', 'init', 'default', 'define', 'transform', 'image',
        'nvl', 'style', 'if', 'elif', 'else', 'while', 'python', 'renpy'
    }

    for rf in rpy_files:
        content = get_file(rf).decode('utf-8-sig', 'replace')
        for line in content.splitlines():
            # Check define
            m_def = re.match(r'^\s*define\s+([a-zA-Z0-9_]+)\s*=\s*Character\s*\(\s*[\'"]([^\'"]*)[\'"]', line)
            if m_def:
                characters[m_def.group(1)] = m_def.group(2)

            # Check dialogue speaker
            m_spk = re.match(r'^\s*([a-zA-Z0-9_]+)\s+[\'"](.*)[\'"]\s*$', line)
            if m_spk:
                spk = m_spk.group(1)
                if spk not in keywords:
                    speakers[spk] = speakers.get(spk, 0) + 1

    print('=== ALL DEFINED CHARACTERS ===')
    for k, v in sorted(characters.items()):
        cnt = speakers.get(k, 0)
        print(f'{k:10} -> {v:25} (lines: {cnt})')

    print('\n=== SPEAKERS USED IN SCRIPT BUT NOT DEFINED IN Character() ===')
    for s, cnt in sorted(speakers.items()):
        if s not in characters:
            print(f'{s:10} (lines: {cnt})')
