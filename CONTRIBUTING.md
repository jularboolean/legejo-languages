# Adding or improving a language

You need [Docker](https://docs.docker.com/get-docker/) and a Legejo of your
own to try the pack in. No programming is needed. A pull request here adds
a short recipe; the packs themselves are built by the workflow, so never
commit the generated files.

## 1. Find the language on kaikki.org

Open https://kaikki.org/dictionary/ and find the language. Note its English
name exactly as kaikki.org writes it (`Dutch`, `Swahili`, `Ancient Greek`).
The page for the language links a file named like
`kaikki.org-dictionary-Dutch.jsonl.gz`: all its Wiktionary entries.
Download it into an empty folder.

## 2. Build the pack

In that folder, run (here for Dutch):

```sh
docker run --rm -v "$PWD:/work" slurvdjur/legejo langpack nl "Nederlands" /work/kaikki.org-dictionary-Dutch.jsonl.gz /work/out
```

The arguments are the language code (see [Codes](#codes)), the language's
name as its speakers write it, the downloaded file, and the folder to write
the pack into. On Linux, add `--user "$(id -u):$(id -g)"` before
`slurvdjur/legejo` so that the files are yours.

`langpack` ships in the Legejo image from the next Legejo release. Until
then, build it from a source checkout of
[Legejo](https://github.com/jularboolean/legejo) with
[Rust](https://rustup.rs):

```sh
cd legejo/server
cargo run --release --bin langpack -- nl "Nederlands" /path/to/kaikki.org-dictionary-Dutch.jsonl.gz /path/to/out
```

## 3. Read the summary

It takes a few seconds and prints a summary like:

```
nl: 51886 lemmas, 176111 forms, 8326 forms of more than one lemma
  ...
  0 lemmas without a gloss, 0 with wikitext left in it
The little words with most senses, as a check of the glosses:
  van	prep,adv,noun	of; by / from
  aan	prep,adv,adj	on; at; to, indicates the target or recipient of an action / ...
```

- `0 lemmas without a gloss` and `0 with wikitext left in it` are what you
  want to see.
- The list at the end shows the little words (prepositions, pronouns,
  adverbs) with most senses and the English the pack gives them. These words
  are the most frequent in any book, so read them: does the first meaning
  make sense to a learner? Look up a few more common words in
  `out/lemmas.tsv` (a text file; one word per line).

## 4. Try it in your own Legejo

Zip the three files in `out/` (`pack.json`, `lemmas.tsv`, `forms.tsv`) and
import the zip under **Admin → Languages → Import**, or copy the folder to
`<data dir>/languages/<code>/` and restart. Open a book in the language and
look at its study list.

## 5. Open a pull request

Add one file, `languages/<code>/recipe.json`:

```json
{
  "code": "nl",
  "name": "Nederlands",
  "english": "Dutch",
  "kaikki": "Dutch",
  "also": ["nld", "dut", "dutch", "nederlands", "vlaams"]
}
```

- `code`: the language code, also the folder's name.
- `name`: the language's name in the language itself, shown in Legejo.
- `english`: the language's name in English.
- `kaikki`: the name in kaikki.org's address (step 1).
- `also`: other names books use for the language in their metadata: the
  ISO 639-2 and 639-3 codes, the English and native names, and regional
  names. Legejo matches them without regard to case.

Optionally add `languages/<code>/fixes.tsv` (below), and a line in the table
in `README.md`. Mention in the pull request what you checked. The workflow
builds the languages a pull request touches and shows their summaries in
the run, so reviewers see the result.

## Codes

A code is two or three lower-case letters: the
[ISO 639-1](https://en.wikipedia.org/wiki/List_of_ISO_639_language_codes)
code when the language has one (`nl`, `sw`), else the
[ISO 639-3](https://iso639-3.sil.org/code_tables/639/data) code (`yor`,
`haw`). `eo` is not possible: Esperanto is built into Legejo.

## Corrections: fixes.tsv

Most problems are best fixed in Wiktionary itself, which helps everyone;
the next monthly build picks the change up. For what cannot wait, a
language can have `languages/<code>/fixes.tsv`, applied after every build.
Corrections name the lemma (its key: the first column of `lemmas.tsv`), so
they survive rebuilds. Columns are separated by one tab; lines starting
with `#` are comments.

```
# Replace a lemma's English (third column of lemmas.tsv).
gloss	jamii	community, society; totality / together
# Remove a lemma, and every form that pointed only to it.
drop	somekey
# Make a form count as a lemma (the form in lower case).
form	gingen	gaan
```

In the English of a lemma, ` / ` separates the meanings of different
parts of speech and `;` the senses within one; put the most common first. A correction that names a lemma no
longer in the pack stops the build, so a stale fix is noticed and removed.

## What reviewers check

- The recipe: a correct code, the language's own name, the kaikki.org name,
  and sensible `also` names.
- The summary from the pull request's build: no wikitext, no empty glosses,
  and little words whose first meanings read well.
- That `fixes.tsv` lines are real corrections, short and in plain English.
- That no generated file (`pack.json`, `lemmas.tsv`, `forms.tsv`, zips) is
  in the pull request.

## Building every pack

`build/build.py` does what the workflow does: for each recipe it downloads
the dump (kept in `cache/`), runs `langpack`, adds `also` and the fixes, and
writes `dist/<code>.zip` and `dist/index.json`. It needs Python 3 and the
`langpack` binary:

```sh
python3 build/build.py --langpack /path/to/langpack          # every language
python3 build/build.py --langpack /path/to/langpack nl sw    # some
python3 -m unittest discover -s build                        # its tests
```

## Licence of contributions

Recipes and scripts you contribute are under the MIT licence of this
repository. Content in `fixes.tsv` becomes part of packs derived from
Wiktionary and is licensed CC BY-SA 4.0, like the packs
(`DATA-LICENSE.md`). By opening a pull request you agree to these terms.
