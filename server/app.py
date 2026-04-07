from fastapi import FastAPI, HTTPException, Query  # ← THIS LINE IS CRITICAL
from pydantic import BaseModel
from .env import EmailTriageEnv
from .models import EmailAction, EmailObservation, StepResult
import uvicorn

app = FastAPI(title="Email Triage OpenEnv")
_env = None

class ResetRequest(BaseModel):
    task: str = "classify"

@app.get("/")
def index():
    return {"message": "Email Triage API. See /docs for interactive schema."}

@app.get("/health")
def health(): return {"status": "ok"}

@app.post("/reset")
def reset(task: str = Query("classify", description="Task: classify, triage, respond")):
    global _env
    if task not in {"classify", "triage", "respond"}:
        raise HTTPException(400, "Task must be: classify, triage, respond")
    _env = EmailTriageEnv(task=task)
    obs = _env.reset()
    return {"observation": obs.model_dump()} 

@app.post("/step")
def step(action: EmailAction) -> StepResult:
    if not _env: raise HTTPException(400, "Call /reset first")
    result: StepResult = _env.step(action)
    return result.model_dump()

@app.get("/state")
def state():
    if _env is None:
        return {"status": "not_initialized"}
    return _env.state().model_dump()

@app.get("/tasks")
def tasks():
    return [{"name":t,"max_steps":{"classify":5,"triage":15,"respond":20}[t]} 
            for t in ["classify","triage","respond"]]

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)

# CLI entrypoint for `python -m server.app` or console_script
def main():
    uvicorn.run(app, host="0.0.0.0", port=7860)
