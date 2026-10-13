import pickle
import zlib
import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

rpa_path = r'D:\Games\FemboySorority-0.4-Public-pc\FemboySorority-0.4-pc\game\archive.rpa'

with open(rpa_path, 'rb') as f:
    header = f.read(40)
    offset = int(header[8:24], 16)
    key = int(header[25:33], 16)
    f.seek(offset)
    index = pickle.loads(zlib.decompress(f.read()))

    def get_file(name):
        entry = index[name][0]
        f.seek(entry[0] ^ key)
        return (entry[2] if len(entry) > 2 else b'') + f.read(entry[1] ^ key)

    string_speakers = {}
    menus = []
    flags_or_vars = set()

    for rf in sorted([k for k in index if k.endswith('.rpy')]):
        content = get_file(rf).decode('utf-8-sig', 'replace')
        lines = content.splitlines()
        for i, line in enumerate(lines):
            # check string speaker: "Speaker" "Line"
            m_str = re.match(r'^\s*["\']([^"\']+)["\']\s+["\'](.*)["\']\s*$', line)
            if m_str:
                spk = m_str.group(1).strip()
                if len(spk) < 30 and not any(p in spk for p in ['.', '{', 'cps=', 'size=']):
                    string_speakers[spk] = string_speakers.get(spk, 0) + 1
            if re.match(r'^\s*menu(?:\s+\w+)?\s*:', line):
                menus.append((rf, i+1, line.strip()))
            m_var = re.match(r'^\s*\$?\s*([a-zA-Z0-9_]+)\s*(\+=|-=|=)\s*', line)
            if m_var:
                flags_or_vars.add(m_var.group(1))

    print('=== STRING SPEAKERS ("Name" "Line") ===')
    for s, c in sorted(string_speakers.items(), key=lambda x: -x[1]):
        print(f'  {s:20}: {c}')

    print(f'\nTotal menus found: {len(menus)}')
    for m in menus:
        print(f'  {m[0]}:{m[1]} -> {m[2]}')
