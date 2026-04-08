import asyncio
import os
import json
import sys
import re
import httpx
from openai import OpenAI

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:7860")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
HF_TOKEN = os.getenv("HF_TOKEN")

TASKS = os.getenv("TASKS", "classify,triage,respond").split(",")
MAX_STEPS = {"classify": 5, "triage": 15, "respond": 20}

if not HF_TOKEN:
    sys.exit("HF_TOKEN required")

llm_client = OpenAI(api_key=HF_TOKEN, base_url="https://api.openai.com/v1")  # OPENAI API
http_client = httpx.AsyncClient()

SYSTEM_PROMPT = """Return ONLY valid JSON action:
{"urgency": "low|medium|high|critical", 
 "category": "billing|technical|general|complaint|praise", 
 "department": "billing|engineering|sales|support|escalation", 
 "priority": 1-5, 
 "requires_escalation": true|false, 
 "draft_reply": "text"}"""

def log_start(task: str, env: str, model: str):
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step: int, action: dict | None, reward: float, done: bool, error: str | None):
    action_str = json.dumps(action) if action else "null"
    done_str = "true" if done else "false"
    error_str = json.dumps(error) if error else "null"
    print(f"[STEP] step={step} action={action_str} reward={reward:.2f} done={done_str} error={error_str}", flush=True)

def log_end(success: bool, steps: int, score: float, rewards: list):
    rewards_str = json.dumps(rewards)
    success_str = "true" if success else "false"
    print(f"[END] success={success_str} steps={steps} score={score:.2f} rewards={rewards_str}", flush=True)

def parse_action(content: str) -> dict:
    match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content)
    if match:
        return json.loads(match.group(0))
    return {}

async def run_task(task: str):
    log_start(task=task, env="email-triage", model=MODEL_NAME)
    rewards = []
    step_count = 0
    
    async with http_client:
        # HTTP RESET
        try:
            resp = await http_client.post(f"{API_BASE_URL.rstrip('/')}/reset?task={task}", timeout=30)
            if resp.status_code != 200:
                log_end(False, 0, 0.0, [])
                return
            obs = resp.json()["observation"]
        except:
            log_end(False, 0, 0.0, [])
            return
        
        max_step = MAX_STEPS.get(task, 5)
        
        for step in range(1, max_step + 1):
            if obs.get("done", False):
                break
            
            # LLM generates action
            try:
                prompt = f"Task: {task}\nEmail: {json.dumps(obs.get('current_email', {}))}\nAction JSON:"
                llm_resp = llm_client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[{"role": "system", "content": SYSTEM_PROMPT},
                             {"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=300
                )
                action = parse_action(llm_resp.choices[0].message.content or "")
                
                # HTTP STEP
                step_resp = await http_client.post(f"{API_BASE_URL.rstrip('/')}/step", 
                                                 json=action, timeout=30)
                if step_resp.status_code != 200:
                    raise ValueError(step_resp.text)
                
                result = step_resp.json()
                reward = result.get("reward", 0.0)
                done = result.get("done", False)
                obs = result.get("observation", {})
                
                rewards.append(reward)
                step_count = step
                log_step(step=step, action=action, reward=reward, done=done, error=None)
                
            except Exception as e:
                log_step(step=step, action=None, reward=0.0, done=True, error=str(e))
                break
        
        score = sum(rewards) / len(rewards) if rewards else 0.0
        success = score >= 0.6
        log_end(success=success, steps=step_count, score=round(score, 2), rewards=rewards)

async def main():
    for task in TASKS:
        if task := task.strip():
            await run_task(task)
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
