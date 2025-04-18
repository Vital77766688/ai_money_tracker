import os
from dotenv import load_dotenv

load_dotenv()


TOOLS_FILENAME = 'aiclient/tools.json'
PROMPT_FILENAME = 'aiclient/prompt.txt'
API_KEY = os.getenv('OPENAI_API_KEY')
MODEL_NAME = 'gpt-4o-mini'
TOOL_CHOICE = 'auto'