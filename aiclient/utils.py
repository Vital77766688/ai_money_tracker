import json
from . import settings


def load_tools() -> list:
    with open(settings.TOOLS_FILENAME, 'r') as f:
        return json.loads(f.read())


def load_prompt() -> str:
    with open(settings.PROMPT_FILENAME, 'r', encoding='utf8') as f:
        return f.read()
