import pickle
import zlib
import re
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLES_DIR = os.path.join(PROJECT_ROOT, "samples")
rpa_path = r'D:\Games\TheHomeOfPleasure-0.3.3-pc\game\scripts.rpa'

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

hints = {}
total_menus = 0

for rf in sorted([k for k in index if k.endswith('.rpy')]):
    content = get_file(rf).decode('utf-8-sig', 'replace')
    lines = content.splitlines()
    
    current_label = os.path.splitext(rf)[0]
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Track labels
        m_lbl = re.match(r'^\s*label\s+([a-zA-Z0-9_]+):', line)
        if m_lbl:
            current_label = m_lbl.group(1)
        
        # Track menus
        m_menu = re.match(r'^(\s*)menu(?:\s+\w+)?\s*:', line)
        if m_menu:
            total_menus += 1
            menu_indent = len(m_menu.group(1))
            i += 1
            current_choice = None
            current_choice_cond = ""
            choice_lines = []
            
            def flush_choice(lbl, caption, cond, clines):
                if not caption or not clines:
                    return
                effects = []
                for cl in clines:
                    cl_str = cl.strip()
                    # Variable modifications: $ var += val or $ var -= val or $ var = val
                    m_vars = re.findall(r'\$?\s*([a-zA-Z0-9_]+\s*(?:\+=|-=|=)\s*[a-zA-Z0-9_"\'.]+)', cl_str)
                    for v in m_vars:
                        v_clean = v.replace('$', '').strip()
                        # Filter out non-stat internals
                        if any(k in v_clean for k in ['renpy.', 'config.', 'persistent.', 'cps=', 'style.']):
                            continue
                        if v_clean not in effects:
                            effects.append(v_clean)
                    # Jumps
                    m_jmp = re.search(r'jump\s+([a-zA-Z0-9_]+)', cl_str)
                    if m_jmp:
                        jmp_target = m_jmp.group(1)
                        if jmp_target not in ('expression', 'endgame'):
                            effects.append(f"Jump -> {jmp_target}")
                
                # Keep significant effects (stats, affection, lust, love, money, plot jumps)
                if effects:
                    key = (lbl, caption)
                    hints[key] = "; ".join(effects)

            while i < len(lines):
                sub_line = lines[i]
                if not sub_line.strip():
                    i += 1
                    continue
                sub_indent = len(sub_line) - len(sub_line.lstrip())
                if sub_indent <= menu_indent:
                    flush_choice(current_label, current_choice, current_choice_cond, choice_lines)
                    current_choice = None
                    choice_lines = []
                    break
                
                # Check choice caption: "caption" [if cond]:
                m_choice = re.match(r'^\s*(?:"([^"]+)"|\'([^\']+)\')(?:\s+if\s+([^:]+))?\s*:', sub_line)
                if m_choice:
                    flush_choice(current_label, current_choice, current_choice_cond, choice_lines)
                    current_choice = (m_choice.group(1) or m_choice.group(2)).strip()
                    current_choice_cond = (m_choice.group(3) or "").strip()
                    choice_lines = []
                else:
                    if current_choice:
                        choice_lines.append(sub_line)
                i += 1
            
            if current_choice:
                flush_choice(current_label, current_choice, current_choice_cond, choice_lines)
            continue
        i += 1

print(f"Total menus processed: {total_menus}")
print(f"Total choice hints with consequences extracted: {len(hints)}")

output_lines = [
    "# Generated for The Home of Pleasure v0.3.3",
    "init -2 python:",
    "    GENERATED_CHOICE_HINTS = {"
]
for (lbl, cap), eff in sorted(hints.items()):
    clean_cap = cap.replace("'", "\\'")
    clean_eff = eff.replace("'", "\\'")
    output_lines.append(f"        ('{lbl}', '{clean_cap}'): '{clean_eff}',")
output_lines.append("    }\n")

output_path = os.path.join(SAMPLES_DIR, "the_home_of_pleasure_choice_hints_generated.rpy")
with open(output_path, "w", encoding="utf-8") as out:
    out.write("\n".join(output_lines))
print(f"Saved hints to: {output_path}")
