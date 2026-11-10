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
counted per pack, day, country and the site the link was followed from;
nothing about who downloaded is kept, and the figures are not published.
The same files are the assets of the
[latest release](https://github.com/jularboolean/legejo-languages/releases/latest),
together with `index.json`, which lists every pack with its size and
SHA-256.

## Install

- In Legejo: **Admin → Languages**, then **Install** next to the language
  (Legejo fetches it from legejo.se). A downloaded zip can be imported there
  too.
- Or by hand: unzip it into the data directory as `<data dir>/languages/<code>/`
  (with Docker, `/data/languages/nl/pack.json`, `lemmas.tsv`, `forms.tsv`)
  and restart Legejo.

Books in that language are counted again in the background and get a study
list.

## Extras

A pack may come with extras: what each inflected form is (*hizo*: third
person singular preterite of *hacer*), from Wiktionary's inflection tables.
With them Legejo counts the forms a book is written in on the book's
Analysis page and shows the table of a word's forms in the reader. They are
a file of their own, `<code>.extras.zip`, listed under the pack's `extras`
in `index.json`; Legejo fetches it together with the pack. Legejo 1.46 and
older do not know of extras and install the pack alone, as before.

## Languages

| Code | Name | English name |
|------|------|--------------|
| `de` | Deutsch | German |
| `es` | Español | Spanish |
| `fr` | Français | French |
| `nl` | Nederlands | Dutch |
| `sw` | Kiswahili | Swahili |

Esperanto is built into Legejo (from ESPDIC) and is not a pack here. Every
other language, Spanish, French and German included, is a pack.

## Add a language

Any language kaikki.org has can become a pack, and you do not need to be a
programmer to add one. [CONTRIBUTING.md](CONTRIBUTING.md) walks through it:
build the pack with one command, check it in your own Legejo, and open a
pull request with a short recipe.

## Licence

The scripts and recipes are MIT (`LICENSE`). The packs are CC BY-SA 4.0,
derived from Wiktionary (`DATA-LICENSE.md`).
