
# LangGraph Documentation

LangGraph is a library for building stateful, multi-step applications with LLMs, represented as graphs. It is built on top of LangChain and extends it with the ability to create cyclic workflows, which is essential for agent-like behaviors such as reasoning, tool use, and self-correction.

Key features include:
- **Stateful**: Maintains a shared state across multiple steps.
- **Cyclic**: Supports loops and retry logic, unlike simple linear chains.
- **Observable**: Supports streaming of intermediate steps for real-time feedback.
- **Debuggable**: Built-in visualization and checkpointing for debugging.
- **Controllable**: Human-in-the-loop capabilities for approval and editing.

LangGraph is particularly well-suited for:
- Retrieval-Augmented Generation (RAG) with self-correction.
- Multi-agent systems with coordinated workflows.
- Conversational AI with memory and context management.
- Complex reasoning tasks requiring multiple tool calls.

---

## Installation

Install LangGraph using pip:

```bash
pip install langgraph
```

For LangChain integration (required for most use cases):

```bash
pip install langchain langchain-openai
```

For visualization support:

```bash
pip install langgraph-cli
```

---

## Core Concepts

A LangGraph application is built around three fundamental concepts:

### 1. State

State is a shared data structure that represents the current snapshot of the application. It is typically defined as a `TypedDict` or a Pydantic model. All nodes in the graph read from and write to this shared state.

**Why state matters:**
- Enables persistence across steps.
- Allows nodes to communicate without direct coupling.
- Supports checkpointing and resumption.
- Makes debugging easier by inspecting state at any point.

### 2. Nodes

Nodes are Python functions that encode the logic of your application. Each node receives the current state as input and returns updates to the state. Nodes are the building blocks of your graph.

**Node characteristics:**
- Pure functions (ideally): Given the same state, produce the same output.
- Atomic: Each node performs a single, well-defined task.
- Composable: Multiple nodes can be combined into larger workflows.

### 3. Edges

Edges define the flow of execution between nodes. They determine which node runs next based on the current state. Edges can be unconditional (always go to the same next node) or conditional (route based on state).

**Edge types:**
- **Normal edges**: Always route to a specific node.
- **Conditional edges**: Route based on a routing function that examines state.
- **Entry points**: Define where the graph starts execution.

---

## Defining State

State is the backbone of LangGraph. It is usually defined as a `TypedDict` for simplicity, though Pydantic models are also supported for more complex validation.

### Basic State Definition

```python
from typing import TypedDict, List

class GraphState(TypedDict):
    question: str
    documents: List[str]
    answer: str
    retries: int
```

**Key points about state:**
- All fields should have type annotations.
- Use `TypedDict` for simple cases; Pydantic `BaseModel` for validation.
- State is immutable in practice: nodes return updates, not modified state.
- Optional fields should use `Optional[T]` or `T | None`.

### State with Pydantic

For more robust validation, especially in production systems:

```python
from pydantic import BaseModel
from typing import List, Optional

class GraphState(BaseModel):
    question: str
    documents: List[str] = []
    answer: Optional[str] = None
    retries: int = 0
    sources: List[str] = []
```

Pydantic state provides:
- Automatic validation of state updates.
- Default values for missing fields.
- Type coercion and error messages.
- JSON serialization for checkpointing.

---

## Creating a Graph

A graph is created using `StateGraph`, which is parameterized by your state type.

### Basic Graph Structure

```python
from langgraph.graph import StateGraph, END

workflow = StateGraph(GraphState)

def retrieve(state: GraphState):
    """Retrieve documents from a vector store."""
    docs = vector_store.similarity_search(state["question"])
    return {"documents": docs}

def generate(state: GraphState):
    """Generate an answer using retrieved documents."""
    answer = llm.invoke(state["question"], state["documents"])
    return {"answer": answer}

# Add nodes to the graph
workflow.add_node("retrieve", retrieve)
workflow.add_node("generate", generate)

# Define the flow
workflow.set_entry_point("retrieve")
workflow.add_edge("retrieve", "generate")
workflow.add_edge("generate", END)

# Compile the graph
app = workflow.compile()
```

**What happens during compilation:**
- LangGraph validates the graph structure (no orphaned nodes, valid edges).
- Creates an executable graph with checkpointing support.
- Returns a callable object that can be invoked with initial state.

### Running the Graph

Once compiled, the graph is invoked like a normal Python function:

```python
result = app.invoke({
    "question": "What is LangGraph?",
    "documents": [],
    "answer": "",
    "retries": 0
})
```

The `invoke` method:
- Takes an initial state dictionary.
- Executes nodes in order according to edges.
- Returns the final state after reaching `END`.
- Raises errors if any node fails (unless error handling is configured).

---

## Conditional Edges

Conditional edges are the key to building dynamic, decision-making workflows. They route execution based on the current state.

### Defining Conditional Edges

```python
def decide_next_step(state: GraphState):
    """Route based on whether documents were found."""
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

**How conditional edges work:**
1. The routing function (`decide_next_step`) receives the current state.
2. It returns a string key (e.g., `"rewrite_query"` or `"generate"`).
3. The mapping dictionary translates that key to the actual node name.
4. Execution continues at the mapped node.

**Best practices for routing functions:**
- Keep them pure and deterministic.
- Return clear, documented string keys.
- Handle all possible state combinations.
- Use type hints for the state parameter.

---

## Cycles and Retry Logic

Unlike simple chains, LangGraph supports cycles, which makes it ideal for implementing retry logic and iterative refinement.

### Retry Pattern Example

```python
def decide_after_grading(state: GraphState):
    """Route based on document relevance and retry count."""
    if state["documents"]:
        return "generate"
    if state["retries"] >= 3:
        return "give_up"
    return "transform_query"

workflow.add_conditional_edges(
    "grade_documents",
    decide_after_grading,
    {
        "generate": "generate",
        "transform_query": "transform_query",
        "give_up": "fallback_response"
    }
)
```

**Retry logic explained:**
- `state["retries"]` tracks how many attempts have been made.
- If documents are found, proceed to generation.
- If no documents and retries remain, rewrite the query and try again.
- If max retries exceeded, fall back to a default response.

### Common Cycle Patterns

| Pattern | Use Case | Key State Field |
|---------|----------|-----------------|
| Retry | Query rewriting, API retries | `retries: int` |
| Refinement | Iterative improvement | `iterations: int`, `best_result` |
| Tool loops | Multi-step tool calling | `tool_calls: list`, `observations` |
| Human-in-loop | Approval workflows | `approved: bool` |

---

## Streaming

LangGraph supports streaming intermediate state updates, which is essential for real-time user feedback in applications like chatbots.

### Streaming Updates

```python
for event in app.stream({"question": "What is AI?"}):
    print(event)
```

**What gets streamed:**
- Each node execution produces an event.
- Events contain the node name and state updates.
- Useful for showing progress: "Retrieving documents...", "Generating answer..."

### Streaming with Async

```python
async for event in app.astream({"question": "What is AI?"}):
    print(event)
```

**Streaming benefits:**
- Improved perceived performance for users.
- Better debugging visibility.
- Enables progress bars and loading states.
- Supports real-time collaborative applications.

---

## Checkpoints and Persistence

LangGraph supports checkpointing, which allows you to save and resume graph execution.

### Using Checkpoints

```python
from langgraph.checkpoint.sqlite import SqliteSaver

memory = SqliteSaver.from_conn_string(":memory:")
app = workflow.compile(checkpointer=memory)

# Run with a thread ID for persistence
config = {"configurable": {"thread_id": "conversation_1"}}
result = app.invoke({"question": "Hello?"}, config=config)

# Resume later
result = app.invoke({"question": "Tell me more"}, config=config)
```

**Checkpointing use cases:**
- Conversational memory across sessions.
- Resuming long-running workflows after crashes.
- Human-in-the-loop approval processes.
- A/B testing different graph configurations.

---

## Human-in-the-Loop

LangGraph supports interrupting execution for human approval or input.

### Interrupting for Approval

```python
from langgraph.types import interrupt

def sensitive_action(state: GraphState):
    """Ask for human approval before executing."""
    approval = interrupt({
        "question": "Approve this action?",
        "action_details": state["action"]
    })
    if approval == "approved":
        return execute_action(state)
    return {"status": "rejected"}
```

**Human-in-the-loop patterns:**
- **Approval**: Pause before sensitive operations.
- **Editing**: Allow humans to modify generated content.
- **Input**: Request additional information when needed.
- **Correction**: Enable fixing errors in the workflow.

---

## Multi-Agent Systems

LangGraph excels at building multi-agent systems where multiple specialized agents collaborate.

### Agent as Node Pattern

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator

class MultiAgentState(TypedDict):
    messages: Annotated[list, operator.add]
    next_agent: str

workflow = StateGraph(MultiAgentState)

def research_agent(state: MultiAgentState):
    """Agent specialized in research tasks."""
    result = research_llm.invoke(state["messages"])
    return {"messages": [result], "next_agent": "writer"}

def writer_agent(state: MultiAgentState):
    """Agent specialized in writing tasks."""
    result = writer_llm.invoke(state["messages"])
    return {"messages": [result], "next_agent": END}

workflow.add_node("research", research_agent)
workflow.add_node("writer", writer_agent)
workflow.set_entry_point("research")
workflow.add_conditional_edges(
    "research",
    lambda state: state["next_agent"],
    {"writer": "writer", END: END}
)
workflow.add_edge("writer", END)

app = workflow.compile()
```

**Multi-agent design patterns:**
- **Sequential**: Agents pass work down a pipeline.
- **Hierarchical**: Supervisor agent delegates to worker agents.
- **Collaborative**: Agents contribute to a shared state iteratively.
- **Competitive**: Multiple agents propose solutions; best one selected.

---

## Integration with LangChain

LangGraph is designed to work seamlessly with LangChain components.

### Using LangChain LLMs

```python
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

llm = ChatOpenAI(model="gpt-4", temperature=0)

def generate(state: dict):
    messages = [
        ("system", "You are a helpful assistant."),
        ("human", state["question"])
    ]
    response = llm.invoke(messages)
    return {"answer": response.content}

workflow = StateGraph(dict)
workflow.add_node("generate", generate)
workflow.set_entry_point("generate")
workflow.add_edge("generate", END)
app = workflow.compile()
```

### Using LangChain Tools

```python
from langchain.tools import tool
from langgraph.prebuilt import ToolNode

@tool
def search(query: str) -> str:
    """Search the web for information."""
    return f"Results for: {query}"

tools = [search]
tool_node = ToolNode(tools)

workflow.add_node("tools", tool_node)
```

---

## Debugging and Visualization

LangGraph provides built-in tools for debugging and visualizing your graphs.

### Graph Visualization

```python
from IPython.display import Image, display

display(Image(app.get_graph().draw_mermaid_png()))
```

This generates a visual diagram of your graph showing:
- All nodes and their names.
- Edges between nodes.
- Conditional branches.
- Entry and exit points.

### Common Debugging Techniques

| Technique | How | When to Use |
|-----------|-----|-------------|
| Print state | `print(state)` inside nodes | Quick debugging |
| Stream events | `app.stream()` | Trace execution flow |
| Checkpoints | `checkpointer.get()` | Inspect saved states |
| Mermaid diagram | `draw_mermaid_png()` | Understand structure |

---

## Best Practices

### Graph Design

- **Keep nodes small**: Each node should do one thing well.
- **Use descriptive names**: Node names should indicate their purpose.
- **Handle errors**: Add error handling nodes for robustness.
- **Limit cycles**: Avoid infinite loops with clear exit conditions.
- **Type your state**: Use TypedDict or Pydantic for clarity.

### State Management

- **Minimize state size**: Only store necessary data.
- **Use defaults**: Provide sensible defaults for optional fields.
- **Document state schema**: Clearly document what each field represents.
- **Version state**: Consider versioning for long-running applications.

### Performance

- **Cache LLM calls**: Use LangChain caching for repeated queries.
- **Parallelize when possible**: Use `Send` for parallel node execution.
- **Stream for UX**: Always stream in user-facing applications.
- **Checkpoint strategically**: Balance persistence with performance.
'''
