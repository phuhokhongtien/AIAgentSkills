"""
Virtual test for csharp-explorer hook.py (v0.1.6)

Two-mode behavior under test:
  Mode A — Auto-analyze: Read <unanalyzed>.cs  → print MANDATORY INTERRUPT to Claude
  Mode B — Read-count:   Everything else        → notify at read #1, every 15 reads

v0.1.6: Mode A output uses MANDATORY INTERRUPT language with explicit Skill tool syntax.

Suites:
  1. Mode B fires for all non-.cs file types
  2. Mode B read-count re-notification (NOTIFY_INTERVAL=15) — Mode B files only
  3. Empty store (no runs) -> Mode A still fires; Mode B silent
  4. Unknown project (no store dir) -> always silent
  5. Mixed session — Mode A and Mode B are independent (don't interfere)
  6. Multi-turn back-and-fork — Mode B counter persists across conversation turns
  7. Grep + Read interleaved — Grep counts toward Mode B interval
  8. Auto-analyze (Mode A) — unanalyzed .cs, skip list, already-analyzed fallthrough

Run: python hook_test.py
"""
import os, json, sys, tempfile, shutil, subprocess
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
    start = src.index("```python\n") + len("```python\n")
    end = src.index("\n```", start)
    return src[start:end]


# ── Test harness ──────────────────────────────────────────────────────────────
class HookTestEnv:
    def __init__(self, project_name="myshop", num_runs=3):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.project_name = project_name
        self.project_slug = project_name.lower().replace(" ", "-").replace(".", "-")

        # Write hook.py with home dir overridden to tmpdir
        self.hook_path = self.tmpdir / "hook.py"
        hook_src = extract_hook_source()
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
        names = ["OrderService", "PaymentService", "CustomerController"]
        for i in range(num_runs):
            fname = f"2026052{i+1}-090000-{names[i % 3]}.json"
            (store / fname).write_text(
                json.dumps({"target": {"name": names[i % 3]}}), encoding="utf-8"
            )

    def run_hook(self, tool_name="Read", file_path="appsettings.json",
                 glob_pattern="", grep_path=""):
        # v0.1.5: hook reads from stdin JSON (Claude Code passes data this way)
        hook_data = json.dumps({
            "tool_name": tool_name,
            "tool_input": {
                "file_path": file_path,
                "glob": glob_pattern,
                "path": grep_path,
            },
            "cwd": str(self.project_dir),
            "hook_event_name": "PostToolUse",
        })
        result = subprocess.run(
            [sys.executable, str(self.hook_path)],
            input=hook_data, capture_output=True, text=True, encoding="utf-8",
            cwd=str(self.project_dir),
        )
        return (result.stdout or "").strip()

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

    # ── Suite 1: Mode B fires for all non-.cs file types ─────────────────────
    # Non-.cs files always go to Mode B (read-count). Program.cs is in skip list
    # so it exits silently in v0.1.4. Already-analyzed .cs falls through to Mode B.
    print(f"\n{BOLD}{HEAD}Suite 1 — Mode B fires for all non-.cs file types{RESET}")
    env1 = HookTestEnv("myshop", num_runs=2)

    out = env1.run_hook(tool_name="Read", file_path="appsettings.json")
    check("Read appsettings.json -> Mode B notify", out, expect_notify=True,
          note="non-.cs file goes straight to Mode B")

    env1.reset_lock()
    out = env1.run_hook(tool_name="Read", file_path="README.md")
    check("Read README.md -> Mode B notify", out, expect_notify=True)

    env1.reset_lock()
    out = env1.run_hook(tool_name="Read", file_path="docker-compose.yml")
    check("Read docker-compose.yml -> Mode B notify", out, expect_notify=True)

    env1.reset_lock()
    # Already-analyzed .cs: OrderService is in the store → falls through to Mode B
    out = env1.run_hook(tool_name="Read", file_path="src/Services/OrderService.cs")
    check("Read OrderService.cs (analyzed) -> Mode B notify", out, expect_notify=True,
          note="already-analyzed .cs falls through to Mode B")

    env1.reset_lock()
    out = env1.run_hook(tool_name="Grep", file_path="", glob_pattern="**/*.ts",
                        grep_path="src/")
    check("Grep *.ts -> Mode B notify", out, expect_notify=True)

    # Program.cs is in skip list → silent in v0.1.4
    env1.reset_lock()
    out = env1.run_hook(tool_name="Read", file_path="Program.cs")
    check("Read Program.cs -> silent (skip list in v0.1.4)", out, expect_notify=False)

    env1.cleanup()

    # ── Suite 2: Mode B read-count re-notification ────────────────────────────
    # Uses only Mode B files (non-.cs + already-analyzed .cs) to test read-count.
    # Unanalyzed .cs are NOT used here — they trigger Mode A and bypass the counter.
    print(f"\n{BOLD}{HEAD}Suite 2 — Mode B read-count re-notification (NOTIFY_INTERVAL=15){RESET}")
    env2 = HookTestEnv("bigproject", num_runs=5)
    # Store has: OrderService (x2), PaymentService (x2), CustomerController (x1)
    # Mode B files: any non-.cs file, or OrderService/PaymentService/CustomerController .cs

    # Alternate non-.cs and analyzed .cs to exercise both paths
    mode_b_files = [
        "appsettings.json",                # non-.cs
        "OrderService.cs",                  # analyzed -> Mode B
        "PaymentService.cs",                # analyzed -> Mode B
        "README.md",                        # non-.cs
        "CustomerController.cs",            # analyzed -> Mode B
        "docker-compose.yml",               # non-.cs
        "OrderService.cs",                  # analyzed (duplicate ok — count still ticks)
        "global.json",                      # non-.cs
        "PaymentService.cs",                # analyzed
        "appsettings.Development.json",     # non-.cs
        "CustomerController.cs",            # analyzed
        "Dockerfile",                       # non-.cs
        "OrderService.cs",                  # analyzed
        "PaymentService.cs",                # analyzed
        "CustomerController.cs",            # analyzed  ← read #15
    ]

    # Read 1 -> notify
    out = env2.run_hook(file_path=mode_b_files[0])
    check("Read #1 (appsettings.json) -> notify", out, expect_notify=True,
          note="first Mode B read")

    # Reads 2-14 -> silent
    silent_ok = True
    for i, fname in enumerate(mode_b_files[1:14], start=2):
        out = env2.run_hook(file_path=fname)
        if "[csharp-explorer]" in out:
            silent_ok = False
            print(f"  {FAIL} Read #{i} ({fname}) should be silent but notified!")
    status = PASS if silent_ok else FAIL
    print(f"  {status} Reads #2-14 -> all silent (13 reads, mix of .cs + non-.cs)")
    results.append(silent_ok)

    # Read 15 -> re-notify
    out = env2.run_hook(file_path=mode_b_files[14])
    check("Read #15 (CustomerController.cs analyzed) -> re-notify", out, expect_notify=True,
          note="NOTIFY_INTERVAL hit")

    # Reads 16-29 -> silent (using another round of Mode B files)
    mode_b_r2 = [
        "appsettings.json", "OrderService.cs", "README.md", "PaymentService.cs",
        "Dockerfile", "CustomerController.cs", "global.json", "OrderService.cs",
        "docker-compose.yml", "PaymentService.cs", "README.md", "CustomerController.cs",
        "appsettings.Development.json", "OrderService.cs",
    ]
    silent_ok2 = True
    for i, fname in enumerate(mode_b_r2, start=16):
        out = env2.run_hook(file_path=fname)
        if "[csharp-explorer]" in out:
            silent_ok2 = False
    status = PASS if silent_ok2 else FAIL
    print(f"  {status} Reads #16-29 -> all silent (14 reads checked)")
    results.append(silent_ok2)

    # Read 30 -> re-notify with label
    out = env2.run_hook(file_path="CustomerController.cs")
    check("Read #30 -> re-notify (2nd interval)", out, expect_notify=True,
          note="[read #30] label in output")

    has_label = "[read #30]" in out or "read #30" in out
    status = PASS if has_label else FAIL
    print(f"  {status} Re-notify includes [read #30] label")
    results.append(has_label)

    env2.cleanup()

    # ── Suite 3: Empty store (no runs) ────────────────────────────────────────
    # Mode A still fires for non-skip .cs (bootstrap). Mode B silent (no runs).
    # Program.cs is in skip list → silent. non-.cs → Mode B → silent (no runs).
    print(f"\n{BOLD}{HEAD}Suite 3 — Empty store (no runs): Mode A bootstraps, Mode B silent{RESET}")
    env3 = HookTestEnv("emptyproject", num_runs=0)
    out = env3.run_hook(file_path="Program.cs")
    check("No runs, Program.cs (skip list) -> silent", out, expect_notify=False)
    out = env3.run_hook(file_path="appsettings.json")
    check("No runs, non-.cs file -> Mode B silent (needs prior runs)", out, expect_notify=False)
    env3.cleanup()

    # ── Suite 4: Unknown project (no store dir) ───────────────────────────────
    print(f"\n{BOLD}{HEAD}Suite 4 — Unknown project (store dir missing){RESET}")
    env4 = HookTestEnv("unknownproject", num_runs=2)
    other_dir = env4.tmpdir / "otherproject"
    other_dir.mkdir()
    # Uses a .cs file NOT in skip list — but store dir for "otherproject" doesn't
    # exist, so hook exits silently (no store dir = init not run for this project)
    hook_data = json.dumps({
        "tool_name": "Read",
        "tool_input": {"file_path": "SomeService.cs"},
        "cwd": str(other_dir),
        "hook_event_name": "PostToolUse",
    })
    result = subprocess.run(
        [sys.executable, str(env4.hook_path)],
        input=hook_data, capture_output=True, text=True, encoding="utf-8",
        cwd=str(other_dir),
    )
    out = (result.stdout or "").strip()
    check("Different project cwd -> silent (no store dir for otherproject)", out, expect_notify=False)
    env4.cleanup()

    # ── Suite 5: Mixed session — Mode A and Mode B independence ──────────────
    # Verifies that Mode A (INSTRUCTION for new classes) and Mode B (read-count)
    # are completely independent. Mode A reads do NOT increment the Mode B counter.
    print(f"\n{BOLD}{HEAD}Suite 5 — Mixed session: Mode A + Mode B independence{RESET}")
    env5 = HookTestEnv("ecommerce", num_runs=4)
    # Store: OrderService (x2), PaymentService, CustomerController

    # Session mixing Mode A and Mode B reads:
    #   Mode B: non-.cs files + analyzed .cs → count ticks
    #   Mode A: unanalyzed .cs → MANDATORY INTERRUPT printed, count does NOT tick
    session = [
        # (tool, file, expect_mode_a_instruction, label)
        ("Read", "appsettings.json",                   False, "non-.cs → Mode B #1 notify"),
        ("Read", "OrderService.cs",                    False, "analyzed → Mode B #2 silent"),
        ("Read", "src/Models/NewClass.cs",             True,  "unanalyzed → Mode A MANDATORY INTERRUPT"),
        ("Read", "README.md",                          False, "non-.cs → Mode B #3 silent"),
        ("Read", "src/Services/UnknownService.cs",     True,  "unanalyzed → Mode A MANDATORY INTERRUPT"),
        ("Read", "PaymentService.cs",                  False, "analyzed → Mode B #4 silent"),
        ("Read", "docker-compose.yml",                 False, "non-.cs → Mode B #5 silent"),
        ("Read", "src/Dtos/FreshDto.cs",               True,  "unanalyzed → Mode A MANDATORY INTERRUPT"),
        ("Read", "CustomerController.cs",              False, "analyzed → Mode B #6 silent"),
        ("Read", "ECommerceApi.csproj",                False, "non-.cs → Mode B #7 silent"),
    ]

    mode_a_count = 0
    mode_b_notifies = 0
    mode_b_unexpected = False

    for tool, fpath, expect_instruction, label in session:
        out = env5.run_hook(tool_name=tool, file_path=fpath)
        has_instruction = "MANDATORY INTERRUPT" in out
        has_notify = "[csharp-explorer]" in out and not has_instruction

        if expect_instruction:
            mode_a_count += 1 if has_instruction else 0
            if not has_instruction:
                print(f"  {FAIL} Expected MANDATORY INTERRUPT for {fpath} but got: {out[:80]}")
        else:
            if has_instruction:
                mode_b_unexpected = True
                print(f"  {FAIL} Unexpected MANDATORY INTERRUPT for {fpath}: {out[:80]}")
            if has_notify:
                mode_b_notifies += 1

    expected_mode_a = sum(1 for _, _, e, _ in session if e)
    check(
        f"Mode A fires for all {expected_mode_a} unanalyzed .cs files",
        "[csharp-explorer]" if mode_a_count == expected_mode_a else "",
        expect_notify=True,
    )
    check(
        "Mode B fired exactly once (read #1 of session, non-.cs file)",
        "[csharp-explorer]" if mode_b_notifies == 1 else "",
        expect_notify=True,
    )
    check(
        "Mode A reads do NOT cause spurious Mode B notifications",
        "[csharp-explorer]" if not mode_b_unexpected else "",
        expect_notify=True,
    )

    env5.cleanup()

    # ── Suite 6: Multi-turn back-and-fork conversation ────────────────────────
    # Verifies Mode B counter persists across conversation turns.
    # Uses ONLY Mode B files (analyzed .cs + non-.cs) to keep counter test clean.
    print(f"\n{BOLD}{HEAD}Suite 6 — Multi-turn back-and-fork conversation (Mode B counter){RESET}")
    env6 = HookTestEnv("bookingapp", num_runs=3)
    # Store: OrderService, PaymentService, CustomerController

    turns = [
        # Turn 1: user asks "explain the booking flow"
        [("Read", "README.md"),
         ("Read", "OrderService.cs"),          # analyzed
         ("Read", "PaymentService.cs")],        # analyzed
        # Turn 2: user forks — "why does payment fail sometimes?"
        [("Read", "appsettings.json"),
         ("Read", "CustomerController.cs"),    # analyzed
         ("Read", "docker-compose.yml"),
         ("Read", "OrderService.cs")],         # analyzed
        # Turn 3: back to booking — "show me the controller"
        [("Read", "PaymentService.cs"),        # analyzed
         ("Read", "README.md"),
         ("Read", "CustomerController.cs")],   # analyzed
        # Turn 4: user asks about infra — forks again
        [("Read", "Dockerfile"),
         ("Read", "OrderService.cs"),          # analyzed
         ("Read", "global.json")],
        # Turn 5: back to main thread — final reads (#14 and #15)
        [("Read", "PaymentService.cs"),        # analyzed — read #14
         ("Read", "CustomerController.cs")],   # analyzed — read #15 → re-notify
    ]

    flat = [(t, f) for turn in turns for t, f in turn]  # exactly 15 reads
    notify_positions = []
    for idx, (tool, fpath) in enumerate(flat, start=1):
        out = env6.run_hook(tool_name=tool, file_path=fpath)
        if "[csharp-explorer]" in out:
            notify_positions.append(idx)

    check(
        "Multi-turn: notified at read #1 (README.md, turn 1)",
        "[csharp-explorer]" if 1 in notify_positions else "",
        expect_notify=True,
    )
    check(
        "Multi-turn: notified at read #15 (last file of turn 5, crosses boundary)",
        "[csharp-explorer]" if 15 in notify_positions else "",
        expect_notify=True,
    )
    check(
        "Multi-turn: silent between reads #2-14 (across all forks and turns)",
        "[csharp-explorer]" if not any(2 <= p <= 14 for p in notify_positions) else "spurious",
        expect_notify=True,
    )
    if notify_positions != [1, 15]:
        print(f"       actual notify positions: {notify_positions}")

    env6.cleanup()

    # ── Suite 7: Grep + Read interleaved ─────────────────────────────────────
    # Verifies Grep calls count toward Mode B interval alongside Read calls.
    # Uses analyzed .cs + non-.cs + Grep (all Mode B) to keep counter clean.
    print(f"\n{BOLD}{HEAD}Suite 7 — Grep + Read interleaved (all Mode B){RESET}")
    env7 = HookTestEnv("microservice", num_runs=2)
    # Store: OrderService, PaymentService

    interleaved = [
        ("Read",  "appsettings.json",        "",             ""),    # #1 notify
        ("Read",  "OrderService.cs",         "",             ""),    # #2 analyzed→Mode B
        ("Grep",  "",                        "**/*.cs",      "src/"),# #3
        ("Read",  "PaymentService.cs",       "",             ""),    # #4 analyzed→Mode B
        ("Grep",  "",                        "**/*.json",    "cfg/"),# #5
        ("Read",  "README.md",               "",             ""),    # #6
        ("Grep",  "",                        "**/*.csproj",  "."),   # #7
        ("Read",  "docker-compose.yml",      "",             ""),    # #8
        ("Grep",  "",                        "**/*.yml",     "."),   # #9
        ("Read",  "OrderService.cs",         "",             ""),    # #10 analyzed
        ("Read",  "Dockerfile",              "",             ""),    # #11
        ("Grep",  "",                        "**/*.md",      "docs/"),# #12
        ("Read",  "global.json",             "",             ""),    # #13
        ("Grep",  "",                        "**/*.xml",     "pkg/"),# #14
        ("Read",  "PaymentService.cs",       "",             ""),    # #15 re-notify
    ]

    notify_pos7 = []
    tool_log    = []
    for idx, (tool, fpath, glob, gpath) in enumerate(interleaved, start=1):
        out = env7.run_hook(tool_name=tool, file_path=fpath,
                            glob_pattern=glob, grep_path=gpath)
        tool_log.append((idx, tool))
        if "[csharp-explorer]" in out:
            notify_pos7.append(idx)

    grep_count = sum(1 for _, t in tool_log if t == "Grep")
    read_count = sum(1 for _, t in tool_log if t == "Read")

    check(
        "Grep+Read mix: notified at read #1",
        "[csharp-explorer]" if 1 in notify_pos7 else "",
        expect_notify=True,
    )
    check(
        "Grep+Read mix: silent between #2 and #14 (mixed tools)",
        "[csharp-explorer]" if not any(2 <= p <= 14 for p in notify_pos7) else "spurious",
        expect_notify=True,
    )
    check(
        "Grep+Read mix: re-notified at #15 (Grep calls counted too)",
        "[csharp-explorer]" if 15 in notify_pos7 else "",
        expect_notify=True,
    )
    status = PASS if grep_count >= 5 else FAIL
    print(f"  {status} Exercised {grep_count} Greps + {read_count} Reads in sequence")
    results.append(grep_count >= 5)
    if notify_pos7 != [1, 15]:
        print(f"       actual notify positions: {notify_pos7}")

    env7.cleanup()

    # ── Suite 8: Auto-analyze Mode A ─────────────────────────────────────────
    # Tests Mode A behavior: unanalyzed .cs → MANDATORY INTERRUPT.
    print(f"\n{BOLD}{HEAD}Suite 8 — Auto-analyze instruction (v0.1.6 Mode A){RESET}")
    env8 = HookTestEnv("salonapp", num_runs=3)
    # Store: OrderService, PaymentService, CustomerController

    # 8a: Unanalyzed .cs → MANDATORY INTERRUPT printed with class name
    out = env8.run_hook(tool_name="Read", file_path="src/Services/SalonDbContext.cs")
    has_inst = "MANDATORY INTERRUPT" in out and "SalonDbContext" in out
    check("Read unanalyzed SalonDbContext.cs -> MANDATORY INTERRUPT",
          "[csharp-explorer]" if has_inst else "", expect_notify=True)

    # 8b: Another unanalyzed class in a subdirectory
    out = env8.run_hook(tool_name="Read", file_path="src/Repositories/BookingRepository.cs")
    has_inst2 = "MANDATORY INTERRUPT" in out and "BookingRepository" in out
    check("Read unanalyzed BookingRepository.cs -> MANDATORY INTERRUPT",
          "[csharp-explorer]" if has_inst2 else "", expect_notify=True)

    # 8c: Already-analyzed class → Mode B (first read → notify, no MANDATORY INTERRUPT)
    env8.reset_lock()
    out = env8.run_hook(tool_name="Read", file_path="src/Services/OrderService.cs")
    is_mode_b = "[csharp-explorer]" in out and "MANDATORY INTERRUPT" not in out
    check("Read already-analyzed OrderService.cs -> Mode B notify (no MANDATORY INTERRUPT)",
          "[csharp-explorer]" if is_mode_b else "", expect_notify=True)

    # 8d: Method-level analysis stored → class still treated as analyzed
    # Store has "OrderService" → "orderservice" matches class_key for OrderService.cs ✓
    # Verify PaymentService.cs also treated as analyzed (it's in store)
    env8.reset_lock()
    out = env8.run_hook(tool_name="Read", file_path="PaymentService.cs")
    is_mode_b2 = "[csharp-explorer]" in out and "MANDATORY INTERRUPT" not in out
    check("Read already-analyzed PaymentService.cs -> Mode B (no MANDATORY INTERRUPT)",
          "[csharp-explorer]" if is_mode_b2 else "", expect_notify=True)

    # 8e–8j: Skip list — all should be silent
    skip_cases = [
        ("Program.cs",                          "Program.cs (skip: program)"),
        ("GlobalUsings.cs",                     "GlobalUsings.cs (skip: globalusings)"),
        ("Startup.cs",                          "Startup.cs (skip: startup)"),
        ("Migrations/20260101_AddOrders.cs",    "Migration path (skip: migrations/ dir)"),
        ("Something.g.cs",                      "Something.g.cs (skip: .g generated)"),
        ("Form.Designer.cs",                    "Form.Designer.cs (skip: .designer)"),
    ]
    for fpath, label in skip_cases:
        out = env8.run_hook(tool_name="Read", file_path=fpath)
        check(f"Read {label} -> silent", out, expect_notify=False)

    # 8k: Test files → silent (never auto-analyze test classes)
    test_cases = [
        ("tests/Services/OrderServiceTests.cs", "OrderServiceTests.cs (test)"),
        ("tests/BookingServiceSpec.cs",         "BookingServiceSpec.cs (spec)"),
        ("mocks/MockPaymentGateway.cs",         "MockPaymentGateway.cs (mock)"),
    ]
    for fpath, label in test_cases:
        out = env8.run_hook(tool_name="Read", file_path=fpath)
        check(f"Read {label} -> silent", out, expect_notify=False)

    # 8l: Empty store (no runs) → Mode A fires (bootstrap mode)
    # store directory exists (init was run), but no JSON runs yet.
    # Mode A should fire and instruct Claude to analyze the class.
    env_empty = HookTestEnv("brandnewproject", num_runs=0)
    out = env_empty.run_hook(tool_name="Read", file_path="src/NewService.cs")
    has_inst_empty = "MANDATORY INTERRUPT" in out and "NewService" in out
    check("Read unanalyzed .cs, empty store -> Mode A fires (bootstrap)",
          "[csharp-explorer]" if has_inst_empty else "", expect_notify=True)
    env_empty.cleanup()

    # 8m: Grep tool → always Mode B (auto-analyze only on Read of .cs)
    env8.reset_lock()
    out = env8.run_hook(tool_name="Grep", file_path="", glob_pattern="**/*.cs",
                        grep_path="src/")
    is_mode_b_grep = "[csharp-explorer]" in out and "MANDATORY INTERRUPT" not in out
    check("Grep **/*.cs -> Mode B notify (not Mode A)",
          "[csharp-explorer]" if is_mode_b_grep else "", expect_notify=True)

    env8.cleanup()

    # ── Summary ───────────────────────────────────────────────────────────────
    total = len(results)
    passed = sum(results)
    print(f"\n{BOLD}Results: {passed}/{total} passed{RESET}")
    if passed == total:
        print(f"{PASS} -- All tests passed -- hook v0.1.6 behaves correctly")
    else:
        print(f"{FAIL} -- {total - passed} test(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    print(f"{BOLD}csharp-explorer hook.py — Virtual Test Suite (v0.1.6){RESET}")
    print("=" * 55)
    run_tests()
