#!/usr/bin/env python3
"""Offline tlc_trace tests on synthetic TLC output."""
import unittest

import tlc_trace

LOG = r"""TLC2 Version 2.19
Error: Invariant RefsExist is violated.
Error: The behavior up to this point is:
State 1: <Initial predicate>
/\ store = [ files |-> {"a"},
  refs |-> (1 :> {"a"} @@ 2 :> {}) ]
/\ log = <<>>
/\ gc = [phase |-> "idle", root |-> "a"]

State 2: <GcSelect line 10, col 5 to line 12, col 30 of module M>
/\ store = [ files |-> {"a", "b"},
  refs |-> (1 :> {"a"} @@ 2 :> {"b"}) ]
/\ log = <<"w">>
/\ gc = [phase |-> "select", root |-> "a"]

State 3: <GcDelete line 14, col 5 to line 16, col 30 of module M>
/\ store = [ files |-> {"b"},
  refs |-> (1 :> {"a"} @@ 2 :> {"b"}) ]
/\ log = <<"w">>
/\ gc = [phase |-> "select", root |-> "a"]

12 states generated, 9 distinct states found, 2 states left on queue.
State 1: <Initial predicate>
/\ store = ignored second trace
"""


class TraceTests(unittest.TestCase):
    def test_summary_lists_changed_fields_only(self):
        lines = tlc_trace.summarize(LOG)
        self.assertEqual(lines[0], "Error: Invariant RefsExist is violated.")
        text = "\n".join(lines)
        self.assertIn('store = [files |-> {"a"}, refs |-> (1 :> {"a"} @@ 2 :> {})]', text)
        self.assertIn("  2 GcSelect", text)
        self.assertIn('store.files: {"a"} -> {"a", "b"}', text)
        self.assertIn('store.refs[2]: {} -> {"b"}', text)
        self.assertIn('log: <<>> -> <<"w">>', text)
        self.assertIn('gc.phase: "idle" -> "select"', text)
        self.assertNotIn("gc.root", text)
        self.assertIn('store.files: {"a", "b"} -> {"b"}', text)
        self.assertNotIn("ignored second trace", text)

    def test_filter_and_final_state(self):
        lines = tlc_trace.summarize(LOG, wanted={"gc"}, final=True)
        text = "\n".join(lines)
        self.assertNotIn("store", text)
        self.assertIn("(no change in shown variables)", text)
        self.assertEqual(lines[-1], '      gc = [phase |-> "select", root |-> "a"]')

    def test_values_and_fallback(self):
        value = tlc_trace.parse_value('[a |-> {2, 1}, b |-> <<TRUE, -3>>, c |-> ("k" :> 0)]')
        self.assertEqual(tlc_trace.render(value),
                         '[a |-> {1, 2}, b |-> <<TRUE, -3>>, c |-> ("k" :> 0)]')
        self.assertEqual(tlc_trace.value_of("[a |-> ]\n  broken"), "[a |-> ] broken")

    def test_single_variable_and_missing_trace(self):
        single = "State 1: <Initial predicate>\nx = 0\n\nState 2: <Inc line 3, col 1 to line 3, col 9 of module M>\nx = 1\n"
        self.assertEqual(tlc_trace.summarize(single)[-1], "      x: 0 -> 1")
        self.assertEqual(tlc_trace.summarize("Model checking completed.")[-1],
                         "No counterexample trace found.")


if __name__ == "__main__":
    unittest.main()
