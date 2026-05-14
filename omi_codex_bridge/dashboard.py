from __future__ import annotations


def render_dashboard(token: str, default_workspace: str, using_default_token: bool) -> str:
    warning = (
        "<div class=\"warning\">Default bridge token is active. Set OMI_CODEX_BRIDGE_TOKEN before using Funnel.</div>"
        if using_default_token
        else ""
    )
    return f"""
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>Omi Codex Bridge</title>
      <style>
        :root {{
          --bg: #f5f6f2;
          --ink: #141914;
          --muted: #667066;
          --surface: #ffffff;
          --line: #dce2d7;
          --accent: #236f52;
          --accent-soft: #e4f2eb;
          --danger: #8b1e1e;
          --dark: #111812;
        }}
        * {{ box-sizing: border-box; }}
        body {{
          margin: 0;
          background: var(--bg);
          color: var(--ink);
          font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          line-height: 1.45;
        }}
        button, input, textarea {{ font: inherit; }}
        .shell {{ display: grid; grid-template-columns: 280px minmax(0, 1fr); min-height: 100vh; }}
        aside {{ background: var(--dark); color: white; padding: 24px 20px; }}
        .brand {{ display: flex; align-items: center; gap: 12px; font-size: 18px; font-weight: 790; }}
        .mark {{ width: 34px; height: 34px; display: grid; place-items: center; border-radius: 8px; background: #d8f35d; color: #111812; font-weight: 850; }}
        .sidecopy {{ margin-top: 28px; color: #c9d4c5; font-size: 14px; }}
        .sidecopy code {{ color: white; }}
        main {{ padding: 28px; min-width: 0; }}
        .top {{ display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; margin-bottom: 18px; }}
        h1 {{ margin: 0; font-size: 31px; line-height: 1.08; }}
        .subtitle {{ margin: 8px 0 0; color: var(--muted); font-size: 14px; }}
        .warning {{ padding: 10px 12px; border: 1px solid #e8c5a4; background: #fff5eb; color: #7a3b00; border-radius: 8px; font-weight: 680; }}
        .grid {{ display: grid; grid-template-columns: repeat(12, minmax(0, 1fr)); gap: 16px; }}
        .panel {{ background: var(--surface); border: 1px solid var(--line); border-radius: 8px; box-shadow: 0 18px 42px rgba(20, 25, 20, 0.07); }}
        .panel.create {{ grid-column: span 5; }}
        .panel.jobs {{ grid-column: span 7; }}
        .panel.output, .panel.events {{ grid-column: span 12; }}
        .head {{ padding: 15px 16px; border-bottom: 1px solid var(--line); font-weight: 780; display: flex; justify-content: space-between; align-items: center; gap: 10px; }}
        .body {{ padding: 14px; }}
        label {{ display: block; margin: 0 0 6px; color: var(--muted); font-size: 12px; font-weight: 780; text-transform: uppercase; }}
        textarea, input {{ width: 100%; border: 1px solid var(--line); border-radius: 8px; padding: 10px 11px; outline: none; background: white; }}
        textarea {{ min-height: 150px; resize: vertical; }}
        textarea:focus, input:focus {{ border-color: var(--accent); box-shadow: 0 0 0 3px rgba(35, 111, 82, 0.14); }}
        .stack {{ display: grid; gap: 12px; }}
        .actions {{ display: flex; gap: 9px; flex-wrap: wrap; }}
        button {{ border: 0; background: var(--dark); color: white; border-radius: 8px; padding: 9px 12px; cursor: pointer; font-weight: 720; font-size: 14px; }}
        button.secondary {{ background: white; color: var(--ink); border: 1px solid var(--line); }}
        button.danger {{ background: var(--danger); }}
        .job {{ display: grid; gap: 8px; padding: 12px; border-radius: 8px; border: 1px solid var(--line); background: #fbfcfa; margin-bottom: 10px; }}
        .job-title {{ display: flex; align-items: center; justify-content: space-between; gap: 10px; font-weight: 760; }}
        .status {{ padding: 4px 7px; border-radius: 6px; background: var(--accent-soft); color: var(--accent); font-size: 12px; font-weight: 790; }}
        .status.failed {{ background: #fae8e8; color: var(--danger); }}
        .status.running {{ background: #e8eefb; color: #244e91; }}
        .status.cancelled {{ background: #eee; color: #555; }}
        .status.succeeded {{ background: #e8f5dc; color: #3b6a1b; }}
        .meta {{ color: var(--muted); font-size: 12px; }}
        .prompt {{ color: #2e372f; font-size: 13px; }}
        pre {{ margin: 0; padding: 12px; border-radius: 8px; background: #101610; color: #eef6eb; overflow: auto; max-height: 260px; }}
        @media (max-width: 980px) {{
          .shell {{ grid-template-columns: 1fr; }}
          .panel.create, .panel.jobs {{ grid-column: span 12; }}
        }}
        @media (max-width: 600px) {{
          main {{ padding: 18px; }}
          .top {{ flex-direction: column; }}
          h1 {{ font-size: 25px; }}
        }}
      </style>
    </head>
    <body>
      <div class="shell">
        <aside>
          <div class="brand"><div class="mark">C</div><span>Omi Codex Bridge</span></div>
          <div class="sidecopy">
            <p>Voice or chat commands become queued Codex CLI jobs on this machine.</p>
            <p>Omi webhook URL:<br><code>/omi/{token}/webhooks/realtime</code></p>
            <p>Tool manifest:<br><code>/omi/{token}/.well-known/omi-tools.json</code></p>
          </div>
        </aside>
        <main>
          <div class="top">
            <div>
              <h1>Voice-controlled coding queue</h1>
              <p class="subtitle">Tailscale Funnel brings Omi to this local Codex bridge; you decide when a queued job runs.</p>
            </div>
            {warning}
          </div>
          <section class="grid">
            <section class="panel create">
              <div class="head">Create a Codex job</div>
              <div class="body stack">
                <div>
                  <label for="uid">Omi uid</label>
                  <input id="uid" value="practice-user" />
                </div>
                <div>
                  <label for="workspace">Workspace</label>
                  <input id="workspace" value="{default_workspace}" />
                </div>
                <div>
                  <label for="prompt">Prompt</label>
                  <textarea id="prompt">Build a small, well-tested improvement in this workspace and summarize the result.</textarea>
                </div>
                <div class="actions">
                  <button id="queue">Queue job</button>
                  <button id="refresh" class="secondary">Refresh</button>
                </div>
              </div>
            </section>
            <section class="panel jobs">
              <div class="head">Jobs <button id="reload" class="secondary">Reload</button></div>
              <div class="body" id="jobs"></div>
            </section>
            <section class="panel output">
              <div class="head">Selected output</div>
              <div class="body"><pre id="output">Select a job output to inspect it.</pre></div>
            </section>
            <section class="panel events">
              <div class="head">Event stream</div>
              <div class="body"><pre id="events"></pre></div>
            </section>
          </section>
        </main>
      </div>
      <script>
        const token = {token!r};
        const apiBase = `/omi/${{token}}`;
        const els = {{
          uid: document.querySelector("#uid"),
          workspace: document.querySelector("#workspace"),
          prompt: document.querySelector("#prompt"),
          jobs: document.querySelector("#jobs"),
          events: document.querySelector("#events"),
          output: document.querySelector("#output"),
          queue: document.querySelector("#queue"),
          refresh: document.querySelector("#refresh"),
          reload: document.querySelector("#reload"),
        }};
        const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, ch => ({{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}}[ch]));
        async function load() {{
          const [jobsRes, eventsRes] = await Promise.all([
            fetch(`${{apiBase}}/api/jobs`),
            fetch(`${{apiBase}}/api/events`),
          ]);
          const jobs = await jobsRes.json();
          const events = await eventsRes.json();
          els.jobs.innerHTML = jobs.jobs.length ? jobs.jobs.map(renderJob).join("") : "<div class='meta'>No jobs queued yet.</div>";
          els.events.textContent = events.events.map(e => `${{e.created_at}} ${{e.kind}} ${{e.job_id || ""}} ${{e.message}}`).join("\\n");
        }}
        function renderJob(job) {{
          const statusClass = ["failed", "running", "cancelled", "succeeded"].includes(job.status) ? job.status : "";
          const runButton = ["pending", "failed"].includes(job.status) ? `<button data-run="${{job.id}}">Run</button>` : "";
          const cancelButton = job.status === "pending" ? `<button class="danger" data-cancel="${{job.id}}">Cancel</button>` : "";
          const retryButton = ["failed", "cancelled", "succeeded"].includes(job.status) ? `<button class="secondary" data-retry="${{job.id}}">Retry</button>` : "";
          const outputButton = (job.output_path || job.last_message_path) ? `<button class="secondary" data-output="${{job.id}}">Output</button>` : "";
          const output = job.output_path ? `<div class="meta">Output: ${{escapeHtml(job.output_path)}}</div>` : "";
          return `<article class="job">
            <div class="job-title"><span>${{escapeHtml(job.id)}} from ${{escapeHtml(job.source)}}</span><span class="status ${{statusClass}}">${{escapeHtml(job.status)}}</span></div>
            <div class="meta">${{escapeHtml(job.workspace)}} &middot; ${{escapeHtml(job.created_at)}}</div>
            <div class="prompt">${{escapeHtml(job.prompt)}}</div>
            ${{output}}
            <div class="actions">${{runButton}}${{cancelButton}}${{retryButton}}${{outputButton}}</div>
          </article>`;
        }}
        els.queue.addEventListener("click", async () => {{
          await fetch(`${{apiBase}}/api/jobs`, {{
            method: "POST",
            headers: {{"Content-Type": "application/json"}},
            body: JSON.stringify({{uid: els.uid.value, prompt: els.prompt.value, workspace: els.workspace.value, source: "dashboard"}}),
          }});
          await load();
        }});
        els.jobs.addEventListener("click", async (event) => {{
          const run = event.target.closest("button[data-run]");
          const cancel = event.target.closest("button[data-cancel]");
          const retry = event.target.closest("button[data-retry]");
          const output = event.target.closest("button[data-output]");
          if (run) {{
            await fetch(`${{apiBase}}/api/jobs/${{run.dataset.run}}/run`, {{method: "POST"}});
          }} else if (cancel) {{
            await fetch(`${{apiBase}}/api/jobs/${{cancel.dataset.cancel}}/cancel`, {{method: "POST"}});
          }} else if (retry) {{
            await fetch(`${{apiBase}}/api/jobs/${{retry.dataset.retry}}/retry`, {{method: "POST"}});
          }} else if (output) {{
            const response = await fetch(`${{apiBase}}/api/jobs/${{output.dataset.output}}/output`);
            const data = await response.json();
            els.output.textContent = data.output || "No output yet.";
          }} else {{
            return;
          }}
          await load();
          window.setTimeout(load, 1200);
        }});
        els.refresh.addEventListener("click", load);
        els.reload.addEventListener("click", load);
        load();
      </script>
    </body>
    </html>
    """
