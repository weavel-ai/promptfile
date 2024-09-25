from .base_client import BaseClient


class Client(BaseClient):
    """
    A non-singleton class for managing and accessing prompt configurations.

    Usage:
        pf = PromptFile()  # Creates a new instance
        prompt_config = pf.get("prompt_name")  # Retrieves a specific prompt configuration
    """

    pass
