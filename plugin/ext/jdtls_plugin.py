from ..core.sessions import AbstractPlugin
from ..core.protocol import Request
from ..core.typing import Callable, Mapping, Any, Dict
import sublime
import urllib.parse

from LSP.plugin.core.edit import apply_workspace_edit
from LSP.plugin.core.edit import parse_workspace_edit
from LSP.plugin.core.protocol import DocumentUri
from LSP.plugin.core.views import text_document_identifier


SESSION_NAME = "java-langserver"


class JdtlsPlugin(AbstractPlugin):
    @classmethod
    def name(cls) -> str:
        return SESSION_NAME

    def on_open_uri_async(
        self, uri: DocumentUri, callback: Callable[[str, str, str], None]
    ) -> bool:
        if not uri.startswith("jdt:"):
            return False
        session = self.weaksession()
        if not session:
            return False
        session.send_request_async(
            Request(
                "java/classFileContents", text_document_identifier(uri), progress=True
            ),
            lambda resp: callback(uri, resp, "Packages/Java/Java.sublime-syntax"),
            lambda err: callback(
                "ERROR", str(err), "Packages/Text/Plain text.tmLanguage"
            ),
        )
        return True

    # Custom command handling
    def on_pre_server_command(
        self, command: Mapping[str, Any], done: Callable[[], None]
    ) -> bool:
        session = self.weaksession()
        if not session:
            return False
        cmd = command["command"]
        if cmd == "java.apply.workspaceEdit":
            changes = parse_workspace_edit(command["arguments"][0])
            window = session.window
            sublime.set_timeout(
                lambda: apply_workspace_edit(window, changes).then(
                    lambda _: sublime.set_timeout_async(done)
                )
            )
            return True
        return False
