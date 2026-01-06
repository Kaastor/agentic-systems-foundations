from __future__ import annotations


from var.eval.brutal_suite import run_brutal_suite


def test_brutal_suite_failure_modes_are_deterministic() -> None:
    results = run_brutal_suite()
    by_case = {r["case"]: r for r in results}

    assert by_case["budget_exhaustion_tool_calls"]["terminal_state"] == "TerminalFailure"
    assert by_case["budget_exhaustion_tool_calls"]["has_budget_error"]

    assert by_case["sandbox_timeout_exhaust_attempts"]["timeout_seen"]
    assert by_case["sandbox_timeout_exhaust_attempts"]["ended_at_max_attempts"]

    assert by_case["model_schema_mismatch"]["detected"]
