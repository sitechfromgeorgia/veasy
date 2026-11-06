"""Tests for the Edit Room: tt_shorts/segments.py, tt_shorts/steer.py, tt_shorts/room.py, and veasy:steer."""
import copy
import json
import os
import pathlib
import shutil
import tempfile
import unittest

from tt_shorts import compose, flash, golden, probe, props, segments, speech, store

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _sample_props():
    story = json.loads((ROOT / "demo" / "film-partia.json").read_text(encoding="utf-8"))
    words = speech.estimate_words(story["narration"])
    marks = speech.scene_frames(story, words)
    scenes = []
    for i, s in enumerate(story["scenes"]):
        scenes.append({
            **s,
            "from": marks[i],
            "duration": marks[i + 1] - marks[i],
        })
    return {
        "id": story["id"],
        "fps": 30,
        "width": 1080,
        "height": 1920,
        "durationInFrames": marks[-1],
        "variant": "editorial",
        "theme": "default",
        "transition": "cut",
        "outro": "card",
        "outroFrom": marks[-2],
        "outroText": "გამოიწერე",
        "source": "Tbilisi Today",
        "sources": ["საკონსტიტუციო სასამართლო"],
        "sourcesLine": "წყარო: საკონსტიტუციო სასამართლო",
        "date": {"date": "6 ნოემბერი 2026", "time": "14:00", "weekday": "პარასკევი"},
        "topic": "პოლიტიკა",
        "category": "პოლიტიკა",
        "cta": "გამოიწერე არხი",
        "url": "tbilisi.today/stories/900003",
        "ticker": "ხუთი პარტია, ერთი სარჩელი",
        "brand": {"name": "tbilisi-today"},
        "style": {"variant": "editorial", "header": "bar", "footer": "ticker", "motif": "none"},
        "chapters": [{"n": 1, "of": 2, "title": "სარჩელი", "from": 0}, {"n": 2, "of": 2, "title": "მუხლი", "from": marks[4]}],
        "captions": {
            "mode": "Flow",
            "design": "page",
            "size": 56,
            "lineHeight": 1.22,
            "band": 768,
            "pad": 24,
            "lines": [
                {"start": 0.0, "end": 2.0, "words": [{"text": "ხუთი", "from": 0.0, "to": 0.5}]},
                {"start": 4.5, "end": 6.5, "words": [{"text": "ორმოცდასამ", "from": 4.5, "to": 5.5}]},
                {"start": 20.0, "end": 22.0, "words": [{"text": "მუხლი", "from": 20.0, "to": 21.0}]},
            ],
            "pages": [
                {"start": 0.0, "end": 2.0, "lines": [0], "key": None},
                {"start": 4.5, "end": 6.5, "lines": [1], "key": None},
                {"start": 20.0, "end": 22.0, "lines": [2], "key": None},
            ],
        },
        "scenes": scenes,
        "music": "news-1.mp3",
        "sfx": [{"t": 1.2, "name": "whoosh"}],
    }


class TestSegments(unittest.TestCase):
    def test_segment_hash_is_deterministic_and_scoped_to_scene(self):
        p1 = _sample_props()
        p2 = copy.deepcopy(p1)
        keys_before = [segments.segment_key(p1, i) for i in range(len(p1["scenes"]))]
        self.assertEqual(keys_before, [segments.segment_key(p2, i) for i in range(len(p2["scenes"]))])

        # Edit scene 1's label: only scene 1's hash should change
        p2["scenes"][1]["label"] = "21 სექტემბრიდან 2 ნოემბრამდე"
        keys_after = [segments.segment_key(p2, i) for i in range(len(p2["scenes"]))]
        self.assertNotEqual(keys_before[1], keys_after[1])
        for i in range(len(p1["scenes"])):
            if i != 1:
                self.assertEqual(keys_before[i], keys_after[i], f"scene {i} hash should not change")

    def test_audio_only_fields_do_not_invalidate_visual_segment_hashes(self):
        p1 = _sample_props()
        p2 = copy.deepcopy(p1)
        p2["music"] = "other-bed.mp3"
        p2["sfx"] = [{"t": 0.5, "name": "pop"}]
        p2["voiceTrim"] = 0.15
        for i in range(len(p1["scenes"])):
            self.assertEqual(segments.segment_key(p1, i), segments.segment_key(p2, i))

    def test_loop_outro_makes_final_scene_depend_on_hook(self):
        p1 = _sample_props()
        p1["outro"] = "loop"
        p2 = copy.deepcopy(p1)
        p2["scenes"][0]["lines"] = ["შეცვლილი", "ჰუკი"]
        last = len(p1["scenes"]) - 1
        self.assertNotEqual(segments.segment_key(p1, 0), segments.segment_key(p2, 0))
        self.assertNotEqual(segments.segment_key(p1, last), segments.segment_key(p2, last))
        self.assertEqual(segments.segment_key(p1, 2), segments.segment_key(p2, 2))

    def test_plan_remotion_tracks_cache_hits_and_misses(self):
        with tempfile.TemporaryDirectory() as d:
            old_home = os.environ.get("VEASY_HOME")
            os.environ["VEASY_HOME"] = d
            try:
                p1 = _sample_props()
                plan1 = segments.plan_remotion(p1)
                self.assertEqual(plan1["hits"], [])
                self.assertEqual(len(plan1["misses"]), len(p1["scenes"]))
                self.assertEqual(plan1["frames_to_render"], p1["durationInFrames"])

                # Populate fake cached segment files for all scenes
                for seg in plan1["segments"]:
                    sp = pathlib.Path(seg["path"])
                    sp.parent.mkdir(parents=True, exist_ok=True)
                    sp.write_bytes(b"fake-mp4-bytes")

                # Edit scene 1 label -> 10 hits, 1 miss
                p2 = copy.deepcopy(p1)
                p2["scenes"][1]["label"] = "ახალი ეტიკეტი"
                plan2 = segments.plan_remotion(p2)
                self.assertEqual(plan2["misses"], [1])
                self.assertEqual(len(plan2["hits"]), len(p1["scenes"]) - 1)
                self.assertEqual(plan2["frames_to_render"], p2["scenes"][1]["duration"])
            finally:
                if old_home is None:
                    os.environ.pop("VEASY_HOME", None)
                else:
                    os.environ["VEASY_HOME"] = old_home

    def test_plan_hyperframes_tracks_scene_isolation(self):
        with tempfile.TemporaryDirectory() as d:
            proj = pathlib.Path(d) / "proj"
            compose.scaffold(ROOT / "stories" / "24835.json", brand="sitech", project=proj,
                             blocks="kinetic-headline,number-reveal,end-card", force=True)
            built = compose.build(proj, ROOT / "stories" / "24835.json", engine="silent")
            try:
                plan1 = segments.plan_hyperframes(proj, built["props"], built["timing"])
                self.assertEqual(len(plan1["segments"]), 3)
                for seg in plan1["segments"]:
                    sp = pathlib.Path(seg["path"])
                    sp.parent.mkdir(parents=True, exist_ok=True)
                    sp.write_bytes(b"fake-hf-mp4")

                # Edit s1.html only -> s0 remains a cache hit
                s1_path = proj / "compositions" / "s1.html"
                s1_path.write_text(s1_path.read_text(encoding="utf-8") + "\n<!-- steer edit -->", encoding="utf-8")
                plan2 = segments.plan_hyperframes(proj, built["props"], built["timing"])
                self.assertIn(0, plan2["hits"])
                self.assertIn(1, plan2["misses"])
            finally:
                shutil.rmtree(built["work"], ignore_errors=True)


class TestFrameHashIdentity(unittest.TestCase):
    def test_remotion_segmented_splice_matches_full_render_outside_changed_scene(self):
        """Render a 3-scene short both monolithically and via segmented cache, then change scene 1's label and
        verify that every frame outside scene 1 has the exact same frame hash as a full render."""
        with tempfile.TemporaryDirectory() as d:
            tmp = pathlib.Path(d)
            old_home = os.environ.get("VEASY_HOME")
            os.environ["VEASY_HOME"] = str(tmp / "home")
            try:
                story = {
                    "id": 99001,
                    "brand": "tbilisi-today",
                    "category": "society",
                    "date": "2026-11-06T12:00:00+04:00",
                    "sources": ["ინტერპრესნიუსი"],
                    "narration": "ვაზისუბანში გაზი შეწყდება. ექვსი ათას ოთხას აბონენტს შეეხება. მოიწონე და გამოიწერე არხი.",
                    "cta": "გამოიწერე არხი",
                    "scenes": [
                        {"type": "hook", "at": "ვაზისუბანში გაზი", "kicker": "უბანი", "lines": ["ვაზისუბანში", "გაზი შეწყდება"]},
                        {"type": "stat", "at": "ექვსი ათას", "kicker": "აბონენტი", "headline": "გაზის გარეშე", "value": 6400, "label": "ვაზისუბნის დასახლება"},
                        {"type": "end", "at": "მოიწონე და", "headline": "გამოიწერე არხი"},
                    ],
                }
                story_file = tmp / "story.json"
                story_file.write_text(json.dumps(story, ensure_ascii=False), encoding="utf-8")

                work1, pr1 = props.build(story_file, variant="editorial", engine="silent", music="off", transition="cut")
                seg_before = tmp / "seg_before.mp4"
                props.render_video(work1, pr1, seg_before, segmented=True)

                # Now edit scene 1's label and render both via segmented cache (1 miss, 2 hits) and full render
                story["scenes"][1]["label"] = "განახლებული ეტიკეტი"
                story_file.write_text(json.dumps(story, ensure_ascii=False), encoding="utf-8")
                work2, pr2 = props.build(story_file, variant="editorial", engine="silent", music="off", transition="cut")

                plan_after = segments.plan_remotion(pr2, work2)
                self.assertEqual(plan_after["hits"], [0, 2])
                self.assertEqual(plan_after["misses"], [1])

                steered_mp4 = tmp / "steered.mp4"
                full_after = tmp / "full_after.mp4"
                props.render_video(work2, pr2, steered_mp4, segmented=True)
                segments.render_remotion_full(work2, pr2, full_after)

                manifest = json.loads(segments.manifest_path(steered_mp4).read_text(encoding="utf-8"))
                self.assertEqual(manifest["hits"], [0, 2])
                self.assertEqual(manifest["misses"], [1])
                self.assertEqual(manifest["splice_mode"], "copy")

                hashes_before_seg = segments.frame_sha256_list(seg_before)
                hashes_steered = segments.frame_sha256_list(steered_mp4)
                dhashes_steered = segments.video_frame_dhashes(steered_mp4)
                dhashes_full_after = segments.video_frame_dhashes(full_after)

                self.assertEqual(len(hashes_steered), pr2["durationInFrames"])
                self.assertEqual(len(dhashes_full_after), pr2["durationInFrames"])

                s1_start = pr2["scenes"][1]["from"]
                s1_end = s1_start + pr2["scenes"][1]["duration"]
                for f in range(pr2["durationInFrames"]):
                    if f < s1_start or f >= s1_end:
                        self.assertEqual(hashes_steered[f], hashes_before_seg[f], f"frame {f} outside scene 1 changed")
                        self.assertEqual(dhashes_steered[f]["hash"], dhashes_full_after[f]["hash"], f"frame {f} outside scene 1 != full")
                        self.assertEqual(dhashes_steered[f]["band"], dhashes_full_after[f]["band"], f"frame {f} band outside scene 1 != full")
                    else:
                        self.assertEqual(dhashes_steered[f]["hash"], dhashes_full_after[f]["hash"], f"frame {f} inside scene 1 != full")
                        self.assertEqual(dhashes_steered[f]["band"], dhashes_full_after[f]["band"], f"frame {f} band inside scene 1 != full")
                self.assertNotEqual(hashes_steered[s1_start:s1_end], hashes_before_seg[s1_start:s1_end])
            finally:
                if old_home is None:
                    os.environ.pop("VEASY_HOME", None)
                else:
                    os.environ["VEASY_HOME"] = old_home


if __name__ == "__main__":
    unittest.main()
