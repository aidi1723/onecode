"""Tests for multi-language symbol scanning and fault localization (Go, TypeScript, Rust)."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from onecode.kernel.symbol_locator import (
    SymbolLocator,
    is_any_test_path,
)
from onecode.kernel.symbol_parsers import (
    GoSymbolScanner,
    RustSymbolScanner,
    TypeScriptSymbolScanner,
)


class TestGoSymbolScanningAndLocalization(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmp_dir.name)
        (self.workspace / "pkg" / "service").mkdir(parents=True, exist_ok=True)

        self.go_src = self.workspace / "pkg" / "service" / "order.go"
        self.go_src.write_text(
            "package service\n\n"
            "type OrderService struct {\n"
            "    taxRate float64\n"
            "}\n\n"
            "func (s *OrderService) CalculateTotal(amount float64) float64 {\n"
            "    return amount * (1.0 + s.taxRate)\n"
            "}\n\n"
            "func NewOrderService(rate float64) *OrderService {\n"
            "    return &OrderService{taxRate: rate}\n"
            "}\n",
            encoding="utf-8",
        )

        self.go_test = self.workspace / "pkg" / "service" / "order_test.go"
        self.go_test.write_text(
            "package service\n\n"
            "import \"testing\"\n\n"
            "func TestCalculateTotal(t *testing.T) {\n"
            "    svc := NewOrderService(0.1)\n"
            "    got := svc.CalculateTotal(100.0)\n"
            "    if got != 110.0 {\n"
            "        t.Errorf(\"expected 110, got %v\", got)\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def test_go_symbol_scanner_raw(self) -> None:
        symbols, imports = GoSymbolScanner.scan(self.go_src.read_text(encoding="utf-8"), "pkg/service/order.go")
        names = {s["name"]: s for s in symbols}
        self.assertIn("OrderService", names)
        self.assertEqual(names["OrderService"]["kind"], "class")
        self.assertIn("CalculateTotal", names)
        self.assertEqual(names["CalculateTotal"]["kind"], "method")
        self.assertEqual(names["CalculateTotal"]["class_name"], "OrderService")
        self.assertIn("NewOrderService", names)
        self.assertEqual(names["NewOrderService"]["kind"], "function")

    def test_go_fault_localization_from_panic(self) -> None:
        panic_trace = (
            "panic: runtime error: invalid memory address or nil pointer dereference\n"
            "[signal SIGSEGV: segmentation violation code=0x1 addr=0x0 pc=0x10a24b0]\n\n"
            "goroutine 1 [running]:\n"
            "pkg/service.(*OrderService).CalculateTotal(0x0, 0x4059000000000000)\n"
            "\tpkg/service/order.go:8 +0x1b\n"
            "pkg/service.TestCalculateTotal(0xc0000bc000)\n"
            "\tpkg/service/order_test.go:7 +0x5a\n"
        )
        locator = SymbolLocator(self.workspace)
        candidates = locator.locate_fault(panic_trace, max_candidates=3)
        self.assertTrue(len(candidates) > 0)
        top = candidates[0]
        self.assertEqual(top.file_path, "pkg/service/order.go")
        self.assertEqual(top.symbol_name, "OrderService.CalculateTotal")
        self.assertFalse(top.is_test_file)
        self.assertGreaterEqual(top.confidence, 0.90)


class TestTypeScriptSymbolScanningAndLocalization(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmp_dir.name)
        (self.workspace / "src").mkdir(parents=True, exist_ok=True)
        (self.workspace / "tests").mkdir(parents=True, exist_ok=True)

        self.ts_src = self.workspace / "src" / "calculator.ts"
        self.ts_src.write_text(
            "export interface MathResult {\n"
            "    val: number;\n"
            "}\n\n"
            "export class Calculator {\n"
            "    add(a: number, b: number): number {\n"
            "        return a + b;\n"
            "    }\n"
            "    multiply(a: number, b: number): number {\n"
            "        return a * b;\n"
            "    }\n"
            "}\n\n"
            "export const computeSquare = (x: number): number => {\n"
            "    return x * x;\n"
            "};\n",
            encoding="utf-8",
        )

        self.ts_test = self.workspace / "tests" / "calculator.test.ts"
        self.ts_test.write_text(
            "import { Calculator, computeSquare } from '../src/calculator';\n\n"
            "describe('Calculator', () => {\n"
            "    test('addition fails', () => {\n"
            "        const calc = new Calculator();\n"
            "        expect(calc.add(2, 3)).toBe(6);\n"
            "    });\n"
            "});\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def test_ts_symbol_scanner_raw(self) -> None:
        symbols, imports = TypeScriptSymbolScanner.scan(
            self.ts_src.read_text(encoding="utf-8"), "src/calculator.ts"
        )
        names = {s["name"]: s for s in symbols}
        self.assertIn("MathResult", names)
        self.assertIn("Calculator", names)
        self.assertEqual(names["Calculator"]["kind"], "class")
        self.assertIn("add", names)
        self.assertEqual(names["add"]["kind"], "method")
        self.assertEqual(names["add"]["class_name"], "Calculator")
        self.assertIn("computeSquare", names)
        self.assertEqual(names["computeSquare"]["kind"], "function")

    def test_ts_fault_localization_from_jest(self) -> None:
        jest_trace = (
            "FAIL tests/calculator.test.ts\n"
            "  ● Calculator › addition fails\n\n"
            "    expect(received).toBe(expected)\n\n"
            "    Expected: 6\n"
            "    Received: 5\n\n"
            "      at Calculator.add (src/calculator.ts:6:16)\n"
            "      at Object.<anonymous> (tests/calculator.test.ts:6:24)\n"
        )
        locator = SymbolLocator(self.workspace)
        candidates = locator.locate_fault(jest_trace, max_candidates=3)
        self.assertTrue(len(candidates) > 0)
        top = candidates[0]
        self.assertEqual(top.file_path, "src/calculator.ts")
        self.assertEqual(top.symbol_name, "Calculator.add")
        self.assertFalse(top.is_test_file)
        self.assertGreaterEqual(top.confidence, 0.90)


class TestRustSymbolScanningAndLocalization(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmp_dir.name)
        (self.workspace / "src").mkdir(parents=True, exist_ok=True)
        (self.workspace / "tests").mkdir(parents=True, exist_ok=True)

        self.rs_src = self.workspace / "src" / "engine.rs"
        self.rs_src.write_text(
            "pub struct ExecutionEngine {\n"
            "    step_limit: u32,\n"
            "}\n\n"
            "impl ExecutionEngine {\n"
            "    pub fn new(limit: u32) -> Self {\n"
            "        Self { step_limit: limit }\n"
            "    }\n\n"
            "    pub fn dispatch(&self, token: &str) -> bool {\n"
            "        !token.is_empty()\n"
            "    }\n"
            "}\n\n"
            "pub fn initialize() -> bool {\n"
            "    true\n"
            "}\n",
            encoding="utf-8",
        )

        self.rs_test = self.workspace / "tests" / "engine_test.rs"
        self.rs_test.write_text(
            "use crate::engine::ExecutionEngine;\n\n"
            "#[test]\n"
            "fn test_dispatch() {\n"
            "    let engine = ExecutionEngine::new(10);\n"
            "    assert!(engine.dispatch(\"\"));\n"
            "}\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def test_rust_symbol_scanner_raw(self) -> None:
        symbols, imports = RustSymbolScanner.scan(
            self.rs_src.read_text(encoding="utf-8"), "src/engine.rs"
        )
        names = {s["name"]: s for s in symbols}
        self.assertIn("ExecutionEngine", names)
        self.assertEqual(names["ExecutionEngine"]["kind"], "class")
        self.assertIn("dispatch", names)
        self.assertEqual(names["dispatch"]["kind"], "method")
        self.assertEqual(names["dispatch"]["class_name"], "ExecutionEngine")
        self.assertIn("initialize", names)
        self.assertEqual(names["initialize"]["kind"], "function")

    def test_rust_fault_localization_from_panic(self) -> None:
        rust_trace = (
            "thread 'test_dispatch' panicked at 'assertion failed: engine.dispatch(\"\")', src/engine.rs:10:9\n"
            "stack backtrace:\n"
            "   0: rust_begin_unwind\n"
            "   1: core::panicking::panic_fmt\n"
            "   2: my_crate::engine::ExecutionEngine::dispatch\n"
            "             at src/engine.rs:10:9\n"
            "   3: tests::engine_test::test_dispatch\n"
            "             at tests/engine_test.rs:6:5\n"
        )
        locator = SymbolLocator(self.workspace)
        candidates = locator.locate_fault(rust_trace, max_candidates=3)
        self.assertTrue(len(candidates) > 0)
        top = candidates[0]
        self.assertEqual(top.file_path, "src/engine.rs")
        self.assertEqual(top.symbol_name, "ExecutionEngine.dispatch")
        self.assertFalse(top.is_test_file)
        self.assertGreaterEqual(top.confidence, 0.90)


class TestMultiLangTestPathIsolation(unittest.TestCase):
    def test_is_any_test_path_detection(self) -> None:
        # Python
        self.assertTrue(is_any_test_path("tests/test_foo.py"))
        self.assertTrue(is_any_test_path("app/test_foo.py"))
        self.assertFalse(is_any_test_path("src/foo.py"))

        # Go
        self.assertTrue(is_any_test_path("pkg/service/order_test.go"))
        self.assertFalse(is_any_test_path("pkg/service/order.go"))

        # TypeScript / JavaScript
        self.assertTrue(is_any_test_path("src/components/button.test.tsx"))
        self.assertTrue(is_any_test_path("src/services/api.spec.ts"))
        self.assertTrue(is_any_test_path("src/__tests__/utils.js"))
        self.assertFalse(is_any_test_path("src/components/button.tsx"))
        self.assertFalse(is_any_test_path("src/services/api.ts"))

        # Rust
        self.assertTrue(is_any_test_path("tests/integration_test.rs"))
        self.assertTrue(is_any_test_path("src/tests.rs"))
        self.assertFalse(is_any_test_path("src/lib.rs"))

        # Ruby / Other
        self.assertTrue(is_any_test_path("spec/models/user_spec.rb"))


if __name__ == "__main__":
    unittest.main()
