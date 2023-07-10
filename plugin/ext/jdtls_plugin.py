from ..core.sessions import AbstractPlugin
from ..core.protocol import Request
from ..core.typing import Callable, Mapping, Any, Dict
import sublime
import urllib.parse

from ..core.edit import apply_workspace_edit
from ..core.edit import parse_workspace_edit
from ..core.protocol import DocumentUri
from ..core.views import text_document_identifier


SESSION_NAME = "java-langserver"


class JdtlsPlugin(AbstractPlugin):
    @classmethod
    def name(cls) -> str:
        return SESSION_NAME

    def unicode_to_str(self, resp):
        text = ""
        try:
            text = resp.encode('ascii','strict').decode('unicode_escape')
        except Exception as e:
            text = resp
        return text

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
            lambda resp: callback(uri, self.unicode_to_str(resp), "Packages/Java/Java.sublime-syntax"),
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
