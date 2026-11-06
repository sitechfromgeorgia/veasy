"""Scenarios: declarative plots and narrative arcs for Veasy videos (ROADMAP Goal 6).

A director (directors.py) gives visual and motion personality; a rubric (rubrics.py) defines a recurring show
in a brand's daily schedule. A scenario governs how a story unfolds dramaturgically:
  - what it promises to the audience (the hook/setup),
  - what obstacles, false leads, or context it establishes,
  - where the narrative turns,
  - when the payoff or core revelation is delivered (held until the reveal beat),
  - and how it resolves into actionable understanding.

Scenarios are pure data, `scenarios/<id>.json`, validated here:
  id, title, label  id is the filename; title is English; label is Georgian for on-screen chips or UI
  about             English explanation of the narrative arc for the agent
  eligible          declarative condition list (OR of ANDs, matching rubrics.holds; no code strings)
  never             declarative exclusions (e.g. news program is refused; deaths; unverified corrections)
  beats             ordered list of 3-7 beats, each with:
                    - id: string identifier (e.g. "hook", "setup", "turn", "payoff", "resolution")
                    - job: promise | setup | context | complication | false_lead | evidence | turn | payoff | resolution
                    - scene_types: list of brush names from catalog (brushes/) or "any"
                    - word_budget: [min_words, max_words] (e.g. [12, 20])
                    - sound: sound cue name ("click", "pop", "whoosh", "tick", "thud", "blip") or null
                    - fact_gates: optional dict of required facts for this beat (e.g. {"numbers": 1})
                    - payoff_held: bool - if true, the core reveal/payoff must not appear before this beat
  pacing            target_words (int or [lo, hi]), min_seconds, max_seconds
  brief             optional lines added to the writer prompt
  requires_correction optional bool: true for myth-vs-fact scenarios requiring verified source correction

News programs (program "news") strictly refuse scenarios (news follows direct factual reporting,
not plotted dramaturgy). myth-vs-fact is refused unless the source document itself makes the correction.
"""
import functools
import json
import pathlib
import re

from tt_shorts import brand, catalog, ka_check, news_check, normalize_ka

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIR = ROOT / "scenarios"

KEYS = ("id", "title", "label", "about", "eligible", "never", "beats", "pacing", "brief", "requires_correction")
REQUIRED = ("id", "title", "label", "about", "eligible", "never", "beats", "pacing")

BEAT_KEYS = ("id", "job", "scene_types", "word_budget", "sound", "fact_gates", "payoff_held")
BEAT_REQUIRED = ("id", "job", "scene_types", "word_budget")

JOBS = (
    "promise",
    "setup",
    "context",
    "complication",
    "false_lead",
    "evidence",
    "turn",
    "payoff",
    "resolution",
)

SOUNDS = ("click", "pop", "whoosh", "tick", "thud", "blip")

FACTS = (
    "numbers", "quantities", "percents", "dates", "times", "places", "regions", "quotes", "speakers",
    "icons", "facts", "outlets", "members", "big_numbers", "prices", "rules", "agreed", "new_outlets",
    "new_facts", "stories", "steps", "comparisons"
)
FLAGS = ("deaths", "had_video", "verified_correction")

CORRECTION_MARKERS = (
    "სინამდვილეში",
    "არ შეესაბამება სიმართლეს",
    "არ შეესაბამება რეალობას",
    "არასწორია",
    "მცდარია",
    "უარყო",
    "უარყოფს",
    "დააზუსტა",
    "დეზინფორმაცია",
    "ფაქტია",
    "ტყუილია",
    "მითია",
    "actually",
    "in reality",
    "debunk",
    "false",
    "misleading",
    "fact check",
    "correction",
)


class ScenarioError(ValueError):
    """Raised when a scenario file or scenario evaluation fails validation."""
    pass


# ---------------------------------------------------------------- validation


def _scene_types():
    return set(catalog.types())


def _condition(name, where, cond):
    if not isinstance(cond, dict) or not cond:
        raise ScenarioError(f"scenario {name!r}: {where}: each condition is a non-empty object")
    for k, v in cond.items():
        if k == "families":
            if not isinstance(v, list) or not set(v) <= set(brand.FAMILIES):
                raise ScenarioError(f"scenario {name!r}: {where}: families must be a list of {', '.join(brand.FAMILIES)}")
        elif k in ("programs", "program"):
            programs_list = v if isinstance(v, list) else [v]
            if not all(isinstance(p, str) for p in programs_list):
                raise ScenarioError(f"scenario {name!r}: {where}: programs must be string or list of strings")
        elif k in FLAGS:
            if not isinstance(v, bool):
                raise ScenarioError(f"scenario {name!r}: {where}: {k} is true or false")
        elif k in FACTS:
            ok = isinstance(v, int) and not isinstance(v, bool) and v >= 0
            ok = ok or (isinstance(v, dict) and set(v) == {"max"} and isinstance(v["max"], int))
            if not ok:
                raise ScenarioError(f"scenario {name!r}: {where}: {k} is a minimum count or {{\"max\": n}}")
        else:
            raise ScenarioError(f"scenario {name!r}: {where}: unknown fact {k!r} (facts: {', '.join(FACTS + FLAGS)}, "
                                "families, programs)")


def validate(name, s):
    """Raise ScenarioError when a scenario definition is invalid; returns it resolved."""
    def need(cond, msg):
        if not cond:
            raise ScenarioError(f"scenario {name!r}: {msg}")

    need(isinstance(s, dict), "not an object")
    missing = [k for k in REQUIRED if k not in s]
    need(not missing, f"missing {missing}")
    unknown = sorted(set(s) - set(KEYS))
    need(not unknown, f"unknown keys {unknown}")

    need(s["id"] == name and re.fullmatch(r"[a-z0-9-]+", name), "id is its file name (lowercase letters and hyphens)")
    need(isinstance(s["title"], str) and s["title"].strip(), "title is a non-empty string")
    need(isinstance(s["label"], str) and s["label"].strip(), "label is a non-empty string")
    need(isinstance(s["about"], str) and s["about"].strip(), "about is a non-empty string")

    need(isinstance(s["eligible"], list) and s["eligible"], "eligible is a non-empty list of alternatives")
    for c in s["eligible"]:
        _condition(name, "eligible", c)

    need(isinstance(s["never"], list), "never is a list of exclusion conditions")
    for c in s["never"]:
        _condition(name, "never", c)

    known_scenes = _scene_types()
    beats = s["beats"]
    need(isinstance(beats, list) and 3 <= len(beats) <= 7, "beats is a list of 3-7 beat objects")

    has_payoff = False
    for i, b in enumerate(beats):
        need(isinstance(b, dict), f"beat[{i}] is not an object")
        b_missing = [k for k in BEAT_REQUIRED if k not in b]
        need(not b_missing, f"beat[{i}] missing {b_missing}")
        b_unknown = sorted(set(b) - set(BEAT_KEYS))
        need(not b_unknown, f"beat[{i}] unknown keys {b_unknown}")

        need(isinstance(b["id"], str) and re.fullmatch(r"[a-z0-9_-]+", b["id"]),
             f"beat[{i}].id must be lowercase letters, digits, underscores, or hyphens")
        need(b["job"] in JOBS, f"beat[{i}].job {b['job']!r} is not one of {', '.join(JOBS)}")
        if b["job"] == "payoff":
            has_payoff = True

        st = b["scene_types"]
        need(st == "any" or (isinstance(st, list) and st and set(st) <= known_scenes),
             f"beat[{i}].scene_types must be 'any' or a non-empty list of catalog brush types")

        wb = b["word_budget"]
        need(isinstance(wb, list) and len(wb) == 2 and all(isinstance(x, int) and not isinstance(x, bool) for x in wb)
             and 0 <= wb[0] <= wb[1] <= 50,
             f"beat[{i}].word_budget must be [min_words, max_words] with 0 <= min <= max <= 50")

        snd = b.get("sound")
        need(snd is None or snd in SOUNDS, f"beat[{i}].sound must be null or one of {', '.join(SOUNDS)}")

        fg = b.get("fact_gates")
        if fg is not None:
            need(isinstance(fg, dict), f"beat[{i}].fact_gates must be an object")
            for fk, fv in fg.items():
                need(fk in FACTS, f"beat[{i}].fact_gates unknown fact {fk!r}")
                need(isinstance(fv, int) and not isinstance(fv, bool) and fv >= 1,
                     f"beat[{i}].fact_gates[{fk!r}] must be integer >= 1")

        if "payoff_held" in b:
            need(isinstance(b["payoff_held"], bool), f"beat[{i}].payoff_held must be true or false")

    pacing = s["pacing"]
    need(isinstance(pacing, dict), "pacing must be an object")
    for pk in ("target_words", "min_seconds", "max_seconds"):
        need(pk in pacing, f"pacing missing {pk!r}")
    tw = pacing["target_words"]
    tw_ok = (isinstance(tw, int) and not isinstance(tw, bool) and tw >= 10) or (
        isinstance(tw, list) and len(tw) == 2 and all(isinstance(x, int) and not isinstance(x, bool) for x in tw)
        and 10 <= tw[0] <= tw[1]
    )
    need(tw_ok, "pacing.target_words must be integer >= 10 or [min_words, max_words]")
    min_s, max_s = pacing["min_seconds"], pacing["max_seconds"]
    need(isinstance(min_s, (int, float)) and not isinstance(min_s, bool) and min_s >= 10.0,
         "pacing.min_seconds must be number >= 10.0")
    need(isinstance(max_s, (int, float)) and not isinstance(max_s, bool) and max_s >= min_s,
         "pacing.max_seconds must be number >= min_seconds")

    brief = s.get("brief")
    if brief is not None:
        need(isinstance(brief, list) and all(isinstance(x, str) and x.strip() for x in brief),
             "brief must be a list of non-empty strings")

    req_corr = s.get("requires_correction", False)
    if name == "myth-vs-fact":
        req_corr = True
    need(isinstance(req_corr, bool), "requires_correction must be true or false")

    resolved = {
        **s,
        "requires_correction": req_corr,
        "brief": list(brief or []),
        "beats": [
            {
                **b,
                "fact_gates": dict(b.get("fact_gates") or {}),
                "payoff_held": bool(b.get("payoff_held", False)),
            }
            for b in beats
        ],
    }
    return resolved


# ---------------------------------------------------------------- loading


@functools.lru_cache(maxsize=4)
def _load(path_str):
    out = {}
    for path in sorted(pathlib.Path(path_str).glob("*.json")):
        if path.name == "schema.json":
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise ScenarioError(f"scenario {path.stem!r}: not JSON ({e})") from e
        out[path.stem] = validate(path.stem, raw)
    return out


def load_all():
    """Load and validate all scenarios from the scenarios/ directory."""
    return dict(_load(str(DIR)))


def load(name):
    """Load a single validated scenario by id."""
    return get(name)


def get(name):
    """Get a validated scenario by id or raise ScenarioError."""
    every = load_all()
    if name not in every:
        raise ScenarioError(f"unknown scenario {name!r}; known: {', '.join(sorted(every))}")
    return every[name]


def names():
    """List of all available scenario ids, sorted."""
    return sorted(load_all())


# ---------------------------------------------------------------- eligibility and conditions


def _holds(cond, f):
    """True when a single condition dictionary holds for the given facts."""
    for k, v in cond.items():
        if k == "families":
            if f.get("family") not in v:
                return False
        elif k in ("programs", "program"):
            programs_list = v if isinstance(v, list) else [v]
            if f.get("program") not in programs_list:
                return False
        elif k in FLAGS:
            if bool(f.get(k)) != v:
                return False
        elif isinstance(v, dict):
            if f.get(k, 0) > v["max"]:
                return False
        elif f.get(k, 0) < v:
            return False
    return True


def holds(scenario, facts, program="explainer"):
    """Check whether a scenario is eligible for given facts and program.

    Hard rule: 'news' program universally refuses scenarios.
    Returns True when at least one eligible condition holds and no never-condition holds.
    """
    if program == "news" or facts.get("program") == "news":
        return False

    sc = get(scenario) if isinstance(scenario, str) else scenario
    augmented_facts = {**facts, "program": program or facts.get("program", "explainer")}

    if sc.get("requires_correction") and not augmented_facts.get("verified_correction"):
        return False

    if any(_holds(c, augmented_facts) for c in sc.get("never", [])):
        return False
    return any(_holds(c, augmented_facts) for c in sc.get("eligible", []))


def eligible(facts, program="explainer"):
    """List of scenario IDs that hold for these facts and program."""
    if program == "news" or facts.get("program") == "news":
        return []
    return [sc_id for sc_id, sc in load_all().items() if holds(sc, facts, program=program)]


# ---------------------------------------------------------------- facts extraction


def story_facts(story, brand_pack=None):
    """Extract factual metrics from a story dict for scenario eligibility."""
    from tt_shorts import rubrics

    narration = story.get("narration", "")
    screen = news_check.screen_text(story)
    combined = f"{narration} {screen}"

    numbers_found = news_check.numbers(combined)
    quantities = [n for n in numbers_found if not re.match(r"^\d{4}$", n)]
    big_nums = [n for n in quantities if re.search(r"^\d{3,}", n) or "%" in n]

    quotes_found = re.findall(r"„([^“]+)“", combined)
    places = [s.get("place") for s in story.get("scenes", []) if s.get("place")]

    doc_corr = bool(story.get("doc_correction") or any(m in combined.lower() for m in CORRECTION_MARKERS))

    category = story.get("category", "general")
    fam = meta_family = brand.family_of(category) if hasattr(brand, "family_of") else category

    facts = {
        "numbers": len(numbers_found),
        "quantities": len(quantities),
        "percents": len(re.findall(r"\d+(?:[.,]\d+)?\s*%", combined)),
        "dates": len(news_check._DAY_MONTH.findall(combined)),
        "times": len(news_check._TIME.findall(combined)),
        "places": len(places),
        "regions": 0,
        "quotes": len(quotes_found),
        "speakers": len([s for s in story.get("scenes", []) if s.get("type") == "who"]),
        "icons": len([s for s in story.get("scenes", []) if s.get("type") == "sign"]),
        "facts": len(quantities) + len(quotes_found) + len(places),
        "outlets": len(story.get("sources", [])),
        "members": len(story.get("sources", [])),
        "big_numbers": len(big_nums),
        "prices": len(rubrics.PRICE.findall(combined)),
        "rules": len(rubrics.RULE_WORDS.findall(combined)),
        "agreed": 0,
        "new_outlets": 0,
        "new_facts": 0,
        "stories": 1,
        "steps": len([s for s in story.get("scenes", []) if s.get("type") in ("steps", "timeline", "route")]),
        "comparisons": len([s for s in story.get("scenes", []) if s.get("type") in ("versus", "compare", "pair")]),
        "deaths": any(w in combined for w in ("დაიღუპა", "გარდაიცვალა", "მკვლელობ")),
        "had_video": False,
        "verified_correction": doc_corr,
        "family": fam,
        "program": story.get("program", "explainer"),
    }
    return facts


def scene_word_counts(story):
    """[(scene_index, scene_type, word_count, narration_slice)] aligned by 'at' anchors."""
    narration = story.get("narration", "")
    tokens = normalize_ka.tokens(narration)
    scenes = story.get("scenes") or []
    if not scenes:
        return []

    keys = [ka_check.norm(t) for t in tokens]
    starts, after = [], 0
    for s in scenes:
        at_phrase = s.get("at", "")
        want = [ka_check.norm(p) for p in normalize_ka.tokens(at_phrase) if ka_check.norm(p)]
        hit = next((i for i in range(after, len(keys) - len(want) + 1) if want and keys[i:i + len(want)] == want), None)
        if hit is None:
            starts.append(after)
        else:
            starts.append(hit)
            after = hit + 1
    starts.append(len(tokens))

    out = []
    for i, s in enumerate(scenes):
        w_count = starts[i + 1] - starts[i]
        slice_toks = tokens[starts[i]:starts[i + 1]]
        out.append((i, s.get("type"), w_count, " ".join(slice_toks)))
    return out


# ---------------------------------------------------------------- ranking and fit


def fit(story_or_data, facts=None):
    """Rank fitting scenarios for a story or data cluster and explain why.

    Returns:
      list of {"scenario": str, "title": str, "score": float, "why": str}
      sorted by score descending.
    """
    program = story_or_data.get("program", "explainer") if isinstance(story_or_data, dict) else "explainer"
    if program == "news":
        return []

    if facts is None:
        if isinstance(story_or_data, dict) and "narration" in story_or_data:
            facts = story_facts(story_or_data)
        elif isinstance(story_or_data, dict) and ("articles" in story_or_data or "cluster" in story_or_data):
            from tt_shorts import rubrics
            facts = rubrics.facts(story_or_data)
        else:
            facts = {}

    all_scenarios = load_all()
    results = []

    scenes = story_or_data.get("scenes", []) if isinstance(story_or_data, dict) else []
    scene_types = [s.get("type") for s in scenes if isinstance(s, dict)]

    for sc_id, sc in all_scenarios.items():
        if not holds(sc, facts, program=program):
            continue

        score = 1.0
        reasons = []

        beats = sc["beats"]
        if len(scenes) == len(beats):
            score += 2.0
            reasons.append(f"exact {len(beats)}-beat scene count match")
        elif scenes:
            score -= 0.5 * abs(len(scenes) - len(beats))

        # Check scene type overlap
        if scenes:
            matches = 0
            for i, (b, st) in enumerate(zip(beats, scene_types)):
                allowed = b["scene_types"]
                if allowed == "any" or st in allowed:
                    matches += 1
            if matches == len(scenes):
                score += 3.0
                reasons.append("every scene matches beat brush specifications")
            elif matches > 0:
                score += 1.0 * (matches / len(scenes))

        # Fact affinity
        big_n = facts.get("big_numbers", 0)
        quotes_n = facts.get("quotes", 0)
        prices_n = facts.get("prices", 0)
        steps_n = facts.get("steps", 0)
        corr_n = facts.get("verified_correction", False)

        if sc_id == "guess-the-number" and big_n >= 1:
            score += 2.5
            reasons.append(f"story carries {big_n} prominent figure(s) ideal for mystery anticipation")
        elif sc_id == "myth-vs-fact" and corr_n:
            score += 3.0
            reasons.append("source document explicitly verifies the correction required for myth-busting")
        elif sc_id == "countdown" and facts.get("quantities", 0) >= 3:
            score += 2.0
            reasons.append(f"dataset provides {facts['quantities']} ranked items")
        elif sc_id == "before-and-after" and (facts.get("comparisons", 0) >= 1 or facts.get("dates", 0) >= 1):
            score += 2.0
            reasons.append("contrasting states or temporal points support a transformation arc")

        if quotes_n >= 2 and any(b["job"] == "evidence" for b in beats):
            score += 1.0
            reasons.append(f"{quotes_n} verbatim quotes ground key evidence beats")

        why_text = "; ".join(reasons) if reasons else "satisfies structural and fact eligibility conditions"
        results.append({
            "scenario": sc_id,
            "title": sc["title"],
            "score": round(score, 2),
            "why": why_text,
        })

    results.sort(key=lambda r: (-r["score"], r["scenario"]))
    return results


# ---------------------------------------------------------------- free checks at engine plan


def _extract_payoff_facts(scene):
    """Extract numbers or prominent values from a scene to detect early payoff leaks."""
    facts = set()
    if not isinstance(scene, dict):
        return facts

    val = scene.get("value")
    if val is not None:
        facts.add(str(val).strip())

    em = scene.get("em")
    if em:
        facts.add(em.strip())

    name = scene.get("name")
    if name:
        facts.add(name.strip())

    for it in scene.get("items") or []:
        if isinstance(it, dict) and it.get("sub"):
            facts.add(str(it["sub"]).strip())
        elif isinstance(it, str):
            for num in news_check.numbers(it):
                facts.add(num)

    return facts


def check_plan_beats(story, scenario=None):
    """Perform free structural and dramaturgy checks during engine plan.

    Verifies:
      a) Scene types match beat scene_types
      b) Word budget per beat is respected
      c) Fact gates for each beat are satisfied
      d) Early payoff check: core payoff fact is NOT spoken before the payoff beat
      e) myth-vs-fact gate: document itself provides the correction
      f) program refusal: news program stories cannot take a scenario

    Returns a list of error strings (empty if valid).
    """
    problems = []

    program = story.get("program", "explainer")
    if program == "news":
        return ["program 'news' refuses scenarios (news follows strict factual reporting without plotted dramaturgy)"]

    if scenario is None:
        sc_id = story.get("scenario")
        if not sc_id:
            return []
        try:
            scenario = get(sc_id)
        except ScenarioError as e:
            return [str(e)]
    elif isinstance(scenario, str):
        try:
            scenario = get(scenario)
        except ScenarioError as e:
            return [str(e)]

    beats = scenario.get("beats") or []
    scenes = story.get("scenes") or []

    # Scene count check
    if len(scenes) != len(beats):
        problems.append(
            f"scenario {scenario['id']!r}: story has {len(scenes)} scenes but scenario requires {len(beats)} beats"
        )
        return problems

    swc = scene_word_counts(story)
    prior_narration = ""

    # Payoff index
    payoff_idx = None
    for idx, b in enumerate(beats):
        if b["job"] == "payoff":
            payoff_idx = idx
            break

    # e) myth-vs-fact gate
    if scenario.get("requires_correction") or scenario.get("id") == "myth-vs-fact":
        combined_text = f"{story.get('narration', '')} {news_check.screen_text(story)}".lower()
        has_corr = bool(story.get("doc_correction") or any(m in combined_text for m in CORRECTION_MARKERS))
        if not has_corr:
            problems.append(
                f"scenario {scenario['id']!r}: document itself does not state a correction "
                "(N1 opinion gate: refusing unverified myth-vs-fact)"
            )

    for i, beat in enumerate(beats):
        sc = scenes[i]
        sc_type = sc.get("type")
        beat_id = beat["id"]

        # a) Scene types match beat scene_types
        allowed = beat["scene_types"]
        if allowed != "any" and sc_type not in allowed:
            problems.append(
                f"beat {i} ({beat_id!r}): scene type {sc_type!r} not in allowed types {allowed}"
            )

        # b) Word budget per beat is respected
        if i < len(swc):
            _, _, w_count, slice_text = swc[i]
            lo, hi = beat["word_budget"]
            if w_count < lo or w_count > hi:
                problems.append(
                    f"beat {i} ({beat_id!r}): narration has {w_count} words, outside budget [{lo}, {hi}]"
                )
        else:
            slice_text = ""

        # c) Fact gates for each beat are satisfied
        fg = beat.get("fact_gates") or {}
        if fg:
            combined_scene = f"{slice_text} {news_check.screen_text({'scenes': [sc]})}"
            nums = news_check.numbers(combined_scene)
            qts = re.findall(r"„([^“]+)“", combined_scene)
            for fk, req in fg.items():
                found = 0
                if fk == "numbers":
                    found = len(nums)
                elif fk == "quotes":
                    found = len(qts)
                elif fk == "percents":
                    found = len(re.findall(r"\d+(?:[.,]\d+)?\s*%", combined_scene))
                elif fk == "dates":
                    found = len(news_check._DAY_MONTH.findall(combined_scene))
                elif fk == "prices":
                    from tt_shorts import rubrics
                    found = len(rubrics.PRICE.findall(combined_scene))
                if found < req:
                    problems.append(
                        f"beat {i} ({beat_id!r}): requires at least {req} {fk}, found {found}"
                    )

        # Track prior narration for early payoff check
        if payoff_idx is not None and i < payoff_idx:
            prior_narration += f" {slice_text}"

    # d) Early payoff check: verifies payoff fact is NOT said in narration before payoff beat
    if payoff_idx is not None and payoff_idx < len(scenes):
        payoff_scene = scenes[payoff_idx]
        payoff_facts = _extract_payoff_facts(payoff_scene)
        prior_lower = prior_narration.lower()
        prior_nums = news_check.numbers(prior_narration)

        for pf in payoff_facts:
            # If pf is numeric
            if any(c.isdigit() for c in pf):
                # Clean numeric tokens
                clean_pf = pf.replace("%", "").strip()
                if clean_pf in prior_nums or (clean_pf and clean_pf in prior_lower):
                    problems.append(
                        f"early payoff: fact {pf!r} is spoken before payoff beat {beats[payoff_idx]['id']!r}"
                    )
                    break
            elif len(pf) >= 4 and pf.lower() in prior_lower:
                problems.append(
                    f"early payoff: fact {pf!r} is spoken before payoff beat {beats[payoff_idx]['id']!r}"
                )
                break

    return problems


def story_problems(story):
    """Check code-owned scenario problems on a story. Stories without a scenario return []."""
    if "scenario" not in story:
        return []
    sc_id = story["scenario"]
    try:
        sc = get(sc_id)
    except ScenarioError as e:
        return [str(e)]
    return check_plan_beats(story, sc)
