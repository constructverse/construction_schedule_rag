from typing import Any
from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError

class MyToolsProvider(ToolProvider):
    """
    Dify will use this class to validate credentials and instantiate the Tools.
    If you have no external credentials, you can leave _validate_credentials() empty.
    """
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        # If you have no real credentials, just pass
        try:
            pass
        except Exception as e:
            raise ToolProviderCredentialValidationError(str(e))
