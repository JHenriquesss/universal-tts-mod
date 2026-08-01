import unittest
import sys
import os
import inspect

sys.dont_write_bytecode = True

# Adiciona o diretório raiz ao path para importar o módulo renpy_mod
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from renpy_mod.text_cleaner import TextCleaner

class TestTextCleaner(unittest.TestCase):
    def test_basic_cleaning(self):
        self.assertEqual(TextCleaner.clean("Olá Mundo"), "Olá Mundo")
    
    def test_remove_tags(self):
        self.assertEqual(TextCleaner.clean("Texto {b}negrito{/b}"), "Texto negrito")
        self.assertEqual(TextCleaner.clean("Texto {color=#f00}colorido{/color}"), "Texto colorido")
        self.assertEqual(TextCleaner.clean("Texto {size=20}grande{/size}"), "Texto grande")
    
    def test_remove_wait_tags(self):
        self.assertEqual(TextCleaner.clean("Espere{w} um pouco{p}."), "Espere um pouco.")
        self.assertEqual(TextCleaner.clean("Rápido{nw}"), "Rápido")

    def test_handle_escapes(self):
        self.assertEqual(TextCleaner.clean("Isso é um [[colchete]]"), "Isso é um [colchete]")
        self.assertEqual(TextCleaner.clean("Isso é uma {{chave}}"), "Isso é uma {chave}")

    def test_multiple_spaces(self):
        self.assertEqual(TextCleaner.clean("Muitos    espaços"), "Muitos espaços")

    def test_complex_case(self):
        input_text = "{color=#ff0}{b}Eileen:{/b}{/color} [[Olá]] {i}Mundo{/i}!{w}{nw}"
        expected = "Eileen: [Olá] Mundo!"
        self.assertEqual(TestTextCleaner.clean_and_compare(input_text), expected)

    def test_symbols_removal(self):
        self.assertEqual(TextCleaner.clean("Oi *suspira*"), "Oi suspira")
        self.assertEqual(TextCleaner.clean("Voz manhosa~"), "Voz manhosa")
        self.assertEqual(TextCleaner.clean("Música ♪♫"), "Música")
        self.assertEqual(TextCleaner.clean("Estrela ★☆ Coração ♥♡"), "Estrela Coração")
        # Japanese quotes and brackets
        self.assertEqual(TextCleaner.clean("「Olá」 e 【Isto】"), '"Olá" e [Isto]')
        # Ellipses
        self.assertEqual(TextCleaner.clean("Pensando…"), "Pensando...")

    def test_punctuation_normalization(self):
        self.assertEqual(TextCleaner.clean("O que???"), "O que?")
        self.assertEqual(TextCleaner.clean("Incrível!!!"), "Incrível!")
        self.assertEqual(TextCleaner.clean("Sério??!!"), "Sério?!")
        self.assertEqual(TextCleaner.clean("Uau!!!!"), "Uau!")

    def test_vn_specific_chars(self):
        # Em-dash should be space for pause
        self.assertEqual(TextCleaner.clean("Pausa — longa"), "Pausa longa")

    def test_slang_and_apostrophes(self):
        # Expansion of in' to ing
        self.assertEqual(TextCleaner.clean("Brooklyn Comin' right up!"), "Brooklyn Coming right up!")
        self.assertEqual(TextCleaner.clean("It's comin'!"), "It's coming!")
        self.assertEqual(TextCleaner.clean("Doin' fine."), "Doing fine.")
        # Leading apostrophes
        self.assertEqual(TextCleaner.clean("'cause I said so"), "cause I said so")
        self.assertEqual(TextCleaner.clean("It's 'til tomorrow"), "It's til tomorrow")
        # Standard contractions should be preserved
        self.assertEqual(TextCleaner.clean("Don't do it"), "Don't do it")
        self.assertEqual(TextCleaner.clean("They're here"), "They're here")
        # Smart apostrophes should be handled and then fixed if slang
        self.assertEqual(TextCleaner.clean("Comin’"), "Coming")

    @staticmethod
    def clean_and_compare(text):
        # Helper para o teste complexo que pode ter espaços extras devido à remoção de tags
        return TextCleaner.clean(text)

    def test_negative_empty_input(self):
        self.assertEqual(TextCleaner.clean(""), "")
        self.assertEqual(TextCleaner.clean(None), "")
        self.assertEqual(TextCleaner.clean("   "), "")

    def test_negative_extreme_length(self):
        # Testa comportamento com strings muito longas (10k caracteres)
        long_input = "a" * 10000
        self.assertEqual(TextCleaner.clean(long_input), long_input)
        
        # Tags aninhadas profundamente ou malformadas
        malformed = "{" * 1000 + "b" + "}" * 1000
        result = TextCleaner.clean(malformed)
        self.assertIsInstance(result, str) # Deve sobreviver sem recursão infinita ou crash

    def test_negative_control_characters(self):
        # Caracteres de controle não devem quebrar o cleaner
        text_with_null = "Olá\0Mundo"
        self.assertIn("Olá", TextCleaner.clean(text_with_null))
        
        text_with_newlines = "Linha 1\nLinha 2\r\nLinha 3"
        self.assertEqual(TextCleaner.clean(text_with_newlines), "Linha 1 Linha 2 Linha 3")

    def test_mojibake_fixing(self):
        # Ellipsis
        self.assertEqual(TextCleaner.clean("againâ€!"), "again...!")
        self.assertEqual(TextCleaner.clean("Helloâ€¦"), "Hello...")
        # Apostrophes
        self.assertEqual(TextCleaner.clean("Itâ€™s"), "It's")
        # Quotes
        self.assertEqual(TextCleaner.clean("â€œQuotesâ€\x9d"), '"Quotes"')
        # Dashes
        self.assertEqual(TextCleaner.clean("Wordâ€”word"), "Word word") # Em-dash becomes space in step 6

    def test_default_pronunciation_overrides(self):
        self.assertEqual(TextCleaner.clean("Nadia saw Dezno."), "Nah-dee-ah saw Dez-no.")
        self.assertEqual(TextCleaner.clean("Nahdia met Ellie."), "Nah-dee-ah met El-lee.")
        self.assertEqual(TextCleaner.clean("Kal'trath and Heleon."), "Kal trath and He-leon.")

    def test_custom_pronunciation_overrides(self):
        overrides = {r"\bXyra\b": "Zy-rah"}
        self.assertEqual(TextCleaner.clean("Xyra arrives.", pronunciation_overrides=overrides), "Zy-rah arrives.")

    def test_custom_pronunciation_overrides_can_replace_default(self):
        overrides = {r"\bNadia\b": "Nay-dia"}
        self.assertEqual(TextCleaner.clean("Nadia arrives.", pronunciation_overrides=overrides), "Nay-dia arrives.")

    def test_empty_pronunciation_overrides_keep_normal_cleaning(self):
        self.assertEqual(TextCleaner.clean("Texto {i}limpo{/i}.", pronunciation_overrides={}), "Texto limpo.")

    def test_pronunciation_defaults_are_not_built_inside_clean_hot_path(self):
        from renpy_mod import text_cleaner

        clean_source = inspect.getsource(TextCleaner.clean)
        self.assertIn("DEFAULT_PRONUNCIATION_OVERRIDES", dir(text_cleaner))
        self.assertNotIn(r"\bNadia\b", clean_source)
        self.assertNotIn(r"\bDezno\b", clean_source)

if __name__ == "__main__":
    unittest.main()
