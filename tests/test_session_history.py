import os
import tempfile
import unittest

from menemory.session_manager import add_message, history_turn_count, init_session, load_session, read_history
from menemory.workspace import session_history_path


class SessionHistoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._old_home = os.environ.get("MENEMORY_HOME")
        os.environ["MENEMORY_HOME"] = self._tmp.name

    def tearDown(self) -> None:
        if self._old_home is None:
            os.environ.pop("MENEMORY_HOME", None)
        else:
            os.environ["MENEMORY_HOME"] = self._old_home
        self._tmp.cleanup()

    def test_add_message_persists_raw_history(self) -> None:
        init_session(session_id="test-history", overwrite=True)
        add_message("user", "hello")
        add_message("assistant", "world")

        rows = read_history(session_id="test-history")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["role"], "user")
        self.assertEqual(rows[0]["content"], "hello")
        self.assertEqual(rows[1]["role"], "assistant")
        self.assertEqual(rows[1]["content"], "world")
        self.assertTrue(session_history_path("test-history").exists())

    def test_prune_still_keeps_full_raw_history(self) -> None:
        init_session(session_id="test-prune", overwrite=True)
        for idx in range(21):
            add_message("user", f"message-{idx}")

        session = load_session()
        self.assertLessEqual(len(session.get("conversation", [])), 10)
        self.assertTrue((session.get("summary") or "").strip())
        self.assertEqual(history_turn_count("test-prune"), 21)
        self.assertEqual(len(read_history("test-prune")), 21)


if __name__ == "__main__":
    unittest.main()
