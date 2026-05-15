# Preview panel orchestration

The dashboard must render **inside Claude Code's Preview panel** via the
`Claude_Preview` MCP — not an OS browser. This is what makes tests visible
in Claude Code.

## 1. Served report directory

Write the dashboard to a stable path so the launch config URL never changes:

```
.claude/skills/testing-explorer/.report/index.html          # always = latest
.claude/skills/testing-explorer/.report/test-report-<ts>.html # archive copy
```

Create `.report/` if missing. It is gitignored.

## 2. .claude/launch.json config

`preview_start` reads `.claude/launch.json`. **Merge** — never overwrite an
existing file or other configurations. Ensure one entry exists:

```json
{
  "version": "0.0.1",
  "configurations": [
    {
      "name": "testing-explorer-report",
      "runtimeExecutable": "python",
      "runtimeArgs": ["-m", "http.server", "7654",
                       "--directory", ".claude/skills/testing-explorer/.report"],
      "port": 7654
    }
  ]
}
```

If the file exists: parse JSON, and if no config named
`testing-explorer-report`, append one to `configurations[]` and write back
(preserve the rest verbatim).

Port 7654 is the default; if it is already taken by a *different* process,
pick the next free port and update both `runtimeArgs` and `port` to match.

### Static-server fallback

`python` may be absent on Windows (or aliased to the App Execution Alias
stub). Probe `python --version` / `python3 --version`. Order of preference:

1. `python -m http.server <port> --directory <dir>`
2. `python3 -m http.server <port> --directory <dir>`
3. `npx --yes serve -l <port> <dir>` (needs Node + one-time network for the
   `serve` package)

Set `runtimeExecutable`/`runtimeArgs` to the first that works.

## 3. Start / refresh

- First render this session: `preview_start("testing-explorer-report")`.
  It returns/`preview_list` gives a `serverId`. The panel loads
  `http://localhost:<port>/` → `index.html`.
- Re-run or regenerate: the file on disk changed; do **not** start again
  (server is reused). Call
  `preview_eval(serverId, "location.reload()")` so the panel live-updates.
- Server already running (later invocation): `preview_list` → reuse the
  `serverId`; reload as above.

## 4. Self-verify

After start/reload, `preview_screenshot(serverId)` and check the dashboard
header/summary is visible. If blank or connection-refused:

1. `preview_list` — is the server actually running?
2. Confirm `.report/index.html` exists and is non-empty.
3. Re-check the port isn't blocked; try the fallback server.
4. As a last resort, tell the user the panel could not start and print the
   archive file path so they can open it manually — but the panel is the
   intended delivery; treat a manual-open fallback as a degraded result, not
   success.

## 5. Lifecycle

Leave the server running across re-runs so the panel stays live. Only call
`preview_stop(serverId)` when the user asks to stop it or ends the session.
Never kill it just to "clean up" mid-task — that closes the user's panel.
