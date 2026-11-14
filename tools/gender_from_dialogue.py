"""
Infere o genero de cada personagem pelo pronome usado no dialogo.

Para cada personagem, procura o nome (ultima palavra do nome de exibicao) nas
falas de todos os locutores e conta pronomes gendered proximos ao nome. O
resultado serve de base para o voice_map.json.
"""
import json
import re
import sys

MALE_PRONOUNS = re.compile(r"\b(he|him|his|himself)\b", re.I)
FEMALE_PRONOUNS = re.compile(r"\b(she|her|hers|herself)\b", re.I)

# Palavras que indicam o genero sem depender de pronome.
FEMALE_WORDS = re.compile(r"\b(girl|woman|lady|miss|mrs|ms\.|she|her)\b", re.I)
MALE_WORDS = re.compile(r"\b(boy|man|guy|mr\.|sir|he|his)\b", re.I)


def candidate_terms(display_name, varname):
    """Nomes pelos quais o personagem pode ser citado no dialogo."""
    terms = set()
    if display_name:
        cleaned = re.sub(r"^(Professor|Doctor|Dr\.|Mr\.|Mrs\.|Ms\.|Nurse|Sir|Lady)\s+", "", display_name).strip()
        if cleaned:
            terms.add(cleaned)
        if " " in cleaned:
            terms.add(cleaned.split()[-1])
    if varname and len(varname) > 3 and varname.isalpha():
        terms.add(varname)
    return {t for t in terms if len(t) >= 4}


def analyze(data):
    dialogue = data.get("dialogue", {})
    characters = data["characters"]
    speakers = data["speakers"]

    all_lines = []
    for lines in dialogue.values():
        all_lines.extend(lines)

    results = {}
    for varname, count in speakers.items():
        display = characters.get(varname)
        terms = candidate_terms(display, varname)
        male = female = 0
        for term in terms:
            pattern = re.compile(r"\b" + re.escape(term) + r"\b", re.I)
            for line in all_lines:
                if not pattern.search(line):
                    continue
                male += len(MALE_PRONOUNS.findall(line))
                female += len(FEMALE_PRONOUNS.findall(line))
        results[varname] = {
            "display": display,
            "lines": count,
            "male": male,
            "female": female,
        }
    return results


def main():
    path = sys.argv[1]
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    results = analyze(data)
    for varname, info in sorted(results.items(), key=lambda kv: -kv[1]["lines"]):
        male, female = info["male"], info["female"]
        if male + female == 0:
            verdict = "?"
        elif female > male * 1.3:
            verdict = "F"
        elif male > female * 1.3:
            verdict = "M"
        else:
            verdict = "~"
        print("{:<14} {:<24} {:>6} falas  he/him={:<5} she/her={:<5} => {}".format(
            varname, str(info["display"]), info["lines"], male, female, verdict))


if __name__ == "__main__":
    main()
