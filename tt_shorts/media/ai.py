"""AI illustration and generated video: the interface a model will plug into, DISABLED in this phase.

The owner has not decided yet (docs/plan-v2.md § 8.3 "AI imagery in news" and § 8.4 "providers and budget"), so
this provider is never available and finds nothing, and `engine check` refuses an asset of kind "ai" (N13). When
the decision is made, an implementation fills in search() (one image model per pack, one house style: a fixed
style prompt and seed, so the same subject gives the same picture) and fetch(), sends every call's cost to
costs.py with a daily cap, and N13's rules for it (never a real person, a logo or the event itself; never crime,
incidents or deaths) are already in news_check.imagery.
"""
NAME = "ai"
KINDS = ("ai",)
ENABLED = False  # the owner's decision, not a setting: change it only with that decision written down


def available():
    return None if ENABLED else "AI imagery is off until the owner decides (docs/plan-v2.md § 8.3)"


def search(query, kind="ai", n=1):
    return []


def fetch(c):
    raise RuntimeError(available() or "not implemented")
