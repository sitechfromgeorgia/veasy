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


def _program_for(source: str | None) -> str | None:
    """The program a source belongs to, from the programs' data: news if news takes it, else the program that
    lists it earliest (url -> explainer, ordo -> law, sitech -> blog). None leaves the choice to write_story."""
    if not source:
        return None
    if source in programs.get(programs.DEFAULT)["sources"]:
        return programs.DEFAULT
    ranked = sorted((p["sources"].index(source), name) for name, p in programs.load_all().items()
                    if source in p.get("sources", []))
    return ranked[0][1] if ranked else None


def _story_file(token: str) -> pathlib.Path | None:
    """A story the request points at: a JSON path, or the name of a story in stories/. A bare number is a source
    ref (a cluster id), never the demo file that happens to share it."""
    token = token.strip().strip("\"'«»„“”.,;:()")
    if not token:
        return None
    named = () if token.isdigit() else (STORIES_DIR / token, STORIES_DIR / f"{token}.json")
    for cand in (pathlib.Path(token),) + named:
        try:
            if cand.suffix == ".json" and cand.is_file():
                return cand
        except (OSError, ValueError):
            pass
    return None


def parse_intent(request: str, brand: str | None = None, style: str | None = None, source: str | None = None) -> dict:
    """Find what the request is about. Facts come only from a story file, a story id in stories/, or a source
    reference (a URL, or a ref with --source: a cluster id, a file, an ordo article); a bare sentence names none,
    so facts_known stays False and make asks for the source. Nothing is guessed from the sentence's words: a guess
    would publish a film about another story."""
    req = (request or "").strip()
    found = None
    for token in [req] + req.split():
        found = _story_file(token)
        if found:
            break
    if found:
        data = json.loads(found.read_text(encoding="utf-8"))
        return {"program": data.get("program") or programs.DEFAULT, "brand": brand or data.get("brand"),
                "source": source or "file", "ref": str(found), "story_path": str(found.resolve()),
                "story_data": data, "facts_known": True}

    ref = None
    url = re.search(r"https?://\S+", req)
    if url:
        ref, source = url.group(0), source or "url"
    elif source:
        ref = req.split()[-1] if req else None  # `make "<what you want> <ref>" --source <src>`: the ref comes last
    elif re.fullmatch(r"\d+", req):
        ref = req  # a bare id is a ref in the news program's first source
    return {"program": _program_for(source), "brand": brand, "source": source, "ref": ref,
            "story_path": None, "story_data": None, "facts_known": False, "write": ref is not None}


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
    missing = not intent.get("facts_known") and not intent.get("write") and not answers.get("facts")
    if missing:
        q1 = {
            "id": "facts",
            "question": "სად არის ამბის წყარო ან ფაქტები? (მიუთითეთ ბმული, ტექსტის ფაილი ან კლასტერის ID)",
            "question_en": "Where is the source or reference for the story? (Provide URL, file, or cluster ID)",
            "default": None,
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

    # Unknown facts are never defaulted, not even with --yes: only a person at a terminal can answer here
    if missing and not (interactive and sys.stdin.isatty()):
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

    if missing and not resolved.get("facts"):
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

    # Step 3: The story: the one named, else written from the source ref by the writer (as `engine write`)
    if not intent.get("facts_known") and resolved_answers.get("facts"):
        intent = parse_intent(str(resolved_answers["facts"]), brand=brand, style=style, source=source)
    if not intent.get("facts_known") and not intent.get("write"):
        return {"status": "needs_input", "request": request, "intent": intent,
                "questions": [{"id": "facts", "question_en": "Where is the source? (a story file or id, a URL, "
                                                             "or a ref with --source)"}],
                "message": "Veasy found no story file and no source reference in the request."}
    b_name = brand or (intent.get("story_data") or {}).get("brand") or brand_mod.DEFAULT
    if intent.get("write") and queue:  # the worker writes it: a job takes a source + ref
        job, created = queue_mod.add(brand=b_name, source=intent.get("source"), ref=intent.get("ref"),
                                     program=intent.get("program"), fmt=overrides.get("format"),
                                     overrides={k: v for k, v in (("director", overrides.get("director")),
                                                                  ("look", overrides.get("look")),
                                                                  ("style", style)) if v})
        return {"status": "queued", "request": request, "job_id": job.get("id"), "created": created,
                "brand": b_name, "program": intent.get("program") or programs.DEFAULT,
                "questions_log": questions_log, "took": round(time.time() - t0, 2)}
    if intent.get("write"):
        from tt_shorts import engine as engine_mod
        written = engine_mod.write_story(intent.get("source"), intent["ref"], brand=b_name,
                                         program=intent.get("program"), director=overrides.get("director"),
                                         style=style)
        if written.get("problems"):
            return {"status": "error", "stage": "write", "problems": written["problems"], "request": request,
                    "story": written["story"]}
        intent["story_path"] = written["story"]
        intent["story_data"] = json.loads(pathlib.Path(written["story"]).read_text(encoding="utf-8"))
    story_path = intent["story_path"]

    story_data = intent.get("story_data") or json.loads(pathlib.Path(story_path).read_text(encoding="utf-8"))
    story_id = str(story_data.get("id") or pathlib.Path(story_path).stem)

    # Step 4: Derive brand, program, format, style, director, look, theme, engine
    b_name = brand or story_data.get("brand") or b_name
    b_pack = brand_mod.load(b_name)
    prog_name = story_data.get("program") or intent.get("program") or programs.DEFAULT
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
