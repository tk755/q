from enum import Enum

from pydantic import BaseModel


class Role(str, Enum):
    ASSISTANT = 'assistant'
    SYSTEM = 'system'
    USER = 'user'


class Message(BaseModel):
    role: Role
    content: str
