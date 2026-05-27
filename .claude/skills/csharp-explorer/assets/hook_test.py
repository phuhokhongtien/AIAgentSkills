"""
Virtual test for csharp-explorer hook.py (v0.1.3)

Tests:
  1. Non-.cs file read triggers notification (bug fix)
  2. First read always notifies
  3. Reads 2-14 are silent
  4. Read 15 re-notifies (NOTIFY_INTERVAL)
  5. Read 30 re-notifies again
  6. Project with no store -> always silent
  7. Grep on non-.cs file triggers notification

Run: python hook_test.py
"""
import os, json, sys, tempfile, shutil, subprocess, textwrap
from pathlib import Path

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
HEAD = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

# ── Extract hook source from hook-setup.md ────────────────────────────────────
def extract_hook_source():
    md = Path(__file__).parent.parent / "references" / "hook-setup.md"
    src = md.read_text(encoding="utf-8")
    # Extract content between first ```python and first closing ```
    start = src.index("```python\n") + len("```python\n")
    end = src.index("\n```", start)
    return src[start:end]

# ── Test harness ──────────────────────────────────────────────────────────────
class HookTestEnv:
    def __init__(self, project_name="myshop", num_runs=3):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.project_name = project_name
        self.project_slug = project_name.lower().replace(" ", "-").replace(".", "-")

        # Write hook.py
        self.hook_path = self.tmpdir / "hook.py"
        hook_src = extract_hook_source()
        # Override home dir to use tmpdir
        hook_src = hook_src.replace(
            'os.path.expanduser("~")',
            f'"{str(self.tmpdir).replace(chr(92), "/")}"'
        )
        self.hook_path.write_text(hook_src, encoding="utf-8")

        # Create mock project dir
        self.project_dir = self.tmpdir / project_name
        self.project_dir.mkdir()

        # Create store with mock runs
        store = self.tmpdir / ".claude" / "csharp-explorer" / self.project_slug
        store.mkdir(parents=True)
        for i in range(num_runs):
            names = ["OrderService", "PaymentService", "CustomerController"]
            (store / f"2026052{i+1}-090000-{names[i % 3]}.json").write_text(
                json.dumps({"target": {"name": names[i % 3]}}), encoding="utf-8"
            )

    def run_hook(self, tool_name="Read", file_path="appsettings.json",
                 glob_pattern="", grep_path=""):
        env = {
            **os.environ,
            "TOOL_NAME": tool_name,
            "TOOL_INPUT": json.dumps({
                "file_path": file_path,
                "glob": glob_pattern,
                "path": grep_path,
            }),
        }
        result = subprocess.run(
            [sys.executable, str(self.hook_path)],
            env=env,
            capture_output=True,
            text=True,
            cwd=str(self.project_dir),
        )
        return result.stdout.strip()

    def reset_lock(self):
        lock = self.tmpdir / ".claude" / "csharp-explorer" / f".notified-{self.project_slug}"
        if lock.exists():
            lock.unlink()

    def cleanup(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)


def run_tests():
    results = []

    def check(name, actual_output, expect_notify, note=""):
        notified = "[csharp-explorer]" in actual_output
        ok = notified == expect_notify
        status = PASS if ok else FAIL
        exp = "notify" if expect_notify else "silent"
        got = "notified" if notified else "silent "
        print(f"  {status} {name}")
        if not ok:
            print(f"       expected={exp}, got={got}")
            if actual_output:
                print(f"       output: {actual_output[:120]}")
        elif notified and note:
            snippet = actual_output.split("\n")[1] if "\n" in actual_output else actual_output
            print(f"       {RESET}\033[90m{snippet[:90]}{RESET}")
        results.append(ok)

    # ── Suite 1: File-type filter removal ────────────────────────────────────
    print(f"\n{BOLD}{HEAD}Suite 1 — File-type filter removed{RESET}")
    env1 = HookTestEnv("myshop", num_runs=2)

    out = env1.run_hook(tool_name="Read", file_path="appsettings.json")
    check("Read appsettings.json -> notifies (non-.cs file)", out, expect_notify=True,
          note="hook now fires for any file type")

    env1.reset_lock()
    out = env1.run_hook(tool_name="Read", file_path="Program.cs")
    check("Read Program.cs -> notifies (.cs file, baseline)", out, expect_notify=True)

    env1.reset_lock()
    out = env1.run_hook(tool_name="Read", file_path="README.md")
    check("Read README.md -> notifies (markdown file)", out, expect_notify=True)

    env1.reset_lock()
    out = env1.run_hook(tool_name="Read", file_path="docker-compose.yml")
    check("Read docker-compose.yml -> notifies (any file)", out, expect_notify=True)

    env1.reset_lock()
    out = env1.run_hook(tool_name="Grep", file_path="", glob_pattern="**/*.ts",
                        grep_path="src/")
    check("Grep *.ts -> notifies (non-.cs glob)", out, expect_notify=True)

    env1.cleanup()

    # ── Suite 2: Read-count re-notification ───────────────────────────────────
    print(f"\n{BOLD}{HEAD}Suite 2 — Read-count re-notification (NOTIFY_INTERVAL=15){RESET}")
    env2 = HookTestEnv("bigproject", num_runs=5)

    # Read 1 -> notify
    out = env2.run_hook(file_path="appsettings.json")
    check("Read #1 -> notify (first read)", out, expect_notify=True, note="initial notification")

    # Reads 2-14 -> silent
    silent_ok = True
    for i in range(2, 15):
        out = env2.run_hook(file_path=f"file{i}.cs")
        if "[csharp-explorer]" in out:
            silent_ok = False
            print(f"  {FAIL} Read #{i} should be silent but notified!")
    status = PASS if silent_ok else FAIL
    print(f"  {status} Reads #2-14 -> all silent (13 reads checked)")
    results.append(silent_ok)

    # Read 15 -> re-notify
    out = env2.run_hook(file_path="OrderService.cs")
    check("Read #15 -> re-notify (NOTIFY_INTERVAL hit)", out, expect_notify=True,
          note="periodic re-notification for long sessions")

    # Reads 16-29 -> silent
    silent_ok2 = True
    for i in range(16, 30):
        out = env2.run_hook(file_path=f"file{i}.json")
        if "[csharp-explorer]" in out:
            silent_ok2 = False
    status = PASS if silent_ok2 else FAIL
    print(f"  {status} Reads #16-29 -> all silent (14 reads checked)")
    results.append(silent_ok2)

    # Read 30 -> re-notify
    out = env2.run_hook(file_path="Startup.cs")
    check("Read #30 -> re-notify (2nd interval)", out, expect_notify=True,
          note="[read #30] label in output")

    # Verify [read #N] label present on re-notify
    has_label = "[read #30]" in out or "read #30" in out
    status = PASS if has_label else FAIL
    print(f"  {status} Re-notify includes [read #30] label")
    results.append(has_label)

    env2.cleanup()

    # ── Suite 3: No store -> always silent ────────────────────────────────────
    print(f"\n{BOLD}{HEAD}Suite 3 — No store -> always silent{RESET}")
    env3 = HookTestEnv("emptyproject", num_runs=0)
    # Remove the store dir (num_runs=0 creates dir but no .json files)
    out = env3.run_hook(file_path="Program.cs")
    check("No runs in store -> silent", out, expect_notify=False)
    out = env3.run_hook(file_path="appsettings.json")
    check("No runs in store, non-.cs -> silent", out, expect_notify=False)
    env3.cleanup()

    # ── Suite 4: Unknown project (no store dir) ───────────────────────────────
    print(f"\n{BOLD}{HEAD}Suite 4 — Unknown project (store dir missing){RESET}")
    env4 = HookTestEnv("unknownproject", num_runs=2)
    # Run hook from a different cwd (not the project with the store)
    other_dir = env4.tmpdir / "otherproject"
    other_dir.mkdir()
    result = subprocess.run(
        [sys.executable, str(env4.hook_path)],
        env={**os.environ, "TOOL_NAME": "Read",
             "TOOL_INPUT": json.dumps({"file_path": "Program.cs"})},
        capture_output=True, text=True,
        cwd=str(other_dir),
    )
    out = result.stdout.strip()
    check("Different project cwd -> silent (no store match)", out, expect_notify=False)
    env4.cleanup()

    # ── Summary ───────────────────────────────────────────────────────────────
    total = len(results)
    passed = sum(results)
    print(f"\n{BOLD}Results: {passed}/{total} passed{RESET}")
    if passed == total:
        print(f"{PASS} -- All tests passed -- hook v0.1.3 behaves correctly")
    else:
        print(f"{FAIL} -- {total - passed} test(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    print(f"{BOLD}csharp-explorer hook.py — Virtual Test Suite (v0.1.3){RESET}")
    print("=" * 55)
    run_tests()
