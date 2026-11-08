import unittest
from types import SimpleNamespace

from orchestration.fixture_outward_responder import select_fixture_response


class StubModel:
    def __init__(self, output):
        self.output = output
        self.calls = []

    def ask(self, task, system, payload):
        self.calls.append((task, system, payload))
        return self.output


class FixtureOutwardResponderTests(unittest.TestCase):
    def setUp(self):
        self.request = SimpleNamespace(
            request_id="RQ-1", request_kind="document_request", wording="Valve inspection",
            target_ids=("H-1",), source_scope=("maintenance",), entity_ids=("V-1",),
            time_scope="Day 0", record_types=("inspection",),
        )
        self.slots = [{"slot_id": "S-1", "description": "Inspection findings"}]
        self.items = [{"item_id": "E08", "text": "Valve inspection report"}]

    def test_returns_only_valid_fixture_and_slot_ids(self):
        model = StubModel({"selected_item_ids": ["E08"], "answered_slot_ids": ["S-1"]})
        result = select_fixture_response(model, self.request, self.slots, self.items)
        self.assertEqual(result, {"selected_item_ids": ["E08"], "answered_slot_ids": ["S-1"]})
        self.assertEqual(model.calls[0][0], "synthetic_custodian_response")

    def test_empty_result_is_valid(self):
        model = StubModel({"selected_item_ids": [], "answered_slot_ids": []})
        self.assertEqual(select_fixture_response(model, self.request, self.slots, self.items),
                         {"selected_item_ids": [], "answered_slot_ids": []})

    def test_rejects_unknown_document_id(self):
        model = StubModel({"selected_item_ids": ["REAL-RECORD"], "answered_slot_ids": []})
        with self.assertRaisesRegex(ValueError, "unknown or duplicate fixture item ID"):
            select_fixture_response(model, self.request, self.slots, self.items)

    def test_rejects_unknown_slot_and_answer_without_material(self):
        model = StubModel({"selected_item_ids": [], "answered_slot_ids": ["S-OTHER"]})
        with self.assertRaisesRegex(ValueError, "unknown or duplicate request slot ID"):
            select_fixture_response(model, self.request, self.slots, self.items)

    def test_rejects_extra_fields_in_model_reply(self):
        model = StubModel({"selected_item_ids": [], "answered_slot_ids": [], "answer": "invented"})
        with self.assertRaisesRegex(ValueError, "only selected_item_ids and answered_slot_ids"):
            select_fixture_response(model, self.request, self.slots, self.items)


if __name__ == "__main__":
    unittest.main()
