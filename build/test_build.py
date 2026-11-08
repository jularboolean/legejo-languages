"""Tests for build.py: python3 -m unittest discover -s build"""

import importlib.util
import json
import os
import tempfile
import unittest
import zipfile

_spec = importlib.util.spec_from_file_location("langpack_build", os.path.join(os.path.dirname(__file__), "build.py"))
build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build)

LEMMAS = [
    ["bank", "noun", "bench; bank"],
    ["gaan", "verb", "to go"],
    ["huis", "noun", "house"],
    ["zijn", "verb, pron", "to be; his"],
    ["Ärger", "noun", "anger", "Ärger"],
]
FORMS = [
    ["bank", "bank"],
    ["banken", "bank"],
    ["gaan", "gaan"],
    ["ging", "gaan"],
    ["huis", "huis"],
    ["huizen", "huis"],
    ["was", "zijn,bank"],
    ["zijn", "zijn"],
]


class Fixes(unittest.TestCase):
    def apply(self, text):
        return build.apply_fixes([row[:] for row in LEMMAS], [row[:] for row in FORMS], build.parse_fixes(text))

    def test_comments_and_blank_lines_are_skipped(self):
        self.assertEqual(build.parse_fixes("# a comment\n\n   # indented\n"), [])

    def test_gloss_replaces_the_english(self):
        lemmas, forms = self.apply("gloss\tbank\tbench, couch\n")
        self.assertEqual(dict((r[0], r[2]) for r in lemmas)["bank"], "bench, couch")
        self.assertEqual(forms, FORMS)

    def test_drop_removes_the_lemma_and_forms_only_it_had(self):
        lemmas, forms = self.apply("drop\tbank\n")
        self.assertNotIn("bank", [r[0] for r in lemmas])
        self.assertEqual(dict(forms).get("banken"), None)
        self.assertEqual(dict(forms)["was"], "zijn")

    def test_form_adds_a_link_once(self):
        lemmas, forms = self.apply("form\tGingen\tgaan\nform\tging\tgaan\nform\twas\thuis\n")
        forms = dict(forms)
        self.assertEqual(forms["gingen"], "gaan")
        self.assertEqual(forms["ging"], "gaan")
        self.assertEqual(forms["was"], "zijn,bank,huis")

    def test_output_is_in_byte_order(self):
        lemmas, forms = self.apply("form\tzzz\tgaan\nform\taaa\tgaan\n")
        keys = [r[0] for r in lemmas]
        self.assertEqual(keys, sorted(keys, key=lambda k: k.encode()))
        self.assertEqual(keys[-1], "Ärger")  # upper-case non-ASCII sorts after z in bytes
        names = [r[0] for r in forms]
        self.assertEqual(names, sorted(names, key=lambda k: k.encode()))

    def test_written_column_is_kept(self):
        lemmas, _ = self.apply("gloss\tÄrger\tannoyance\n")
        self.assertEqual(lemmas[-1], ["Ärger", "noun", "annoyance", "Ärger"])

    def test_unknown_key_and_bad_lines_are_errors(self):
        with self.assertRaises(build.BuildError):
            self.apply("gloss\tnope\tnothing\n")
        with self.assertRaises(build.BuildError):
            self.apply("drop\tbank\nform\tbanken\tbank\n")
        for bad in ("gloss\tbank\n", "replace\tbank\tx\n", "drop bank\n", "form\t\tbank\n"):
            with self.assertRaises(build.BuildError, msg=bad):
                build.parse_fixes(bad)


class Also(unittest.TestCase):
    def test_merged_lower_case_without_duplicates_or_the_code(self):
        meta = build.merge_also({"also": ["nld", "dutch"]}, ["NLD", "nl", "Vlaams", " dutch "], "nl")
        self.assertEqual(meta["also"], ["nld", "dutch", "vlaams"])


class Index(unittest.TestCase):
    def test_entry_counts_the_files_and_hashes_the_zip(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack = os.path.join(tmp, "nl")
            os.makedirs(pack)
            with open(os.path.join(pack, "pack.json"), "w") as f:
                json.dump({"format": 1, "language": "nl", "version": "2026-01-02", "license": "CC BY-SA 4.0",
                           "attribution": build.ATTRIBUTION, "also": []}, f)
            build.write_tsv(os.path.join(pack, "lemmas.tsv"), LEMMAS)
            build.write_tsv(os.path.join(pack, "forms.tsv"), FORMS)
            zip_path = os.path.join(tmp, "nl.zip")
            build.write_zip(pack, zip_path, "readme")
            recipe = {"code": "nl", "name": "Nederlands", "english": "Dutch", "kaikki": "Dutch"}
            entry = build.index_entry(recipe, pack, zip_path)

            with zipfile.ZipFile(zip_path) as z:
                self.assertEqual(sorted(z.namelist()), ["README.txt", "forms.tsv", "lemmas.tsv", "pack.json"])
                self.assertTrue(all(i.compress_type == zipfile.ZIP_DEFLATED for i in z.infolist()))
            self.assertEqual(entry["lemmas"], 5)
            self.assertEqual(entry["forms"], 8)
            self.assertEqual(entry["version"], "2026-01-02")
            self.assertEqual(entry["bytes"], os.path.getsize(zip_path))
            self.assertEqual(entry["sha256"], build.sha256(zip_path))
            self.assertEqual(len(entry["sha256"]), 64)

            index = build.make_index([dict(entry, code="sw"), entry], "2026-01-03")
            self.assertEqual(index["format"], 1)
            self.assertEqual(index["built"], "2026-01-03")
            self.assertEqual([p["code"] for p in index["packs"]], ["nl", "sw"])
            self.assertEqual(set(entry), {"code", "name", "english", "version", "lemmas", "forms", "bytes",
                                          "sha256", "license", "attribution"})


class Recipes(unittest.TestCase):
    def test_every_recipe_loads(self):
        codes = build.all_codes()
        self.assertIn("nl", codes)
        for code in codes:
            recipe = build.load_recipe(code)
            self.assertTrue(build.dump_url(recipe).startswith("https://kaikki.org/dictionary/"))

    def test_dump_url(self):
        self.assertEqual(build.dump_url({"kaikki": "Dutch"}),
                         "https://kaikki.org/dictionary/Dutch/kaikki.org-dictionary-Dutch.jsonl.gz")


if __name__ == "__main__":
    unittest.main()
