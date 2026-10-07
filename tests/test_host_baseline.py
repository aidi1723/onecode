import math
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from onecode.kernel.agent_cycle import run_agent_cycle
from onecode.kernel.cycle_approvals import load_pending_approvals, resume_pending_approval


_HOLD_PENDING = """
import sys
import time
from pathlib import Path
from onecode.kernel.agent_cycle import run_agent_cycle

workspace = Path(sys.argv[1])

def propose(history, allowed):
    return [{"tool_name": "run_command", "params": {"argv": ["rm", "-rf", "./temp_test_dir"]}}]

def execute(tool_name, params):
    raise SystemExit("executed before approval")

run_agent_cycle(propose=propose, execute=execute, workspace=workspace, max_turns=1)
(workspace / "ready").write_text("1", encoding="utf-8")
time.sleep(60)
"""


_SLOW_WRITE = """
import os
import sys
import time
from pathlib import Path

from onecode.kernel.path_guard import PathGuard

workspace = Path(sys.argv[1])
ready = Path(sys.argv[2])
real_fsync = os.fsync

def slow_fsync(descriptor):
    ready.write_text("1", encoding="utf-8")
    time.sleep(60)
    return real_fsync(descriptor)

os.fsync = slow_fsync
PathGuard.write_text(workspace, "src/app.py", "def first(items):\\n    return items[0]\\nchanged\\n")
"""


def _percentile(samples: list[float], percent: float) -> float:
    ordered = sorted(samples)
    rank = math.ceil(percent / 100 * len(ordered)) - 1
    return ordered[max(0, min(rank, len(ordered) - 1))]


def _time_ms(action) -> float:
    started = time.perf_counter_ns()
    action()
    return (time.perf_counter_ns() - started) / 1_000_000


class HostLatencyTests(unittest.TestCase):
    def test_host_actions_stay_within_the_latency_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "note.txt").write_text("hello\n", encoding="utf-8")
            long_text = ("PASSED line\n" * 4_000) + "1 failed, 5 passed\n"
            samples = {
                "dangerous_approval": [],
                "truncation_tail": [],
                "missing_file": [],
                "allowlisted_read": [],
                "allowlisted_list": [],
            }

            def dangerous():
                index = len(samples["dangerous_approval"])

                def propose(history, allowed):
                    return [{"tool_name": "run_command", "params": {"argv": ["rm", "-rf", f"./temp-{index}"]}}]

                result = run_agent_cycle(
                    propose=propose,
                    execute=lambda tool_name, params: {"status": "completed"},
                    workspace=workspace,
                    max_turns=1,
                )
                self.assertEqual(result["reason"], "approval_required")

            def truncated():
                def propose(history, allowed):
                    if history:
                        return []
                    return [{"tool_name": "run_command", "params": {"argv": ["pytest"]}}]

                def execute(tool_name, params):
                    return {"status": "completed", "reason": None, "stdout": long_text, "returncode": 1}

                result = run_agent_cycle(
                    propose=propose,
                    execute=execute,
                    approve=lambda tool_name, params: True,
                    max_turns=2,
                )
                self.assertIn("1 failed, 5 passed", result["turns"][0]["output"])

            def missing():
                def propose(history, allowed):
                    return [{"tool_name": "read_text", "params": {"path": "missing.ini"}}]

                def execute(tool_name, params):
                    return {"status": "halted", "reason": "path_not_found"}

                result = run_agent_cycle(propose=propose, execute=execute, max_turns=1)
                self.assertEqual(result["turns"][0]["reason"], "path_not_found")

            def read_note():
                from onecode.kernel.execution_tools import ReadTextTool

                tool = ReadTextTool()

                def propose(history, allowed):
                    if history:
                        return []
                    return [{"tool_name": "read_text", "params": {"path": "note.txt"}}]

                def execute(tool_name, params):
                    return {"status": "completed", "reason": None, **tool.execute(params, workspace)}

                result = run_agent_cycle(propose=propose, execute=execute, max_turns=2)
                self.assertIn("hello", result["turns"][0]["output"])

            def list_root():
                from onecode.kernel.execution_tools import ListFilesTool

                tool = ListFilesTool()

                def propose(history, allowed):
                    if history:
                        return []
                    return [{"tool_name": "list_files", "params": {"path": "."}}]

                def execute(tool_name, params):
                    outcome = tool.execute(params, workspace)
                    return {"status": "completed", "reason": None, "entries": outcome.get("files", [])}

                result = run_agent_cycle(propose=propose, execute=execute, max_turns=2)
                self.assertEqual(result["status"], "completed")

            actions = {
                "dangerous_approval": dangerous,
                "truncation_tail": truncated,
                "missing_file": missing,
                "allowlisted_read": read_note,
                "allowlisted_list": list_root,
            }
            for _ in range(10):
                for action in actions.values():
                    action()
            for name, action in actions.items():
                for _ in range(200):
                    samples[name].append(_time_ms(action))

        for name, values in samples.items():
            self.assertLessEqual(_percentile(values, 95), 20, name)
            self.assertLessEqual(_percentile(values, 99), 50, name)


class ApprovalRecoveryTests(unittest.TestCase):
    def test_kill_leaves_a_pending_approval_that_restart_cannot_skip(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            target = workspace / "temp_test_dir"
            target.mkdir()
            child = subprocess.Popen(
                [sys.executable, "-c", _HOLD_PENDING, str(workspace)],
                env={**os.environ, "PYTHONPATH": str(Path("src").resolve())},
            )
            deadline = time.time() + 10
            ready = workspace / "ready"
            while not ready.exists():
                if time.time() > deadline:
                    child.kill()
                    self.fail("pending approval was not stored")
                time.sleep(0.02)
            os.kill(child.pid, signal.SIGKILL)
            child.wait(timeout=5)

            pending = load_pending_approvals(workspace)
            self.assertEqual(len(pending), 1)
            record = pending[0]
            self.assertEqual(record["status"], "PENDING_APPROVAL")
            self.assertEqual(record["tool_name"], "run_command")
            self.assertEqual(record["params"]["argv"], ["rm", "-rf", "./temp_test_dir"])
            self.assertEqual(record["reason"], "approval_required")
            self.assertFalse(list(workspace.rglob("*.tmp")))
            self.assertFalse([path for path in workspace.rglob("*") if path.name.startswith(".") and path.is_file() and path.suffix != ".json"])

            calls = []

            def propose(history, allowed):
                return [{"tool_name": "run_command", "params": {"argv": ["rm", "-rf", "./temp_test_dir"]}}]

            def execute(tool_name, params):
                calls.append(params["argv"])
                target.rmdir()
                return {"status": "completed", "reason": None}

            restarted = run_agent_cycle(
                propose=propose,
                execute=execute,
                approve=lambda tool_name, params: True,
                workspace=workspace,
                max_turns=1,
            )
            self.assertEqual(calls, [])
            self.assertTrue(target.is_dir())
            self.assertEqual(restarted["reason"], "approval_required")

            rejected = resume_pending_approval(workspace, record["id"], "rejected", execute)
            self.assertEqual(calls, [])
            self.assertEqual(rejected["reason"], "permission_denied")
            self.assertEqual(load_pending_approvals(workspace), [])

    def test_explicit_approval_executes_the_stored_command_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            calls = []

            def propose(history, allowed):
                return [{"tool_name": "run_command", "params": {"argv": ["rm", "-rf", "./temp_test_dir"]}}]

            def execute(tool_name, params):
                calls.append(params["argv"])
                return {"status": "completed", "reason": None, "stdout": "removed"}

            suspended = run_agent_cycle(propose=propose, execute=execute, workspace=workspace, max_turns=1)
            resumed = resume_pending_approval(workspace, suspended["pending_id"], "approved", execute)

            self.assertEqual(calls, [["rm", "-rf", "./temp_test_dir"]])
            self.assertEqual(resumed["stdout"], "removed")
            self.assertEqual(load_pending_approvals(workspace), [])


class SoakTests(unittest.TestCase):
    def test_fifty_recorded_rounds_keep_memory_and_descriptors_stable(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "note.txt").write_text("hello\n", encoding="utf-8")
            long_text = ("PASSED\n" * 4_000) + "1 failed, 5 passed\n"
            marks = {}
            for index in range(1, 51):
                self._one_round(workspace, index, long_text)
                if index in {5, 50}:
                    marks[index] = (_resident_bytes(), _descriptor_count())


        baseline = marks[5][0]
        finished = marks[50][0]
        self.assertLessEqual((finished - baseline) / baseline, 0.15)
        self.assertEqual(marks[5][1], marks[50][1])
        self.assertEqual(_descriptor_count(), marks[50][1])

    def _one_round(self, workspace: Path, index: int, long_text: str) -> None:
        state = {"reads": 0}

        def propose(history, allowed):
            turn = len(history)
            if turn == 0:
                return [{"tool_name": "read_text", "params": {"path": "note.txt"}}]
            if turn == 1:
                return [{"tool_name": "patch_text", "params": {"path": "note.txt", "search_block": "hello", "replace_block": f"hello-{index}"}}]
            if turn == 2:
                return [{"tool_name": "run_command", "params": {"argv": ["pytest"]}}]
            if turn < 5:
                return [{"tool_name": "read_text", "params": {"path": "remote.txt"}}]
            return []

        def execute(tool_name, params):
            if tool_name == "patch_text":
                return {"status": "completed", "reason": None, "diff": f"hello-{index}"}
            if tool_name == "run_command":
                return {"status": "completed", "reason": None, "stdout": long_text, "returncode": 1}
            if params.get("path") == "remote.txt":
                state["reads"] += 1
                if state["reads"] < 3:
                    return {"status": "completed", "reason": None, "retryable": True, "stdout": "HTTP 429"}
                return {"status": "completed", "reason": None, "stdout": "SUCCESS"}
            return {"status": "completed", "reason": None, "content": "hello"}

        run_agent_cycle(
            propose=propose,
            execute=execute,
            approve=lambda tool_name, params: True,
            workspace=workspace,
            max_turns=8,
        )

        def hold(history, allowed):
            return [{"tool_name": "run_command", "params": {"argv": ["rm", "-rf", "./temp_test_dir"]}}]

        def blocked(tool_name, params):
            raise AssertionError("suspended command ran")

        held = run_agent_cycle(propose=hold, execute=blocked, workspace=workspace, max_turns=1)
        resume_pending_approval(workspace, held["pending_id"], "rejected", blocked)

        def miss(history, allowed):
            if history:
                return []
            return [{"tool_name": "search_text", "params": {"query": f"missing-{index}"}}]

        run_agent_cycle(
            propose=miss,
            execute=lambda tool_name, params: {"status": "completed", "reason": "search_miss"},
            workspace=workspace,
            max_turns=2,
        )


class AtomicWriteTests(unittest.TestCase):
    def test_interrupted_write_leaves_the_original_bytes(self):
        from unittest.mock import patch

        from onecode.kernel.path_guard import PathGuard

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            original = "def first(items):\n    return items[0]\n"
            PathGuard.write_text(workspace, "src/app.py", original)
            target = workspace / "src" / "app.py"
            before = target.read_bytes()

            def fail_sync(descriptor):
                raise KeyboardInterrupt

            with patch("onecode.kernel.path_guard.os.fsync", fail_sync):
                with self.assertRaises(KeyboardInterrupt):
                    PathGuard.write_text(workspace, "src/app.py", original + "added\n")

            self.assertEqual(target.read_bytes(), before)
            self.assertEqual([path.name for path in target.parent.iterdir()], ["app.py"])

    def test_sigkill_during_write_keeps_the_original_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            source = workspace / "src"
            source.mkdir()
            target = source / "app.py"
            original = "def first(items):\n    return items[0]\n"
            target.write_text(original, encoding="utf-8")
            ready = workspace / "ready"
            child = subprocess.Popen(
                [sys.executable, "-c", _SLOW_WRITE, str(workspace), str(ready)],
                env={**os.environ, "PYTHONPATH": str(Path("src").resolve())},
            )
            deadline = time.time() + 10
            while not ready.exists():
                if time.time() > deadline:
                    child.kill()
                    self.fail("write did not reach fsync")
                time.sleep(0.02)
            os.kill(child.pid, signal.SIGKILL)
            child.wait(timeout=5)

            self.assertEqual(target.read_text(encoding="utf-8"), original)
            self.assertTrue(any(path.name.startswith(".app.py.") for path in source.iterdir()))
            run_agent_cycle(
                propose=lambda history, allowed: [],
                execute=lambda tool_name, params: {},
                workspace=workspace,
                max_turns=1,
            )
            self.assertEqual(target.read_text(encoding="utf-8"), original)
            self.assertEqual([path.name for path in source.iterdir()], ["app.py"])


def _resident_bytes() -> int:
    status = Path("/proc/self/status")
    if status.exists():
        for line in status.read_text(encoding="utf-8").splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) * 1024
    import ctypes

    class ProcTaskInfo(ctypes.Structure):
        _fields_ = [
            ("pti_virtual_size", ctypes.c_uint64),
            ("pti_resident_size", ctypes.c_uint64),
            ("pti_total_user", ctypes.c_uint64),
            ("pti_total_system", ctypes.c_uint64),
            ("pti_threads_user", ctypes.c_uint64),
            ("pti_threads_system", ctypes.c_uint64),
            ("pti_policy", ctypes.c_int32),
            ("pti_faults", ctypes.c_int32),
            ("pti_pageins", ctypes.c_int32),
            ("pti_cow_faults", ctypes.c_int32),
            ("pti_messages_sent", ctypes.c_int32),
            ("pti_messages_received", ctypes.c_int32),
            ("pti_syscalls_mach", ctypes.c_int32),
            ("pti_syscalls_unix", ctypes.c_int32),
            ("pti_csw", ctypes.c_int32),
            ("pti_threadnum", ctypes.c_int32),
            ("pti_numrunning", ctypes.c_int32),
            ("pti_priority", ctypes.c_int32),
        ]

    info = ProcTaskInfo()
    written = ctypes.CDLL("/usr/lib/libproc.dylib").proc_pidinfo(os.getpid(), 4, 0, ctypes.byref(info), ctypes.sizeof(info))
    if written <= 0:
        raise OSError("resident memory is unavailable")
    return int(info.pti_resident_size)


def _descriptor_count() -> int:
    directory = "/proc/self/fd" if Path("/proc/self/fd").exists() else "/dev/fd"
    return len(os.listdir(directory))


if __name__ == "__main__":
    unittest.main()
