import copy
import re
from typing import Any, Dict, List, Optional
import yaml
from pydantic import Field, BaseModel

from .types import Message
from .utils import _read_file, _extract_messages


class Prompt(BaseModel):
    """
    A class representing a prompt with associated model, messages, and metadata.

    Attributes:
        model (Optional[str]): The model associated with the prompt.
        messages (List[Message]): A list of messages in the prompt.
        metadata (Dict[str, Any]): Additional metadata associated with the prompt.
    """

    model: Optional[str] = None
    messages: List[Message] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def __repr__(self):
        """
        Returns a string representation of the Prompt object.

        Returns:
            str: A string representation of the Prompt object.
        """
        return f"Prompt(model={self.model}, messages={self.messages}, metadata={self.metadata})"

    @classmethod
    def load(cls, content: str) -> "Prompt":
        """
        Loads a Prompt object from a string content.

        Args:
            content (str): The string content containing YAML front matter and prompt messages.

        Returns:
            Prompt: A new Prompt object.

        Raises:
            ValueError: If the content format is invalid.
        """
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
    def load_file(cls, file_path: str) -> "Prompt":
        """
        Loads a Prompt object from a file.

        Args:
            file_path (str): The path to the file containing the prompt.

        Returns:
            Prompt: A new Prompt object.
        """
        content = _read_file(file_path)
        return cls.load(content)

    def format(self, **kwargs) -> "Prompt":
        """
        Formats the prompt by replacing placeholders with provided values.

        Args:
            **kwargs: Keyword arguments where keys are placeholders and values are their replacements.

        Returns:
            Prompt: A new Prompt object with formatted messages.
        """
        new = self.deepcopy()
        for i, msg in enumerate(new.messages):
            content = msg["content"]
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

            msg["content"] = content

            if remaining_placeholders:
                pass
                # print(
                #     f"The following placeholders in message {i} were not replaced: {', '.join(remaining_placeholders)}"
                # )

        return new

    def dump(self) -> str:
        """
        Restores the prompt to its original format with all attributes.

        Returns:
            str: A string representation of the prompt in its original format.
        """
        # Prepare the YAML content
        yaml_content = {"model": self.model, **self.metadata}

        # Dump the YAML content
        yaml_header = yaml.dump(yaml_content, default_flow_style=False, sort_keys=False)

        # Prepare the messages content
        messages_content = "\n".join(
            f"<{msg['role']}>\n{msg['content']}\n</{msg['role']}>"
            for msg in (self.messages if isinstance(self.messages, list) else [])
        )

        # Combine YAML header and messages
        full_content = f"---\n{yaml_header}---\n{messages_content}\n"

        return full_content

    def deepcopy(self) -> "Prompt":
        """
        Creates a deep copy of the Prompt object.

        Returns:
            Prompt: A new Prompt object that is a deep copy of the original.
        """
        return copy.deepcopy(self)
