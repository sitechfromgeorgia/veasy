"""The cost ledger: every paid or quota call in data/state.db, a monthly limit, and the daily report.

  kind   tts (Gemini voice, paid from Louie's prepay), script / edit (Command Code tokens, Louie's shared
         agent quota; free opencode models cost 0)
  usd    known prices only: Gemini TTS from the published price (env-overridable, the research notes a scheduled
         change on 2027-01-01), Command Code only when COMMANDCODE_USD_IN / _OUT (per 1M tokens) are set;
         otherwise NULL and the report shows the tokens with "price unknown".

The monthly limit (default $10) is SHORTS_MONTHLY_LIMIT_USD or the value set with /limit in Telegram (meta table).
At 80% the report warns; at 100% daily.py stops the paid Georgian voice until the next month.
Values are read when used, not at import: daily.py loads data/.env after importing this module.
"""
import datetime as dt
import json
import os
import pathlib
import sqlite3

ROOT = pathlib.Path(__file__).resolve().parent.parent
AUDIO_TOKENS_PER_SECOND = 25  # Gemini bills output audio at 25 tokens per second
WARN_AT = 0.8


def data_dir():
    return pathlib.Path(os.environ.get("SHORTS_DATA", ROOT / "data"))


def env_float(name, default=None):
    try:
        return float(os.environ[name])
    except (KeyError, ValueError):
        return default


def db():
    d = data_dir()
    d.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(d / "state.db", timeout=30)
    con.row_factory = sqlite3.Row
    con.executescript("""
    create table if not exists costs(time text, day text, slug text, kind text, model text,
                                     units_in int, units_out int, usd real);
    create table if not exists meta(k text primary key, v text);
    """)
    return con


def record(kind, model, units_in, units_out, usd, slug=None):
    """One call into the ledger. Never raises: accounting must not stop a video."""
    now = dt.datetime.now()
    try:
        with db() as con:
            con.execute("insert into costs values (?,?,?,?,?,?,?,?)",
                        (now.isoformat(timespec="seconds"), now.date().isoformat(), slug, kind, model,
                         int(units_in or 0), int(units_out or 0), usd))
    except sqlite3.Error:
        pass


def llm_usd(model, tokens_in, tokens_out):
    if model.startswith("opencode/"):
        return 0.0  # free tier
    if model.startswith("commandcode/"):
        pin, pout = env_float("COMMANDCODE_USD_IN"), env_float("COMMANDCODE_USD_OUT")
        if pin is not None and pout is not None:
            return (tokens_in * pin + tokens_out * pout) / 1e6
    return None  # price not known: tokens only


def tts_usd(text_tokens, audio_tokens):
    return (text_tokens * env_float("GEMINI_TTS_USD_IN", 0.50) + audio_tokens * env_float("GEMINI_TTS_USD_OUT", 9.00)) / 1e6


def record_tts(model, usage, audio_seconds, text, slug=None):
    """Gemini voice: the response's own token counts when it has them, else the published rate."""
    usage = usage or {}
    audio = next((usage[k] for k in ("output_tokens", "total_output_tokens", "candidatesTokenCount") if usage.get(k)),
                 round(audio_seconds * AUDIO_TOKENS_PER_SECOND))
    text_in = next((usage[k] for k in ("input_tokens", "total_input_tokens", "promptTokenCount") if usage.get(k)),
                   len(text) // 3)
    record("tts", model, text_in, audio, tts_usd(text_in, audio), slug)


def limit(con=None):
    con = con or db()
    row = con.execute("select v from meta where k='monthly_limit_usd'").fetchone()
    try:
        return float(row["v"]) if row else env_float("SHORTS_MONTHLY_LIMIT_USD", 10.0)
    except ValueError:
        return 10.0


def set_limit(usd):
    with db() as con:
        con.execute("insert or replace into meta values ('monthly_limit_usd', ?)", (str(float(usd)),))


def spent(month=None, con=None):
    """Known dollars spent this month (calls with an unknown price are not in it)."""
    con = con or db()
    month = month or dt.date.today().strftime("%Y-%m")
    return con.execute("select coalesce(sum(usd), 0) from costs where day like ?", (month + "%",)).fetchone()[0]


def paid_allowed(estimate=0.01):
    """False once this month's spend plus the next call would pass the limit."""
    con = db()
    return spent(con=con) + estimate <= limit(con)


def report(day=None):
    """The daily summary in Georgian (for Louie): videos, money, tokens, the month against the limit."""
    day = day or dt.date.today().isoformat()
    con = db()
    rows = con.execute("select kind, count(*) n, count(distinct slug) slugs, sum(units_in) tin, sum(units_out) tout, "
                       "sum(usd) usd, sum(usd is null) unknown from costs where day=? group by kind", (day,)).fetchall()
    by = {r["kind"]: r for r in rows}
    lines = [f"📊 tbilisi.today Shorts · {day}"]
    done, fails = 0, ""
    if con.execute("select 1 from sqlite_master where name='posts'").fetchone():
        done = con.execute("select count(*) from posts where status in ('rendered','review','approved') "
                           "and substr(updated,1,10)=?", (day,)).fetchone()[0]
        failed = con.execute("select error_class, count(*) n from posts where status='failed' and substr(updated,1,10)=? "
                             "group by error_class", (day,)).fetchall()
        fails = ", ".join(f"{r['error_class']} {r['n']}" for r in failed)
    done = done or (by["tts"]["slugs"] if "tts" in by else 0)  # lab batches don't use the queue: count the voices
    if done or fails:
        lines.append(f"ვიდეო: {done} გაკეთდა" + (f" · ჩავარდა: {fails}" if fails else ""))
    if "tts" in by:
        lines.append(f"ქართული ხმა (Gemini, ფასიანი): ${by['tts']['usd'] or 0:.3f} · {by['tts']['slugs']} ჩანაწერი")
    if done:
        lines.append("ინგლისური ხმა (edge-tts): უფასო")
    for kind, name in (("script", "სცენარი"), ("edit", "რედაქტორი")):
        if kind in by:
            r = by[kind]
            money = f"${r['usd']:.3f}" if r["usd"] is not None and not r["unknown"] else "ფასი დასაზუსტებელია"
            lines.append(f"{name}: {r['n']} გამოძახება · {r['tin'] + r['tout']:,} token ({money})".replace(",", " "))
    if not rows:
        lines.append("დღეს ფასიანი გამოძახება არ ყოფილა.")
    month, cap = spent(con=con), limit(con)
    warn = " ⚠️ ლიმიტს უახლოვდება" if month >= WARN_AT * cap else ""
    if month >= cap:
        warn = " ⛔ ლიმიტი ამოიწურა: ქართული ხმა შეჩერებულია თვის ბოლომდე"
    lines.append(f"თვე: ${month:.2f} / ${cap:.0f} ლიმიტი{warn}")
    learned = learned_today(day)
    if learned:
        shown = ", ".join(f"{k} → {v if len(v) <= 28 else v[:27] + '…'}" for k, v in learned[:10])
        lines.append(f"ახალი სახელები ({len(learned)}, დაადასტურე): {shown}" + (" …" if len(learned) > 10 else ""))
    edits = edits_today(day)
    if edits:
        lines.append(f"რედაქტორმა {edits} რამ გაასწორა")
    text = "\n".join(lines)
    out = data_dir() / "reports" / f"{day}.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text + "\n", encoding="utf-8")
    return text


def learned_today(day):
    try:
        known = json.loads((data_dir() / "lexicon_learned.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [(k, v.get("say")) for k, v in known.items() if v.get("status") == "auto" and v.get("first") == day]


def edits_today(day):
    try:
        lines = (data_dir() / "edits.jsonl").read_text(encoding="utf-8").splitlines()
    except OSError:
        return 0
    return sum(len(json.loads(x).get("changes") or []) for x in lines if x.startswith('{"time": "' + day))
