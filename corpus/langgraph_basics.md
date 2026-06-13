# LangGraph Basics

LangGraph is a library for building stateful, multi-step applications with LLMs, represented as graphs.

## Core Concepts

A LangGraph application is built around three core concepts:

1. **State**: A shared data structure that represents the current snapshot of the application. It is typically a `TypedDict` or Pydantic model.
2. **Nodes**: Python functions that encode the logic of your agents. They receive the current state and return updates to it.
3. **Edges**: Python functions that determine which node to execute next based on the current state. Edges can be conditional.

## Defining State

State is usually defined as a `TypedDict`:

```python
from typing import TypedDict, List

class GraphState(TypedDict):
    question: str
    documents: List[str]
    answer: str
    retries: int
```

## Creating a Graph

A graph is created using `StateGraph`:

```python
from langgraph.graph import StateGraph, END

workflow = StateGraph(GraphState)

def retrieve(state: GraphState):
    docs = vector_store.similarity_search(state["question"])
    return {"documents": docs}

def generate(state: GraphState):
    answer = llm.invoke(state["question"], state["documents"])
    return {"answer": answer}

workflow.add_node("retrieve", retrieve)
workflow.add_node("generate", generate)

workflow.set_entry_point("retrieve")
workflow.add_edge("retrieve", "generate")
workflow.add_edge("generate", END)

app = workflow.compile()
```

## Conditional Edges

Conditional edges route execution based on the current state, using a routing function that returns the name of the next node:

```python
def decide_next_step(state: GraphState):
    if not state["documents"]:
        return "rewrite_query"
    return "generate"

workflow.add_conditional_edges(
    "grade_documents",
    decide_next_step,
    {
        "rewrite_query": "transform_query",
        "generate": "generate"
    }
)
```

## Running the Graph

Once compiled, a graph is invoked like a normal Python callable:

```python
result = app.invoke({"question": "What is LangGraph?", "documents": [], "answer": "", "retries": 0})
```

## Cycles and Retry Logic

Unlike a simple chain, LangGraph supports cycles, which makes it suitable for implementing retry logic. A common pattern is to track a retry counter in the state and route back to an earlier node until either a success condition is met or a maximum retry count is reached:

```python
def decide_after_grading(state: GraphState):
    if state["documents"]:
        return "generate"
    if state["retries"] >= 3:
        return "give_up"
    return "transform_query"
```

## Streaming

LangGraph supports streaming intermediate state updates as the graph executes, which is useful for showing progress to users in real time.
