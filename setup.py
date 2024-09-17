"""
promptfile: language support for .prompt files
"""

from setuptools import setup, find_namespace_packages

# Read README.md for the long description
with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="promptfile",
    version="0.4.0",
    packages=find_namespace_packages(),
    entry_points={},
    description="promptfile: language support for .prompt files",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="weavel",
    url="https://github.com/weavel-ai/promptfile",
    install_requires=["pydantic", "pyyaml"],
    python_requires=">=3.8.10",
    keywords=[
        ".prompt",
        "prompt",
        "prompt file",
        "llm",
    ],
)
