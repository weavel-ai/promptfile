import copy
import os
import re
from typing import Any, Dict, List, Literal, Optional, Self, Union
import yaml
from threading import Lock

from .types import Message

# Global instance for the singleton
_prompt_file_instance: Union["PromptFile", None] = None


class PromptConfig:
    def __init__(
        self,
        messages: List[Dict[Literal["role", "content"], str]],
        model: Optional[str] = None,
        **kwargs,
    ):
        self.model: Optional[str] = model
        self.messages: List[Dict[Literal["role", "content"], str]] = [
            Message.model_validate(msg).model_dump() for msg in messages
        ]
        self.metadata: Dict[str, Any] = kwargs

    def __repr__(self):
        return f"PromptConfig(model={self.model}, messages={self.messages}, metadata={self.metadata})"

    @classmethod
    def load(cls, content: str) -> Self:
        instance = cls.__new__(cls)
        # Split the content into YAML and prompt parts
        yaml_section, prompt_section = content.split("---", 2)[1:]

        # Load the YAML front matter
        config = yaml.safe_load(yaml_section.strip())
        instance.model = config.pop("model", None)

        # Extract the messages
        instance.messages = _extract_messages(prompt_section)
        instance.metadata = config

        return instance

    @classmethod
    def load_file(cls, file_path: str) -> Self:
        content = _read_file(file_path)
        return cls.load(content)

    @classmethod
    def from_filename(cls, name: str) -> Self:
        # instance = cls.__new__(cls)
        pf = PromptFile()
        if name in pf.prompt_names:
            prompt = pf.get(name)
            instance = cls.__new__(cls)
            instance.model = prompt.model
            instance.messages = prompt.messages
            instance.metadata = prompt.metadata
            return instance
        else:
            raise ValueError(
                f"Invalid prompt name: {name}. Must be one of {pf.prompt_names}"
            )

    def format(self, **kwargs) -> Self:
        new = self.deepcopy()
        for i, msg in enumerate(new.messages):
            content = msg["content"]
            try:
                # Use a single format call with all kwargs
                msg["content"] = content.format(**kwargs)
            except KeyError as e:
                # If KeyError occurs, fall back to manual replacement
                missing_keys = []
                for key, value in kwargs.items():
                    if f"{{{key}}}" in content:
                        content = content.replace(f"{{{key}}}", str(value))
                    elif key == str(e).strip("'"):
                        missing_keys.append(key)

                msg["content"] = content

                if missing_keys:
                    print(
                        f"Warning: KeyError in message {i}. The following keys were not found in the content: {', '.join(missing_keys)}"
                    )

                # Check for any remaining placeholders
                import re

                remaining_placeholders = re.findall(r"\{(.+?)\}", content)
                if remaining_placeholders:
                    print(
                        f"Warning: The following placeholders in message {i} were not replaced: {', '.join(remaining_placeholders)}"
                    )

            except ValueError as e:
                print(f"Error in message {i}: Invalid format string. {str(e)}")

        return new

    def dump(self) -> str:
        """Restore the prompt file to its original format with all attributes."""
        # Prepare the YAML content
        yaml_content = {"model": self.model, **self.metadata}

        # Dump the YAML content
        yaml_header = yaml.dump(yaml_content, default_flow_style=False)

        # Prepare the messages content
        messages_content = "\n".join(
            f"<{msg['role']}>\n{msg['content']}\n</{msg['role']}>"
            for msg in self.messages
        )

        # Combine YAML header and messages
        full_content = f"---\n{yaml_header}---\n{messages_content}\n"

        return full_content

    def deepcopy(self) -> Self:
        return copy.deepcopy(self)


class PromptFile:
    _instance = None
    _lock = Lock()

    def __new__(cls, base_path: Optional[str] = None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(PromptFile, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, base_path: Optional[str] = None):
        if self._initialized:
            return
        self.base_path = base_path or "./prompts"
        self.prompt_names = get_prompt_file_names(self.base_path)
        self.prompts: Dict[str, PromptConfig] = {}
        self._initialized = True
        self.init()

    def init(self):
        for prompt_name in self.prompt_names:
            file_path = os.path.join(self.base_path, f"{prompt_name}.prompt")
            content = _read_file(file_path)
            self.prompts[prompt_name] = PromptConfig.load(content)

    @classmethod
    def get(cls, name: str) -> PromptConfig:
        instance = cls()
        if name in instance.prompt_names:
            return instance.prompts.get(name)
        else:
            raise ValueError(
                f"Invalid prompt name: {name}. Must be one of {instance.prompt_names}"
            )


def init(base_path: Optional[str] = None) -> None:
    global _prompt_file_instance
    _prompt_file_instance = PromptFile(base_path)
    PromptFile(base_path)


def load(name: str) -> PromptConfig:
    if _prompt_file_instance is None:
        raise RuntimeError("PromptFile is not initialized. Call init() first.")
    return PromptFile.get(name)


# This function should return the list of prompt file names in the specified directory.
def get_prompt_file_names(base_path: str) -> list:
    return [f[:-7] for f in os.listdir(base_path) if f.endswith(".prompt")]


# def read_prompt(text: str):
#     # Split the content into YAML and prompt parts
#     yaml_section, prompt_section = text.split("---", 2)[1:]

#     # Load the YAML front matter
#     config = yaml.safe_load(yaml_section.strip())
#     model = config.pop("model", None)

#     # Extract the messages
#     messages = _extract_messages(prompt_section)

#     return PromptConfig(model=model, messages=messages, **config)


def _read_file(file_path: str):
    with open(file_path, "r") as file:
        content = file.read()
    return content


def load_file(file_path: str):
    content = _read_file(file_path)
    return PromptConfig.load(content)


def _extract_messages(
    prompt_section: str,
) -> List[Dict[Literal["role", "content"], str]]:
    messages = []

    # First, replace CDATA sections with a unique placeholder
    cdata_sections = []

    def replace_cdata(match):
        cdata_sections.append(match.group(1))
        return f"CDATA_PLACEHOLDER_{len(cdata_sections) - 1}"

    prompt_section = re.sub(
        r"<!\[CDATA\[(.*?)\]\]>", replace_cdata, prompt_section, flags=re.DOTALL
    )

    # Use a single regex to match all types of tags in order
    pattern = r"<(system|user|assistant)>(.*?)</\1>"
    matches = re.findall(pattern, prompt_section, re.DOTALL)

    for role, content in matches:
        # Replace CDATA placeholders with their original content
        message = re.sub(
            r"CDATA_PLACEHOLDER_(\d+)",
            lambda m: cdata_sections[int(m.group(1))],
            content,
        )
        message = message.strip()
        messages.append({"role": role, "content": message})

    return messages


# Usage
# import promptfile as pf

# example_prompt = pf.load("example")

# print(example_prompt.model)
# print(example_prompt.messages)


# Example usage
if __name__ == "__main__":
    PromptFile.load()
    TEST_PROMPT = PromptFile.get(name="example")
    TEST_PROMPT.messages
