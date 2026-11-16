"""Offline tests for the five-model consensus.

No network: a fixture payload stands in for Open-Meteo. What is under test is the arithmetic and the
honesty rules, because a wrong number on a weather page is worse than no page.

Run: /root/.hermes/shared-plugins/veasy/.venv/bin/python -m unittest tt_shorts.tests.test_openmeteo -v
"""
import unittest

from tt_shorts.sources import openmeteo as om


def payload(tmax, tmin, rain, pop, models=om.ALL_MODELS, days=1):
    """Build a payload with one value per model. tmax etc are dicts keyed by model."""
    daily = {"time": [f"2026-11-{15 + i:02d}" for i in range(days)]}
    for key, src in (("temperature_2m_max", tmax), ("temperature_2m_min", tmin),
                     ("precipitation_sum", rain), ("precipitation_probability_max", pop)):
        for m in models:
            daily[f"{key}_{m}"] = [src[m]] * days
    for m in models:
        daily[f"wind_speed_10m_max_{m}"] = [10.0] * days
        daily[f"wind_gusts_10m_max_{m}"] = [20.0] * days
        daily[f"weather_code_{m}"] = [3] * days
    return {"daily": daily}


class ConsensusTests(unittest.TestCase):
    def test_agreeing_models_produce_a_high_confidence_number(self):
        p = payload({m: 20.0 for m in om.ALL_MODELS}, {m: 10.0 for m in om.ALL_MODELS},
                    {m: 0.0 for m in om.ALL_MODELS}, {m: 0 for m in om.ALL_MODELS})
        day = om.consensus(p)[0]
        self.assertEqual(day.tmax, 20.0)
        self.assertEqual(day.band, "high")
        self.assertEqual(day.spread, 0.0)

    def test_a_wide_split_publishes_a_range_not_a_number(self):
        tmax = {m: 20.0 for m in om.ALL_MODELS}
        tmax["gfs_seamless"] = 30.0
        tmax["icon_seamless"] = 28.0
        p = payload(tmax, {m: 10.0 for m in om.ALL_MODELS},
                    {m: 0.0 for m in om.ALL_MODELS}, {m: 0 for m in om.ALL_MODELS})
        day = om.consensus(p)[0]
        # A 10 degree range is a split even when the standard deviation stays under the threshold:
        # the models are not slightly off, they disagree about the day itself.
        self.assertEqual(day.band, "split")
        self.assertIsNotNone(day.lo)
        self.assertIsNotNone(day.hi)
        self.assertLess(day.lo, day.hi)
        self.assertIn("ეწინააღმდეგებიან", day.as_dict()["text_ka"])

    def test_an_outlier_leaves_the_value_but_stays_in_the_spread(self):
        """One broken run must not drag the published number, but it must widen the honest spread."""
        tmax = {m: 20.0 for m in om.ALL_MODELS}
        tmax["gfs_seamless"] = 34.0  # outside the 4 degree guard
        p = payload(tmax, {m: 10.0 for m in om.ALL_MODELS},
                    {m: 0.0 for m in om.ALL_MODELS}, {m: 0 for m in om.ALL_MODELS})
        day = om.consensus(p)[0]
        self.assertLess(day.tmax, 21.0)
        self.assertGreater(day.spread, 4.0)

    def test_fewer_than_three_models_is_low_confidence(self):
        models = ("ecmwf_ifs025", "gfs_seamless")
        p = payload({m: 20.0 for m in models}, {m: 10.0 for m in models},
                    {m: 0.0 for m in models}, {m: 0 for m in models}, models=models)
        day = om.consensus(p)[0]
        self.assertEqual(day.band, "low")

    def test_missing_values_for_a_model_drop_that_model_only(self):
        p = payload({m: 20.0 for m in om.ALL_MODELS}, {m: 10.0 for m in om.ALL_MODELS},
                    {m: 0.0 for m in om.ALL_MODELS}, {m: 0 for m in om.ALL_MODELS})
        p["daily"]["temperature_2m_max_ukmo_seamless"] = [None]
        day = om.consensus(p)[0]
        self.assertEqual(len(day.models), len(om.ALL_MODELS) - 1)
        self.assertEqual(day.tmax, 20.0)

    def test_precipitation_is_a_weighted_share_of_the_wet_models(self):
        rain = {m: 0.2 for m in om.ALL_MODELS}
        for m in ("ecmwf_ifs025", "icon_seamless", "gfs_seamless"):
            rain[m] = 5.0
        p = payload({m: 20.0 for m in om.ALL_MODELS}, {m: 10.0 for m in om.ALL_MODELS},
                    rain, {m: 50 for m in om.ALL_MODELS})
        day = om.consensus(p)[0]
        self.assertAlmostEqual(day.pop, 0.5, places=1)
        self.assertGreater(day.rain_mm, 0)

    def test_dry_models_give_zero_rain_not_a_small_number(self):
        p = payload({m: 20.0 for m in om.ALL_MODELS}, {m: 10.0 for m in om.ALL_MODELS},
                    {m: 0.0 for m in om.ALL_MODELS}, {m: 0 for m in om.ALL_MODELS})
        day = om.consensus(p)[0]
        self.assertEqual(day.pop, 0.0)
        self.assertEqual(day.rain_mm, 0.0)

    def test_weights_cannot_let_one_model_rule_alone(self):
        """A model with a great score is clipped to 0.40, so a single broken run cannot own the day."""
        weights = {m: 0.01 for m in om.ALL_MODELS}
        weights["ecmwf_ifs025"] = 100.0
        tmax = {m: 20.0 for m in om.ALL_MODELS}
        tmax["ecmwf_ifs025"] = 30.0
        p = payload(tmax, {m: 10.0 for m in om.ALL_MODELS},
                    {m: 0.0 for m in om.ALL_MODELS}, {m: 0 for m in om.ALL_MODELS})
        day = om.consensus(p, weights=weights)[0]
        self.assertLess(day.tmax, 25.0)

    def test_the_url_names_every_independent_model(self):
        url = om.fetch_url(om.Place("tbilisi", "თბილისი", 41.69, 44.80, 455))
        for m in om.MODELS:
            self.assertIn(m, url)
        self.assertIn("elevation=455", url)
        # met.no is a fallback, not a voter: it must never be in the voting set.
        self.assertNotIn("metno", url)


if __name__ == "__main__":
    unittest.main(verbosity=2)
