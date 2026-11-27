import importlib.util
import unittest
from pathlib import Path
from unittest import mock

import sentry_sdk
from sentry_sdk.transport import Transport

MAIN_PATH = Path(__file__).resolve().parent.parent / "src" / "main.py"


class EventTransport(Transport):
    def __init__(self):
        super().__init__()
        self.events = []

    def capture_envelope(self, envelope):
        for item in envelope.items:
            if item.type == "event":
                self.events.append(item.get_event())


def load_main_init_kwargs():
    spec = importlib.util.spec_from_file_location(
        "main_init_probe", MAIN_PATH
    )
    module = importlib.util.module_from_spec(spec)
    with mock.patch("sentry_sdk.init") as init:
        spec.loader.exec_module(module)
    init.assert_called_once()
    return init.call_args.kwargs


def raise_with_secret_local():
    webhook_url = "https://discord.com/api/webhooks/123/dummy-token"
    raise RuntimeError(f"failed: {len(webhook_url)}")


class SentryInitTest(unittest.TestCase):
    def test_ローカル変数の送信を_SDK_3_の設定で無効にする(self):
        kwargs = load_main_init_kwargs()
        self.assertEqual(
            kwargs["data_collection"], {"stack_frame_variables": False}
        )
        self.assertNotIn("include_local_variables", kwargs)

    def test_捕捉したイベントのフレームにローカル変数を含めない(self):
        kwargs = load_main_init_kwargs()
        transport = EventTransport()
        kwargs.update(dsn="https://public@example.com/1", transport=transport)
        client = sentry_sdk.Client(**kwargs)
        self.addCleanup(client.close)
        with sentry_sdk.isolation_scope():
            sentry_sdk.get_current_scope().set_client(client)
            try:
                raise_with_secret_local()
            except RuntimeError:
                sentry_sdk.capture_exception()
        client.flush()
        self.assertEqual(len(transport.events), 1)
        frames = transport.events[0]["exception"]["values"][0]["stacktrace"][
            "frames"
        ]
        self.assertGreaterEqual(len(frames), 1)
        for frame in frames:
            self.assertNotIn("vars", frame)
