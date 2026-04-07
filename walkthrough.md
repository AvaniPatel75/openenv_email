# Real-Time Gmail → Email Triage OpenEnv → Firestore/Actions (FastAPI/Firebase Cloud Run)

This guide turns the training env into a live agent that watches Gmail, routes each new message through `EmailTriageEnv`, executes high-reward actions (label/archive/reply), and logs everything to Firestore. Steps are optimized for Python + FastAPI and Firebase (Cloud Run), but you can swap Cloud Functions if you prefer.

## 0) Prereqs
- Python 3.11+ local dev; `pip install -r requirements.txt` and `pip install -r server/requirements.txt`.
- Google Cloud project with:
  - Gmail API enabled (OAuth client + service account for Pub/Sub).
  - Pub/Sub topic/subscription for Gmail push.
  - Firestore in Native mode (multi-region).
- Firebase project linked to the same GCP project (for auth rules + Firestore UI).
- A Gmail account you control for testing.

## 1) Repo layout for the integration
```
openenv-email-triage/
├─ server/app.py            # keep FastAPI here; will add Gmail webhook + Firestore
├─ server/email_ingest.py   # NEW: Gmail push handler + polling fallback
├─ server/actions.py        # NEW: side effects (label/archive/reply via Gmail; log to Firestore)
├─ server/firebase_client.py# NEW: Firestore + auth helpers
├─ walkthrough.md           # this file
```

## 2) Python deps to add
Append to `server/requirements.txt`:
- `google-api-python-client`
- `google-auth`
- `google-auth-httplib2`
- `google-cloud-pubsub`
- `google-cloud-firestore`

Install locally: `pip install -r server/requirements.txt`.

## 3) Service accounts & credentials
1. Create a service account with roles:
   - `Pub/Sub Subscriber`
   - `Cloud Functions Invoker` (if using push to HTTP)
   - `Firestore User` (or Owner for dev)
2. Create a separate OAuth client (Desktop) to authorize Gmail scopes:
   - Scopes: `https://www.googleapis.com/auth/gmail.modify`
   - Run a one-time local consent to generate a token.json stored securely (not committed).
3. Set env vars for the service on Cloud Run:
   - `GOOGLE_APPLICATION_CREDENTIALS=/var/secrets/google/key.json`
   - `GMAIL_TOKEN_JSON` (optional: mount as secret)
   - `PROJECT_ID`, `FIRESTORE_COLLECTION=triage_logs`

## 4) Gmail ingestion (push + polling fallback)
- Preferred: Gmail push → Pub/Sub → FastAPI endpoint `/gmail/push`.
  - Use `users.watch` to register:
    - topic: `projects/<project-id>/topics/gmail-push`
    - labelIds: `INBOX`
  - Pub/Sub message includes `historyId`; use Gmail `users.history.list` to fetch new messages since last cursor (store cursor in Firestore doc `meta/gmail_cursor`).
- Fallback (dev): polling every 1–5 minutes using `users.messages.list` with `q="label:INBOX is:unread newer_than:2d"` and `maxResults`.

## 5) Processing pipeline
1. Fetch raw MIME → parse subject/body/sender.
2. Map to env structures:
   - `email_id` = Gmail message ID.
   - Populate `EmailData` fields with heuristics (you can leave unknown labels blank; grading still works).
3. Instantiate `EmailTriageEnv(task="classify"/"triage"/"respond")` per chosen mode.
4. Call `env.reset()` then `env.step(action)` using either:
   - A deterministic policy (rules) or
   - An LLM call (not in scope here) to choose action.
5. Evaluate reward. If reward ≥ threshold (e.g., 0.6), perform side effects:
   - Classify: apply Gmail labels (`urgency/<level>`, `category/<type>`).
   - Triage: label and move to appropriate label (e.g., `Dept/Engineering`), optionally set importance.
   - Respond: send reply email; optionally mark as sent + add note label `auto-replied`.
6. Log to Firestore:
   ```
   triage_logs/{messageId} = {
     task, action, reward, grading, executed_at, labels_applied, reply_id?, error?
   }
   ```

## 6) FastAPI endpoints to add (server/app.py)
- `POST /gmail/push` — Pub/Sub push handler:
  - Verify pubsub signature header if enabled.
  - Decode message.data (base64), extract `historyId`.
  - Enqueue processing (`process_history(historyId)`).
- `POST /gmail/poll` — manual poll trigger (secured with token).
- `GET /health` — already present.

## 7) Firestore client helper (server/firebase_client.py)
```python
from google.cloud import firestore

_db = firestore.Client()

def log_triage(message_id: str, payload: dict):
    _db.collection("triage_logs").document(message_id).set(payload, merge=True)

def get_cursor():
    doc = _db.collection("meta").document("gmail_cursor").get()
    return doc.to_dict().get("historyId") if doc.exists else None

def set_cursor(history_id: str):
    _db.collection("meta").document("gmail_cursor").set({"historyId": history_id})
```

## 8) Actions helper (server/actions.py)
- `apply_labels(message_id, labels: list[str])`
- `archive(message_id)`
- `send_reply(message_id, subject, body, thread_id)`
- All using Gmail API with the OAuth token.

## 9) Minimal processing loop (server/email_ingest.py)
```python
def process_new_messages(history_id: str | None):
    # 1) list history or poll messages
    # 2) for each message -> parse -> choose action -> env.step -> reward
    # 3) side effects if reward >= threshold
    # 4) log to Firestore and update cursor
```

## 10) Deployment (Cloud Run)
```bash
gcloud builds submit --tag gcr.io/$PROJECT_ID/email-triage
gcloud run deploy email-triage \
  --image gcr.io/$PROJECT_ID/email-triage \
  --allow-unauthenticated \
  --port 7860 \
  --set-env-vars PROJECT_ID=$PROJECT_ID,FIRESTORE_COLLECTION=triage_logs \
  --set-secrets GOOGLE_APPLICATION_CREDENTIALS=projects/$PROJECT_ID/secrets/sa-key:latest,GMAIL_TOKEN_JSON=projects/$PROJECT_ID/secrets/gmail-token:latest
```
Point Pub/Sub push to `https://<service-url>/gmail/push`.

## 11) Firebase security notes
- Firestore rules: restrict write to service account; expose read-only dashboard via Firebase Hosting + rules or BigQuery export.
- Rotate OAuth token; store in Secret Manager.

## 12) Local dev quickstart
```bash
# terminal 1
cd openenv-email-triage/server
python app.py  # serves UI + webhook endpoints

# terminal 2
python -m server.email_ingest --poll
```

## 13) Tuning ideas
- Different reward thresholds per task.
- Canary mode: log-only until confidence > 0.7.
- Rate-limit replies; require human confirmation for escalation label.

## 14) Observability
- Add `structlog`/`loguru` with JSON logs.
- Firestore dashboard by querying `triage_logs`.
- Cloud Run metrics + Error Reporting.

## 15) What to build next
- Add OAuth 2 user login (Firebase Auth) for a lightweight review console.
- Add BigQuery sink for analytics (daily export from Firestore).
- Add per-tenant label mapping config stored in Firestore.



Short answer: not yet. You’ll likely get disqualified in current form. Here’s what’s blocking and how to fix fast:

Baseline inference logs: Your [STEP] action=... prints Python enums (<Urgency.critical: 'critical'>) not JSON and ordering/field names may not match the required sample. Fix to emit exactly the sample format with JSON strings (no Enum repr, no extra text) and consistent field order.
Router credits: Runs stopped with HF 402. Judges will hit the same unless you switch to a free/low‑cost router model or provide paid credits. Set a small free model and lower MAX_STEPS / TASKS so the script finishes under quota.
Runtime/compute: Max 20 steps × 3 tasks = many calls; on 2 vCPU/8GB this will be slow. Trim to a handful of steps per task or one task only, per rules.
Docker/HF Space: Needs to deploy and respond. Verify the Space returns 200 and /reset works. Your repo has a server-only Dockerfile; ensure the Space uses it and includes openenv.yaml, typed models, and mounts static if required.
OpenEnv spec validation: run the validator mentioned in the brief; fix any errors (openenv.yaml schema, step/reset/state endpoints).
Baseline completeness: confirm python -m pytest test/test_env.py -v passes, and python inference.py completes without error using the chosen free model.
Mandatory env vars: document that API_BASE_URL, MODEL_NAME, and HF_TOKEN must be set; supply defaults that work with the free model.
If you want, I can patch inference.py to emit compliant logs (pure JSON), lower steps/tasks, and point to a free router model so it passes the automated checks.