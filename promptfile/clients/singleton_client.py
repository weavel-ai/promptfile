from typing import Optional
from threading import Lock

from .base_client import BaseClient


class SingletonClient(BaseClient):
    """
    A singleton class for managing and accessing prompt configurations.

    Usage:
        pf = PromptFileSingleton.instance()  # Gets or creates the singleton instance
        prompt_config = pf.get("prompt_name")  # Retrieves a specific prompt configuration
    """

    _instance = None
    _lock = Lock()

    @classmethod
    def instance(cls, base_path: Optional[str] = None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(base_path)
        return cls._instance
