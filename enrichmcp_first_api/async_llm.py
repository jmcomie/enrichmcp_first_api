from typing import Optional
from enrichmcp_first_api.model import Message


async def get_chat_completion_response(
    messages: list[Message],
    tools: Optional[list[dict]] = None,
):
    return "Mock response."