#!/usr/bin/env python3
"""Build Legejo language packs from their recipes.

    python3 build/build.py --langpack PATH [--cache DIR] [--dist DIR] [--offline] [code ...]

For each language (all under languages/ when no code is given): download the
kaikki.org dump into the cache, run the `langpack` builder, merge the
recipe's `also` into pack.json, apply fixes.tsv, and write <code>.zip into
the dist directory. When every language built, dist/index.json lists them.
Python 3 standard library only.
"""

import argparse
import datetime
import email.utils
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LANGUAGES = os.path.join(ROOT, "languages")
CODE = re.compile(r"^[a-z]{2,3}$")
LICENSE = "CC BY-SA 4.0"
ATTRIBUTION = "Wiktionary contributors (CC BY-SA 4.0), via kaikki.org"
MAX_ZIP = 64 << 20
MAX_UNPACKED = 256 << 20

README_TXT = """Legejo language pack: {name} ({code}), version {version}

A study list for books in {english}: each word taken to its dictionary
form with a short English meaning. Import this zip in Legejo under
Admin > Languages, or unzip it into <data dir>/languages/{code}/ and
restart Legejo.

Data: the English Wiktionary (https://en.wiktionary.org), extracted by
kaikki.org (https://kaikki.org), shortened and reorganised by the Legejo
langpack builder. Attribution: {attribution}.

This pack is licensed under the Creative Commons Attribution-ShareAlike
4.0 International licence: https://creativecommons.org/licenses/by-sa/4.0/
You may share and adapt it, also commercially, if you give the same
attribution and share your changes under the same licence.

Source: https://github.com/jularboolean/legejo-languages
"""


class BuildError(Exception):
    pass


# ------------------------------------------------------------ recipes


def load_recipe(code):
    path = os.path.join(LANGUAGES, code, "recipe.json")
    try:
        with open(path, encoding="utf-8") as f:
            recipe = json.load(f)
    except (OSError, ValueError) as e:
        raise BuildError(f"{path}: {e}")
    for field in ("code", "name", "english", "kaikki"):
        if not isinstance(recipe.get(field), str) or not recipe[field].strip():
            raise BuildError(f"{path}: \"{field}\" is missing")
    if recipe["code"] != code or not CODE.match(code):
        raise BuildError(f"{path}: the code must be two or three lower-case letters and the directory's name")
    if code == "eo":
        raise BuildError("eo: Esperanto is built into Legejo and cannot be a pack")
    also = recipe.get("also", [])
    if not isinstance(also, list) or not all(isinstance(a, str) for a in also):
        raise BuildError(f"{path}: \"also\" must be a list of names")
    return recipe


def dump_url(recipe):
    if recipe.get("url"):
        return recipe["url"]
    name = recipe["kaikki"]
    return (f"https://kaikki.org/dictionary/{urllib.parse.quote(name)}/"
            f"kaikki.org-dictionary-{name.replace(' ', '')}.jsonl.gz")


# ------------------------------------------------------------ download


def fetch(url, cache, offline=False):
    """The dump at url, from the cache when it is there and still current."""
    os.makedirs(cache, exist_ok=True)
    path = os.path.join(cache, os.path.basename(urllib.parse.urlparse(url).path))
    have = os.path.exists(path)
    if have and offline:
        return path
    request = urllib.request.Request(url, headers={"User-Agent": "legejo-languages build"})
    if have:
        request.add_header("If-Modified-Since", email.utils.formatdate(os.path.getmtime(path), usegmt=True))
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            tmp = path + ".part"
            with open(tmp, "wb") as out:
                shutil.copyfileobj(response, out, 1 << 20)
            os.replace(tmp, path)
            modified = response.headers.get("Last-Modified")
            if modified:
                t = email.utils.parsedate_to_datetime(modified).timestamp()
                os.utime(path, (t, t))
            print(f"  downloaded {url} ({os.path.getsize(path)} bytes)")
    except urllib.error.HTTPError as e:
        if e.code == 304:
            print(f"  {os.path.basename(path)} is current")
        elif have:
            print(f"  warning: {url}: {e}; using the cached copy")
        else:
            raise BuildError(f"downloading {url}: {e}")
    except (urllib.error.URLError, OSError) as e:
        if not have:
            raise BuildError(f"downloading {url}: {e}")
        print(f"  warning: {url}: {e}; using the cached copy")
    return path


# ------------------------------------------------------------ pack files


def merge_also(pack_json, also, code):
    names = []
    for name in list(pack_json.get("also", [])) + list(also):
        name = name.strip().lower()
        if name and name != code and name not in names:
            names.append(name)
    pack_json["also"] = names
    return pack_json


def read_tsv(path):
    with open(path, encoding="utf-8", newline="\n") as f:
        return [line.rstrip("\n").split("\t") for line in f if line.strip()]


def write_tsv(path, rows):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write("\t".join(row) + "\n")


def by_bytes(s):
    return s.encode("utf-8")


def parse_fixes(text, source="fixes.tsv"):
    """The lines of a fixes file as (line number, op, arguments)."""
    fixes = []
    arity = {"gloss": 2, "drop": 1, "form": 2}
    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = [p.strip() for p in line.split("\t")]
        op, args = parts[0], parts[1:]
        if op not in arity or len(args) != arity[op] or not all(args):
            raise BuildError(f"{source}:{n}: expected \"gloss<TAB>key<TAB>English\", \"drop<TAB>key\" or \"form<TAB>form<TAB>key\"")
        fixes.append((n, op, args))
    return fixes


def apply_fixes(lemmas, forms, fixes, source="fixes.tsv"):
    """Apply fixes to the rows of lemmas.tsv and forms.tsv, in file order.

    Returns new (lemmas, forms): lemmas sorted by key in byte order, forms
    sorted by form in byte order. A fix naming a key that is not there is an
    error, so a fix that a rebuild has made stale is noticed."""
    table = {row[0]: row for row in lemmas}
    links = {row[0]: row[1].split(",") for row in forms}
    for n, op, args in fixes:
        key = args[0] if op != "form" else args[1]
        if key not in table:
            raise BuildError(f"{source}:{n}: no lemma \"{key}\" in the pack")
        if op == "gloss":
            table[key][2] = args[1]
        elif op == "drop":
            del table[key]
            for form in list(links):
                links[form] = [k for k in links[form] if k != key]
                if not links[form]:
                    del links[form]
        else:
            form = args[0].lower()
            targets = links.setdefault(form, [])
            if key not in targets:
                targets.append(key)
    lemmas = sorted(table.values(), key=lambda row: by_bytes(row[0]))
    forms = [[form, ",".join(keys)] for form, keys in sorted(links.items(), key=lambda item: by_bytes(item[0]))]
    return lemmas, forms


def count_lines(path):
    with open(path, "rb") as f:
        return sum(1 for line in f if line.strip())


def write_zip(pack_dir, zip_path, readme):
    names = ["pack.json", "lemmas.tsv", "forms.tsv"]
    unpacked = sum(os.path.getsize(os.path.join(pack_dir, n)) for n in names) + len(readme.encode())
    if unpacked > MAX_UNPACKED:
        raise BuildError(f"{zip_path}: {unpacked} bytes unpacked, the importer takes at most {MAX_UNPACKED}")
    tmp = zip_path + ".part"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name in names:
            z.write(os.path.join(pack_dir, name), name)
        z.writestr("README.txt", readme)
    if os.path.getsize(tmp) > MAX_ZIP:
        os.remove(tmp)
        raise BuildError(f"{zip_path}: larger than the importer's {MAX_ZIP} bytes")
    os.replace(tmp, zip_path)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def index_entry(recipe, pack_dir, zip_path):
    with open(os.path.join(pack_dir, "pack.json"), encoding="utf-8") as f:
        meta = json.load(f)
    return {
        "code": recipe["code"],
        "name": recipe["name"],
        "english": recipe["english"],
        "version": meta.get("version", ""),
        "lemmas": count_lines(os.path.join(pack_dir, "lemmas.tsv")),
        "forms": count_lines(os.path.join(pack_dir, "forms.tsv")),
        "bytes": os.path.getsize(zip_path),
        "sha256": sha256(zip_path),
        "license": meta.get("license", LICENSE),
        "attribution": meta.get("attribution", ATTRIBUTION),
    }


def make_index(entries, built):
    return {"format": 1, "built": built, "packs": sorted(entries, key=lambda e: e["code"])}


# ------------------------------------------------------------ one language


def build_one(code, langpack, cache, dist, work, offline=False):
    recipe = load_recipe(code)
    print(f"== {code} ({recipe['english']})", flush=True)
    dump = fetch(dump_url(recipe), cache, offline)
    pack_dir = os.path.join(work, code)
    run = subprocess.run([langpack, code, recipe["name"], dump, pack_dir], capture_output=True, text=True)
    sys.stdout.write(run.stdout)
    sys.stderr.write(run.stderr)
    if run.returncode != 0:
        raise BuildError(f"{code}: langpack failed with exit code {run.returncode}")

    meta_path = os.path.join(pack_dir, "pack.json")
    with open(meta_path, encoding="utf-8") as f:
        meta = merge_also(json.load(f), recipe.get("also", []), code)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
        f.write("\n")

    fixes_path = os.path.join(LANGUAGES, code, "fixes.tsv")
    if os.path.exists(fixes_path):
        with open(fixes_path, encoding="utf-8") as f:
            fixes = parse_fixes(f.read(), f"languages/{code}/fixes.tsv")
        if fixes:
            lemmas_path, forms_path = (os.path.join(pack_dir, n) for n in ("lemmas.tsv", "forms.tsv"))
            lemmas, forms = apply_fixes(read_tsv(lemmas_path), read_tsv(forms_path), fixes, f"languages/{code}/fixes.tsv")
            write_tsv(lemmas_path, lemmas)
            write_tsv(forms_path, forms)
            print(f"  {len(fixes)} fixes applied from languages/{code}/fixes.tsv")

    zip_path = os.path.join(dist, f"{code}.zip")
    readme = README_TXT.format(name=recipe["name"], code=code, english=recipe["english"],
                               version=meta.get("version", ""), attribution=meta.get("attribution", ATTRIBUTION))
    write_zip(pack_dir, zip_path, readme)
    entry = index_entry(recipe, pack_dir, zip_path)
    print(f"  {code}.zip: {entry['bytes']} bytes, {entry['lemmas']} lemmas, {entry['forms']} forms", flush=True)
    return entry


def all_codes():
    return sorted(d for d in os.listdir(LANGUAGES) if os.path.exists(os.path.join(LANGUAGES, d, "recipe.json")))


def main(argv=None):
    p = argparse.ArgumentParser(description="Build Legejo language packs from languages/<code>/recipe.json.")
    p.add_argument("codes", nargs="*", help="languages to build (default: all)")
    p.add_argument("--langpack", default=os.environ.get("LANGPACK"), help="the langpack binary (or LANGPACK)")
    p.add_argument("--cache", default=os.path.join(ROOT, "cache"), help="where downloaded dumps are kept")
    p.add_argument("--dist", default=os.path.join(ROOT, "dist"), help="where the zips and index.json go")
    p.add_argument("--offline", action="store_true", help="use cached dumps without asking for newer ones")
    args = p.parse_args(argv)
    if not args.langpack:
        p.error("give the langpack binary with --langpack or LANGPACK")

    codes = args.codes or all_codes()
    os.makedirs(args.dist, exist_ok=True)
    entries, failed = [], []
    with tempfile.TemporaryDirectory(prefix="langpacks-") as work:
        for code in codes:
            try:
                entries.append(build_one(code, args.langpack, args.cache, args.dist, work, args.offline))
            except (BuildError, OSError, ValueError) as e:
                print(f"error: {e}", file=sys.stderr, flush=True)
                failed.append(code)
    if failed:
        print(f"failed: {' '.join(failed)}", file=sys.stderr)
        return 1
    built = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    with open(os.path.join(args.dist, "index.json"), "w", encoding="utf-8") as f:
        json.dump(make_index(entries, built), f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"wrote {len(entries)} packs and index.json to {args.dist}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
