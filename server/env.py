# Your existing EmailData + EMAILS list here (keep as-is)
from .email_data import (
    EmailData,
    EMAILS,
    get_email_by_id,
    get_triage_queue,
    RESPOND_TARGET_ID,
)
from .models import EmailAction, EmailObservation, EmailState, StepResult
from typing import Dict, Any
import uuid, random

random.seed(42)


class EmailTriageEnv:
    def __init__(self, task: str = "classify"):
        if task not in {"classify", "triage", "respond"}:
            raise ValueError(f"Unknown task '{task}'")
        self.task = task
        self.max_steps = {"classify": 5, "triage": 10, "respond": 8}[task]
        self.reset()

    def reset(self) -> EmailObservation:
        self.step_count = 0
        self.processed = []
        self.episode_id = str(uuid.uuid4())
        self.last_done = False

        if self.task == "classify":
            self.current_email = random.choice(EMAILS)

        elif self.task == "triage":
            self.queue = [e.id for e in get_triage_queue()]
            self.current_email = get_email_by_id(self.queue.pop(0))
            if self.queue:  # 🔥 ADD SAFETY CHECK
                self.current_email = get_email_by_id(self.queue.pop(0))
            else:
                self.current_email = random.choice(EMAILS)

        else:  # respond
            self.current_email = get_email_by_id(RESPOND_TARGET_ID)

        return EmailObservation(
            task=self.task,
            current_email=self.current_email.model_dump(),
            queue_status=getattr(self, "queue", None),
            step_count=0,
            max_steps=self.max_steps,
            done=False 
        )

    def step(self, action: EmailAction) -> StepResult:
        if getattr(self, "last_done", False):
            return StepResult(
                observation=EmailObservation(
                    task=self.task,
                    current_email=self.current_email.model_dump(),
                    queue_status=getattr(self, "queue", None),
                    feedback="episode_already_done",
                    step_count=self.step_count,
                    max_steps=self.max_steps,
                    done=True,
                ),
                reward=0.0,
                done=True,
                info={"error": "episode_done"},
            )

        self.step_count += 1

        reward = self._grade_action(action)

        if self.task == "triage" and hasattr(self, "queue") and self.queue:
            self.current_email = get_email_by_id(self.queue.pop(0))

        done = self.step_count >= self.max_steps or self._is_complete()
        if self.task == "respond" and action.draft_reply:
            done = True
        self.last_done = done

        feedback = self._feedback(action)

        obs = EmailObservation(
            task=self.task,
            current_email=self.current_email.model_dump(),
            queue_status=getattr(self, "queue", None),
            feedback=feedback,
            step_count=self.step_count,
            max_steps=self.max_steps,
            done=done
        )

        return StepResult(
            observation=obs,
            reward=reward,
            done=done,
            info={"accuracy": self._action_accuracy(action)}
        )

    def _feedback(self, action: EmailAction) -> str:
        return (
            f"urgency={action.urgency}, "
            f"category={action.category}, "
            f"department={action.department}, "
            f"escalation={action.requires_escalation}"
        )

    def _action_accuracy(self, action: EmailAction) -> float:
        return self._grade_action(action)

    def _grade_action(self, action: EmailAction) -> float:
        if self.task == "respond":
            return self._grade_response(action)
        elif self.task == "triage":
            return self._grade_triage(action)
        else:
            return self._grade_classification(action)

    def _grade_classification(self, action: EmailAction) -> float:
        score = 0.0
        gt = self.current_email
        if action.urgency == gt.true_urgency:
            score += 0.4
        if action.category == gt.true_category:
            score += 0.4
        if action.department == gt.true_department:
            score += 0.2
        return self._clamp(score)

    def _grade_triage(self, action: EmailAction) -> float:
        score = 0.0
        gt = self.current_email
        if action.department == gt.true_department:
            score += 0.5
        if action.priority:
            if action.priority == gt.true_priority:
                score += 0.3
            elif abs(action.priority - gt.true_priority) == 1:
                score += 0.15
        if action.requires_escalation == gt.requires_escalation:
            score += 0.2
        return self._clamp(score)

    def _grade_response(self, action: EmailAction) -> float:
        if not action.draft_reply:
            return 0.01                    # ← was: return 0.0
        text = action.draft_reply.lower()
        score = 0.0
        if "sorry" in text or "apolog" in text:
            score += 0.2
        if len(text.split()) > 50:
            score += 0.2
        if "resolve" in text or "fix" in text:
            score += 0.2
        if action.requires_escalation:
            score += 0.2
        if "thank" in text:
            score += 0.2
        return self._clamp(score)

    @staticmethod
    def _clamp(score: float) -> float:
        """Keep score strictly within (0, 1) — never 0.0 or 1.0."""
        return max(0.01, min(score, 0.99))

    def _is_complete(self) -> bool:
        if self.task == "triage":
            return not getattr(self, "queue", [])
        return False

    def state(self) -> EmailState:
        return EmailState(
            episode_id=self.episode_id, 
            task=self.task,
            step_count=self.step_count,
            done=self.last_done or self._is_complete() or self.step_count >= self.max_steps
        )
