import json
from openai import AsyncOpenAI
from . import settings
from .utils import load_prompt, load_tools
from .tools import tools_mapping


tools = load_tools()
prompt = load_prompt()


class Client:
    def __init__(self, context: dict) -> None:
        self.model = settings.MODEL_NAME
        self.prompt = prompt
        self.tools = tools or []
        self.tool_choice = settings.TOOL_CHOICE
        self.context = context or {}
        self.messages = [{"role": "system", "content": self.prompt.format(**self.context)}]

        self.client = AsyncOpenAI(api_key=settings.API_KEY, base_url='https://api.openai.com/v1')

    def add_message(self, content: dict) -> None:
        self.messages.append(content)

    async def get_completion(self) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            tools=self.tools,
            tool_choice=self.tool_choice
        )
        if not response.choices:
            raise Exception(f"Error: {response.error}")
        return response.choices[0].message

    async def tool_call(self, tool) -> str:
        if tool.type == "function":
            function_name = tool.function.name
            function_args = json.loads(tool.function.arguments)
            if function_name in tools_mapping:
                result = await tools_mapping[function_name](**function_args)
                return json.dumps(result)

    async def chat(self, message: str) -> str:
        self.add_message({"role": "user", "content": message})
        response = await self.get_completion()

        while response.tool_calls:
            """
            Call tools sequentially for each response while there are some
            """
            self.add_message(response)
            for tool in response.tool_calls:
                """
                Call tools simultaneously in each response
                """
                tool_response = await self.tool_call(tool)
                self.add_message({
                    "role": "tool",
                    "tool_call_id": tool.id,
                    "name": tool.function.name,
                    "content": tool_response
                })
            response = await self.get_completion()
            
        if response.content:
            self.add_message({"role": "assistant", "content": response.content})
            return response.content
        return "No reply! Try again!"
