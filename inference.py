import asyncio
import os
import json
import sys
import re
from pathlib import Path
from typing import List, Dict, Any
from openai import OpenAI


ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from server.env import EmailTriageEnv
from server.models import EmailAction


HF_TOKEN = os.getenv("HF_TOKEN")
MODEL_NAME = os.getenv("MODEL_NAME", "meta-llama/Meta-Llama-3-8B-Instruct")
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
TASKS = os.getenv("TASKS", "classify,triage,respond").split(",")  # <-- 3 tasks
MAX_STEPS = int(os.getenv("MAX_STEPS", "4"))
MAX_TOTAL_REWARD = MAX_STEPS
SUCCESS_SCORE_THRESHOLD = 0.6
BENCHMARK = "email-triage"


if not HF_TOKEN:
    print("WARNING: HF_TOKEN not set; using dummy actions for validation.", flush=True)
    HF_TOKEN = None


if HF_TOKEN:
    client = OpenAI(api_key=HF_TOKEN, base_url=API_BASE_URL)
else:
    client = None

# Do NOT reassign client here; above if/else is enough.
# Remove this line:
# client = OpenAI(api_key=HF_TOKEN, base_url=API_BASE_URL)


SYSTEM_PROMPT = (
    "You are an API client. Return only a JSON object for the next action. "
    "Allowed keys: urgency, category, department, priority, requires_escalation, draft_reply. "
    "No prose, no code fences."
)


def log_start(task: str, env: str, model: str):
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: Dict[str, Any] | None, reward: float, done: bool, error: str | None):
    action_str = json.dumps(action, ensure_ascii=False) if action is not None else "null"
    done_str = "true" if done else "false"
    error_str = json.dumps(error) if error else "null"
    print(f"[STEP] step={step} action={action_str} reward={reward:.2f} done={done_str} error={error_str}", flush=True)


def log_end(success: bool, steps: int, score: float, rewards: List[float]):
    rewards_str = json.dumps(rewards)
    success_str = "true" if success else "false"
    print(f"[END] success={success_str} steps={steps} score={score:.2f} rewards={rewards_str}", flush=True)


def parse_action(raw: str) -> EmailAction:
    def fix_json(d: dict) -> dict:
        if "priority" in d:
            v = d["priority"]
            if isinstance(v, str):
                priority_map = {
                    "1": 1, "2": 2, "3": 3, "4": 4, "5": 5,
                    "low": 1, "medium": 2, "high": 3, "critical": 4,
                }
                d["priority"] = priority_map.get(v.lower().strip(), 1)
        return d

    try:
        data = json.loads(raw)
        data = fix_json(data)
        return EmailAction(**data)
    except Exception:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            data = json.loads(m.group(0))
            data = fix_json(data)
            return EmailAction(**data)
        raise


async def run_task(task: str):
    log_start(task=task, env=BENCHMARK, model=MODEL_NAME)
    env = EmailTriageEnv(task)
    obs = env.reset()
    rewards: List[float] = []
    steps_taken = 0

    try:
        for step in range(1, MAX_STEPS + 1):
            if obs.done:
                break

            prompt = (
                f"task: {task}\n"
                f"email: {json.dumps(obs.current_email)}\n"
                f"queue_status: {json.dumps(getattr(obs, 'queue_status', None))}\n"
                "Return JSON action."
            )

            if client is None:
                # Dummy action for validation (no HF_TOKEN)
                action = EmailAction(
                    urgency="medium",
                    category="general",
                    department="support",
                    priority=3,
                    requires_escalation=False,
                    draft_reply="This is a placeholder reply.",
                )
                action_payload = action.model_dump(mode="json")
            else:
                try:
                    resp = client.chat.completions.create(
                        model=MODEL_NAME,
                        messages=[
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": prompt},
                        ],
                        temperature=0.1,
                        max_tokens=256,
                        stream=False,
                    )
                    content = (resp.choices[0].message.content or "").strip()
                    action = parse_action(content)
                    action_payload = action.model_dump(mode="json")
                except Exception as exc:
                    log_step(step=step, action=None, reward=0.0, done=True, error=str(exc))
                    steps_taken = step
                    break

            result = env.step(action)
            obs = result.observation
            reward = result.reward
            done = result.done

            rewards.append(reward)
            steps_taken = step

            log_step(step=step, action=action_payload, reward=reward, done=done, error=None)

            if done:
                break

    finally:
        max_reward = MAX_TOTAL_REWARD if MAX_TOTAL_REWARD > 0 else len(rewards)
        score = sum(rewards) / max_reward if max_reward else 0.0
        score = min(max(score, 0.0), 1.0)
        success = score >= SUCCESS_SCORE_THRESHOLD
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)


async def main():
    for task in TASKS:
        task = task.strip()
        if not task:
            continue
        await run_task(task)
        await asyncio.sleep(0)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"[CRITICAL] Unhandled exception: {type(e).__name__}: {e}", flush=True)
        sys.exit(1)
