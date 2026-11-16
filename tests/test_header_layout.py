"""Header safe-width layout across dark and light themes (Item B2)."""
import json
import pathlib
import tempfile
import unittest

from tt_shorts import formats, probe, props, speech

ROOT = pathlib.Path(__file__).resolve().parent.parent


class TestHeaderLayout(unittest.TestCase):
    def test_news_short_tsx_header_structure(self):
        """Header wraps logo and right meta in one flex row with safe logo and meta widths."""
        src = (ROOT / "remotion" / "src" / "NewsShort.tsx").read_text(encoding="utf-8")

        # Container row at top: 80 with space-between and gap: 24
        self.assertIn('position: "absolute", left: SIDE, right: SIDE, top: 80', src)
        self.assertIn('display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 24', src)

        # Left logo child
        self.assertIn('<div data-probe="header" style={{ height: 88, display: "flex", alignItems: "center", flexShrink: 0 }}>', src)
        self.assertIn('<Logo place="header" size={88} />', src)

        # Safe logo width calculation
        self.assertIn('const logoW = props.brand.logo === "svg" ? 360 : 88 + 24 + measure(props.brand.wordmark.text, 700) * 0.44;', src)
        self.assertIn('const maxMetaW = Math.max(240, W - 2 * SIDE - logoW - 24);', src)

        # Right meta line calculation (compact fallback when full Georgian meta exceeds maxMetaW)
        self.assertIn('const fullMeta = `${props.date.weekday} · ${props.date.time} · ${props.category}`;', src)
        self.assertIn('const compactMeta = `${props.date.time} · ${props.category}`;', src)
        self.assertIn('const metaLine = measure(fullMeta, 400) * 0.30 <= maxMetaW ? fullMeta : compactMeta;', src)

        # Second child with maxMetaW and text truncation safeguards
        self.assertIn('<div data-probe="header" style={{ flex: "1 1 auto", minWidth: 0, maxWidth: maxMetaW, textAlign: "right", fontFamily: FONT }}>', src)
        self.assertIn('whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis"', src)

        # Progress and chapter bar untouched below Header
        self.assertIn('top: 204', src)
        self.assertIn('top: 188', src)

    def _probe_story_variant(self, theme: str, category: str = "ai", date_iso: str = "2026-10-22T00:00:00Z"):
        """Run layout probe on sitech-cybercartel with specified category, date, and theme."""
        data = json.loads((ROOT / "stories" / "sitech-cybercartel.json").read_text(encoding="utf-8"))
        data["category"] = category
        data["date"] = date_iso

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
            story_path = f.name

        work, p_built = props.build(
            story_path,
            "editorial",
            "silent",
            None,
            speech.EDGE_VOICES["eka"],
            "shorts",
            theme=theme,
        )

        frames = probe.settled(p_built["scenes"])
        job = {"props": str(work / "props.json"), "public": str(work / "public"), "frames": frames, "name": f"test-{theme}"}
        per, _ = probe.run_jobs([job])
        res = probe.judge(per[0], work / "public", frames)
        header_texts = [t for t in per[0][0]["probe"]["texts"] if t.get("region") == "header"]
        return res, header_texts

    def test_sitech_cybercartel_long_meta_dark_theme(self):
        """Long Georgian meta ('ხუთშაბათი · 04:00 · ხელოვნური ინტელექტი') on dark theme."""
        res, header_texts = self._probe_story_variant(theme="dark", category="ai", date_iso="2026-10-22T00:00:00Z")

        # 0 probe problems (no overflow, no frame, no contrast errors)
        self.assertEqual(res["problems"], [])

        # Find date and meta texts
        texts_by_str = {t["text"]: t for t in header_texts}
        self.assertIn("22 ოქტომბერი 2026", texts_by_str)
        # Full meta ("ხუთშაბათი · 04:00 · ხელოვნური ინტელექტი") would exceed safe width next to SiTech SVG logo (360px),
        # so compact meta is cleanly selected:
        self.assertIn("04:00 · ხელოვნური ინტელექტი", texts_by_str)

        # Verify header texts do not overlap with left logo safe boundary (SIDE=64 + 360 = 424px)
        for t in header_texts:
            x, y, w, h = t["box"]
            self.assertGreaterEqual(x, 424, f"Header text '{t['text']}' overlaps logo area: x={x}")
            self.assertLessEqual(x + w, 1080 - 64 + 1, f"Header text '{t['text']}' extends past right safe margin")

    def test_sitech_cybercartel_long_meta_light_theme(self):
        """Long Georgian meta on light theme has 0 probe problems and 0 header overlap."""
        res, header_texts = self._probe_story_variant(theme="light", category="ai", date_iso="2026-10-22T00:00:00Z")

        self.assertEqual(res["problems"], [])

        texts_by_str = {t["text"]: t for t in header_texts}
        self.assertIn("22 ოქტომბერი 2026", texts_by_str)
        self.assertIn("04:00 · ხელოვნური ინტელექტი", texts_by_str)

        for t in header_texts:
            x, y, w, h = t["box"]
            self.assertGreaterEqual(x, 424, f"Header text '{t['text']}' overlaps logo area: x={x}")
            self.assertLessEqual(x + w, 1080 - 64 + 1, f"Header text '{t['text']}' extends past right safe margin")

    def test_sitech_cybercartel_short_meta_preserves_full_weekday(self):
        """When meta line fits within maxMetaW, full weekday · time · category is preserved."""
        res, header_texts = self._probe_story_variant(theme="dark", category="security", date_iso="2026-10-24T09:00:00Z")

        self.assertEqual(res["problems"], [])
        texts_by_str = {t["text"]: t for t in header_texts}
        self.assertIn("შაბათი · 13:00 · უსაფრთხოება", texts_by_str)

    def test_probe_story_both_themes(self):
        """probe.story runs cleanly with 0 problems on both dark and light themes."""
        data = json.loads((ROOT / "stories" / "sitech-cybercartel.json").read_text(encoding="utf-8"))
        data["category"] = "ai"
        data["date"] = "2026-10-22T00:00:00Z"

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
            story_path = f.name

        for theme in ("dark", "light"):
            fmt = dict(formats.get("news"), theme=theme)
            res = probe.story(story_path, fmt)
            self.assertEqual(res["problems"], [], f"probe.story reported problems on {theme}: {res['problems']}")


if __name__ == "__main__":
    unittest.main()
