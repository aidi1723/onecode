"""Tests for data_contract_guidance prompt injection precision and false-positive prevention."""
from __future__ import annotations

import unittest
from onecode.kernel.model_loop import data_contract_guidance


class TestDataContractGuidance(unittest.TestCase):
    def test_audit_report_problem_prompts_do_not_trigger(self) -> None:
        """Verifies the 5 problematic prompts identified in the audit report do not false-trigger."""
        problem_prompts = [
            "Translate the following user manual to Spanish",
            "Implement a binary search function in Python",
            "Combine two sorted lists into one",
            "Show recent git commits",
            "Sort a list of strings by length",
        ]
        for prompt in problem_prompts:
            res = data_contract_guidance(prompt).strip()
            self.assertEqual(res, "", f"False positive guidance triggered for prompt: '{prompt}': {res}")

    def test_fifty_general_programming_prompts_precision(self) -> None:
        """Verifies 50 diverse common programming tasks have <= 2% false positive trigger rate."""
        fifty_prompts = [
            "Write a simple HTTP server using socket library",
            "Calculate the factorial of a non-negative integer",
            "Invert a binary tree and return its root",
            "Check if a string is a valid palindrome",
            "Find the longest common prefix among an array of strings",
            "Implement quicksort on an integer array",
            "Parse JSON string and pretty print formatted output",
            "Serialize Python object to YAML format",
            "Generate random UUID version 4 strings",
            "Create a thread pool executor for CPU-bound tasks",
            "Implement depth-first search on a directed graph",
            "Compute breadth-first search path between two nodes",
            "Check whether two strings are anagrams of each other",
            "Find all prime numbers up to N using Sieve of Eratosthenes",
            "Implement a priority queue using a min-heap",
            "Calculate Euclidean distance between two 3D points",
            "Convert markdown document headings to HTML anchor links",
            "Encode binary data into base64 ASCII characters",
            "Decode base64 string back into binary bytes",
            "Implement basic token bucket rate limiter",
            "Find maximum subarray sum using Kadane's algorithm",
            "Reverse a singly linked list in-place",
            "Detect cycle in a directed graph using Kahn's algorithm",
            "Implement doubly linked list with push and pop methods",
            "Validate balanced parentheses using a stack",
            "Implement trie data structure for prefix search",
            "Compute string edit distance with Wagner-Fischer algorithm",
            "Implement Dijkstra shortest path algorithm",
            "Create a simple cron expression evaluator",
            "Calculate MD5 checksum of a stream of bytes",
            "Read environment variables and set fallback values",
            "Construct binary search tree from preorder traversal",
            "Perform run-length encoding on repetitive string",
            "Compress and decompress data using zlib",
            "Implement semaphore-based worker queue",
            "Build regex pattern for validating email addresses",
            "Compute cosine similarity between two float vectors",
            "Evaluate mathematical reverse Polish notation expression",
            "Find median of two sorted integer lists",
            "Rotate 2D matrix 90 degrees clockwise",
            "Implement consistent hashing ring with virtual nodes",
            "Extract all hyperlinks from raw HTML text",
            "Generate permutations of a list of characters",
            "Find connected components in an undirected graph",
            "Compute eigenvalues of a 2x2 matrix",
            "Simulate Conway's Game of Life grid step",
            "Implement basic publish-subscribe event emitter",
            "Parse semantic version string into major minor patch",
            "Count distinct words in a text passage",
            "Flatten a deeply nested dictionary into dot notation",
        ]
        false_positives: list[tuple[str, str]] = []
        for prompt in fifty_prompts:
            res = data_contract_guidance(prompt).strip()
            if res:
                false_positives.append((prompt, res))

        error_rate = len(false_positives) / len(fifty_prompts)
        self.assertLessEqual(
            error_rate,
            0.02,
            f"False positive rate {error_rate:.1%} exceeds 2% threshold. Triggered: {false_positives}",
        )
        self.assertEqual(len(false_positives), 0, f"Expected 0 false positives, got: {false_positives}")

    def test_legitimate_domain_prompts_still_trigger(self) -> None:
        """Verifies that legitimate data contract tasks correctly receive appropriate guidance."""
        sla_prompt = "Compute ticket resolution and SLA service level agreement metrics for support team"
        self.assertIn("support SLA metrics", data_contract_guidance(sla_prompt))

        ece_prompt = "Compute expected calibration error (ECE) and reliability diagram across calibration bins"
        self.assertIn("calibration bins and ECE", data_contract_guidance(ece_prompt))

        invoice_prompt = "Export billing records and invoice line items with proper taxes"
        self.assertIn("invoice line and tabular exports", data_contract_guidance(invoice_prompt))

        cross_prompt = "Generate cross-categorical features and interaction features for dataset"
        self.assertIn("cross categorical features", data_contract_guidance(cross_prompt))


class TestWorkspaceContractSnippet(unittest.TestCase):
    def test_nested_readme_return_shape_is_injected_without_hidden_slugs(self) -> None:
        import tempfile
        from pathlib import Path

        from onecode.kernel.model_guidance import _contract_spec_snippet

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            doc = root / "target_python"
            doc.mkdir()
            (doc / "README.md").write_text(
                'get_size(path_or_bytes) -> {"type": "png", "width": 1, "height": 1}\n',
                encoding="utf-8",
            )
            (root / "reference_repo").mkdir()
            (root / "reference_repo" / "README.md").write_text("secret upstream\n", encoding="utf-8")
            text = _contract_spec_snippet(root, task="parse image headers")
        self.assertIn("get_size(path_or_bytes)", text)
        self.assertIn("target_python/README.md", text)
        self.assertNotIn("secret upstream", text)
        self.assertIn("offending field or header name", text)
        self.assertNotIn("too_recently_active", text)
        self.assertNotIn("outside_window", text)

    def test_decision_contract_asks_for_a_short_reason_code(self) -> None:
        import tempfile
        from pathlib import Path

        from onecode.kernel.model_guidance import _contract_spec_snippet

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text(
                "Expected decisions.json: status, reason.\n"
                "Error path indexes are part of validation output.\n",
                encoding="utf-8",
            )
            text = _contract_spec_snippet(root, task="build refund decisions")
        self.assertIn("short lowercase snake_case identifier", text)
        self.assertIn("integers, not numeric strings", text)
        self.assertNotIn("seat_limit_reached", text)
        self.assertNotIn("no_paid_charge", text)

    def test_cli_json_contract_asks_for_path_and_file_keys(self) -> None:
        import tempfile
        from pathlib import Path

        from onecode.kernel.model_guidance import _contract_spec_snippet

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text(
                "Usage: python main.py image1.png --json\n",
                encoding="utf-8",
            )
            text = _contract_spec_snippet(root, task="read image headers via cli")
        self.assertIn("both 'path' and 'file' keys", text)

    def test_targeted_assertion_extracts_policy_reason_guidance(self) -> None:
        from onecode.kernel.model_guidance import _extract_targeted_assertions

        error_parts = [
            "- [FAIL] recently active churned user blocked\n- [PASS] active user blocked"
        ]
        alerts = _extract_targeted_assertions(error_parts)
        text = "\n".join(alerts)
        self.assertIn("Precision reason target", text)
        self.assertIn("recently active churned user blocked", text)
        self.assertNotIn("too_recently_active", text)


if __name__ == "__main__":
    unittest.main()
