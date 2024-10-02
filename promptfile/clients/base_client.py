import os
from typing import Dict, Optional, Type

from ..utils import _get_prompt_file_names, _read_file
from ..prompt import Prompt


class BaseClient:
    def __init__(
        self, base_path: Optional[str] = None, prompt_class: Type[Prompt] = Prompt
    ):
        self.base_path = base_path or "./prompts"
        self.prompt_names = _get_prompt_file_names(self.base_path)
        self.prompts: Dict[str, Prompt] = {}
        self.prompt_class = prompt_class
        self.init()

    def init(self):
        for prompt_name in self.prompt_names:
            file_path = os.path.join(self.base_path, f"{prompt_name}.prompt")
            content = _read_file(file_path)
            self.prompts[prompt_name] = self.prompt_class.load(content)
            self.prompts[prompt_name].name = prompt_name

    def get(self, name: str) -> Prompt:
        if name in self.prompt_names:
            return self.prompts.get(name)
        else:
            raise ValueError(
                f"Invalid prompt name: {name}. Must be one of {self.prompt_names}"
            )
