# Scenario library: research (cut down)

**The one line.** `engine make "<url>" --scenario auto --preview-storyboard` returns the plot code chose for the
source's facts and its storyboard, with the writer not yet called; without the flag the film is written, checked and
rendered to that plot. A person or agent who has read only `skills/scenarios/SKILL.md` can do it.

Scope: cut from the brief's 30 sources to 7 (quota). **Each was looked up on the web on 2026-11-07** (a search that
returned the bibliographic record or the text); where a claim in the table is wider than what was found it says so.
No code was taken from any of them: ideas only, so there is no licence to record.

## What was studied and what it teaches Veasy

| # | source (checked) | idea | used in |
|---|---|---|---|
| 1 | Loewenstein, "The psychology of curiosity: a review and reinterpretation", Psychological Bulletin 116(1), 75-98, 1994. [record](https://stafforini.com/works/loewenstein-1994-psychology-curiosity-review/) | curiosity is a perceived gap between what one knows and wants to know | `guess-the-number`, `three-clues`: the question comes with some facts already given |
| 2 | Zeigarnik, "Über das Behalten von erledigten und unerledigten Handlungen", Psychologische Forschung 9, 1-85, 1927. [PDF](https://www.interruptions.net/literature/Zeigarnik-PsychologischeForschung27.pdf) | unfinished tasks were remembered about twice as well. **Replication of the effect is disputed** (Spektrum lexicon, found in the search), so it is a design hint, not a proof | `payoff_held`: the figure waits for its beat |
| 3 | Kahneman, Fredrickson, Schreiber, Redelmeier, "When more pain is preferred to less: adding a better end", Psychological Science 4(6), 401-405, 1993. [DOI](https://doi.org/10.1111/j.1467-9280.1993.tb00589.x) | an episode is judged by how it ends (the study is of pain, not video; "peak-end" is commentators' name for it) | every plot ends on a payoff, then the call to action |
| 4 | Aristotle, Poetics, in Butcher's translation ([Gutenberg #1974](https://www.gutenberg.org/ebooks/1974)); peripeteia (reversal) and anagnorisis (recognition) | a turn reverses what was expected, and recognition follows | the `turn` job: `false-lead`, `rule-and-exception` |
| 5 | Truffaut, "Hitchcock" (1967); the bomb under the table, summarised in [Bordwell](https://www.davidbordwell.net/blog/2013/11/29/hitchcock-lessing-and-the-bomb-under-the-table/trackback/) and [No Film School](https://nofilmschool.com/alfred-hitchcock-and-francois-truffaut-explain-surprise-vs-suspense) (the book itself was not opened) | suspense is the audience knowing more than the characters; surprise is a short shock | `cold-open` gives the answer first and spends the film on why |
| 6 | Heath and Heath, "Made to Stick", Random House, 2007 ([overview](https://en.wikipedia.org/wiki/Made_to_Stick)) | simple, unexpected, concrete, credible, emotional, stories | one figure per payoff; every plot says only the document's facts |
| 7 | Propp, "Morfologija skazki", Leningrad, 1928 (English: Univ. of Texas Press, 1968) ([overview](https://en.wikipedia.org/wiki/Vladimir_Propp)) | 31 functions in a fixed order; the order makes the form | beats with jobs in a fixed order, as data |

Dropped as unverifiable: a radio-documentary "reverse order" craft note, a Tufte reference and a countdown/listicle
claim. `reverse-chronology` and `countdown` rest on the design reasoning in the table above, not on a source.

## What each form promises, where it turns, why people stay (only where unsure)

- **Guess the number / countdown / three clues**: promise a figure or a winner; turn at the reveal; stay for the gap
  (1) and the open task (2). Risk: if the figure is said early the film has no reason to continue: checked free.
- **Cold open / reverse chronology**: promise an explanation of a known result; no turn, a chain; stay for "why".
  Risk (unsure): without a held payoff they may read as a list: kept short, one cause per beat.
- **False lead**: promise a plan then a result that differs; turn at the difference. The false lead must be a plan,
  target or forecast the document states. A belief the document does not name would be an opinion (news rule N1).
- **Myth vs fact**: same, but only where the document itself corrects. Refused otherwise.
- **Profile, two voices, says-and-shows**: promise a person or a claim; stay for a verbatim quote and one figure.

## Ranked backlog (value / effort), and what was done

1. Data model, validation, free beat checks, `news` refused (high / medium): **done**
2. 24 plots with a Georgian demo each that passes `check` and `plan` (high / high): **done**
3. `scenario fit`, `make --scenario auto --preview-storyboard`, `--length` (high / medium): **done**
4. Skill and tool; sound cues from beats (medium / low): **done**
5. Chapters with a different plot each in a long film (medium / high): **done** (`story["scenario"]` as a list of ids)
6. Measure the cheap writer on real calls (high / needs a paid call): **not done**, no model calls allowed here
