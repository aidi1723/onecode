"""Tests for large-repo symbol index and call-chain fault localization."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from onecode.kernel.symbol_locator import (
    FaultLocation,
    ImportRef,
    StackFrame,
    SymbolDef,
    SymbolLocator,
    WorkspaceSymbolIndex,
    aggregate_locator_hits,
    file_hit_rates,
    files_touched_by_patch,
)


class TestSymbolLocator(unittest.TestCase):
    def test_symbol_def_and_stack_frame_properties(self) -> None:
        sym = SymbolDef(
            name="calculate_sla",
            kind="method",
            file_path="src/service/sla.py",
            line_start=15,
            line_end=42,
            class_name="SlaEngine",
            docstring="Compute SLA deadline.",
            parameters=("self", "ticket", "priority"),
        )
        self.assertEqual(sym.qualified_name, "SlaEngine.calculate_sla")
        self.assertEqual(sym.parameters, ("self", "ticket", "priority"))

        top_sym = SymbolDef(
            name="run_pipeline",
            kind="function",
            file_path="src/pipeline.py",
            line_start=1,
            line_end=10,
        )
        self.assertEqual(top_sym.qualified_name, "run_pipeline")

        frame = StackFrame(
            file_path="src/service/sla.py",
            line=25,
            function_name="calculate_sla",
        )
        self.assertEqual(frame.line, 25)
        self.assertEqual(frame.function_name, "calculate_sla")

    def test_fault_location_serialization(self) -> None:
        loc = FaultLocation(
            file_path="src/service/sla.py",
            symbol_name="SlaEngine.calculate_sla",
            symbol_kind="method",
            line_start=15,
            line_end=42,
            confidence=0.92,
            call_chain=("tests/test_sla.py", "calculate_sla"),
            is_test_file=False,
            reason="Stack frame match",
        )
        data = loc.to_dict()
        self.assertEqual(data["file_path"], "src/service/sla.py")
        self.assertEqual(data["symbol_name"], "SlaEngine.calculate_sla")
        self.assertFalse(data["is_test_file"])
        self.assertEqual(data["confidence"], 0.92)
        self.assertEqual(data["call_chain"], ["tests/test_sla.py", "calculate_sla"])

    def test_workspace_symbol_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            src_dir = tmp_path / "src" / "billing"
            src_dir.mkdir(parents=True)
            tests_dir = tmp_path / "tests"
            tests_dir.mkdir(parents=True)
            ignored_dir = tmp_path / ".venv" / "lib"
            ignored_dir.mkdir(parents=True)

            service_code = '''"""Billing service implementation."""

class InvoiceProcessor:
    """Handles invoice computations."""
    def compute_total(self, items: list, tax_rate: float) -> float:
        """Calculate line totals."""
        return sum(items) * (1 + tax_rate)

async def dispatch_invoice(invoice_id: str) -> bool:
    return True
'''
            (src_dir / "processor.py").write_text(service_code, encoding="utf-8")

            test_code = '''"""Test suite for billing."""
from src.billing.processor import InvoiceProcessor, dispatch_invoice

def test_invoice_total():
    proc = InvoiceProcessor()
    assert proc.compute_total([100], 0.1) == 110.0
'''
            (tests_dir / "test_billing.py").write_text(test_code, encoding="utf-8")
            (ignored_dir / "vendor.py").write_text("def vendor_func(): pass", encoding="utf-8")

            index = WorkspaceSymbolIndex(tmp_path)
            self.assertEqual(index.scanned_files_count, 2)

            self.assertIn("InvoiceProcessor", index.symbols_by_name)
            cls_sym = index.symbols_by_name["InvoiceProcessor"][0]
            self.assertEqual(cls_sym.kind, "class")
            self.assertEqual(cls_sym.file_path, "src/billing/processor.py")
            self.assertEqual(cls_sym.docstring, "Handles invoice computations.")

            self.assertIn("compute_total", index.symbols_by_name)
            m_sym = index.symbols_by_name["compute_total"][0]
            self.assertEqual(m_sym.kind, "method")
            self.assertEqual(m_sym.class_name, "InvoiceProcessor")
            self.assertEqual(m_sym.parameters, ("self", "items", "tax_rate"))
            self.assertIn("InvoiceProcessor.compute_total", index.symbols_by_name)

            self.assertIn("dispatch_invoice", index.symbols_by_name)
            async_sym = index.symbols_by_name["dispatch_invoice"][0]
            self.assertEqual(async_sym.kind, "async_function")

            test_imports = index.imports_by_file.get("tests/test_billing.py", {})
            self.assertIn("InvoiceProcessor", test_imports)
            self.assertEqual(test_imports["InvoiceProcessor"], "src.billing.processor.InvoiceProcessor")

    def test_symbol_locator_extract_failing_symbols(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            locator = SymbolLocator(Path(tmp_dir))

            traceback_sample = """
Traceback (most recent call last):
  File "tests/test_service.py", line 42, in test_dispatch
    service.submit_order(order_id)
  File "src/billing/order.py", line 88, in submit_order
    self.validator.validate_order(order)
AttributeError: 'OrderValidator' object has no attribute 'validate_order'
"""
            symbols = locator.extract_failing_symbols(traceback_sample)
            self.assertIn("validate_order", symbols)
            self.assertIn("OrderValidator", symbols)
            self.assertIn("OrderValidator.validate_order", symbols)
            self.assertIn("submit_order", symbols)

            type_error_sample = "TypeError: calculate_tax() missing 1 required positional argument: 'rate'"
            self.assertIn("calculate_tax", locator.extract_failing_symbols(type_error_sample))

            name_error_sample = "NameError: name 'UnknownHandler' is not defined"
            self.assertIn("UnknownHandler", locator.extract_failing_symbols(name_error_sample))

            import_error_sample = "ImportError: cannot import name 'reconcile_batch' from 'src.accounting'"
            self.assertIn("reconcile_batch", locator.extract_failing_symbols(import_error_sample))

            pytest_sample = "FAILED tests/test_orders.py::TestOrder::test_cancel_flow - AssertionError"
            failing = locator.extract_failing_symbols(pytest_sample)
            self.assertIn("cancel_flow", failing)

    def test_symbol_locator_locate_fault_prioritizes_implementation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            src_dir = tmp_path / "src" / "orders"
            src_dir.mkdir(parents=True)
            tests_dir = tmp_path / "tests"
            tests_dir.mkdir(parents=True)

            order_py = '''"""Order module."""

class OrderService:
    def execute_order(self, order_id: str) -> None:
        pass
'''
            (src_dir / "service.py").write_text(order_py, encoding="utf-8")

            test_py = '''"""Order test."""
from src.orders.service import OrderService

def test_execute_order():
    service = OrderService()
    service.execute_order("123")
'''
            (tests_dir / "test_service.py").write_text(test_py, encoding="utf-8")

            locator = SymbolLocator(tmp_path)

            failure_text = f"""
Traceback (most recent call last):
  File "{tmp_path}/tests/test_service.py", line 6, in test_execute_order
    service.execute_order("123")
  File "{tmp_path}/src/orders/service.py", line 5, in execute_order
    raise ValueError("invalid order")
ValueError: invalid order
"""
            candidates = locator.locate_fault(failure_text)
            self.assertGreaterEqual(len(candidates), 1)

            # First candidate MUST be non-test implementation file
            top_candidate = candidates[0]
            self.assertFalse(top_candidate.is_test_file)
            self.assertEqual(top_candidate.file_path, "src/orders/service.py")
            self.assertIn("execute_order", top_candidate.symbol_name)
            self.assertGreater(top_candidate.confidence, 0.5)

    def test_symbol_locator_direct_import_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            src_dir = tmp_path / "src" / "sla"
            src_dir.mkdir(parents=True)
            tests_dir = tmp_path / "tests"
            tests_dir.mkdir(parents=True)

            (src_dir / "calculator.py").write_text(
                "def compute_sla_hours(created_at, priority):\n    return 4\n",
                encoding="utf-8",
            )
            (tests_dir / "test_sla.py").write_text(
                "from src.sla.calculator import compute_sla_hours\n\ndef test_sla():\n    assert compute_sla_hours(1, 2) == 4\n",
                encoding="utf-8",
            )

            locator = SymbolLocator(tmp_path)
            failure_msg = "AssertionError: compute_sla_hours returned 4, expected 2"
            candidates = locator.locate_fault(failure_msg, test_file_hint="tests/test_sla.py")

            self.assertGreaterEqual(len(candidates), 1)
            top = candidates[0]
            self.assertEqual(top.file_path, "src/sla/calculator.py")
            self.assertEqual(top.symbol_name, "compute_sla_hours")
            self.assertFalse(top.is_test_file)

    def test_syntax_error_resilience_and_empty_failures(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            src_dir = tmp_path / "src"
            src_dir.mkdir(parents=True)
            # Create a file with syntax error
            (src_dir / "broken.py").write_text("def unclosed_func(:", encoding="utf-8")
            (src_dir / "valid.py").write_text("def ok(): return 1", encoding="utf-8")

            index = WorkspaceSymbolIndex(tmp_path)
            self.assertEqual(index.scanned_files_count, 1)  # only valid.py was indexed

            locator = SymbolLocator(tmp_path, index=index)
            # Locate with empty or random failure
            empty_loc = locator.locate_fault("")
            self.assertEqual(empty_loc, [])

            random_loc = locator.locate_fault("Random non-traceback error text without any symbol match")
            self.assertEqual(random_loc, [])

    def test_repair_prompt_integration_with_symbol_locator(self) -> None:
        from onecode.kernel.model_loop import repair_prompt

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            src_dir = tmp_path / "src" / "engine"
            src_dir.mkdir(parents=True)
            tests_dir = tmp_path / "tests"
            tests_dir.mkdir(parents=True)

            code = (
                "class DiscountEngine:\n"
                "    def compute_discount(self, price: float) -> float:\n"
                "        return price * 0.1\n"
            )
            (src_dir / "calculator.py").write_text(code, encoding="utf-8")
            (tests_dir / "test_calc.py").write_text("def test_dummy(): pass\n", encoding="utf-8")

            failed_result = {
                "status": "verifier_failed",
                "reason": "verifier_failed",
                "verifier_results": [
                    {
                        "status": "failed",
                        "stderr_tail": (
                            f'File "{tmp_path}/tests/test_calc.py", line 5, in test_calc\n'
                            f'  engine.compute_discount(100)\n'
                            f'File "{tmp_path}/src/engine/calculator.py", line 3, in compute_discount\n'
                            f'AssertionError: 10.0 != 20.0\n'
                        ),
                    }
                ],
                "workspace_files": {},
            }

            prompt = repair_prompt("fix discount engine", failed_result, workspace=tmp_path)

            self.assertIn("Fault localization (天相印绶·符号溯源定位):", prompt)
            self.assertIn("src/engine/calculator.py", prompt)
            self.assertIn("DiscountEngine.compute_discount", prompt)
            self.assertIn("## src/engine/calculator.py", prompt)
            self.assertIn("compute_discount", failed_result["workspace_files"]["src/engine/calculator.py"])

    def test_pytest_stack_frame_parsing_and_reexport_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            pkg_dir = tmp_path / "src" / "shop"
            pkg_dir.mkdir(parents=True)
            tests_dir = tmp_path / "tests"
            tests_dir.mkdir(parents=True)

            # 1. Implementation modules
            (pkg_dir / "service.py").write_text(
                "class ShopService:\n    def checkout(self): pass\n",
                encoding="utf-8",
            )
            (pkg_dir / "calc.py").write_text(
                "def calculate_tax(amount: float) -> float:\n    return amount * 0.05\n",
                encoding="utf-8",
            )
            # 2. Package re-exporting in __init__.py
            (pkg_dir / "__init__.py").write_text(
                "from .service import ShopService\nfrom .calc import calculate_tax\n",
                encoding="utf-8",
            )
            # 3. Test file importing from shop package
            (tests_dir / "test_shop.py").write_text(
                "from shop import ShopService, calculate_tax\n\ndef test_shop():\n    assert calculate_tax(100) == 10.0\n",
                encoding="utf-8",
            )

            locator = SymbolLocator(tmp_path)

            # Test pytest frame parsing
            pytest_output = """
tests/test_shop.py:4: in test_shop
    assert calculate_tax(100) == 10.0
E   AssertionError: assert 5.0 == 10.0
FAILED tests/test_shop.py::test_shop - AssertionError
"""
            frames = locator.parse_stack_frames(pytest_output)
            self.assertEqual(len(frames), 1)
            self.assertEqual(frames[0].file_path, "tests/test_shop.py")
            self.assertEqual(frames[0].line, 4)
            self.assertEqual(frames[0].function_name, "test_shop")

            # Locate fault: must resolve through __init__.py into src/shop/calc.py
            candidates = locator.locate_fault(pytest_output)
            self.assertGreaterEqual(len(candidates), 1)
            top = candidates[0]
            self.assertEqual(top.file_path, "src/shop/calc.py")
            self.assertEqual(top.symbol_name, "calculate_tax")
            self.assertFalse(top.is_test_file)
            self.assertGreaterEqual(top.confidence, 0.90)

            # Test minimal 2-line log without code body: test scope token extraction must still achieve 0.92
            minimal_log = "tests/test_shop.py:4: AssertionError\nFAILED tests/test_shop.py::test_shop\n"
            min_candidates = locator.locate_fault(minimal_log)
            self.assertGreaterEqual(len(min_candidates), 1)
            min_top = min_candidates[0]
            self.assertEqual(min_top.file_path, "src/shop/calc.py")
            self.assertEqual(min_top.symbol_name, "calculate_tax")
            self.assertFalse(min_top.is_test_file)
            self.assertGreaterEqual(min_top.confidence, 0.90)

    def test_python_call_edge_puts_the_callee_file_in_the_top_five(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "src"
            tests = root / "tests"
            src.mkdir()
            tests.mkdir()
            (src / "app.py").write_text("def run():\n    return helper()\n", encoding="utf-8")
            (src / "helper.py").write_text("def helper():\n    return 1\n", encoding="utf-8")
            (tests / "test_app.py").write_text(
                "from src.app import run\n\ndef test_run():\n    assert run() == 2\n",
                encoding="utf-8",
            )
            locator = SymbolLocator(root)
            self.assertIn(("src/app.py", "run"), locator.index.callers_by_name["helper"])
            failure = (
                'File "tests/test_app.py", line 4, in test_run\n'
                "    assert run() == 2\n"
                "AssertionError: 1 != 2\n"
            )
            ranked = [item.file_path for item in locator.locate_fault(failure)]
            diff = "--- a/src/helper.py\n+++ b/src/helper.py\n@@\n-return 1\n+return 2\n"
            gold = files_touched_by_patch(diff)
            rates = file_hit_rates(ranked, gold)
            self.assertIn("src/helper.py", ranked[:5])
            self.assertTrue(rates["top5"])
            summary = aggregate_locator_hits([{"ranked_files": ranked, "patch": diff}, {"instance_id": "missing"}])
            self.assertEqual(summary["scored_count"], 1)
            self.assertEqual(summary["patches_absent"], 1)
            self.assertEqual(summary["top5_hit_rate"], 1.0)
            self.assertFalse(summary["claims_mainstream_parity"])

    def test_go_module_prefix_resolves_to_the_package_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "go.mod").write_text("module example.com/edwards\n\ngo 1.22\n", encoding="utf-8")
            point = root / "point"
            scalar = root / "scalar"
            point.mkdir()
            scalar.mkdir()
            (point / "base.go").write_text("package point\nfunc ScalarBaseMult() {}\n", encoding="utf-8")
            (scalar / "mul.go").write_text("package scalar\nfunc Multiply() {}\n", encoding="utf-8")
            (root / "other").mkdir()
            (root / "other" / "point.go").write_text("package other\nfunc Point() {}\n", encoding="utf-8")
            index = WorkspaceSymbolIndex(root)
            resolved = index.resolve_import_file(ImportRef(module="example.com/edwards/point"))
        self.assertIsNotNone(resolved)
        self.assertTrue(str(resolved).startswith("point/"))


if __name__ == "__main__":
    unittest.main()
