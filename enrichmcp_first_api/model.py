from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Optional
from enrichmcp import EnrichMCP, EnrichModel, Relationship

from pydantic import BaseModel


# This exists to cue the LLM that the class was created
# via an MCP tool and to hopefully lower the risk of
# type-selection confusion when creating new instances.
class WorldBuilderEntity(EnrichModel):
    """
    Model for world builder entities.
    """
    #class Config:
    #    title = "World Builder Model"
    #    description = "Base model for world builder entities in EnrichMCP."
    pass