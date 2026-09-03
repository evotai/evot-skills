#!/usr/bin/env python3
import io
import json
import unittest
import urllib.error
from unittest import mock

import query

CREDS = {
    "org": "acme",
    "token": "t0ken",
    "host": "api.databend.com",
    "port": None,
    "warehouse": "default",
}


def http_error(code, body):
    return urllib.error.HTTPError(
        "https://api.databend.com/v1/query", code, "err", {}, io.BytesIO(body.encode())
    )


class ParseDsnTest(unittest.TestCase):
    def test_full_dsn(self):
        creds = query.parse_dsn("bendcloud://acme:t0ken@api.databend.com/wh1")
        self.assertEqual(creds["org"], "acme")
        self.assertEqual(creds["token"], "t0ken")
        self.assertEqual(creds["host"], "api.databend.com")
        self.assertEqual(creds["warehouse"], "wh1")

    def test_warehouse_and_host_default(self):
        creds = query.parse_dsn("bendcloud://acme:t0ken@")
        self.assertEqual(creds["host"], query.DEFAULT_HOST)
        self.assertEqual(creds["warehouse"], query.DEFAULT_WAREHOUSE)

    def test_databend_scheme_allowed(self):
        self.assertEqual(query.parse_dsn("databend://a:b@h/w")["org"], "a")

    def test_percent_escapes_are_decoded(self):
        creds = query.parse_dsn("bendcloud://acme:ab%40c%2Fd@api.databend.com/w")
        self.assertEqual(creds["token"], "ab@c/d")

    def test_port_is_kept(self):
        self.assertEqual(query.parse_dsn("bendcloud://a:b@localhost:8000/w")["port"], 8000)

    def test_rejects_bad_scheme_and_missing_parts(self):
        for dsn in ("https://a:b@h/w", "a:b@h/w", "bendcloud://acme@h/w", "bendcloud://:t@h/w"):
            with self.assertRaises(query.ConfigError):
                query.parse_dsn(dsn)


class SelectDsnTest(unittest.TestCase):
    def test_plain_variable(self):
        self.assertEqual(query.select_dsn({"BENDCLOUD_DSN": "dsn0"}), "dsn0")

    def test_named_target_exact_and_normalized(self):
        env = {"BENDCLOUD_DSN_PROD": "p", "BENDCLOUD_DSN_AVIA_ADMIN": "a"}
        self.assertEqual(query.select_dsn(env, "PROD"), "p")
        self.assertEqual(query.select_dsn(env, "avia-admin"), "a")

    def test_plain_wins_over_targets(self):
        env = {"BENDCLOUD_DSN": "plain", "BENDCLOUD_DSN_PROD": "p"}
        self.assertEqual(query.select_dsn(env), "plain")

    def test_sole_target_is_implicit(self):
        self.assertEqual(query.select_dsn({"BENDCLOUD_DSN_ONLY": "o"}), "o")

    def test_ambiguous_targets_are_listed(self):
        env = {"BENDCLOUD_DSN_A": "a", "BENDCLOUD_DSN_B": "b"}
        with self.assertRaises(query.ConfigError) as raised:
            query.select_dsn(env)
        self.assertIn("--target", str(raised.exception))
        self.assertIn("A, B", str(raised.exception))

    def test_unknown_target_lists_choices(self):
        with self.assertRaises(query.ConfigError) as raised:
            query.select_dsn({"BENDCLOUD_DSN_A": "a"}, "nope")
        self.assertIn("A", str(raised.exception))

    def test_blank_values_are_ignored(self):
        with self.assertRaises(query.ConfigError) as raised:
            query.select_dsn({"BENDCLOUD_DSN": "   "})
        self.assertIn("/env set", str(raised.exception))


class RequestTest(unittest.TestCase):
    def send(self, opener, url="https://api.databend.com/v1/query", payload=None):
        with mock.patch.object(query.urllib.request, "urlopen", opener):
            return query.request(url, {"X-DatabendCloud-Org": "acme"}, payload, 5)

    def test_sets_non_python_user_agent(self):
        seen = {}

        def opener(req, timeout=None):
            seen["ua"] = req.get_header("User-agent")
            seen["method"] = req.get_method()
            return io.BytesIO(b'{"id":"q"}')

        self.assertEqual(self.send(opener, payload={"sql": "SELECT 1"}), {"id": "q"})
        self.assertEqual(seen["method"], "POST")
        self.assertEqual(seen["ua"], query.USER_AGENT)
        self.assertNotIn("python", seen["ua"].lower())

    def test_get_without_payload_keeps_user_agent(self):
        seen = {}

        def opener(req, timeout=None):
            seen["ua"] = req.get_header("User-agent")
            seen["method"] = req.get_method()
            return io.BytesIO(b"{}")

        self.send(opener)
        self.assertEqual(seen["method"], "GET")
        self.assertEqual(seen["ua"], query.USER_AGENT)

    def test_json_error_body_is_returned_for_envelope_handling(self):
        def opener(req, timeout=None):
            raise http_error(400, '{"error":{"kind":"BadSQL","message":"nope"}}')

        self.assertEqual(self.send(opener)["error"]["kind"], "BadSQL")

    def test_non_json_error_body_raises_with_status(self):
        def opener(req, timeout=None):
            raise http_error(403, "error code: 1010")

        with self.assertRaises(query.QueryError) as raised:
            self.send(opener)
        self.assertIn("HTTP 403", str(raised.exception))
        self.assertIn("1010", str(raised.exception))

    def test_unreachable_host_raises(self):
        def opener(req, timeout=None):
            raise urllib.error.URLError("no route")

        with self.assertRaises(query.QueryError) as raised:
            self.send(opener)
        self.assertIn("cannot reach", str(raised.exception))


class RaiseForErrorTest(unittest.TestCase):
    def test_kind_and_code_and_string_shapes(self):
        with self.assertRaises(query.QueryError) as raised:
            query.raise_for_error({"error": {"kind": "BadSQL", "message": "boom"}})
        self.assertIn("BadSQL", str(raised.exception))

        with self.assertRaises(query.QueryError) as raised:
            query.raise_for_error({"error": {"code": 1008, "message": "no function"}})
        self.assertIn("1008", str(raised.exception))

        with self.assertRaises(query.QueryError):
            query.raise_for_error({"error": "AuthFailed"})

    def test_absent_or_null_error_passes(self):
        query.raise_for_error({"data": []})
        query.raise_for_error({"error": None})


class PaginationTest(unittest.TestCase):
    def paginate(self, pages, timeout=60):
        calls = []

        def fake(url, headers, payload=None, timeout=60):
            calls.append(url)
            return pages.pop(0) if pages else {"data": []}

        with mock.patch.object(query, "request", fake), mock.patch.object(query.time, "sleep"):
            schema, rows = query.run_once("SELECT 1", CREDS, timeout)
        return schema, rows, calls

    def test_empty_page_does_not_end_pagination(self):
        schema, rows, calls = self.paginate(
            [
                {"id": "q1", "schema": [{"name": "a", "type": "Int"}], "data": [[1]],
                 "next_uri": "/v1/query/q1/page/0"},
                {"data": [], "next_uri": "/v1/query/q1/page/0"},
                {"data": [[2]], "next_uri": "/v1/query/q1/page/1"},
                {"data": [[3]], "next_uri": "/v1/query/q1/final"},
            ]
        )
        self.assertEqual(rows, [[1], [2], [3]])
        self.assertEqual(schema[0]["name"], "a")
        self.assertTrue(calls[-1].endswith("/v1/query/q1/final"))

    def test_single_page_query_skips_polling(self):
        schema, rows, calls = self.paginate([{"id": "q", "schema": [], "data": [[1]], "next_uri": ""}])
        self.assertEqual(rows, [[1]])
        self.assertEqual(len(calls), 2)

    def test_first_page_already_final_stops(self):
        _, rows, calls = self.paginate(
            [{"id": "q", "schema": [], "data": [[1]], "next_uri": "/v1/query/q/final"}]
        )
        self.assertEqual(rows, [[1]])
        self.assertEqual(len(calls), 2)

    def test_error_on_a_later_page_propagates(self):
        with self.assertRaises(query.QueryError) as raised:
            self.paginate(
                [
                    {"id": "q", "schema": [], "data": [], "next_uri": "/v1/query/q/page/0"},
                    {"error": {"kind": "Aborted", "message": "cancelled"}},
                ]
            )
        self.assertIn("Aborted", str(raised.exception))

    def test_error_in_first_response_skips_paging(self):
        with self.assertRaises(query.QueryError):
            self.paginate([{"error": {"kind": "BadSQL", "message": "x"}}])

    def test_final_call_failure_is_ignored(self):
        def fake(url, headers, payload=None, timeout=60):
            if url.endswith("/final"):
                raise query.QueryError("final unreachable")
            return {"id": "q", "schema": [], "data": [[7]], "next_uri": ""}

        with mock.patch.object(query, "request", fake):
            _, rows = query.run_once("SELECT 7", CREDS, 60)
        self.assertEqual(rows, [[7]])

    def test_missing_query_id_skips_final(self):
        calls = []

        def fake(url, headers, payload=None, timeout=60):
            calls.append(url)
            return {"schema": [], "data": [[1]], "next_uri": ""}

        with mock.patch.object(query, "request", fake):
            query.run_once("SELECT 1", CREDS, 60)
        self.assertFalse(any(url.endswith("/final") for url in calls))

    def test_stalled_pagination_gives_up_at_the_deadline(self):
        clock = {"now": 0.0}

        def fake(url, headers, payload=None, timeout=60):
            return {"id": "q", "schema": [], "data": [], "next_uri": "/v1/query/q/page/0"}

        def advance(seconds):
            clock["now"] += seconds

        with mock.patch.object(query, "request", fake), \
                mock.patch.object(query.time, "sleep", advance), \
                mock.patch.object(query.time, "monotonic", lambda: clock["now"]):
            with self.assertRaises(query.QueryError) as raised:
                query.run_once("SELECT 1", CREDS, 1)
        self.assertIn("still paging", str(raised.exception))
        self.assertIn("q", str(raised.exception))

    def test_headers_carry_org_token_and_warehouse(self):
        seen = {}

        def fake(url, headers, payload=None, timeout=60):
            seen.update(headers)
            return {"id": "q", "schema": [], "data": [], "next_uri": ""}

        with mock.patch.object(query, "request", fake):
            query.run_once("SELECT 1", CREDS, 60)
        self.assertEqual(seen["X-DatabendCloud-Token"], "t0ken")
        self.assertEqual(seen["X-DatabendCloud-Org"], "acme")
        self.assertEqual(seen["X-DatabendCloud-Warehouse"], "default")


class RetryTest(unittest.TestCase):
    def run_with(self, outcomes):
        state = {"n": 0}

        def fake(sql, creds, timeout):
            item = outcomes[state["n"]]
            state["n"] += 1
            if isinstance(item, Exception):
                raise item
            return item

        with mock.patch.object(query, "run_once", fake), mock.patch.object(query.time, "sleep"):
            result = query.run("SELECT 1", CREDS, 60)
        return result, state["n"]

    def test_provisioning_error_is_retried(self):
        result, attempts = self.run_with(
            [query.QueryError("ProvisionWarehouseTimeout: cold"), ([], [[1]])]
        )
        self.assertEqual(result[1], [[1]])
        self.assertEqual(attempts, 2)

    def test_retries_are_bounded(self):
        with mock.patch.object(query, "run_once",
                               mock.Mock(side_effect=query.QueryError("ProvisionWarehouse: x"))) as run_once, \
                mock.patch.object(query.time, "sleep"):
            with self.assertRaises(query.QueryError):
                query.run("SELECT 1", CREDS, 60)
        self.assertEqual(run_once.call_count, 3)

    def test_non_retryable_fails_on_first_attempt(self):
        with self.assertRaises(query.QueryError):
            self.run_with([query.QueryError("BadSQL: nope")])

    def test_auth_failure_is_not_retried(self):
        with mock.patch.object(query, "run_once",
                               mock.Mock(side_effect=query.QueryError("AuthFailed"))) as run_once, \
                mock.patch.object(query.time, "sleep"):
            with self.assertRaises(query.QueryError):
                query.run("SELECT 1", CREDS, 60)
        self.assertEqual(run_once.call_count, 1)


class BaseUrlTest(unittest.TestCase):
    def test_default_and_explicit_port(self):
        self.assertEqual(query.base_url(CREDS), "https://api.databend.com")
        self.assertEqual(query.base_url({**CREDS, "host": "localhost", "port": 8000}),
                         "https://localhost:8000")


class RenderTableTest(unittest.TestCase):
    def render(self, schema, rows):
        buffer = io.StringIO()
        with mock.patch("sys.stdout", buffer):
            query.render_table(schema, rows)
        return buffer.getvalue()

    def test_nulls_widths_and_row_count(self):
        out = self.render(
            [{"name": "id", "type": "Int"}, {"name": "note", "type": "String"}],
            [[1, None], [2, "hi"]],
        )
        self.assertIn("NULL", out)
        self.assertIn("(2 rows)", out)

    def test_empty_result_reports_zero_rows(self):
        self.assertEqual(self.render([{"name": "a", "type": "Int"}], []).strip(), "(0 rows)")

    def test_utc_notice_only_when_time_columns_present(self):
        self.assertIn("UTC", self.render([{"name": "event_time", "type": "Timestamp"}], [["x"]]))
        self.assertNotIn("UTC", self.render([{"name": "id", "type": "Int"}], [[1]]))

    def test_long_values_are_truncated(self):
        out = self.render([{"name": "sql", "type": "String"}], [["x" * 200]])
        self.assertIn("...", out)
        self.assertTrue(all(len(line) < 200 for line in out.splitlines()))


class MainTest(unittest.TestCase):
    def invoke(self, argv, env, runner=None):
        out, err = io.StringIO(), io.StringIO()
        runner = runner or (lambda sql, creds, timeout: ([{"name": "a", "type": "Int"}], [[1]]))
        with mock.patch.object(query.sys, "argv", ["query.py", *argv]), \
                mock.patch.dict(query.os.environ, env, clear=True), \
                mock.patch.object(query, "run", runner), \
                mock.patch("sys.stdout", out), mock.patch("sys.stderr", err):
            code = query.main()
        return code, out.getvalue(), err.getvalue()

    def test_missing_config_exits_2_with_actionable_hint(self):
        code, _, err = self.invoke(["SELECT 1"], {})
        self.assertEqual(code, 2)
        self.assertIn("/env set BENDCLOUD_DSN=", err)

    def test_query_failure_exits_1(self):
        def boom(sql, creds, timeout):
            raise query.QueryError("AuthFailed")

        code, _, err = self.invoke(
            ["SELECT 1"], {"BENDCLOUD_DSN": "bendcloud://a:b@h/w"}, runner=boom
        )
        self.assertEqual(code, 1)
        self.assertIn("AuthFailed", err)

    def test_success_exits_0_as_table(self):
        code, out, _ = self.invoke(["SELECT 1"], {"BENDCLOUD_DSN": "bendcloud://a:b@h/w"})
        self.assertEqual(code, 0)
        self.assertIn("(1 rows)", out)

    def test_json_format_emits_schema_then_rows(self):
        code, out, _ = self.invoke(
            ["--format", "json", "SELECT 1"], {"BENDCLOUD_DSN": "bendcloud://a:b@h/w"}
        )
        lines = out.strip().splitlines()
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(lines[0])[0]["name"], "a")
        self.assertEqual(json.loads(lines[1]), [1])

    def test_warehouse_flag_overrides_the_dsn(self):
        seen = {}

        def capture(sql, creds, timeout):
            seen.update(creds)
            return [], []

        self.invoke(
            ["--warehouse", "big", "SELECT 1"],
            {"BENDCLOUD_DSN": "bendcloud://a:b@h/small"},
            runner=capture,
        )
        self.assertEqual(seen["warehouse"], "big")

    def test_target_flag_picks_the_named_dsn(self):
        seen = {}

        def capture(sql, creds, timeout):
            seen.update(creds)
            return [], []

        self.invoke(
            ["--target", "prod", "SELECT 1"],
            {"BENDCLOUD_DSN_PROD": "bendcloud://prod:tok@h/w",
             "BENDCLOUD_DSN_DEV": "bendcloud://dev:tok@h/w"},
            runner=capture,
        )
        self.assertEqual(seen["org"], "prod")


if __name__ == "__main__":
    unittest.main(verbosity=2)
