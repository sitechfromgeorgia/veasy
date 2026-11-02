"""The queue and the storage layout: names, idempotent jobs, states, retries, one worker, retention."""
import json
import os
import pathlib
import subprocess
import tempfile
import time
import unittest
import urllib.error
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parent.parent


class Home(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"VEASY_HOME": self.tmp.name})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()


class Store(Home):
    def test_layout_and_names(self):
        from tt_shorts import store
        self.assertEqual(store.job_name("tbilisi-today", 24725, "news"), "tbilisi-today-24725-news")
        self.assertEqual(store.safe("ზელენსკი Putin 2!"), "putin-2")
        p = store.render_path("tbilisi-today", 24725, "news", "cards", "page", day="2026-11-02")
        self.assertEqual(p.relative_to(store.home()).as_posix(),
                         "renders/tbilisi-today/2026-11-02/24725-news-cards-page.mp4")
        s = store.story_path("sitech", "my-post", day="2026-11-02")
        self.assertEqual(store.sources_path(s).name, "my-post.sources.json")

    def test_voice_cache_is_content_addressed(self):
        from tt_shorts import store
        a, b = store.voice_dir("gemini|Kore|calm|ტექსტი"), store.voice_dir("gemini|Sulafat|warm|ტექსტი")
        self.assertNotEqual(a, b)  # another tone never overwrites the first
        self.assertEqual(a, store.voice_dir("gemini|Kore|calm|ტექსტი"))

    def test_gc_keeps_what_is_fresh(self):
        from tt_shorts import store
        old, fresh = store.work_dir("old-job"), store.work_dir("new-job")
        past = time.time() - 5 * 86400
        os.utime(old, (past, past))
        removed = store.gc()
        self.assertEqual([pathlib.Path(p).name for p in removed["work"]], ["old-job"])
        self.assertTrue(fresh.exists())

    def test_log_lines_are_json(self):
        from tt_shorts import store
        store.log("queued", job="x")
        line = next((store.home() / "logs").glob("*.jsonl")).read_text(encoding="utf-8").splitlines()[0]
        self.assertEqual(json.loads(line)["event"], "queued")


class Queue(Home):
    def test_same_request_same_job(self):
        from tt_shorts import queue
        a, created = queue.add(source="tbilisi-today", ref=24725)
        b, again = queue.add(source="tbilisi-today", ref="24725")
        self.assertTrue(created)
        self.assertFalse(again)
        self.assertEqual(a["id"], b["id"])
        c, _ = queue.add(source="tbilisi-today", ref=24725, overrides={"captions": "roll"})
        self.assertNotEqual(a["id"], c["id"])  # another choice is another video

    def test_bad_requests_are_refused_before_queueing(self):
        from tt_shorts import formats, queue
        with self.assertRaises(ValueError):
            queue.add()
        with self.assertRaises(formats.FormatError):
            queue.add(source="text", ref="x.json", overrides={"look": "neon"})

    def test_a_story_job_is_named_after_the_story(self):
        from tt_shorts import queue
        job, _ = queue.add(story=str(ROOT / "stories" / "24725.json"))
        self.assertEqual(job["name"], "tbilisi-today-24725-news")
        self.assertEqual(job["source"], "story")

    def test_a_story_job_takes_the_story_brand(self):
        from tt_shorts import queue
        job, _ = queue.add(story=str(ROOT / "stories" / "sitech-cybercartel.json"))
        self.assertEqual(job["brand"], "sitech")
        self.assertTrue(job["name"].startswith("sitech-claude-and-grok"))
        with self.assertRaises(ValueError):  # the story decides how it looks
            queue.add(brand="tbilisi-today", story=str(ROOT / "stories" / "sitech-cybercartel.json"))
        with self.assertRaises(ValueError):  # an unknown pack is refused before it is queued
            queue.add(brand="nobody", source="tbilisi-today", ref=1)

    def test_classify(self):
        from tt_shorts import formats, queue
        self.assertEqual(queue.classify(TimeoutError("x")), "transient")
        self.assertEqual(queue.classify(urllib.error.HTTPError("u", 429, "x", {}, None)), "transient")
        self.assertEqual(queue.classify(RuntimeError("OPENROUTER_API_KEY is not set")), "config")
        self.assertEqual(queue.classify(formats.FormatError("x")), "config")
        self.assertEqual(queue.classify(RuntimeError("layout QA failed: ...")), "layout")
        self.assertEqual(queue.classify(subprocess.CalledProcessError(1, ["npx"])), "render")
        self.assertEqual(queue.classify(ValueError("checks failed: N2")), "content")

    def _run_with(self, render=None, check=None, qa=None, engine_name="gemini"):
        from tt_shorts import engine, queue
        job, _ = queue.add(story=str(ROOT / "stories" / "24725.json"))
        patches = [mock.patch.object(engine, "render_story", side_effect=render or (lambda *a, **k: {
                       "file": "/x.mp4", "problems": []})),
                   mock.patch.object(engine, "check_story", side_effect=check or (lambda *a, **k: [])),
                   mock.patch.object(engine, "qa_file", side_effect=qa or (lambda *a, **k: {"problems": []}))]
        for p in patches:
            p.start()
        try:
            out = queue.run(max_jobs=1, engine=engine_name)
        finally:
            for p in patches:
                p.stop()
        return job["id"], out

    def test_done_held_failed(self):
        from tt_shorts import queue
        jid, out = self._run_with()
        self.assertEqual(queue.get(jid)["state"], "done")
        self.assertEqual(out["counts"], {"done": 1})
        queue.retry(jid)
        self._run_with(qa=lambda *a, **k: {"problems": ["loudness -25 LUFS"]})
        self.assertEqual(queue.get(jid)["state"], "held")
        queue.retry(jid)
        self._run_with(check=lambda *a, **k: ["N2: number 7000 is not in any source article"])
        self.assertEqual((queue.get(jid)["state"], queue.get(jid)["error_class"]), ("failed", "content"))

    def test_a_preview_voice_is_never_done(self):  # done means ready to publish
        from tt_shorts import queue
        jid, _ = self._run_with(engine_name="silent")
        j = queue.get(jid)
        self.assertEqual(j["state"], "held")
        self.assertIn("preview", j["error"])

    def test_transient_errors_wait_and_retry_then_fail(self):
        from tt_shorts import queue

        def boom(*a, **k):
            raise ConnectionError("HTTP 503 from the TTS")
        jid, _ = self._run_with(render=boom)
        j = queue.get(jid)
        self.assertEqual((j["state"], j["error_class"]), ("queued", "transient"))
        self.assertGreater(j["not_before"], time.time())  # backed off, not retried at once
        for _ in range(queue.MAX_TRANSIENT):
            queue._set(jid, not_before=0)
            self._run_with(render=boom)
        self.assertEqual(queue.get(jid)["state"], "failed")

    def test_one_worker_at_a_time(self):
        from tt_shorts import queue
        with queue._lock() as first:
            self.assertTrue(first)
            self.assertTrue(queue.run(1)["busy"])

    def test_cancel(self):
        from tt_shorts import queue
        job, _ = queue.add(source="tbilisi-today", ref=1)
        self.assertEqual(queue.cancel(job["id"])["state"], "cancelled")
        self.assertEqual(queue.run(1)["processed"], [])


if __name__ == "__main__":
    unittest.main()
