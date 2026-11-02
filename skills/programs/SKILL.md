---
name: programs
description: "Use when a video should be made from something other than a news cluster (a web page, a PDF, an article of Georgian law, a SiTech blog post), when choosing which program a video is, or when adding a new kind of video. Examples: \"make a video about article 17 of the Constitution\", \"explain this PDF in a Short\", \"turn this sitech.ge post into a video\", \"add a program for city guides\""
---

# Programs: any source in

A **program** says what a video is made from and what it may claim; a **format** (`veasy:formats`) says how it looks
and sounds. Every job and story has one; `news` is the default and is exactly what Veasy did before programs.

```bash
python -m tt_shorts.engine options          # "programs" and "sources": what each takes, its rules, its format
```

## Which program for what

| Program | For | Sources (first = default) | Rules | Format | Publish |
|---|---|---|---|---|---|
| `news` | one story told by several outlets | tbilisi-today, text | news (N1-N5) | news | auto |
| `explainer` | any one document: a page, a report, a PDF | url, pdf, text, ordo, sitech | claims | explainer | review |
| `law` | one article of Georgian law | ordo, text, pdf, url | law | explainer | review |
| `blog` | a SiTech blog post (brand `sitech`) | sitech, url, text | claims | news | auto |

- **claims**: every number, name and quote is in the document (N2, C1, N3); no opinion (N1, though a word the
  document itself uses is fine); no relative days (N4).
- **law**: claims, plus the article number on screen (L1), no advice or "you can / you should" (L2), the act named
  in the narration (L3). The end card's QR opens the article on matsne.gov.ge (`"link": "source"`).
- **publish: review**: the queue ends such a job `held` with `error_class: review` even when QA passed. A person
  watches it before it goes out.
- Every program checks the length against its format (`timing: ... program law wants 25-45s`): about 0.75 s per
  Georgian word, so 45-58 words.

## Sources (`--source`, `--ref`)

| Source | ref | Notes |
|---|---|---|
| `url` | a web page URL, or a saved `.html` file | trafilatura when installed, else a stdlib extractor; title, date, site from the page's metadata; a PDF URL goes to `pdf` |
| `pdf` | a PDF file or URL | pypdf, else `pdftotext`; title and date from its metadata. Old non-Unicode Georgian PDFs come out garbled: read `articles` first |
| `ordo` | `<law>:<article>[:<part>]` | `constitution:17`, `30346:17` (matsne id), `სამოქალაქო კოდექსი:361:2`, `31702:1507^1`. Needs Ordo (`ORDO_DIR`, see doctor). Only acts in force |
| `sitech` | a sitech.ge post slug or URL | the Georgian post (`/ka/blog/<slug>/`), its RSS time and its source outlet |
| `text` | a JSON file `{id, headline, category, date, sources, articles}` | anything else, written by the agent |

## Make one

```bash
python -m tt_shorts.engine write --program law --source ordo --ref constitution:17 [--brand tbilisi-today]
python -m tt_shorts.engine write --program explainer --source url --ref https://example.ge/report
python -m tt_shorts.engine write --program blog --ref <slug> --brand sitech
python -m tt_shorts.engine queue add --program law --ref constitution:17      # source defaults to the program's first
python -m tt_shorts.engine check <story.json> --sources <story>.sources.json  # the program's rules, from the story
python -m tt_shorts.engine render <story.json> --engine silent              # format defaults to the program's
```
Tools: `veasy_write` and `veasy_queue` take `program` and `source`. The story is kept as
`stories/<brand>/<day>/<program>-<id>.json` with the document beside it (`.sources.json`); it carries
`"program"`, the document facts in `"source"` (title, article, url, version) and, for `link: source`, `"link"`.
These come from the source's data, never from a writer, like `id`, `date` and `sources`.

Written by hand (`veasy:write-script`): follow the program's brief in `programs/briefs/<name>.md`.
`stories/law-constitution-17.json` is a law example (its document is `tests/fixtures/law-constitution-17.sources.json`).

## Writing law well

- Name the act and the article in the first sentence: „საქართველოს კონსტიტუციის 17-ე მუხლი ...“.
- Say what it guarantees, requires or forbids, in its own terms (დაუშვებელია, დასაშვებია მხოლოდ). Third person:
  „ყველას აქვს უფლება“, never „შენ გაქვს“ or „შეგიძლია“.
- Scenes: hook (kicker „კონსტიტუცია · მუხლი 17“), quote (verbatim, by „კონსტიტუცია“, via „მუხლი 17, პუნქტი 1“),
  points (what it protects), pair (the rule and its exception), end.
- End with „სრული ტექსტი საკანონმდებლო მაცნეზეა.“ and a call to action of at least 4 words (a shorter last
  sentence loses the end card).

## Add a program (no code)

1. `programs/<name>.json` with `label` (Georgian), `about`, `sources`, `brief`, `scenes` ("all" or a list with hook
   and end), `rules` (news, claims or law), `format`, `publish` (auto or review), optional `category` and `link`.
2. `programs/briefs/<name>.md`: what the video says, its length (45-58 words for 30-45 s), its scenes, its ending.
3. `python -m tt_shorts.engine options` must not fail (it refuses an unknown source, tier, scene, format or a
   missing brief). A new rule tier or a new source kind is code: `tt_shorts/claims_check.py` or
   `tt_shorts/sources/<name>.py` with a test.
