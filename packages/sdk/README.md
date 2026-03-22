# runledger-sdk

Python SDK for instrumenting OpenAI, Anthropic Claude, LangChain, and LangGraph agents with RunLedger — billing-grade observability, budget enforcement, and analytics.

## Installation

Not yet published to PyPI. Install from the repo:

```bash
# from a local clone
pip install -e "/path/to/runledger/packages/sdk[all]"

# or directly from GitHub
pip install "runledger-sdk[all] @ git+https://github.com/avs6/runledger.git#subdirectory=packages/sdk"
```

Available extras:

| Extra | Installs |
|-------|----------|
| `openai` | `openai>=1.0.0` |
| `anthropic` | `anthropic>=0.25.0` |
| `langchain` | `langchain-core>=0.3.0` |
| `langgraph` | `langchain-core>=0.3.0` + `langgraph>=0.2.0` |
| `all` | everything above + CLI |

## Quick start

### OpenAI (2 lines)

```python
from runledger_sdk import RunLedger
import openai

rl = RunLedger(api_key="rl_dev_...")  # or set RUNLEDGER_API_KEY env var
rl.instrument()                        # wraps openai.OpenAI + AsyncOpenAI

client = openai.OpenAI()

with rl.context(end_user_id="u_123", feature_tag="support-chat") as run_id:
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Hello!"}],
    )

rl.shutdown()  # flush before process exits
```

### Anthropic Claude (2 lines)

```python
from runledger_sdk import RunLedger
import anthropic

rl = RunLedger(api_key="rl_dev_...")
rl.instrument_anthropic()   # patches anthropic.Anthropic + AsyncAnthropic

client = anthropic.Anthropic()

with rl.context(end_user_id="u_123", feature_tag="support-chat") as run_id:
    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=256,
        messages=[{"role": "user", "content": "What is 2+2?"}],
    )
    print(message.content[0].text)

rl.shutdown()
```

Streaming and `AsyncAnthropic` are both supported. Token counts are captured from `usage.input_tokens` / `usage.output_tokens` on the response.

### LangChain

```python
from runledger_sdk import RunLedger
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

rl = RunLedger(api_key="rl_dev_...")

chain = (
    ChatPromptTemplate.from_template("Explain {topic} in one sentence.")
    | ChatOpenAI(model="gpt-4o-mini")
    | StrOutputParser()
)

handler = rl.callback_handler()

with rl.context(end_user_id="u_456", feature_tag="explainer") as run_id:
    result = chain.invoke({"topic": "gradient descent"}, config={"callbacks": [handler]})

rl.shutdown()
```

> If you also call `rl.instrument()`, pass `track_llm_cost=False` to the handler to avoid double-counting.

### LangGraph

```python
from runledger_sdk import RunLedger
from runledger_sdk.langgraph import instrument_graph

rl = RunLedger(api_key="rl_dev_...")

graph = builder.compile()
instrumented = instrument_graph(graph, rl._get_sync_transport())

with rl.context(end_user_id="u_789", feature_tag="qa-agent") as run_id:
    result = instrumented.invoke({"question": "What is 2+2?"})

rl.shutdown()
```

## Context propagation

```python
# Nest as many LLM calls as you like — all get tagged with the same run_id
with rl.context(
    end_user_id="u_123",
    session_id="sess_abc",
    feature_tag="checkout-assistant",
    deployment_version="v2.1",
) as run_id:
    # every provider call in this block is tracked under run_id
    pass
```

Context vars propagate through threads and asyncio tasks automatically.

## Quality scores

```python
with rl.context(feature_tag="support-chat") as run_id:
    resp = client.chat.completions.create(...)
    rl.score("helpfulness", 0.9, label="good", source="human")
    rl.score("relevance", 0.8, confidence=0.95)
```

## Prompt management

```python
rendered = rl.get_prompt(
    "support-agent",
    environment="production",
    variables={"user_name": "Alice", "company": "Acme"},
)
# rendered["content"]  → rendered template string
# rendered["version"]  → version number (for linking runs to prompt versions)
# rendered["model_hint"] → suggested model from the prompt registry
```

Prompts are cached for 60 seconds per process — safe to call on every request.

## Budget enforcement

```python
rl = RunLedger(api_key="rl_dev_...", budget_check=True)
rl.instrument()

try:
    with rl.context(end_user_id="u_123") as run_id:
        resp = client.chat.completions.create(...)
except RunLedgerBudgetExceededError as e:
    print(f"Blocked: {e}")
```

## Local / offline mode

```python
rl = RunLedger(local=True)   # prints events to stdout, no HTTP calls
```

## Configuration

| Parameter | Env var | Default |
|-----------|---------|---------|
| `api_key` | `RUNLEDGER_API_KEY` | required |
| `base_url` | `RUNLEDGER_BASE_URL` | `http://localhost:8000` |
| `local` | `RUNLEDGER_LOCAL` | `False` |
| `budget_check` | — | `False` |
| `privacy_mode` | — | `metadata_only` |

Privacy modes: `metadata_only` (default) · `errors_only` · `sampled` · `full`
