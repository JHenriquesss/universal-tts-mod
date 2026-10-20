import json
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLES_DIR = os.path.join(PROJECT_ROOT, "samples")
TARGET_JSON = os.path.join(SAMPLES_DIR, "the_home_of_pleasure_voice_map.json")

voice_map = {}

def add_entry(key, voice):
    voice_map[key] = voice

# Protagonist & Narrator (am_onyx)
protagonists = [
    "default", "narrator", "Narrator", "NARRATOR", "None", "", "none",
    "n", "N",
    "player", "Player", "PLAYER", "you", "You", "YOU", "me", "Me", "ME",
    "mc", "MC", "Mc",
    "[PlayerName]", "[player]", "[player_name]", "PlayerName", "player_name",
    "aa1", "AA1", "???", "blank", "Blank"
]
for p in protagonists:
    add_entry(p, "am_onyx")

# Main Females
females = {
    # Sophie: af_bella
    "af_bella": [
        "s", "S", "Sophie", "sophie", "SOPHIE",
        "e", "E", "Ellie", "ellie", "ELLIE",
        "Customer", "customer", "CUSTOMER",
        "Shopkeeper", "shopkeeper", "SHOPKEEPER"
    ],
    # Beth: af_heart
    "af_heart": [
        "b", "B", "Beth", "beth", "BETH",
        "Guest", "guest", "GUEST"
    ],
    # Bo: af_sky
    "af_sky": [
        "bo", "Bo", "BO", "bO",
        "Blondie", "blondie", "BLONDIE",
        "Blonde woman", "blonde woman", "BLONDE WOMAN",
        "Sophie's friend", "sophie's friend", "Sophie's friend.", "sophie's friend."
    ],
    # Grace & Jennifer & Jane & Woman: af_sarah
    "af_sarah": [
        "g", "G", "Grace", "grace", "GRACE",
        "jn", "Jn", "JN", "Jennifer", "jennifer", "JENNIFER", "Jen", "jen", "JEN",
        "Jane", "jane", "JANE",
        "Woman", "woman", "WOMAN"
    ],
    # Kate & Georgina & Anya Malkova: af_nicole
    "af_nicole": [
        "k", "K", "Kate", "kate", "KATE",
        "ge", "Ge", "GE", "Georgina", "georgina", "GEORGINA",
        "Anya Malkova", "anya malkova", "ANYA MALKOVA"
    ],
    # Angela & Cashier & Receptionist & Staff: af_aoede
    "af_aoede": [
        "a", "A", "Angela", "angela", "ANGELA",
        "Cashier", "cashier", "CASHIER",
        "Receptionist", "receptionist", "RECEPTIONIST",
        "Staff", "staff", "STAFF"
    ],
    # Jessica: af_jessica
    "af_jessica": [
        "j", "J", "Jessica", "jessica", "JESSICA", "Jess", "jess", "JESS"
    ],
    # Cara & Redhead: af_river
    "af_river": [
        "c", "C", "Cara", "cara", "CARA",
        "Redhead", "redhead", "REDHEAD"
    ],
    # Lilith & Chyou & Mrs Li & Waitress: af_kore
    "af_kore": [
        "l", "L", "Lilith", "lilith", "LILITH",
        "ch", "Ch", "CH", "Chyou", "chyou", "CHYOU",
        "Mrs Li", "mrs li", "MRS LI",
        "Waitress", "waitress", "WAITRESS"
    ]
}

for voice, keys in females.items():
    for k in keys:
        add_entry(k, voice)

# Main Males & Secondaries
males = {
    # Mr Noonan, Bald Man, Boss, Phantom Shitter, Police Officer, The Men, Regional Manager: am_fenrir
    "am_fenrir": [
        "mr", "Mr", "MR", "Mr Noonan", "mr noonan", "MR NOONAN", "Noonan", "noonan",
        "Bald Man", "Bald man", "bald man", "BALD MAN",
        "Boss", "boss", "BOSS",
        "The Phantom Shitter", "the phantom shitter", "THE PHANTOM SHITTER",
        "Police Officer", "police officer", "POLICE OFFICER",
        "The men", "the men", "THE MEN",
        "Regional Manager", "regional manager", "REGIONAL MANAGER"
    ],
    # Paul & Council Worker: am_michael
    "am_michael": [
        "p", "P", "Paul", "paul", "PAUL",
        "Council Worker", "council worker", "COUNCIL WORKER"
    ],
    # Tony & Thomas & Waiter & His Friend & Andre: am_liam
    "am_liam": [
        "t", "T", "Tony", "tony", "TONY",
        "Thomas", "thomas", "THOMAS",
        "Waiter", "waiter", "WAITER",
        "His friend", "his friend", "HIS FRIEND",
        "Andre", "andre", "ANDRE"
    ],
    # D.I. Stoker, Mr Li, Ronnie, Vince, Gentleman, Angry Boyfriend, Undercover Officer: am_eric
    "am_eric": [
        "di", "Di", "DI", "D.I. Stoker", "d.i. stoker", "D.I. STOKER", "DI Stoker", "di stoker", "Stoker", "stoker",
        "li", "Li", "LI", "Mr Li", "mr li", "MR LI", "Li", "li",
        "Ronnie", "ronnie", "RONNIE",
        "Vince", "vince", "VINCE",
        "Gentleman", "gentleman", "GENTLEMAN",
        "Angry boyfriend", "angry boyfriend", "ANGRY BOYFRIEND",
        "Undercover officer", "undercover officer", "UNDERCOVER OFFICER"
    ],
    # Mick, Stephen, Young Man, Ride Attendant, Paul's Friend: am_adam
    "am_adam": [
        "Mick", "mick", "MICK",
        "Stephen", "stephen", "STEPHEN",
        "Young man", "young man", "YOUNG MAN",
        "Ride attendant", "ride attendant", "RIDE ATTENDANT",
        "Paul's friend", "paul's friend", "PAUL'S FRIEND"
    ]
}

for voice, keys in males.items():
    for k in keys:
        add_entry(k, voice)

with open(TARGET_JSON, "w", encoding="utf-8") as f:
    json.dump(voice_map, f, indent=4, ensure_ascii=False)

print(f"Generated {len(voice_map)} voice mappings in {TARGET_JSON}")
