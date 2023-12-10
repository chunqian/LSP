from ..core.sessions import AbstractPlugin
from ..core.protocol import Request
from ..core.typing import Callable, Mapping, Any, Dict
import sublime
import urllib.parse


SESSION_NAME = "rust-langserver"


class RustPlugin(AbstractPlugin):

    @classmethod
    def name(cls) -> str:
        return SESSION_NAME

    def on_pre_server_command(self, command: Mapping[str, Any], done_callback: Callable[[], None]) -> bool:
        command_name = command["command"]
        try:
            session = self.weaksession()
            if not session:
                return False
            if command_name in ("rust-analyzer.runSingle", "rust-analyzer.runDebug",
                                "rust-analyzer.showReferences", "rust-analyzer.triggerParameterHints"):
                done_callback()
                return True
            else:
                return False
        except Exception as ex:
            print("Exception handling command {}: {}".format(command_name, ex))
            return False
