import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import main
import state


class StateTest(unittest.TestCase):
    def test_未作成の状態ファイルは空の辞書を返す(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            self.assertEqual(state.load_state(path), {})

    def test_有効な状態ファイルを読み込む(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            expected = {"2026-01-01": {"lunch": {"message_id": "123"}}}
            path.write_text(json.dumps(expected), encoding="utf-8")
            self.assertEqual(state.load_state(path), expected)

    def test_破損した状態ファイルでは同期せず原本を保持する(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            original = b'{"2026-01-01": '
            path.write_bytes(original)
            config = main.Config(
                "user", "password", "webhook", 1, 60, path, path.parent, True
            )
            with (
                mock.patch.object(
                    main.Config, "from_env", return_value=config
                ),
                mock.patch.object(main, "AskenClient"),
                mock.patch.object(main, "DiscordWebhookClient"),
                mock.patch.object(main, "run_cycle") as run_cycle,
                mock.patch.object(state, "save_state") as save_state,
                mock.patch.object(
                    main._shutdown, "is_set", return_value=False
                ),
            ):
                with self.assertRaises(json.JSONDecodeError):
                    main.main()
            run_cycle.assert_not_called()
            save_state.assert_not_called()
            self.assertEqual(path.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
