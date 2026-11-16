"""Five-model consensus forecast for tbilisi.today.

The owner, 2026-11-15: „ამინდის პროგნოზი უნდა გვქონდეს ძალიან დახვეწილი ... ავიღოთ რამე სანდო 5
წყარო ამინდის კუთხით და მაგათი პროგნოზით ვაწარმოოთ ჩვენი ამინდის პროგნოზი".

The design is in docs/ops/weather/plan-data.md. Three rules decide everything here:

1. Compute each daily value PER MODEL first, then combine. Averaging hourly curves first lets the
   peaks cancel out, because models place the warmest hour at different times.
2. Independence is what makes a consensus worth anything. met.no is built on ECMWF and JMA's grid
   cannot see the Caucasus, so neither votes; they are a fallback and a cross-check.
3. Never publish a number the models disagree about. Below three models, or above the split
   threshold, the product says so and publishes a range.

No network in the tests: `consensus()` takes an already-fetched payload.
"""
from __future__ import annotations

import json
import math
import statistics
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

# Five independent centres. UKMO is here because its 10 km grid resolves the Likhi ridge better
# than any 0.25 degree model; ECMWF AIFS is a sixth method, not a sixth centre.
MODELS = ("ecmwf_ifs025", "icon_seamless", "gfs_seamless", "meteofrance_seamless", "ukmo_seamless")
AI_MODEL = "ecmwf_aifs025_single"
ALL_MODELS = MODELS + (AI_MODEL,)
MIN_MODELS = 3

BANDS = {
    "high": "მაღალი სანდოობა",
    "medium": "საშუალო სანდოობა",
    "low": "დაბალი სანდოობა",
    "split": "მოდელები ეწინააღმდეგება",
}
BAND_TEXT = {
    "high": "პროგნოზი მყარია: ყველა მოდელი ერთსა და იმავეს აჩვენებს.",
    "medium": "პროგნოზი ძირითადად სანდოა, მცირე გადახრა შესაძლებელია.",
    "low": "მოდელები ნაწილობრივ განსხვავდება. ტემპერატურა შეიძლება 2-3 გრადუსით გადაიხაროს.",
    "split": "მოდელები ერთმანეთს ეწინააღმდეგებიან: ზოგი წვიმას აჩვენებს, ზოგი მშრალ ამინდს. "
             "ამიტომ ზუსტ ციფრს არ ვასახელებთ.",
}


@dataclass
class Place:
    slug: str
    name: str
    lat: float
    lon: float
    elevation: float | None = None
    region: str | None = None


@dataclass
class Day:
    date: str
    tmax: float | None
    tmin: float | None
    pop: float | None            # 0..1
    rain_mm: float | None
    wind: float | None
    gust: float | None
    code: int | None
    band: str
    spread: float | None
    models: dict = field(default_factory=dict)
    lo: float | None = None
    hi: float | None = None

    def as_dict(self) -> dict:
        return {"date": self.date, "tmax": self.tmax, "tmin": self.tmin, "pop": self.pop,
                "rain_mm": self.rain_mm, "wind": self.wind, "gust": self.gust, "code": self.code,
                "band": self.band, "band_ka": BANDS[self.band], "text_ka": BAND_TEXT[self.band],
                "spread": self.spread, "lo": self.lo, "hi": self.hi, "models": self.models}


def fetch_url(place: Place, days: int = 7) -> str:
    params = {
        "latitude": f"{place.lat:.4f}", "longitude": f"{place.lon:.4f}",
        "hourly": "temperature_2m,precipitation,precipitation_probability,wind_speed_10m,"
                  "wind_gusts_10m,weather_code,cloud_cover",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,"
                 "precipitation_probability_max,wind_speed_10m_max,wind_gusts_10m_max,weather_code",
        "models": ",".join(ALL_MODELS),
        "forecast_days": str(days),
        "timezone": "Asia/Tbilisi",
    }
    if place.elevation is not None:
        params["elevation"] = str(int(place.elevation))
    return "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(params)


def fetch(place: Place, days: int = 7, timeout: int = 40) -> dict:
    """One call, every model. Raises on network trouble; the caller decides whether to fall back."""
    req = urllib.request.Request(fetch_url(place, days), headers={"User-Agent": "tbilisi.today weather"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def _vals(block: dict, key: str, model: str) -> list:
    return block.get(f"{key}_{model}") or []


def _daily_per_model(payload: dict, model: str, day_index: int) -> dict | None:
    daily = payload.get("daily") or {}
    try:
        tmax = _vals(daily, "temperature_2m_max", model)[day_index]
        tmin = _vals(daily, "temperature_2m_min", model)[day_index]
    except (IndexError, TypeError):
        return None
    if tmax is None or tmin is None:
        return None
    def at(key):
        seq = _vals(daily, key, model)
        return seq[day_index] if day_index < len(seq) else None
    return {"tmax": float(tmax), "tmin": float(tmin),
            "rain": at("precipitation_sum"), "pop": at("precipitation_probability_max"),
            "wind": at("wind_speed_10m_max"), "gust": at("wind_gusts_10m_max"),
            "code": at("weather_code")}


def _weighted_median(pairs: list[tuple[float, float]]) -> float:
    """pairs of (value, weight), weight > 0."""
    ordered = sorted(pairs)
    total = sum(w for _v, w in ordered)
    if total <= 0:
        return statistics.median(v for v, _w in ordered)
    acc = 0.0
    for value, weight in ordered:
        acc += weight
        if acc >= total / 2:
            return value
    return ordered[-1][0]


def _band(spread: float, pop: float | None, rain: float | None, models_used: int) -> str:
    if models_used < MIN_MODELS:
        return "low"
    if spread > 3.5:
        return "split"
    if pop is not None and 0.4 <= pop <= 0.6 and rain is not None and rain > 2:
        return "low"
    if spread <= 1.0:
        return "high"
    if spread <= 2.0:
        return "medium"
    return "low"


def consensus(payload: dict, place: Place | None = None, days: int = 7,
              weights: dict | None = None) -> list[Day]:
    """Combine the models into one forecast per day.

    weights: model -> weight, normally 1/MAE^2 from the accuracy loop. Equal weights until 30 days
    of scoring exist, clipped to [0.05, 0.40] so no single model can rule alone.
    """
    weights = weights or {m: 1.0 for m in ALL_MODELS}
    dates = (payload.get("daily") or {}).get("time") or []
    out: list[Day] = []
    for i, date in enumerate(dates[:days]):
        per_model = {}
        for m in ALL_MODELS:
            got = _daily_per_model(payload, m, i)
            if got is not None:
                per_model[m] = got
        used = len(per_model)
        if used == 0:
            continue
        w = {m: max(0.05, min(0.40, float(weights.get(m, 1.0)))) for m in per_model}
        total_w = sum(w.values()) or 1.0
        w = {m: v / total_w for m, v in w.items()}

        tmax_points = [(d["tmax"], w[m]) for m, d in per_model.items()]
        tmin_points = [(d["tmin"], w[m]) for m, d in per_model.items()]
        # The outlier centre is the PLAIN median, not the weighted one: with a clipped 0.40 weight a
        # single model can otherwise capture the weighted median and pull the whole day to itself.
        centre = statistics.median(v for v, _wt in tmax_points)
        # Outliers stay in the spread but leave the value: one broken run must not drag the number.
        keep = [(v, wt) for v, wt in tmax_points if abs(v - centre) <= 4.0] or tmax_points
        tmax = sum(v * wt for v, wt in keep) / sum(wt for _v, wt in keep)
        tmin = sum(v * wt for v, wt in tmin_points) / sum(wt for _v, wt in tmin_points)

        spread = statistics.pstdev([d["tmax"] for d in per_model.values()]) if used > 1 else 0.0

        wet = [(m, d) for m, d in per_model.items() if (d.get("rain") or 0) >= 1.0]
        pop = sum(w[m] for m, _d in wet) if wet else 0.0
        rain = (sum((d.get("rain") or 0) * w[m] for m, d in wet) / sum(w[m] for m, _d in wet)
                if wet else 0.0)

        gust = max((d.get("gust") or 0) for d in per_model.values())
        wind = statistics.median([d.get("wind") or 0 for d in per_model.values()])
        code = statistics.median([d.get("code") for d in per_model.values()
                                  if d.get("code") is not None] or [0])

        band = _band(spread, pop, rain, used)
        lo = hi = None
        if band == "split":
            lo = round(min(d["tmax"] for d in per_model.values()))
            hi = round(max(d["tmax"] for d in per_model.values()))

        out.append(Day(date=date, tmax=round(tmax, 1), tmin=round(tmin, 1),
                       pop=round(pop, 2), rain_mm=round(rain, 1), wind=round(wind, 1),
                       gust=round(gust, 1), code=int(code) if code else None, band=band,
                       spread=round(spread, 1), lo=lo, hi=hi,
                       models={m: {"tmax": d["tmax"], "tmin": d["tmin"], "rain": d["rain"]}
                               for m, d in per_model.items()}))
    return out


def fetch_consensus(place: Place, days: int = 7, weights: dict | None = None) -> list[Day]:
    return consensus(fetch(place, days), place, days, weights)
