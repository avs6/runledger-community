# runledger-sdk

Python SDK for instrumenting LangChain, LangGraph, and OpenAI agents with RunLedger.

```python
from runledger_sdk import RunLedger

rl = RunLedger(api_key="rl_live_...")
rl.instrument()  # patches OpenAI + LangChain/LangGraph automatically
```

See the [RunLedger docs](https://github.com/yourorg/runledger) for full usage.
