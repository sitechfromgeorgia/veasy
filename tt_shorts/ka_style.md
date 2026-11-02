# tbilisi.today Georgian rulebook (for the script writer)

Forked from sitech-shorts `shorts/ka_style.md` (K1-K22 unchanged, SiTech-only examples kept as language examples).
tbilisi.today adds the news rules N1-N6 at the end; `news_check.py` checks them.

The one set of rules for every Georgian Short. Sources: the SiTech-wide standard `GEORGIAN-STYLE.md` (SiTech Hub
`/root/sitech/georgian-style/`, the base of every agent's `georgian-copy-quality` skill) and Louie's TTS research
(My Projects `knowledge/video-brainstorm/georgian-tts/`). This file is appended to the writer's prompt; the editor
(`ka_editor.md`) checks the same rules by number, and `ka_check.py` checks the mechanical ones (marked [checked]).
A problem report names the rule it broke ("K12: ..."). Change a rule here, never in the prompt.
It covers the WRITTEN text (screen and narration); the spoken form (numbers in words, brand pronunciation) is
made later by code from the text and from your "say" map (K20).

## A. Register
- K1 Talk to the viewer as შენ everywhere, matching the ending "გამოიწერე": "ენდობოდი?", "შენ რას ფიქრობ?".
  ❌ "თქვენ ენდობით?" The closing question is in the present tense: "შენ რას ფიქრობ?", "როგორ ფიქრობ?".
  ❌ "შენ რას იფიქრებ?" (future: "what will you think"). [checked]
- K2 Educated conversational Georgian, like a good native presenter explaining tech to a young informed viewer:
  direct, clear, friendly. No hype words unless a fact proves them: რევოლუციური, გასაოცარი, შოკისმომგვრელი,
  უპრეცედენტო. No filler: "მნიშვნელოვანია აღინიშნოს", "აღსანიშნავია, რომ", "ამ კონტექსტში", "როგორც ცნობილია".
- K3 Write as a Georgian journalist would write it from scratch, never a word-for-word translation of English.
  Calques to avoid: მიიღოს ადგილი → მოხდეს; თამაშობს როლს → მნიშვნელოვანია; გააკეთა გადაწყვეტილება → მიიღო
  გადაწყვეტილება; იქნა გაკეთებული → გაკეთდა; არის საჭიროება → საჭიროა; ამ მომენტში → ამჟამად; დიდი რაოდენობით
  → ბევრი; შედეგად იმისა, რომ → იმის გამო, რომ; "game changer" ≠ "თამაშის შემცვლელი"; "security debt" ≠
  "უსაფრთხოების ვალი" → "უსაფრთხოების უგულებელყოფა ძვირად დაუჯდა"; "X allows homebrew" ≠ "საშუალებას აძლევს
  homebrew-ს" → "X homebrew-ს გაშვების საშუალებას იძლევა".
- K4 Clear actor + finite verb, active voice, the verb near the end: "კომპანიამ აპლიკაცია განაახლა".
  ❌ "კომპანიის მიერ განხორციელდა აპლიკაციის განახლება", "იქნა აღნიშნული". Passive only when the actor is unknown.

## B. Grammar
- K5 The subject of an aorist transitive or active verb takes the ergative -მა/-მ: "აგენტებმა აჯობეს",
  "13 AI აგენტმა ითამაშა", "მისმა ინსტრუმენტმა იპოვა", "Microsoft-მა წარადგინა". ❌ "აგენტები აჯობეს" (wrong even
  when the blog post has it). Intransitive verbs keep the nominative: "Microsoft გაიზარდა", "სერვისი დაიხურა".
- K6 After a number the noun is singular: "5 სტატია", "300 მომხმარებელი", "სამი GPU". ❌ "5 სტატიები". [checked]
- K7 Postpositions govern the case: შესახებ, გამო, მიხედვით, დროს + genitive ("კვლევის მიხედვით");
  "based on X" = "X-ს ეყრდნობა" / "X-ზე დააფუძნა".
- K8 Repeat the noun when ის / ეს / მისი could point to two things.

## C. Sentences for the voice
- K9 6-14 words per sentence, one idea each. Split a sentence that has a relative clause plus a number plus an
  acronym. Keep the scene anchors far enough apart for the eye: a "draw" scene needs at least 8 narration words
  before the next scene starts, every other scene at least 6, "end" at least 4. [checked]
- K10 Keep the qualifier next to the claim it qualifies: "კომპანიის თქმით, ...", "ცნობით, ...". Never drop or
  strengthen one: "შესაძლოა", "ვარაუდობს", "აცხადებს", "ზოგადად" stay. Name the source once, then let the next
  sentences from the same report follow it; don't open every sentence or screen with the same "X-ის თქმით".
- K11 Commas only where grammar needs them (before მაგრამ, in რომ-clauses). No comma between subject and verb.
- K12 No "!", "?!", "...", "…", slashes ("ძიება/თარგმნა"), emoji, em dash or en dash (— –): use a comma, a colon
  or a plain hyphen. A list: "სამი ფუნქცია: ძიება, თარგმნა და შეჯამება". [checked]
- K13 Every on-screen line set (hook, take lines) reads as one grammatical phrase top to bottom; no stray
  inflected fragment like "ნაკლებად შესამჩნევს" on its own line.

## D. Facts
- K14 What someone said or wrote is copied from the article word for word, in Georgian quotes („ვაი, რგოლი
  დავკარგე“), or left out.
  Never paraphrase a quote into a new claim. [checked]
- K15 Keep exactly the article's numbers; "up to" = -მდე, "about" = დაახლოებით, "more than" = -ზე მეტი.
  An identifier (CVE-2026-97631, KB5034441) is never read aloud: the narration says "ხარვეზი" or "განახლება",
  the screen may show the ID. [checked]
- K22 The viewer is Georgian: units are metric. Convert the article's pounds, ounces, miles, feet, yards, gallons,
  acres and °F, rounded as a presenter would say it: 3 ფუნტი → 1,4 კილოგრამი; ნახევარი ფუნტი → დაახლოებით 230
  გრამი; 60 მილი → დაახლოებით 97 კილომეტრი; 90°F → 32°C. Write "დაახლოებით" when you round. Only a screen's
  diagonal stays in inches, as Georgian shops sell it: "14-დიუმიანი ეკრანი". Prices stay in the article's
  currency (2 899 დოლარი); never convert money, the rate changes. [checked]

## E. Names and words
- K16 Brands, products and acronyms stay in Latin script, exactly as the brand writes them: Microsoft, NVIDIA,
  OpenAI, ChatGPT, Google, Apple, iPhone, GitHub, DeepSeek, xAI, YouTube, Linux, Android. Never transliterated
  on screen (❌ მაიკროსოფტი, ლინუქსი) and no quotes around brands. The Georgian case ending follows a plain
  hyphen, no space: Microsoft-მა, Microsoft-ის, NVIDIA-ს, OpenAI-მ, Google-მა, GPU-ები. Nominative: the bare
  brand (Microsoft, Apple). Instead of "AI-ები" write "AI მოდელები" or "აგენტები". SiTech is always "SiTech". [checked]
- K17 Countries, cities, peoples and languages in Georgian: გერმანია, ტოკიო, იაპონური; აშშ, დიდი ბრიტანეთი,
  ევროკავშირი. ❌ "Germany-ში".
- K18 Use the established Georgian word: ხელოვნური ინტელექტი (first mention; then AI), მონაცემები, მონაცემთა ბაზა,
  მონაცემთა ცენტრი, ჩიპი, სერვერი, აპლიკაცია, კომპიუტერი (not PC), სტარტაპი, ალგორითმი, ჩატბოტი, AI აგენტი,
  პროგრამული უზრუნველყოფა, კიბერუსაფრთხოება (one word), კიბერშეტევა, ჰაკერი, ფიშინგი, დაშიფვრა, გამომძალველი
  პროგრამა (ransomware), ღია კოდის მქონე (open source), დიდი ენობრივი მოდელი (LLM), გრაფიკული პროცესორი (GPU),
  ბირთვი (kernel), ღრუბლოვანი სერვისი / ინფრასტრუქტურა (never a bare "ღრუბელი" for cloud). Explain a specialist
  acronym once ("გრაფიკული პროცესორი (GPU)"), then use the short form.
- K19 No plain English words inside Georgian sentences when a Georgian word exists: ❌ "tethered ჰაკი",
  "userland წვდომა", "save ფაილები" → drop the word, explain it in Georgian, or keep only a real product name.
  Applies to kickers too. [checked]
- K20 Pronunciation map: add a top-level "say" object to the JSON with the Georgian spoken form of every Latin
  name in the narration that is not a plain letter acronym (AI, GPU, AWS are spelled letter by letter by code).
  Write the nominative as a Georgian speaker says it: {"ConnectWise": "ქონექთვაიზი", "ARTEX": "არტექსი",
  "Zeabur": "ზიბური", "SmileBasic": "სმაილბეისიკი", "Storm-0940": "სტორმ ნოლ ცხრაას ორმოცი"}.
  A name of several words is one key with one spoken word per written word: {"Hugging Face": "ჰაგინგ ფეისი",
  "1Password for Agents": "უანფასვორდ ფორ ეიჯენტს"}. Only real names go in "say", never a plain English word
  (K19). Well-known brands (Microsoft, Google, NVIDIA, OpenAI, Anthropic...) may be left out: code knows them.
  Letters inside a name are read with their English names, never the Russian ones (❌ ტე, პე, ბე, დე, კა, ე, ო):
  A ეი, B ბი, C სი, D დი, E ი, F ეფ, G ჯი, H ეიჩ, I აი, J ჯეი, K ქეი, L ელ, M ემ, N ენ, O ოუ, P პი, Q ქიუ,
  R არ, S ეს, T ტი, U იუ, V ვი, W დაბლიუ, X ექს, Y უაი, Z ზედ: {"macOS": "მაკ ოუ ეს", "EDK II": "ი დი ქეი ორი",
  "Vera CPU": "ვერა სი პი იუ"}. A name said as a word keeps its word: {"PXE": "პიქსი", "NASA": "ნასა"}. [checked]

## F. Numbers and dates (written form)
- K21 Digits with a hyphenated ending: 83%, 36%-ით, 4-ჯერ, 4-ჯერამდე, 2025 წელს, 15 წლამდე, 3 მილიონი.
  Thousands as in the article ("2 250" or "2250"), the decimal separator is a comma (3,5%), a range uses a plain
  hyphen (2020-2024, 10-14 ოქტომბერს). Dates: "2026 წლის 15 ოქტომბერს".

## Common fixes (bad → good)
- "ახალი სერვისი, რომელიც კომპანიამ გუშინ წარადგინა და რომელიც ქართულს უჭერს მხარს, ხელმისაწვდომია."
  → "კომპანიამ გუშინ ახალი სერვისი წარადგინა. ის ქართულსაც უჭერს მხარს." (K9)
- "აპლიკაცია, ქართულ ენას, უკვე უჭერს მხარს." → "აპლიკაცია ქართულ ენას უკვე უჭერს მხარს." (K11)
- "Eko-ს აგენტები აჯობეს იდენტურ აგენტებს." → "Eko-ს აგენტებმა ზოგადად აჯობეს იდენტურ აგენტებს." (K5, K10)
- "მოგვიანებით კი თქვა, რომ რგოლი მაცვია." (not in the article) → "დაწერა: „ვაი, რგოლი დავკარგე“." (K14)
- "ჰაკი SmileBasic 4-ის ვერსიას დააფუძნა." → "ჰაკი SmileBasic 4-ს ეყრდნობა." (K7)
- "Microsoft-ის თქმით, ... Microsoft-ის თქმით, ..." → "Microsoft-ის თქმით, ... კომპანიამ ისიც გააფრთხილა, რომ ..." (K10)
- "14-დიუმიანი 3 ფუნტს იწონის, წინაზე ნახევარი ფუნტით მსუბუქია." → "14-დიუმიანი მოდელი 1,4 კილოგრამს იწონის,
  წინაზე დაახლოებით 230 გრამით მსუბუქია." (K22)
- "შენ რას იფიქრებ, გამოგადგება?" → "შენ რას ფიქრობ, გამოგადგება?" (K1)

## N. News (tbilisi.today)
Every video goes out without a human review, so these rules are hard. `news_check.py` checks N1-N5 and N10-N12
[checked].
- N1 Report, don't judge. No "take" scene, no closing opinion, no evaluative words
  (❌ სკანდალური, შოკისმომგვრელი, ისტორიული, უპრეცედენტო). A judgement is said only as somebody's words, with the
  speaker: ✅ „ოპოზიციის თქმით, გადაწყვეტილება უკანონოა“. [checked]
- N2 Every number, on screen and in the narration, is in at least one member article. No sums, no differences, no
  rounding of your own (❌ „12 საათი“ when the sources say 22:00-10:00: show 22:00 → 10:00). [checked]
- N3 A quote is word for word from a member article, in „…“, with who said it and where (by, via). [checked]
- N4 No relative days: დღეს, გუშინ, ხვალ, ზეგ. People watch a Short for days; the screen shows the date, the voice
  names it (✅ „2 ნოემბერს“). [checked]
- N5 Sensitive stories are not written at all: sexual violence, children as victims, suicide. The pipeline skips them
  before the writer sees them. [checked]
- N6 Attribution for every claim that isn't a plain public fact: ✅ „შსს-ს ცნობით“, „ზელენსკის თქმით“. Political
  sides get the same verbs (განაცხადა, თქვა), never loaded ones (❌ აღიარა, იყვირა, დაიჩივლა).
- N7 Never name a victim, a minor, or a detained person who has not been charged. Officials and public figures by
  name and role.
- N8 The hook says what happened in one sentence (who + what), 6-8 words; the next sentence says the source.
  End with „დეტალები tbilisi.today-ზე.“ and one short call to action (გამოიწერე / მოიწონე / გააზიარე).
- N9 30-40 seconds: about 55-70 words. One story per video; no background the sources don't give.
- N10 A pictogram shows only what the voice says. A `sign` scene's verb is said in that scene's part of the narration
  (✅ stops + „გაზის მიწოდება შეწყდება“; ❌ rises when that part never says გაიზარდა, იზრდება...). A stat's icon
  repeats only for a count of 2-30 whole things the articles state (never „1 icon = 100“). No sign, no stat icon and
  no motif for crime and incidents or for a story about deaths. [checked]
- N11 A mark or a link shows only what the voice says. `"em"` names 1-4 words that are on that scene's screen word for
  word and said in its part of the narration; a `link` scene's `edge` is the verb that part says (✅ "შეხვდა" with
  „პრემიერი ელჩს შეხვდა“). A `share` shows only a percent an article writes with %, a `rail` only dates the articles
  give, in time order. [checked]
- N12 What several outlets state alike is counted, never weighed. An `agree` scene (the rubric „ადასტურებს N
  გამოცემა“) shows only facts that are literally in at least N member articles; code finds them and counts them, and
  its part of the narration says „მინიმუმ“ (✅ „მინიმუმ ოთხი გამოცემა წერს“, ❌ „ყველა მედია წერს“). It never names
  the outlets, and no video calls an outlet by a side (❌ პროსამთავრობო, ოპოზიციური მედია). [checked]
