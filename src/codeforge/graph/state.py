"""LangGraph state schema — uses TypedDict for graph edges."""
from __future__ import annotations
from typing import TypedDict, Annotated
from operator import add
from ..schemas import SwarmState


class GraphState(TypedDict, total=False):
    state: SwarmState           # full pydantic state object
    messages: Annotated[list, add]