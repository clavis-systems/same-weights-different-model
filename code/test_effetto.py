"""Test della correzione e delle statistiche del passo 1, senza GPU ne' rete.
Eseguire dalla cartella con l'ambiente che ha transformers: python test_effetto.py"""
import unittest

import effetto as e


class TestCorrezione(unittest.TestCase):
    def test_estrai_boxed_e_ultimo_numero(self):
        self.assertEqual(e.estrai("so the answer is \\boxed{1,234}."), 1234.0)
        self.assertEqual(e.estrai("first \\boxed{3} then \\boxed{\\frac{1}{2}} no, \\boxed{18}"), 18.0)
        self.assertEqual(e.estrai("The total is 42 dollars."), 42.0)
        self.assertEqual(e.estrai("\\boxed{\\$7.50}"), 7.5)
        self.assertIsNone(e.estrai("no numbers here"))

    def test_giusta(self):
        self.assertTrue(e.giusta({"risposta": "\\boxed{72}", "oro": "72"}))
        self.assertFalse(e.giusta({"risposta": "\\boxed{71}", "oro": "72"}))
        self.assertTrue(e.giusta({"risposta": "\\boxed{18.0}", "oro": "18"}))

    def test_pensiero_vuoto(self):
        self.assertTrue(e.pensiero_vuoto("<think>\n\n</think>\nThe answer is \\boxed{3}"))
        self.assertFalse(e.pensiero_vuoto("<think>\nLet me compute 3 + 4 carefully step by step.\n</think> 7"))
        self.assertFalse(e.pensiero_vuoto("no think tags"))


class TestStatistica(unittest.TestCase):
    def test_mcnemar(self):
        self.assertEqual(e.mcnemar(0, 0), 1.0)
        self.assertAlmostEqual(e.mcnemar(0, 6), 2 / 64)
        self.assertEqual(e.mcnemar(5, 5), 1.0)


if __name__ == "__main__":
    unittest.main()
