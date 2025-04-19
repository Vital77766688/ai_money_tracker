import os
from dotenv import load_dotenv

load_dotenv()


TOOLS_FILENAME = 'aiclient/tools.json'
USER_PROMPT_FILENAME = 'aiclient/prompt.txt'
SYSTEM_PROMPT_DIRECTORY = 'aiclient/system_prompts'
API_KEY = os.getenv('OPENAI_API_KEY')
MODEL_NAME = 'gpt-4o-mini'
TOOL_CHOICE = 'auto'