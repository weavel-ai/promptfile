from typing import Literal
from typing_extensions import TypedDict


class Message(TypedDict):
    role: Literal["system", "user", "assistant"]
    content: str
