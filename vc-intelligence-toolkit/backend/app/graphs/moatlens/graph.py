from typing import Any, Awaitable, Callable

from langgraph.graph import END, START, StateGraph

from app.graphs.moatlens.nodes import (
    bear_agent_node,
    bull_agent_node,
    claim_extraction_node,
    conflict_checker_node,
    reflection_edge,
    reflection_node,
    synthesis_node,
)
from app.graphs.moatlens.state import MoatlensState


NodeFunction = Callable[
    [dict[str, Any]],
    Awaitable[dict[str, Any]],
]


class MoatlensNodeError(Exception):
    def __init__(self, node_name: str, original_error: Exception):
        self.node_name = node_name
        self.original_error = original_error

        super().__init__(
            f"MoatLens node '{node_name}' failed: {original_error}"
        )


def tracked_node(
    node_name: str,
    node_function: NodeFunction,
) -> NodeFunction:
    async def wrapper(state: dict[str, Any]) -> dict[str, Any]:
        try:
            return await node_function(state)
        except Exception as exc:
            raise MoatlensNodeError(node_name, exc) from exc

    return wrapper


builder = StateGraph(MoatlensState)

builder.add_node(
    "claim_extraction",
    tracked_node("claim_extraction", claim_extraction_node),
)

builder.add_node(
    "bull_agent",
    tracked_node("bull_agent", bull_agent_node),
)

builder.add_node(
    "bear_agent",
    tracked_node("bear_agent", bear_agent_node),
)

builder.add_node(
    "conflict_checker",
    tracked_node("conflict_checker", conflict_checker_node),
)

builder.add_node(
    "reflection",
    reflection_node,
)

builder.add_node(
    "synthesis",
    tracked_node("synthesis", synthesis_node),
)

builder.add_edge(START, "claim_extraction")
builder.add_edge("claim_extraction", "bull_agent")
builder.add_edge("claim_extraction", "bear_agent")

builder.add_edge("bull_agent", "conflict_checker")
builder.add_edge("bear_agent", "conflict_checker")

builder.add_conditional_edges(
    "conflict_checker",
    reflection_edge,
    {
        "reflect": "reflection",
        "synthesize": "synthesis",
    },
)

builder.add_edge("reflection", "bull_agent")
builder.add_edge("reflection", "bear_agent")

builder.add_edge("synthesis", END)


def build_moatlens_graph(checkpointer):
    return builder.compile(checkpointer=checkpointer)