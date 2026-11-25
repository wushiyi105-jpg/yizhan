"""译站离线单测:不联网、不花 token。"""

from __future__ import annotations

import io
import json
import os
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen

from yizhan import agent, cli, mock, tools, web
from yizhan.db import Database

SAMPLE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "doc-sample.json")


def load_sample() -> dict:
    with open(SAMPLE, encoding="utf-8") as f:
        return json.load(f)


class BaseCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Database(os.path.join(self.tmp.name, "t.db"))
        s = load_sample()
        self.did = self.db.add_doc(s["src_lang"], s["dst_lang"], s["source"])
        self.db.add_term("待办清单", "to-do list", "产品里的固定叫法")
        self.db.add_term("准确率", "accuracy")

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()


class TestTextLayer(unittest.TestCase):
    def test_numbers_strip_thousands(self):
        self.assertEqual(tools.numbers("1,200 人和 92%"), ["1200", "92%"])

    def test_missing_numbers_detected(self):
        self.assertEqual(tools.missing_numbers("共 1200 人,准确率 92%", "1200 people"), ["92%"])

    def test_han_ratio(self):
        self.assertEqual(tools.han_ratio("abc 中文"), 0.4)

    def test_sentences_split(self):
        self.assertEqual(len(tools.sentences("Hi there. Second line!")), 2)

    def test_term_apply_zh2en(self):
        body, n = tools.apply_terms("核心是待办清单", [{"zh": "待办清单", "en": "to-do list"}], "zh2en")
        self.assertEqual(n, 1)
        self.assertIn("to-do list", body)

    def test_term_check_flags_missing(self):
        probs = tools.term_check("准确率 92%", "92% precise", [{"zh": "准确率", "en": "accuracy"}], "zh", "en")
        self.assertTrue(probs)


class TestDb(BaseCase):
    def test_term_upsert_and_list(self):
        tid = self.db.add_term("待办清单", "to-do list", "改过的备注")
        self.assertEqual(next(t for t in self.db.list_terms() if t["id"] == tid)["note"], "改过的备注")

    def test_doc_roundtrip(self):
        d = self.db.get_doc(self.did)
        self.assertEqual(d["src_lang"], "zh")
        self.assertEqual(d["output"], "")

    def test_update_output_and_stats(self):
        self.db.update_output(self.did, "translated")
        self.assertEqual(self.db.stats()["translated"], 1)

    def test_delete_term(self):
        ts = self.db.list_terms()
        self.assertTrue(self.db.delete_term(ts[0]["id"]))


class TestChecks(BaseCase):
    def test_check_passes_for_clean_english(self):
        terms = self.db.list_terms()
        out = "Launched in 2026-03 with 1200 users. The core is turning recordings into a to-do list, accuracy 92%."
        probs = agent.check(load_sample()["source"], out, "zh", "en", terms)
        self.assertEqual([p for p in probs if "92%" in p or "1200" in p], [])

    def test_check_catches_han_leftover(self):
        probs = agent.check("这是中文原文", "This is 中文 mixed", "zh", "en", [])
        self.assertTrue(any("汉字" in p for p in probs))

    def test_offline_translate_is_glossary_draft(self):
        r = mock.translate(load_sample()["source"], "zh", "en", self.db.list_terms())
        self.assertTrue(r["offline"])
        self.assertIn("to-do list", r["output"])
        self.assertIn("需要模型", r["output"])

    def test_offline_polish_terms(self):
        r = mock.polish("The core is to-do-list", "zh", "en", self.db.list_terms())
        self.assertTrue(r["offline"])


class TestCli(BaseCase):
    def _run(self, argv, db_path):
        buf = io.StringIO()
        with redirect_stdout(buf):
            cli.main(["--db", db_path] + argv)
        return buf.getvalue()

    def test_add_terms_translate(self):
        tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        db_path = os.path.join(tmp.name, "c.db")
        f = os.path.join(tmp.name, "s.txt")
        with open(f, "w", encoding="utf-8") as fh:
            fh.write(load_sample()["source"])
        self.assertIn("已导入", self._run(["add", f], db_path))
        self.assertIn("to-do list", self._run(["terms", "add", "待办清单", "to-do list"], db_path))
        out = self._run(["--mock", "translate", "1"], db_path)
        self.assertIn("离线模式", out)
        self.assertIn("译文已入库", out)
        tmp.cleanup()


class TestWeb(BaseCase):
    def test_api_translate(self):
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), web._make_handler(self.db, {"api_key": ""}, True))
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        port = httpd.server_address[1]
        try:
            body = json.dumps({"text": load_sample()["source"], "src": "zh", "dst": "en"}).encode("utf-8")
            req = Request(f"http://127.0.0.1:{port}/api/translate", data=body,
                          headers={"Content-Type": "application/json"}, method="POST")
            with urlopen(req, timeout=15) as resp:
                r = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(r["offline"])
            self.assertIn("to-do list", r["output"])
            with urlopen(f"http://127.0.0.1:{port}/api/terms", timeout=10) as resp:
                self.assertEqual(len(json.loads(resp.read().decode("utf-8"))), 2)
        finally:
            httpd.shutdown()
            httpd.server_close()


if __name__ == "__main__":
    unittest.main()
