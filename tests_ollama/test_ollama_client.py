from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
from threading import Thread
import unittest
from unittest.mock import patch

from shared.llm.factory import create_model_client
from shared.llm.ollama_client import OllamaChatModel
from shared.llm.client import ModelFailure

COMBINED_ROOT = Path(__file__).resolve().parents[1]
V3_ROOT = COMBINED_ROOT / "V3_Neurosymbolic_Inspired"
if str(V3_ROOT) in sys.path:
    sys.path.remove(str(V3_ROOT))
sys.path.insert(0, str(V3_ROOT))
from orchestration.v3_runtime import V3CaseRuntime


class FakeOllamaHandler(BaseHTTPRequestHandler):
    models = ["qwen-test:latest"]
    replies: list[str] = []
    bodies: list[dict] = []

    def log_message(self, *_args):
        pass

    def do_GET(self):
        if self.path != "/api/tags":
            self.send_error(404)
            return
        body = json.dumps({"models": [{"name": name} for name in self.models]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        request = json.loads(self.rfile.read(length))
        self.bodies.append(request)
        reply = self.replies.pop(0)
        fields = {"content": reply} if isinstance(reply, str) else dict(reply)
        extra = {} if isinstance(reply, str) else {"done": True, "done_reason": fields.pop("done_reason", "stop")}
        message = {"role": "assistant", **fields}
        body = json.dumps({"message": message, **extra,
                           "prompt_eval_count": 12, "eval_count": 5,
                           "total_duration": 1000}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class OllamaAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeOllamaHandler)
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def setUp(self):
        FakeOllamaHandler.models = ["qwen-test:latest"]
        FakeOllamaHandler.replies = []
        FakeOllamaHandler.bodies = []

    def test_lists_and_checks_exact_local_model(self):
        client = OllamaChatModel("qwen-test:latest", self.base_url, timeout=2)
        self.assertEqual(client.check_model(), ("qwen-test:latest",))

    def test_native_chat_payload_and_usage(self):
        FakeOllamaHandler.replies = ['{"answer":"ok"}']
        client = create_model_client(
            provider="ollama_native", model="qwen-test:latest", base_url=self.base_url,
            timeout=2, response_format="json_object", retries=0, temperature=0.2,
        )

        result = client.ask("unit-test", "Return JSON.", {"question": "test"})

        self.assertEqual(result, {"answer": "ok"})
        body = FakeOllamaHandler.bodies[0]
        self.assertEqual(body["model"], "qwen-test:latest")
        self.assertFalse(body["stream"])
        self.assertEqual(body["format"], "json")
        self.assertEqual(body["options"]["temperature"], 0.2)
        self.assertEqual(client.calls[0].provider, "ollama_native")
        self.assertTrue(client.calls[0].actual_call_performed)
        self.assertEqual(client.calls[0].tokens["eval_count"], 5)

    def test_factory_enables_native_json_mode_for_legacy_off_setting(self):
        FakeOllamaHandler.replies = ['{"answer":"ok"}']
        client = create_model_client(
            provider="ollama_native", model="qwen-test:latest", base_url=self.base_url,
            timeout=2, response_format="off", retries=0,
        )

        self.assertEqual(client.ask("legacy-profile", "Return JSON.", {}), {"answer": "ok"})
        self.assertEqual(FakeOllamaHandler.bodies[0]["format"], "json")

    def test_invalid_json_gets_one_bounded_format_retry(self):
        FakeOllamaHandler.replies = ["not-json", '{"fixed":true}']
        client = OllamaChatModel("qwen-test:latest", self.base_url, timeout=2, retries=1)

        self.assertEqual(client.ask("repair", "Return JSON.", {}), {"fixed": True})
        self.assertEqual(client.http_attempts, 2)
        self.assertIn("not a valid JSON object", FakeOllamaHandler.bodies[1]["messages"][-1]["content"])

    SCHEMA = {
        "type": "object", "additionalProperties": False, "required": ["answer", "n"],
        "properties": {"answer": {"enum": ["yes", "no"]}, "n": {"type": "integer"},
                       "tag": {"$ref": "#/$defs/tag"}},
        "$defs": {"tag": {"type": ["string", "null"]}},
    }

    def _schema_client(self, **kwargs):
        return OllamaChatModel("qwen-test:latest", self.base_url, timeout=2, retries=0,
                               task_schemas={"typed": self.SCHEMA}, **kwargs)

    def test_schema_is_sent_as_format_and_raw_fields_are_captured(self):
        FakeOllamaHandler.replies = [{"content": '{"answer":"yes","n":1}', "thinking": "weighing it",
                                      "done_reason": "stop"}]
        client = self._schema_client()

        self.assertEqual(client.ask("typed", "Return JSON.", {}), {"answer": "yes", "n": 1})
        self.assertEqual(FakeOllamaHandler.bodies[0]["format"], self.SCHEMA)
        raw = client.raw_responses[0]
        self.assertEqual(raw["outcome"], "accepted")
        self.assertEqual(raw["format"], "schema")
        self.assertEqual(raw["response"]["message"]["thinking"], "weighing it")
        self.assertEqual(raw["response"]["done_reason"], "stop")
        self.assertEqual(raw["thinking_chars"], len("weighing it"))

    def test_num_ctx_is_sent_only_when_configured(self):
        FakeOllamaHandler.replies = ['{"x":1}', '{"x":2}']
        OllamaChatModel("qwen-test:latest", self.base_url, timeout=2).ask("a", "s", {})
        client = OllamaChatModel("qwen-test:latest", self.base_url, timeout=2, num_ctx=16384)
        client.ask("a", "s", {})

        self.assertNotIn("num_ctx", FakeOllamaHandler.bodies[0]["options"])
        self.assertEqual(FakeOllamaHandler.bodies[1]["options"]["num_ctx"], 16384)
        self.assertEqual(client.raw_responses[0]["num_ctx"], 16384)

    def test_untyped_tasks_keep_plain_json_mode(self):
        FakeOllamaHandler.replies = ['{"x":1}']
        self.assertEqual(self._schema_client().ask("other", "Return JSON.", {}), {"x": 1})
        self.assertEqual(FakeOllamaHandler.bodies[0]["format"], "json")

    def test_schema_violation_gets_feedback_retry_then_succeeds(self):
        FakeOllamaHandler.replies = ['{"answer":"maybe","n":1,"extra":true}', '{"answer":"no","n":2}']
        client = self._schema_client()

        self.assertEqual(client.ask("typed", "Return JSON.", {}), {"answer": "no", "n": 2})
        self.assertEqual(client.http_attempts, 2)
        retry = FakeOllamaHandler.bodies[1]["messages"]
        self.assertIn("maybe", retry[-2]["content"])
        self.assertIn("unexpected field 'extra'", retry[-1]["content"])
        self.assertEqual([r["outcome"] for r in client.raw_responses], ["schema_invalid", "accepted"])

    def test_schema_retries_are_bounded_and_failures_are_still_rejected(self):
        FakeOllamaHandler.replies = ['{"answer":"no"}'] * 5
        client = self._schema_client(schema_retries=2)

        with self.assertRaisesRegex(ModelFailure, "violated the task schema"):
            client.ask("typed", "Return JSON.", {})
        self.assertEqual(client.http_attempts, 3)
        self.assertEqual(len(FakeOllamaHandler.replies), 2)
        self.assertEqual(client.calls, [])
        self.assertEqual([r["outcome"] for r in client.raw_responses], ["schema_invalid"] * 3)

    def test_reasoning_only_reply_is_captured_and_rejected(self):
        FakeOllamaHandler.replies = [{"content": "", "thinking": "long chain " * 50,
                                      "done_reason": "length"}] * 2
        client = self._schema_client(schema_retries=1)

        with self.assertRaisesRegex(ModelFailure, "done_reason='length'"):
            client.ask("typed", "Return JSON.", {})
        first = client.raw_responses[0]
        self.assertEqual(first["outcome"], "empty_content")
        self.assertEqual(first["content_chars"], 0)
        self.assertGreater(first["thinking_chars"], 0)
        self.assertEqual(first["response"]["done_reason"], "length")
        self.assertIn("not in reasoning", FakeOllamaHandler.bodies[1]["messages"][-1]["content"])

    def test_schema_errors_checks_enum_type_refs_and_nested_paths(self):
        from shared.llm.ollama_client import schema_errors

        self.assertEqual(schema_errors({"answer": "yes", "n": 1, "tag": None}, self.SCHEMA), [])
        errors = schema_errors({"answer": "yes", "n": True, "tag": 3}, self.SCHEMA)
        self.assertIn("$.n: expected integer, got bool", errors)
        self.assertIn("$.tag: expected string|null, got int", errors)

    def test_sahs_format_schema_pins_version_and_rejects_missing_fields(self):
        from shared.llm.ollama_client import schema_errors
        from sahs.prompt_builder import PROPOSAL_FORMAT_SCHEMA

        ok = {"schema_version": "1", "proposed_propositions": [], "proposed_rules": [],
              "clarification_items": [], "information_gaps": []}
        self.assertEqual(schema_errors(ok, PROPOSAL_FORMAT_SCHEMA), [])
        self.assertTrue(schema_errors({**ok, "schema_version": "2"}, PROPOSAL_FORMAT_SCHEMA))
        wrong_shape = {"case_id": "case:7", "sources": []}
        self.assertTrue(any("missing required field 'schema_version'" in e
                            for e in schema_errors(wrong_shape, PROPOSAL_FORMAT_SCHEMA)))

    def test_hera_schemas_accept_validator_shapes_and_reject_observed_failure(self):
        from hera1.schemas import COMPARE_STATEMENTS_SCHEMA, EXTRACT_STATEMENTS_SCHEMA
        from shared.llm.ollama_client import schema_errors

        statement = {"statement_id": "s1", "material_id": "L1", "source_id": "D1",
                     "source_version": "v1", "representation_id": "R1", "quote": "A leak.",
                     "start_offset": 0, "kind": "general_mechanism", "modality": "conditional",
                     "scope": "general", "timing": "unspecified"}
        self.assertEqual(schema_errors({"statements": [statement]}, EXTRACT_STATEMENTS_SCHEMA), [])
        # The gpt-oss reply that HERA rejected: `exact_quote` for `quote`, null timing.
        observed = {k: v for k, v in statement.items() if k != "quote"}
        observed.update(exact_quote="A leak.", timing=None)
        errors = schema_errors({"statements": [observed]}, EXTRACT_STATEMENTS_SCHEMA)
        self.assertIn("$.statements[0]: missing required field 'quote'", errors)
        self.assertIn("$.statements[0]: unexpected field 'exact_quote'", errors)
        self.assertIn("$.statements[0].timing: expected string, got NoneType", errors)

        finding = {"relation": "does_not_address", "statement_ids": ["s1"], "rationale": "r",
                   "inference_bridge": "", "relevance_status": "direct",
                   "scope_alignment": "match", "time_alignment": "unknown"}
        comparison = {"parts": [{"part_id": "p1", "findings": [finding]}]}
        self.assertEqual(schema_errors(comparison, COMPARE_STATEMENTS_SCHEMA), [])
        comparison["parts"][0]["findings"][0]["relation"] = "proves"
        self.assertTrue(schema_errors(comparison, COMPARE_STATEMENTS_SCHEMA))

    def test_request_review_schema_rejects_the_observed_empty_proportionality(self):
        from hera1.schemas import REVIEW_REQUEST_SCHEMA
        from shared.llm.ollama_client import schema_errors

        reply = {"disposition": "not_eligible", "rationale": "r", "existing_evidence_status": "resolved",
                 "existing_evidence_rationale": "cl:53e7 provides it.", "proportionality": "proportionate",
                 "revision_feedback": "", "revised_request": ""}
        self.assertEqual(schema_errors(reply, REVIEW_REQUEST_SCHEMA), [])
        # The gpt-oss reply HERA rejected: proportionality left as an empty string.
        errors = schema_errors({**reply, "proportionality": ""}, REVIEW_REQUEST_SCHEMA)
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("$.proportionality: '' is not one of"))
        # Missing and extra fields are both refused.
        partial = {k: v for k, v in reply.items() if k != "revised_request"}
        self.assertIn("$: missing required field 'revised_request'", schema_errors(partial, REVIEW_REQUEST_SCHEMA))
        self.assertIn("$: unexpected field 'reason'", schema_errors({**reply, "reason": "x"}, REVIEW_REQUEST_SCHEMA))

    def test_ollama_runtime_registers_sahs_and_hera_schemas(self):
        from types import SimpleNamespace

        with patch("orchestration.v3_runtime.V3PackageBridge.from_models",
                   side_effect=lambda workflow, **_kwargs: SimpleNamespace(workflow=workflow)):
            on = V3CaseRuntime.from_ollama("c", model="qwen-test:latest", base_url=self.base_url,
                                           enable_intake_interpreter=False, enable_lead_semantics=False)
            off = V3CaseRuntime.from_ollama("c", model="qwen-test:latest", base_url=self.base_url,
                                            structured_output=False, enable_intake_interpreter=False,
                                            enable_lead_semantics=False)
        self.assertEqual(set(on.model_client.task_schemas),
                         {"sahs_proposal", "extract_statements", "compare_statements", "review_request"})
        self.assertEqual(off.model_client.task_schemas, {})

    def test_hera_rejection_feedback_is_delivered_as_chat_turns(self):
        FakeOllamaHandler.replies = ['{"x":1}']
        client = OllamaChatModel("qwen-test:latest", self.base_url, timeout=2, retries=0)
        prior = {"proportionality": ""}

        client.ask("review_request", "Return JSON.", {"request": "r1", "previous_response_rejected": {
            "reason": "request proportionality is invalid", "previous_reply": prior,
            "instruction": "Return one corrected JSON object that follows the task instructions exactly."}})

        roles = [m["role"] for m in FakeOllamaHandler.bodies[0]["messages"]]
        system, user, assistant, rejection = FakeOllamaHandler.bodies[0]["messages"]
        self.assertEqual(roles, ["system", "user", "assistant", "user"])
        self.assertEqual(json.loads(user["content"]), {"request": "r1"})   # key removed from the payload
        self.assertEqual(json.loads(assistant["content"]), prior)
        self.assertIn("request proportionality is invalid", rejection["content"])
        self.assertIn("corrected JSON object", rejection["content"])

    def test_a_real_hera_retry_reaches_the_model_as_chat_turns_for_the_rejected_step_only(self):
        from hera1 import AssessmentTask, EvidenceMaterial, Hera1Engine
        from hera1.config import AssessorConfig
        from hera1.contracts import VersionSnapshot

        text = "A leaking valve can cause pressure loss."

        class Versions:
            def read(self, case_id, material_ids):
                return VersionSnapshot("case:s1", "b1", {"D1": "v1"})

        task = AssessmentTask(
            schema_version="1", task_id="t1", work_item_id="w1", event_id="e1", case_id="c1",
            case_snapshot_id="case:s1", board_version="b1", task_kind="evidence_review",
            sender_role="evidence_worker", sender_id="ew7",
            materials=(EvidenceMaterial("L1", "D1", "v1", "R1", text, "manual", 0, {}),),
            hypothesis={"hypothesis_id": "h1", "parts": [
                {"part_id": "p1", "claim_type": "incident_causal_link", "text": "The leak caused pressure loss."}]})
        extraction = {"statements": [{"statement_id": "s1", "material_id": "L1", "source_id": "D1",
            "source_version": "v1", "representation_id": "R1", "quote": text, "start_offset": 0,
            "kind": "general_mechanism", "modality": "conditional", "scope": "general", "timing": "unspecified"}]}

        def comparison(bridge):
            return {"parts": [{"part_id": "p1", "findings": [{
                "relation": "supports", "statement_ids": ["s1"], "rationale": "Describes the mechanism.",
                "inference_bridge": bridge, "relevance_status": "direct",
                "scope_alignment": "match", "time_alignment": "match"}]}]}

        FakeOllamaHandler.replies = [json.dumps(extraction), json.dumps(comparison("")),
                                     json.dumps(extraction), json.dumps(comparison("The mechanism explains the loss."))]
        client = OllamaChatModel("qwen-test:latest", self.base_url, timeout=2, retries=0)
        hera = Hera1Engine(client, Versions(), config=AssessorConfig(max_output_retries=1))

        result = hera.run(task)

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.model_calls, 4)
        bodies = FakeOllamaHandler.bodies
        self.assertEqual([len(b["messages"]) for b in bodies], [2, 2, 2, 4])  # only the compare retry has turns
        rejected_compare = bodies[3]["messages"]
        self.assertNotIn("previous_response_rejected", rejected_compare[1]["content"])
        self.assertEqual(json.loads(rejected_compare[2]["content"]), comparison(""))
        self.assertIn("inference bridge", rejected_compare[3]["content"])

    def test_missing_model_reports_installed_tags(self):
        client = OllamaChatModel("missing:latest", self.base_url, timeout=2)
        with self.assertRaisesRegex(ModelFailure, "qwen-test:latest"):
            client.check_model()

    def test_v3_runtime_factory_uses_native_adapter_without_calling_server(self):
        from types import SimpleNamespace

        with patch("orchestration.v3_runtime.V3PackageBridge.from_models",
                   side_effect=lambda workflow, **_kwargs: SimpleNamespace(workflow=workflow)):
            runtime = V3CaseRuntime.from_ollama(
                "case-test", model="qwen-test:latest", base_url=self.base_url,
                enable_intake_interpreter=False, enable_lead_semantics=False,
            )

        self.assertIsInstance(runtime.model_client, OllamaChatModel)
        self.assertEqual(runtime.model_client.provider, "ollama_native")
        self.assertEqual(runtime.model_client.model, "qwen-test:latest")


if __name__ == "__main__":
    unittest.main()
