from LSP.plugin.core.protocol import TextDocumentSyncKindFull, TextDocumentSyncKindNone, TextDocumentSyncKindIncremental
from LSP.plugin.core.protocol import WorkspaceFolder
from LSP.plugin.core.sessions import create_session, Session, InitializeError
from LSP.plugin.core.settings import settings as global_settings
from LSP.plugin.core.types import ClientConfig
from LSP.plugin.core.types import Settings
from LSP.plugin.core.typing import Callable, Optional
from test_mocks import MockClient
from test_mocks import TEST_CONFIG
from test_mocks import TEST_LANGUAGE
import sublime
import unittest
import unittest.mock


class SessionTest(unittest.TestCase):
    def assert_if_none(self, session: Optional[Session]) -> Session:
        self.assertIsNotNone(session)
        assert session  # mypy
        return session

    def assert_initialized(self, session: Session) -> None:
        try:
            with session.acquire_timeout():
                return
        except InitializeError:
            pass
        self.fail("session failed to initialize")

    def make_session(self,
                     bootstrap_client,
                     on_pre_initialize=None,
                     on_post_initialize=None,
                     on_post_exit=None) -> Session:
        project_path = "/"
        folders = [WorkspaceFolder.from_path(project_path)]
        return self.assert_if_none(
            create_session(config=TEST_CONFIG,
                           workspace_folders=folders,
                           designated_folder=folders[0],
                           env=dict(),
                           settings=Settings(),
                           bootstrap_client=bootstrap_client,
                           on_pre_initialize=on_pre_initialize,
                           on_post_initialize=on_post_initialize,
                           on_post_exit=on_post_exit))

    # @unittest.skip("need an example config")
    def test_can_create_session(self):
        config = ClientConfig("test", ["cmd.exe"] if sublime.platform() == "windows" else ["ls"], None, [], [], None,
                              [TEST_LANGUAGE])
        project_path = "/"
        folders = [WorkspaceFolder.from_path(project_path)]
        session = self.assert_if_none(create_session(config, folders, folders[0], dict(), Settings()))
        session.client.transport.close()

    def test_can_get_started_session(self):

        post_initialize_callback = unittest.mock.Mock()
        session = self.make_session(MockClient(), on_post_initialize=post_initialize_callback)
        self.assert_initialized(session)
        self.assertIsNotNone(session.client)
        self.assertTrue(session.has_capability("testing"))
        self.assertTrue(session.get_capability("testing"))
        assert post_initialize_callback.call_count == 1

    def test_pre_initialize_callback_is_invoked(self):
        pre_initialize_callback = unittest.mock.Mock()
        post_initialize_callback = unittest.mock.Mock()
        session = self.make_session(MockClient(),
                                    on_pre_initialize=pre_initialize_callback,
                                    on_post_initialize=post_initialize_callback)
        self.assert_initialized(session)
        self.assertIsNotNone(session.client)
        self.assertTrue(session.has_capability("testing"))
        self.assertTrue(session.get_capability("testing"))
        assert pre_initialize_callback.call_count == 1
        assert post_initialize_callback.call_count == 1

    def test_can_shutdown_session(self):
        post_initialize_callback = unittest.mock.Mock()
        post_exit_callback = unittest.mock.Mock()
        session = self.make_session(MockClient(),
                                    on_post_initialize=post_initialize_callback,
                                    on_post_exit=post_exit_callback)
        self.assert_initialized(session)
        self.assertIsNotNone(session.client)
        self.assertTrue(session.has_capability("testing"))
        assert post_initialize_callback.call_count == 1
        session.end()
        self.assertIsNone(session.client)
        self.assertFalse(session.has_capability("testing"))
        self.assertIsNone(session.get_capability("testing"))
        assert post_exit_callback.call_count == 1

    def test_initialize_failure(self):
        def async_response(f: Callable[[], None]) -> None:
            # resolve the request one second after the timeout triggers (so it's always too late).
            timeout_ms = 1000 * (global_settings.initialize_timeout + 1)
            sublime.set_timeout(f, timeout_ms=timeout_ms)

        client = MockClient(async_response=async_response)
        session = self.make_session(client)
        with self.assertRaises(InitializeError):
            session.handles_path("foo")

    def test_document_sync_capabilities(self) -> None:
        client = MockClient()
        client.responses = {
            'initialize': {
                'capabilities': {
                    'textDocumentSync': {
                        "openClose": True,
                        "change": TextDocumentSyncKindFull,
                        "save": True
                    }
                }
            }
        }
        session = Session(TEST_CONFIG, [], None, client)
        self.assertTrue(session.should_notify_did_open())
        self.assertTrue(session.should_notify_did_close())
        self.assertEqual(session.text_sync_kind(), TextDocumentSyncKindFull)
        self.assertTrue(session.should_notify_did_change())
        self.assertFalse(session.should_notify_will_save())
        self.assertFalse(session.should_request_will_save_wait_until())
        self.assertEqual(session.should_notify_did_save(), (True, False))

        client.responses = {
            'initialize': {
                'capabilities': {
                    'textDocumentSync': {
                        "openClose": False,
                        "change": TextDocumentSyncKindNone,
                        "save": {},
                        "willSave": True,
                        "willSaveWaitUntil": False
                    }
                }
            }
        }
        session = Session(TEST_CONFIG, [], None, client)
        self.assertFalse(session.should_notify_did_open())
        self.assertFalse(session.should_notify_did_close())
        self.assertEqual(session.text_sync_kind(), TextDocumentSyncKindNone)
        self.assertFalse(session.should_notify_did_change())
        self.assertTrue(session.should_notify_will_save())
        self.assertFalse(session.should_request_will_save_wait_until())
        self.assertEqual(session.should_notify_did_save(), (True, False))

        client.responses = {
            'initialize': {
                'capabilities': {
                    'textDocumentSync': {
                        "openClose": False,
                        "change": TextDocumentSyncKindIncremental,
                        "save": {
                            "includeText": True
                        },
                        "willSave": False,
                        "willSaveWaitUntil": True
                    }
                }
            }
        }
        session = Session(TEST_CONFIG, [], None, client)
        self.assertFalse(session.should_notify_did_open())
        self.assertFalse(session.should_notify_did_close())
        self.assertEqual(session.text_sync_kind(), TextDocumentSyncKindIncremental)
        self.assertTrue(session.should_notify_did_change())
        self.assertFalse(session.should_notify_will_save())
        self.assertTrue(session.should_request_will_save_wait_until())
        self.assertEqual(session.should_notify_did_save(), (True, True))

        client.responses = {
            'initialize': {
                'capabilities': {  # backwards compatible :)
                    'textDocumentSync': TextDocumentSyncKindIncremental
                }
            }
        }
        session = Session(TEST_CONFIG, [], None, client)
        self.assertTrue(session.should_notify_did_open())
        self.assertTrue(session.should_notify_did_close())
        self.assertEqual(session.text_sync_kind(), TextDocumentSyncKindIncremental)
        self.assertTrue(session.should_notify_did_change())
        self.assertTrue(session.should_notify_will_save())
        self.assertFalse(session.should_request_will_save_wait_until())
        self.assertEqual(session.should_notify_did_save(), (True, False))

        client.responses = {
            'initialize': {
                'capabilities': {  # backwards compatible :)
                    'textDocumentSync': TextDocumentSyncKindNone
                }
            }
        }
        session = Session(TEST_CONFIG, [], None, client)
        self.assertFalse(session.should_notify_did_open())
        self.assertFalse(session.should_notify_did_close())
        self.assertEqual(session.text_sync_kind(), TextDocumentSyncKindNone)
        self.assertFalse(session.should_notify_did_change())
        self.assertFalse(session.should_notify_will_save())
        self.assertFalse(session.should_request_will_save_wait_until())
        self.assertEqual(session.should_notify_did_save(), (False, False))
