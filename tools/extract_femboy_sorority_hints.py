import pickle
import zlib
import re
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

# Caminhos do jogo e do arquivo gerado: argumentos da linha de comando.
# Uso: python tools/extract_femboy_sorority_hints.py <archive.rpa> <saida.rpy>
if len(sys.argv) < 3:
    print("Uso: python tools/extract_femboy_sorority_hints.py <archive.rpa> <saida.rpy>")
    sys.exit(1)

rpa_path = sys.argv[1]
output_path = sys.argv[2]

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

    hints = {}
    
    # Process each rpy file
    for rf in sorted([k for k in index if k.endswith('.rpy')]):
        content = get_file(rf).decode('utf-8-sig', 'replace')
        lines = content.splitlines()
        
        current_label = "unknown"
        
        i = 0
        while i < len(lines):
            line = lines[i]
            # Track label
            m_lbl = re.match(r'^\s*label\s+([a-zA-Z0-9_]+):', line)
            if m_lbl:
                current_label = m_lbl.group(1)
            
            # Check menu:
            m_menu = re.match(r'^(\s*)menu(?:\s+\w+)?\s*:', line)
            if m_menu:
                menu_indent = len(m_menu.group(1))
                i += 1
                current_choice = None
                choice_lines = []
                
                def flush_choice(lbl, caption, clines):
                    if not caption or not clines:
                        return
                    # Extract effects
                    effects = []
                    for cl in clines:
                        cl_str = cl.strip()
                        # $ var += val or $ var = val
                        m_vars = re.findall(r'\$?\s*([a-zA-Z0-9_]+\s*(?:\+=|-=|=)\s*[a-zA-Z0-9_"\'.]+)', cl_str)
                        for v in m_vars:
                            v_clean = v.replace('$', '').strip()
                            if v_clean not in effects and not any(k in v_clean for k in ['renpy.input', 'persistent.dsc', 'cps=']):
                                effects.append(v_clean)
                        # jumps
                        m_jmp = re.search(r'jump\s+([a-zA-Z0-9_]+)', cl_str)
                        if m_jmp:
                            effects.append(f"Jump -> {m_jmp.group(1)}")
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
                        # end of menu
                        flush_choice(current_label, current_choice, choice_lines)
                        current_choice = None
                        choice_lines = []
                        break
                    
                    # check if this is a choice caption
                    m_choice = re.match(r'^\s*(?:"([^"]+)"|\'([^\']+)\')\s*:', sub_line)
                    if m_choice:
                        flush_choice(current_label, current_choice, choice_lines)
                        current_choice = (m_choice.group(1) or m_choice.group(2)).strip()
                        choice_lines = []
                    else:
                        if current_choice:
                            choice_lines.append(sub_line)
                    i += 1
                
                if current_choice:
                    flush_choice(current_label, current_choice, choice_lines)
                continue
            i += 1

print(f"Total clean choice hints extracted: {len(hints)}")
output_lines = [
    "# Generated for Femboy Sorority v0.4",
    "init -2 python:",
    "    GENERATED_CHOICE_HINTS = {"
]
for (lbl, cap), eff in sorted(hints.items()):
    clean_cap = cap.replace("'", "\\'")
    clean_eff = eff.replace("'", "\\'")
    output_lines.append(f"        ('{lbl}', '{clean_cap}'): '{clean_eff}',")
    print(f"  ('{lbl}', '{cap}') -> '{eff}'")
output_lines.append("    }\n")

with open(output_path, "w", encoding="utf-8") as out:
    out.write("\n".join(output_lines))
print(f"Saved to {output_path}")
