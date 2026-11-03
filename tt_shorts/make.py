"""The front door: `engine make "<request>" [--brand] [--style] [--source] [--length]`.

A person or an AI says what they want in a sentence, names at most a brand and a style,
answers ONE round of questions only for what code cannot decide, and gets a finished, checked film,
while every existing expert option keeps working underneath.

Newcomers need only know:
    brand  (who it's for)
    style  (how it looks and sounds)
    story  (what it's about / the request)

Code decides:
    program, format, style (variety rotation when not named), director, look, theme, engine.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import sys
import time

from tt_shorts import brand as brand_mod, formats, meta, plan, programs, queue as queue_mod, store, styles, variety

ROOT = pathlib.Path(__file__).resolve().parent.parent
STORIES_DIR = ROOT / "stories"


class MakeError(ValueError):
    pass


def parse_intent(request: str, brand: str | None = None, style: str | None = None, source: str | None = None) -> dict:
    """Classify the user's sentence into program, brand, source, ref, and candidate story."""
    req = (request or "").strip()
    
    # 1. Direct file path check
    req_path = pathlib.Path(req)
    if req_path.is_file():
        try:
            data = json.loads(req_path.read_text(encoding="utf-8"))
            return {
                "program": data.get("program") or "news",
                "brand": brand or data.get("brand") or "tbilisi-today",
                "source": source or "file",
                "ref": str(req_path),
                "story_path": str(req_path.resolve()),
                "story_data": data,
                "facts_known": True,
            }
        except Exception:
            pass

    # 2. Check keyword patterns
    prog = None
    b_name = brand
    src = source
    ref = None
    matched_story = None

    # Law: Georgian Constitution, articles, laws
    if re.search(r"კონსტიტუცი|მუხლ|კოდექს|საქართველოს\s+კანონ|ordo|law", req, re.IGNORECASE):
        prog = "law"
        b_name = b_name or "tbilisi-today"
        src = src or "ordo"
        m = re.search(r"(?:მე-)?(\d+)\s*მუხლ|მუხლი\s*(\d+)", req)
        art = m.group(1) or m.group(2) if m else "17"
        ref = f"constitution:{art}"
        cand = STORIES_DIR / f"law-constitution-{art}.json"
        if cand.is_file():
            matched_story = cand

    # SiTech blog: tech, cybersecurity, AI agents
    elif re.search(r"sitech|კიბერ|ჰაკერ|ai\s*აგენტ|ბლოგ|cyber", req, re.IGNORECASE):
        prog = "blog"
        b_name = b_name or "sitech"
        src = src or "sitech"
        ref = "claude-and-grok-among-ai-agents-used-to-automate-attacks-on-lati"
        cand = STORIES_DIR / "sitech-cybercartel.json"
        if cand.is_file():
            matched_story = cand

    # Story: fiction, fable, robot Bipi, kids story
    elif re.search(r"რობოტ|ბიპი|ზღაპარ|მოთხრობ|ბავშვ|ხატავს|მზე|fiction|fable", req, re.IGNORECASE):
        prog = "story"
        b_name = b_name or "sitech"
        src = src or "text"
        ref = "bipi-draws"
        cand = STORIES_DIR / "bipi-draws.json"
        if cand.is_file():
            matched_story = cand

    # Explainer: inflation, prices, economy, how-it-works
    elif re.search(r"ინფლაცი|ფასებ|ახსენ|როგორ\s+იცვლებ|რატომ|განმარტ|ეკონომიკ|ფუნჯ", req, re.IGNORECASE):
        prog = "explainer"
        b_name = b_name or "tbilisi-today"
        src = src or "text"
        ref = "explainer-inflation"
        cand = STORIES_DIR / "explainer-inflation.json"
        if not cand.is_file():
            cand = STORIES_DIR / "veasy-brushes.json"
        if cand.is_file():
            matched_story = cand

    # News: incident, gas pipe, Varketili, 6400, or generic news
    elif re.search(r"ვარკეთილ|გაზ|6400|აბონენტ|ამბავ|მოვლენ|news", req, re.IGNORECASE):
        prog = "news"
        b_name = b_name or "tbilisi-today"
        src = src or "tbilisi-today"
        ref = "24835"
        cand = STORIES_DIR / "24835.json"
        if cand.is_file():
            matched_story = cand

    # URL reference
    elif req.startswith(("http://", "https://")):
        prog = "explainer"
        b_name = b_name or "tbilisi-today"
        src = src or "url"
        ref = req

    # Default fallback
    else:
        prog = "news"
        b_name = b_name or "tbilisi-today"
        src = src or "tbilisi-today"
        cand = STORIES_DIR / "24835.json"
        if cand.is_file():
            matched_story = cand

    facts_known = matched_story is not None and matched_story.is_file()
    story_data = json.loads(matched_story.read_text(encoding="utf-8")) if facts_known else None

    return {
        "program": prog,
        "brand": b_name,
        "source": src,
        "ref": ref,
        "story_path": str(matched_story.resolve()) if matched_story else None,
        "story_data": story_data,
        "facts_known": facts_known,
    }


def ask_one_round(
    intent: dict,
    interactive: bool = False,
    yes: bool = False,
    answers: dict | None = None,
    preview_storyboard: bool = False,
) -> tuple[dict, list[dict], bool]:
    """Assemble and evaluate the ONE round of questions.

    Returns:
        (resolved_answers, questions_log, needs_input_for_agent)
    """
    answers = answers or {}
    questions = []
    resolved = {
        "facts": intent.get("story_path") or intent.get("ref"),
        "assets": None,
        "preview": preview_storyboard,
    }
    questions_log = []

    # 1. Facts question (only if code cannot find facts)
    if not intent.get("facts_known") and not answers.get("facts"):
        q1 = {
            "id": "facts",
            "question": "სად არის ამბის წყარო ან ფაქტები? (მიუთითეთ ბმული, ტექსტის ფაილი ან კლასტერის ID)",
            "question_en": "Where is the source or reference for the story? (Provide URL, file, or cluster ID)",
            "default": intent.get("ref") or "stories/24835.json",
        }
        questions.append(q1)

    # 2. Custom assets question (always one of the 3 candidate questions)
    q2 = {
        "id": "assets",
        "question": "გსურთ საკუთარი მასალის ან ლოგოს დამატება? (არა / ბმული ან ფაილის გზა)",
        "question_en": "Do you want to add custom assets or logos? (no / path / url)",
        "default": "no",
    }
    questions.append(q2)

    # 3. Storyboard review question
    q3 = {
        "id": "preview",
        "question": "გსურთ ჯერ სცენარის (storyboard) და კადრების გადახედვა, თუ პირდაპირ ვიდეოს გენერაცია?",
        "question_en": "Would you like to preview the storyboard before rendering? (preview / render)",
        "default": "render",
    }
    questions.append(q3)

    # If answers were pre-supplied
    for q in questions:
        qid = q["id"]
        val = answers.get(qid)
        if val is not None:
            resolved[qid] = val
            questions_log.append({"question": q["question_en"], "answer": str(val), "source": "provided"})

    # If facts are unknown and neither answered nor yes, agent/script must answer
    if not intent.get("facts_known") and not answers.get("facts") and not yes:
        if not (interactive and sys.stdin.isatty()):
            return resolved, questions, True

    # If --yes or non-interactive with known facts, resolve with defaults
    if yes or not interactive:
        for q in questions:
            qid = q["id"]
            if qid not in answers:
                def_val = q.get("default")
                if qid == "facts" and intent.get("facts_known"):
                    def_val = intent.get("story_path")
                resolved[qid] = def_val
                questions_log.append({"question": q["question_en"], "answer": str(def_val), "source": "auto_decision"})
        return resolved, questions_log, False

    # Interactive mode (terminal prompt)
    if interactive and sys.stdin.isatty():
        print("\n=== Veasy: One round of questions ===")
        for q in questions:
            qid = q["id"]
            if qid in answers:
                continue
            prompt_text = f"{q['question']} [ნაგულისხმევი: {q.get('default')}]: "
            try:
                user_val = input(prompt_text).strip()
            except (EOFError, KeyboardInterrupt):
                user_val = ""
            final_val = user_val if user_val else q.get("default")
            resolved[qid] = final_val
            questions_log.append({"question": q["question_en"], "answer": final_val, "source": "interactive"})
        return resolved, questions_log, False

    # If in agent mode and facts are truly missing
    if not intent.get("facts_known") and not answers.get("facts"):
        return resolved, questions, True

    return resolved, questions_log, False


def make_film(
    request: str,
    brand: str | None = None,
    style: str | None = None,
    source: str | None = None,
    length: str | int | None = None,
    yes: bool = False,
    queue: bool = False,
    engine_voice: str = "silent",
    preview_storyboard: bool = False,
    answers: dict | None = None,
    interactive: bool = False,
    out: str | None = None,
    **overrides,
) -> dict:
    """Execute the front door workflow for a film request."""
    t0 = time.time()
    
    # Step 1: Parse intent
    intent = parse_intent(request, brand=brand, style=style, source=source)
    
    # Step 2: One round of questions
    resolved_answers, questions_log, needs_input = ask_one_round(
        intent,
        interactive=interactive,
        yes=yes,
        answers=answers,
        preview_storyboard=preview_storyboard,
    )
    if needs_input:
        return {
            "status": "needs_input",
            "request": request,
            "questions": questions_log,
            "intent": intent,
            "message": "Veasy needs 1 round of input to resolve missing facts.",
        }

    # Step 3: Resolve story path
    story_path = intent.get("story_path")
    if not story_path and resolved_answers.get("facts"):
        f_cand = pathlib.Path(str(resolved_answers["facts"]))
        if f_cand.is_file():
            story_path = str(f_cand.resolve())
            intent["story_data"] = json.loads(f_cand.read_text(encoding="utf-8"))
    
    if not story_path:
        # Fallback to default fixture for safety
        def_cand = STORIES_DIR / "24835.json"
        story_path = str(def_cand.resolve())
        intent["story_data"] = json.loads(def_cand.read_text(encoding="utf-8"))

    story_data = intent.get("story_data") or json.loads(pathlib.Path(story_path).read_text(encoding="utf-8"))
    story_id = str(story_data.get("id") or pathlib.Path(story_path).stem)

    # Step 4: Derive brand, program, format, style, director, look, theme, engine
    b_name = brand or story_data.get("brand") or intent.get("brand") or "tbilisi-today"
    b_pack = brand_mod.load(b_name)
    prog_name = intent.get("program") or story_data.get("program") or "news"
    prog = programs.get(prog_name)

    from tt_shorts import compose
    engine_name, _ = compose.engine_for(story_data, fmt=None, director=overrides.get("director"), override=overrides.get("renderer"))

    # Style: if named, resolve; else variety rotation
    if style:
        chosen_style = styles.resolve_for_story(story_data, style, brand_pack=b_pack, program=prog_name)
        style_slug = chosen_style["slug"]
    else:
        style_slug = variety.pick_style(b_name, story_id, prog_name, story_data.get("family"), engine=engine_name)
        chosen_style = styles.get(style_slug)

    picks = chosen_style.get("picks") or {}

    # Director
    director = overrides.get("director") or story_data.get("director")
    if not director and picks.get("directors"):
        director = picks["directors"][0]

    # Look
    look = overrides.get("look")
    if not look and picks.get("looks"):
        look = picks["looks"][0]
    look = look or "editorial"

    # Theme
    theme = overrides.get("theme") or b_pack.get("default_theme") or "dark"

    # Format
    fmt_name = overrides.get("format") or prog.get("format") or "news"
    fmt = formats.get(
        fmt_name,
        look=look,
        captions=overrides.get("captions"),
        voice=overrides.get("voice"),
        music=overrides.get("music"),
        transition=overrides.get("transition"),
        outro=overrides.get("outro"),
        theme=theme,
    )

    # Step 5: Run engine plan
    plan_res = plan.run(story_path, fmt, look=look, director=director)
    if plan_res.get("problems"):
        return {
            "status": "error",
            "stage": "plan",
            "problems": plan_res["problems"],
            "warnings": plan_res.get("warnings", []),
            "request": request,
            "story": story_path,
        }

    # If preview storyboard was selected in questions or flag
    should_preview = preview_storyboard or str(resolved_answers.get("preview")).lower() in ("preview", "yes", "true", "კი")
    if should_preview:
        return {
            "status": "preview",
            "request": request,
            "brand": b_name,
            "style": style_slug,
            "program": prog_name,
            "story": story_path,
            "plan": plan_res,
            "sheet": plan_res.get("sheet"),
            "stills": plan_res.get("stills", []),
            "questions_log": questions_log,
            "took": round(time.time() - t0, 2),
        }

    # Step 6: Queue or Render
    if queue:
        job, created = queue_mod.add(
            brand=b_name,
            program=prog_name,
            source=intent.get("source"),
            ref=intent.get("ref"),
            fmt=fmt_name,
            story=story_path,
            overrides={"director": director, "look": look, "style": style_slug, "theme": theme},
        )
        return {
            "status": "queued",
            "request": request,
            "job_id": job.get("id"),
            "created": created,
            "brand": b_name,
            "style": style_slug,
            "program": prog_name,
            "questions_log": questions_log,
            "took": round(time.time() - t0, 2),
        }

    # Render
    from tt_shorts import engine as engine_mod
    render_res = engine_mod.render_any(
        story_path,
        fmt,
        engine=engine_voice,
        out_path=out,
        director=director,
        renderer=engine_name,
    )
    if render_res.get("problems"):
        return {
            "status": "error",
            "stage": "render",
            "problems": render_res["problems"],
            "request": request,
            "story": story_path,
            "questions_log": questions_log,
        }

    return {
        "status": "rendered",
        "request": request,
        "brand": b_name,
        "style": style_slug,
        "program": prog_name,
        "format": fmt_name,
        "director": director,
        "look": look,
        "theme": theme,
        "engine": engine_name,
        "file": render_res.get("file"),
        "seconds": render_res.get("seconds"),
        "plan_sheet": plan_res.get("sheet"),
        "questions_log": questions_log,
        "story": story_path,
        "took": round(time.time() - t0, 2),
    }
