from typing import Optional
from .clients.base_client import BaseClient
from .clients.client import Client
from .clients.singleton_client import SingletonClient
from .types import Message
from .prompt import Prompt


def init(base_path: Optional[str] = None) -> None:
    """
    Initialize the SingletonClient with the given base path.

    Args:
        base_path (Optional[str]): The base path for prompt files. If None, defaults to "./prompts".
    """
    SingletonClient.instance(base_path)


def get(name: str) -> Prompt:
    """
    Retrieve a Prompt object by its name using the SingletonClient.

    Args:
        name (str): The name of the prompt to retrieve.

    Returns:
        Prompt: The Prompt object corresponding to the given name.

    Raises:
        ValueError: If the prompt name is not found.
    """
    return SingletonClient.instance().get(name)


def load_file(file_path: str) -> Prompt:
    """
    Load a Prompt object from a file.

    Args:
        file_path (str): The path to the prompt file.

    Returns:
        Prompt: The Prompt object loaded from the file.
    """
    return Prompt.load_file(file_path)


# For backwards compatibility
PromptConfig = Prompt


__all__ = [
    "init",
    "get",
    "load_file",
    "BaseClient",
    "Client",
    "SingletonClient",
    "Message",
    "Prompt",
    # For backwards compatibility
    "PromptConfig",
]
