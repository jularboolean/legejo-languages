# Language packs for Legejo

A language pack gives books in a language a study list in
[Legejo](https://github.com/jularboolean/legejo): the words of a book in
order of how often they occur, each taken to its dictionary form (Spanish
*hizo* to *hacer*) with a short English meaning.

The data comes from the English [Wiktionary](https://en.wiktionary.org) as
extracted by [kaikki.org](https://kaikki.org/dictionary/). This repository
holds a small recipe per language and the script that turns kaikki.org's
dump into a pack. A workflow rebuilds every pack each month and publishes
them as a [release](https://github.com/jularboolean/legejo-languages/releases/latest).

## Download

Get packs from **https://legejo.se/languages**. Downloads there are
counted: one number per pack and day, nothing about who downloaded.
The same files are the assets of the
[latest release](https://github.com/jularboolean/legejo-languages/releases/latest),
together with `index.json`, which lists every pack with its size and
SHA-256.

## Install

- In Legejo: **Admin → Languages → Import**, and choose the zip.
- Or by hand: unzip it into the data directory as `<data dir>/languages/<code>/`
  (with Docker, `/data/languages/nl/pack.json`, `lemmas.tsv`, `forms.tsv`)
  and restart Legejo.

Books in that language are counted again in the background and get a study
list.

## Languages

| Code | Name | English name |
|------|------|--------------|
| `de` | Deutsch | German |
| `es` | Español | Spanish |
| `fr` | Français | French |
| `nl` | Nederlands | Dutch |
| `sw` | Kiswahili | Swahili |

Esperanto is built into Legejo (from ESPDIC) and is not a pack here.
Spanish, French and German are currently also built into Legejo; their
packs here are made from the same data, and an imported pack replaces the
built-in one.

## Add a language

Any language kaikki.org has can become a pack, and you do not need to be a
programmer to add one. [CONTRIBUTING.md](CONTRIBUTING.md) walks through it:
build the pack with one command, check it in your own Legejo, and open a
pull request with a short recipe.

## Licence

The scripts and recipes are MIT (`LICENSE`). The packs are CC BY-SA 4.0,
derived from Wiktionary (`DATA-LICENSE.md`).
