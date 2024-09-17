import copy
import os
import re
from typing import Any, Dict, List, Literal, Optional, Union
from typing_extensions import TypedDict
import yaml
from threading import Lock
from pydantic import Field, BaseModel

# Global instance for the singleton
_prompt_file_instance: Union["PromptFile", None] = None


class Message(TypedDict):
    role: Literal["system", "user", "assistant"]
    content: str


class PromptConfig(BaseModel):
    model: Optional[str] = None
    messages: List[Message] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def __repr__(self):
        return f"PromptConfig(model={self.model}, messages={self.messages}, metadata={self.metadata})"

    @classmethod
    def load(cls, content: str) -> "PromptConfig":
        # Split the content into YAML and prompt parts
        match = re.match(r"^\s*---\n(.*?\n)---\n(.*)$", content, re.DOTALL)
        if not match:
            raise ValueError(f"Invalid content format, {content}")
        yaml_section, prompt_section = match.groups()

        # Load the YAML front matter
        config = yaml.safe_load(yaml_section.strip())
        messages = _extract_messages(prompt_section)

        # Create the instance using Pydantic's model_construct
        instance = cls.model_construct(
            model=config.pop("model", None), messages=messages, metadata=config
        )
        return instance

    @classmethod
    def load_file(cls, file_path: str) -> "PromptConfig":
        content = _read_file(file_path)
        return cls.load(content)

    @classmethod
    def from_filename(cls, name: str) -> "PromptConfig":
        pf = PromptFile()
        if name in pf.prompt_names:
            prompt = pf.get(name)
            # Use model_construct to create and initialize the instance
            instance = cls.model_construct(
                model=prompt.model, messages=prompt.messages, metadata=prompt.metadata
            )
            return instance
        else:
            raise ValueError(
                f"Invalid prompt name: {name}. Must be one of {pf.prompt_names}"
            )

    def format(self, **kwargs) -> "PromptConfig":
        new = self.deepcopy()
        for i, msg in enumerate(new.messages):
            content = msg["content"]
            try:
                msg["content"] = content.format(**kwargs)
            except KeyError as e:
                missing_keys = []
                remaining_placeholders = set()

                # Extract all placeholders
                placeholders = re.findall(r"(?<!\{)\{([^}\s]+)\}(?!\})", content)

                for placeholder in placeholders:
                    if placeholder in kwargs:
                        content = content.replace(
                            f"{{{placeholder}}}", str(kwargs[placeholder])
                        )
                    else:
                        remaining_placeholders.add(placeholder)
                        if placeholder == str(e).strip("'"):
                            missing_keys.append(placeholder)

                msg["content"] = content

                if missing_keys:
                    print(
                        f"Warning: KeyError in message {i}. The following keys were not found in the kwargs: {', '.join(missing_keys)}"
                    )

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
        yaml_header = yaml.dump(yaml_content, default_flow_style=False, sort_keys=False)

        # Prepare the messages content
        messages_content = "\n".join(
            f"<{msg['role']}>\n{msg['content']}\n</{msg['role']}>"
            for msg in self.messages
        )

        # Combine YAML header and messages
        full_content = f"---\n{yaml_header}---\n{messages_content}\n"

        return full_content

    def deepcopy(self) -> "PromptConfig":
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
        if not hasattr(self, "_initialized") or not self._initialized:
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
