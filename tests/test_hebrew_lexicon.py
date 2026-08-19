import unittest
from quarries.hebrew_lexicon import HebrewLexicon, normalize_hebrew


class HebrewLexiconTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lex = HebrewLexicon()

    @classmethod
    def tearDownClass(cls):
        cls.lex.close()

    def test_database_preserved(self):
        self.assertEqual(self.lex.stats().words, 8674)

    def test_niqqud_normalization(self):
        self.assertEqual(normalize_hebrew("בְּרָכָה"), normalize_hebrew("ברכה"))

    def test_strongs_exact(self):
        rows = self.lex.search("H1293")
        self.assertEqual(rows[0]["strong_id"], "H1293")

    def test_hebrew_lookup(self):
        rows = self.lex.search("בְּרָכָה", limit=5)
        self.assertTrue(any(r["strong_id"] == "H1293" for r in rows))

    def test_fuzzy_transliteration(self):
        rows = self.lex.search("berakhah", limit=5)
        self.assertTrue(any(r["strong_id"] == "H1293" for r in rows))


if __name__ == "__main__":
    unittest.main()
