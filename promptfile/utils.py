import os
import re
from typing import Dict, List, Literal


def _get_prompt_file_names(base_path: str) -> list:
    """
    Get a list of prompt file names without the '.prompt' extension.

    Args:
        base_path (str): The directory path to search for prompt files.

    Returns:
        list: A list of prompt file names without the '.prompt' extension.
    """
    return [f[:-7] for f in os.listdir(base_path) if f.endswith(".prompt")]


def _read_file(file_path: str) -> str:
    """
    Read the contents of a file.

    Args:
        file_path (str): The path to the file to be read.

    Returns:
        str: The contents of the file as a string.
    """
    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()
    return content


def _extract_messages(
    prompt_section: str,
) -> List[Dict[Literal["role", "content"], str]]:
    """
    Extract messages from a prompt section, handling CDATA sections.

    Args:
        prompt_section (str): The prompt section containing messages.

    Returns:
        List[Dict[Literal["role", "content"], str]]: A list of dictionaries,
        each containing a 'role' and 'content' key-value pair.
    """
    messages = []

    # First, replace CDATA sections with a unique placeholder
    cdata_sections = []

    def replace_cdata(match):
        """
        Replace CDATA sections with placeholders.

        Args:
            match: A regex match object containing the CDATA section.

        Returns:
            str: A placeholder string for the CDATA section.
        """
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
