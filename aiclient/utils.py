import os
import json
from . import settings


def load_tools() -> list:
    with open(settings.TOOLS_FILENAME, 'r') as f:
        return json.loads(f.read())


def load_system_prompts() -> str:
    prompts = {}
    for file in os.listdir(settings.SYSTEM_PROMPT_DIRECTORY):
        if file.endswith('.txt'):
            with open(os.path.join(settings.SYSTEM_PROMPT_DIRECTORY, file), 'r', encoding='utf8') as f:
                prompts[file.split('.')[0]] = f.read()
    return prompts


def load_user_prompt() -> str:
    with open(settings.USER_PROMPT_FILENAME, 'r', encoding='utf8') as f:
        return f.read()
