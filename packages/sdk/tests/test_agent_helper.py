from __future__ import annotations

from unittest.mock import MagicMock, patch

from runledger_sdk import RunLedger, published_skill_tool_names


def test_record_run_start_enqueues_event() -> None:
    rl = RunLedger(api_key="rl_test_abc")
    helper = rl.agent_helper()
    transport = MagicMock()
    rl._sync_transport = transport  # type: ignore[assignment]

    run_id = helper.record_run_start(feature_tag="support", intent="triage")

    assert run_id
    transport.enqueue.assert_called_once()
    event = transport.enqueue.call_args.args[0]
    assert event["event_type"] == "run_start"
    assert event["feature_tag"] == "support"
    assert event["intent"] == "triage"


def test_record_span_enqueues_start_and_end() -> None:
    rl = RunLedger(api_key="rl_test_abc")
    helper = rl.agent_helper()
    transport = MagicMock()
    rl._sync_transport = transport  # type: ignore[assignment]

    span_id = helper.record_span(run_id="run-1", name="research", cost_usd="0.25")

    assert span_id
    assert transport.enqueue.call_count == 2
    assert transport.enqueue.call_args_list[0].args[0]["event_type"] == "span_start"
    assert transport.enqueue.call_args_list[1].args[0]["event_type"] == "span_end"


def test_check_budget_calls_api() -> None:
    rl = RunLedger(api_key="rl_test_abc", base_url="http://example.test")

    response = MagicMock()
    response.json.return_value = {"allowed": True}
    response.raise_for_status.return_value = None

    with patch("runledger_sdk.agent_helper.httpx.get", return_value=response) as mock_get:
        result = rl.check_budget(end_user_id="u_1", feature_tag="qa")

    assert result["allowed"] is True
    mock_get.assert_called_once()


def test_check_policy_calls_api() -> None:
    rl = RunLedger(api_key="rl_test_abc", base_url="http://example.test")

    response = MagicMock()
    response.json.return_value = {"allowed": False, "decision": "block"}
    response.raise_for_status.return_value = None

    with patch("runledger_sdk.agent_helper.httpx.post", return_value=response) as mock_post:
        result = rl.check_policy(tool_name="shell", dry_run=True)

    assert result["decision"] == "block"
    body = mock_post.call_args.kwargs["json"]
    assert body["tool_name"] == "shell"
    assert body["dry_run"] is True


def test_published_skill_tool_names_contains_expected_canonical_tools() -> None:
    names = published_skill_tool_names()
    assert "runledger.budget_check" in names
    assert "runledger.policy_check" in names
    assert "runledger.filter_mcp_tool" in names


def test_from_env_sets_default_task_metadata(monkeypatch) -> None:
    monkeypatch.setenv("RUNLEDGER_API_KEY", "rl_test_env")
    rl = RunLedger.from_env(agent="cursor", workspace="Desktop Agents")
    assert rl._default_task_metadata["agent"] == "cursor"
    assert rl._default_task_metadata["workspace"] == "Desktop Agents"


def test_task_wrapper_records_default_outcome() -> None:
    rl = RunLedger(api_key="rl_test_abc")
    transport = MagicMock()
    rl._sync_transport = transport  # type: ignore[assignment]

    with rl.task("Fix failing tests", intent="code_generation") as task:
        task.tool_call("pytest")
        task.model_call(provider="openai", model="gpt-4o-mini", input_tokens=10, output_tokens=4)

    event_types = [call.args[0]["event_type"] for call in transport.enqueue.call_args_list]
    assert "run_start" in event_types
    assert "tool_call" in event_types
    assert "provider_call" in event_types
    assert "outcome" in event_types
    assert "run_end" in event_types
