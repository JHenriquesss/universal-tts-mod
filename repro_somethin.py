from renpy_mod.text_cleaner import TextCleaner

test_cases = [
    "Thought you'd be neck-deep in paperwork or somethin'.",
    "somethin'",
    "somethin'.",
    "somethin'!",
    "somethin'?",
]

for tc in test_cases:
    print(f"Original: {tc}")
    print(f"Cleaned:  {TextCleaner.clean(tc)}")
    print("-" * 20)
