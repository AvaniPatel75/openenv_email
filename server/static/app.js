const taskButtons = document.querySelectorAll(".chip");
const emailViewer = document.getElementById("email-viewer");
const actionPanel = document.getElementById("action-panel");
const gradingBox = document.getElementById("grading-result");
const scoreValue = document.getElementById("score-value");
const scoreProgress = document.getElementById("score-progress");
const stepHistory = document.getElementById("step-history");
const stateTask = document.getElementById("state-task");
const stateStep = document.getElementById("state-step");
const stateDone = document.getElementById("state-done");
const stateReward = document.getElementById("state-reward");
const banner = document.getElementById("done-banner");
const finalScore = document.getElementById("final-score");
const serverIndicator = document.getElementById("server-indicator");

let currentTask = null;
let currentObservation = null;
let history = [];

// --- Helpers ---------------------------------------------------------------
function setServerStatus(ok) {
  if (ok) {
    serverIndicator.textContent = "Server Online";
    serverIndicator.classList.remove("pill-off");
    serverIndicator.classList.add("pill-on");
  } else {
    serverIndicator.textContent = "Server Offline";
    serverIndicator.classList.remove("pill-on");
    serverIndicator.classList.add("pill-off");
  }
}

async function checkHealth() {
  try {
    const res = await fetch("/health");
    setServerStatus(res.ok);
  } catch (e) {
    setServerStatus(false);
  }
}

function renderEmailCard(email) {
  const tpl = document.getElementById("email-card-template").content.cloneNode(true);
  tpl.querySelector(".email-subject").textContent = email.subject;
  tpl.querySelector(".email-meta").textContent = `${email.sender} · ${email.sender_domain}`;
  tpl.querySelector(".email-body").textContent = email.body;
  tpl.querySelector(".pill").textContent = email.id;
  return tpl;
}

function renderObservation(obs) {
  emailViewer.innerHTML = "";
  gradingBox.innerHTML = "";
  if (!obs) return;

  if (obs.task === "classify") {
    emailViewer.appendChild(renderEmailCard(obs.email));
  } else if (obs.task === "triage") {
    const frag = document.createDocumentFragment();
    obs.queue.forEach((e) => frag.appendChild(renderEmailCard(e)));
    emailViewer.appendChild(frag);
  } else if (obs.task === "respond") {
    const frag = document.createDocumentFragment();
    frag.appendChild(renderEmailCard(obs.email));
    const ctx = document.createElement("div");
    ctx.className = "panel";
    ctx.innerHTML = `<div class="panel-title">Account Context</div><p class="email-body">${obs.context}</p>`;
    emailViewer.appendChild(frag);
    emailViewer.appendChild(ctx);
  }
}

function makeSelect(options, name, defaultValue) {
  const sel = document.createElement("select");
  sel.name = name;
  options.forEach((opt) => {
    const o = document.createElement("option");
    o.value = opt;
    o.textContent = opt;
    if (opt === defaultValue) o.selected = true;
    sel.appendChild(o);
  });
  return sel;
}

function renderActionPanel(obs) {
  actionPanel.innerHTML = "";
  if (!obs) {
    actionPanel.textContent = "Choose a task to see actions.";
    return;
  }

  if (obs.task === "classify") {
    const form = document.createElement("form");
    form.innerHTML = `
      <div class="field">
        <label>Urgency</label>
        <select name="urgency">
          <option>low</option><option>medium</option><option>high</option><option>critical</option>
        </select>
      </div>
      <div class="field">
        <label>Category</label>
        <select name="category">
          <option>billing</option><option>technical</option><option>general</option><option>complaint</option><option>praise</option>
        </select>
      </div>
      <div class="field">
        <label>Reasoning (optional)</label>
        <textarea name="reasoning" placeholder="Why you chose this urgency/category"></textarea>
      </div>
      <div class="submit-row">
        <span class="hint">Action type: classify</span>
        <button class="btn" type="submit">Submit Classification</button>
      </div>
    `;
    form.onsubmit = async (e) => {
      e.preventDefault();
      const data = Object.fromEntries(new FormData(form));
      await sendAction({
        action_type: "classify",
        email_id: obs.email.id,
        urgency: data.urgency,
        category: data.category,
        reasoning: data.reasoning,
      });
    };
    actionPanel.appendChild(form);
  } else if (obs.task === "triage") {
    const form = document.createElement("form");
    const table = document.createElement("table");
    table.className = "triage-table";
    table.innerHTML = `
      <thead><tr><th>Email</th><th>Priority (1-5)</th><th>Department</th></tr></thead>
      <tbody></tbody>
    `;
    const tbody = table.querySelector("tbody");
    obs.queue.forEach((email, idx) => {
      const row = document.createElement("tr");
      const prioritySel = makeSelect(["1","2","3","4","5"], `priority_${idx}`, "3");
      const deptSel = makeSelect(["billing","engineering","sales","support","escalation"], `department_${idx}`, "support");
      row.innerHTML = `<td>${email.subject}</td>`;
      const tdP = document.createElement("td"); tdP.appendChild(prioritySel);
      const tdD = document.createElement("td"); tdD.appendChild(deptSel);
      row.appendChild(tdP); row.appendChild(tdD);
      // stash email id
      row.dataset.emailId = email.id;
      tbody.appendChild(row);
    });
    form.appendChild(table);
    const submitRow = document.createElement("div");
    submitRow.className = "submit-row";
    submitRow.innerHTML = `<span class="hint">Action type: triage_queue</span><button class="btn" type="submit">Submit Triage</button>`;
    form.appendChild(submitRow);
    form.onsubmit = async (e) => {
      e.preventDefault();
      const decisions = [];
      [...tbody.children].forEach((row, idx) => {
        const priority = parseInt(form[`priority_${idx}`].value, 10);
        const dept = form[`department_${idx}`].value;
        decisions.push({
          email_id: row.dataset.emailId,
          priority,
          department: dept,
        });
      });
      await sendAction({ action_type: "triage_queue", decisions });
    };
    actionPanel.appendChild(form);
  } else if (obs.task === "respond") {
    const form = document.createElement("form");
    form.innerHTML = `
      <div class="field">
        <label>Subject</label>
        <input type="text" name="subject" value="Re: ${obs.email.subject}">
      </div>
      <div class="field">
        <label>Body</label>
        <textarea name="body" placeholder="Compose a professional, empathetic reply">${defaultRespondBody(obs.email)}</textarea>
      </div>
      <div class="field">
        <label>Escalate?</label>
        <select name="escalate">
          <option value="true">true</option>
          <option value="false">false</option>
        </select>
      </div>
      <div class="field">
        <label>Escalation Reason (optional)</label>
        <textarea name="escalation_reason" placeholder="Why escalate"></textarea>
      </div>
      <div class="submit-row">
        <span class="hint">Action type: draft_reply</span>
        <button class="btn" type="submit">Submit Reply</button>
      </div>
    `;
    form.onsubmit = async (e) => {
      e.preventDefault();
      const data = Object.fromEntries(new FormData(form));
      await sendAction({
        action_type: "draft_reply",
        email_id: obs.email.id,
        subject: data.subject,
        body: data.body,
        escalate: data.escalate === "true",
        escalation_reason: data.escalation_reason || undefined,
      });
    };
    actionPanel.appendChild(form);
  }
}

function defaultRespondBody(email) {
  return `Dear ${email.sender.split("@")[0]},\n\nThank you for writing in. I understand the impact this is having and I'm here to help.\n\n(Replace this with a full plan that addresses the specific issues.)\n\nBest regards,\nSupport Team`;
}

function updateScore(reward, info) {
  if (typeof reward !== "number") return;
  scoreValue.textContent = reward.toFixed(2);
  scoreProgress.style.width = `${Math.min(Math.max(reward, 0), 1) * 100}%`;
  history.push(reward);

  const chip = document.createElement("div");
  chip.className = "step-chip";
  if (reward >= 0.7) chip.classList.add("good");
  else if (reward >= 0.3) chip.classList.add("partial");
  else chip.classList.add("miss");
  chip.textContent = `Step ${info?.step ?? history.length}: ${reward.toFixed(2)}`;
  stepHistory.prepend(chip);
}

function updateStateInfo(task, info, done) {
  stateTask.textContent = task ?? "—";
  stateStep.textContent = info?.step ?? 0;
  stateDone.textContent = done ? "Yes" : "No";
  stateReward.textContent = (info?.cumulative_reward ?? 0).toFixed(2);
}

function renderGrading(lastResult) {
  gradingBox.innerHTML = "";
  if (!lastResult || !lastResult.grading) return;
  const grade = lastResult.grading;
  const wrapper = document.createElement("div");
  wrapper.innerHTML = `<div class="panel-title" style="margin:0 0 6px 0;">Last Grading</div>`;
  const chips = document.createElement("div");
  chips.className = "grade-chips";

  const addChip = (label, kind) => {
    const c = document.createElement("span");
    c.className = `grade-chip ${kind}`;
    c.textContent = label;
    chips.appendChild(c);
  };

  if (currentTask === "classify") {
    const u = grade.urgency ?? "—";
    const c = grade.category ?? "—";
    addChip(`Urgency: ${u}`, u === "exact" ? "good" : u === "adjacent" ? "partial" : "miss");
    addChip(`Category: ${c}`, c === "exact" ? "good" : "miss");
  } else if (currentTask === "triage" && grade.per_email) {
    grade.per_email.forEach((e) => {
      const kind = e.score >= 0.7 ? "good" : e.score >= 0.3 ? "partial" : "miss";
      addChip(`${e.email_id}: ${e.score.toFixed(2)}`, kind);
    });
  } else if (currentTask === "respond") {
    if (grade.escalation) addChip(`Escalation: ${grade.escalation}`, grade.escalation === "correct" ? "good" : "miss");
    if (typeof grade.coverage_score === "number") addChip(`Coverage ${(grade.coverage_score*100).toFixed(0)}%`, grade.coverage_score >= 0.3 ? "good" : "partial");
    if (typeof grade.length_score === "number") addChip(`Length ${(grade.length_score*100).toFixed(0)}%`, grade.length_score >= 0.1 ? "good" : "partial");
    if (typeof grade.empathy_score === "number") addChip(`Empathy ${(grade.empathy_score*100).toFixed(0)}%`, grade.empathy_score > 0 ? "good" : "miss");
  }

  wrapper.appendChild(chips);
  gradingBox.appendChild(wrapper);
}

// --- API actions -----------------------------------------------------------
async function resetTask(task) {
  banner.classList.add("hidden");
  history = [];
  stepHistory.innerHTML = "";
  scoreValue.textContent = "—";
  scoreProgress.style.width = "0%";
  gradingBox.innerHTML = "";
  currentTask = task;
  taskButtons.forEach((b) => b.classList.toggle("active", b.dataset.task === task));
  try {
    const res = await fetch("/reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task }),
    });
    if (!res.ok) throw new Error("Reset failed");
    const data = await res.json();
    currentObservation = data.observation;
    renderObservation(currentObservation);
    renderActionPanel(currentObservation);
    updateStateInfo(task, { step: 0, cumulative_reward: 0 }, false);
  } catch (e) {
    actionPanel.textContent = `Reset failed: ${e.message}`;
  }
}

async function sendAction(action) {
  try {
    const res = await fetch("/step", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action }),
    });
    if (!res.ok) throw new Error("Step failed");
    const data = await res.json();
    currentObservation = data.observation;
    renderObservation(currentObservation);
    renderActionPanel(currentObservation);
    updateScore(data.reward, data.info);
    renderGrading(data.info);
    const done = data.done === true;
    updateStateInfo(currentTask, data.info, done);
    if (done) {
      banner.classList.remove("hidden");
      finalScore.textContent = data.reward.toFixed(2);
    }
  } catch (e) {
    gradingBox.innerHTML = `<div class="grading-result">Error: ${e.message}</div>`;
  }
}

// --- Wiring ---------------------------------------------------------------
taskButtons.forEach((btn) => {
  btn.addEventListener("click", () => resetTask(btn.dataset.task));
});

checkHealth();
setInterval(checkHealth, 8000);
