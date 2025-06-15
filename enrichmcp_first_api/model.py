from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel



class Role(StrEnum):
    SYSTEM = "system"
    USER = "user"
    FUNCTION = "function"
    ASSISTANT = "assistant"



class Message(BaseModel):
    role: Role
    content: str
    name: Optional[str] = None  # Only used for function role

    class Config:
        extra = "forbid"
        use_enum_values = True

    def __str__(self):
        return f"{str(self.role).upper()} MESSAGE:\n{'-' * len(str(self.role + ' MESSAGE:'))}\n{self.content}"



class ContextBuffer(ABC):
    def __init__(self):
        self._buffer: list[Message] = []

    # Note: no seek position is maintained.
    def add(self, message: Message) -> int:
        assert isinstance(message, Message)
        self._buffer.append(message)
        return len(self._buffer) - 1

    @abstractmethod
    def save(self):
        ...

    def delete(self, index: int):
        self._buffer.pop(index)

    def list(self) -> list[Message]:
        return self._buffer

    def move(self, from_index: int, to_index: int):
        if from_index == to_index:
            return
        message: Message = self._buffer.pop(from_index)
        #if from_index < to_index:
        #    to_index -= 1
        self._buffer.insert(to_index, message)

    def clear(self):
        self._buffer.clear()

    def __len__(self):
        return len(self._buffer)

