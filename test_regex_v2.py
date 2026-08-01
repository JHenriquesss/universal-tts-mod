import re

def clean_old(text):
    return re.sub(r'\b(\w+)in\'(?=\s|$|[.,!?])', r'\1ing', text)

def clean_new(text):
    # Match any word ending in 'n' followed by an apostrophe
    return re.sub(r'\b(\w+n)\'(?=\s|$|[.,!?])', r'\1g', text)

test_cases = [
    "somethin'",
    "comin'",
    "doin'",
    "runnin'",
    "nothin'",
]

for tc in test_cases:
    print(f"Original: {tc}")
    print(f"Old:      {clean_old(tc)}")
    print(f"New:      {clean_new(tc)}")
    print("-" * 20)
