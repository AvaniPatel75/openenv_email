"""
Unit tests for the updated Email Triage OpenEnv environment.
Run with: python -m pytest test/test_env.py -v
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from server.env import EmailTriageEnv
from server.models import EmailAction, EmailObservation, StepResult
from server.email_data import get_email_by_id, get_triage_queue, RESPOND_TARGET_ID


class TestReset:
    def test_reset_includes_task_and_bounds(self):
        env = EmailTriageEnv(task="classify")
        obs = env.reset()
        assert isinstance(obs, EmailObservation)
        assert obs.task == "classify"
        assert obs.step_count == 0
        assert obs.max_steps == env.max_steps
        assert isinstance(obs.current_email["id"], str) and len(obs.current_email["id"]) > 0

    def test_triage_reset_queues_items(self):
        env = EmailTriageEnv(task="triage")
        obs = env.reset()
        assert obs.queue_status is not None
        assert len(obs.queue_status) == len(get_triage_queue()) - 1  # one popped as current

    def test_respond_reset_targets_specific_email(self):
        env = EmailTriageEnv(task="respond")
        obs = env.reset()
        assert obs.current_email["id"] == RESPOND_TARGET_ID
        assert obs.done is False


class TestStepAndRewards:
    def test_classify_reward_partial(self):
        env = EmailTriageEnv(task="classify")
        env.reset()
        action = EmailAction(urgency="medium", category="billing", department="billing")
        result: StepResult = env.step(action)
        assert 0.0 <= result.reward <= 1.0
        assert result.observation.step_count == 1

    def test_triage_progresses_queue(self):
        env = EmailTriageEnv(task="triage")
        obs = env.reset()
        first_id = obs.current_email["id"]
        action = EmailAction(department=obs.current_email["true_department"], priority=obs.current_email["true_priority"])
        result: StepResult = env.step(action)
        assert result.observation.current_email["id"] != first_id or result.done

    def test_respond_requires_text(self):
        env = EmailTriageEnv(task="respond")
        env.reset()
        action = EmailAction(
            draft_reply="Apologies for the delay. We will increase your rate limits within 24 hours.",
            requires_escalation=True,
        )
        result = env.step(action)
        assert result.reward > 0.0
        assert result.done is True


class TestState:
    def test_state_reports_done_flag(self):
        env = EmailTriageEnv(task="triage")
        env.reset()
        state = env.state()
        assert state.done is False
        env.step(EmailAction(department="support"))
        state = env.state()
        assert state.step_count == 1
        assert isinstance(state.done, bool)

    def test_invalid_task_raises(self):
        with pytest.raises(ValueError):
            EmailTriageEnv(task="invalid")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
