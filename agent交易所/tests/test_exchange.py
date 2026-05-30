"""End-to-end tests for the trusted capability trading layer."""
import unittest

from fastapi.testclient import TestClient

from a2a_exchange.app import create_app
from a2a_exchange.credit import MockCreditGuard


GOOD_ARTIFACT = """
def run(input):
    text = input["text"]
    return {"upper": text.upper()}
""".strip()


BAD_ARTIFACT = """
def run(input):
    return {"upper": "wrong"}
""".strip()


MALFORMED_ARTIFACT = """
def not_run(input):
    return input
""".strip()


def register_payload(artifact=GOOD_ARTIFACT, price=500, expected=None):
    expected_output = expected or {"upper": "HELLO"}
    return {
        "manifest": {
            "name": "uppercase-tool",
            "interface": {
                "input_schema": {
                    "type": "object",
                    "properties": {"text": {"type": "string"}},
                    "required": ["text"],
                },
                "output_schema": {
                    "type": "object",
                    "properties": {"upper": {"type": "string"}},
                    "required": ["upper"],
                },
            },
            "price_tokens": price,
            "permission_policy": {"network": False, "filesystem": False},
            "description": "Converts text to uppercase.",
        },
        "artifact": artifact,
        "eval_pack": {
            "cases": [
                {
                    "name": "hello uppercase",
                    "input": {"text": "hello"},
                    "expected_output": expected_output,
                }
            ]
        },
        "sandbox_policy": {"network": False, "timeout_ms": 1000, "max_cases": 5},
    }


class TrustedCapabilityFlowTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(create_app())

    def test_register_success_creates_scorecard(self):
        resp = self.client.post("/register", json=register_payload())
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertEqual(body["verification_status"], "verified")
        self.assertTrue(body["scorecard"]["verified"])
        self.assertEqual(body["scorecard"]["cases_total"], 1)
        self.assertEqual(body["scorecard"]["cases_passed"], 1)
        self.assertEqual(body["scorecard"]["pass_rate"], 1.0)
        self.assertEqual(len(body["scorecard"]["artifact_sha256"]), 64)

    def test_failing_eval_is_not_discoverable_by_default(self):
        resp = self.client.post(
            "/register",
            json=register_payload(artifact=BAD_ARTIFACT),
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["verification_status"], "failed")

        discover = self.client.post("/discover", json={})
        self.assertEqual(discover.status_code, 200, discover.text)
        self.assertEqual(discover.json(), [])

    def test_malformed_artifact_rejected(self):
        resp = self.client.post(
            "/register",
            json=register_payload(artifact=MALFORMED_ARTIFACT),
        )
        self.assertEqual(resp.status_code, 422, resp.text)

    def test_discover_filters_and_never_returns_artifact(self):
        self.client.post("/register", json=register_payload(price=500))
        resp = self.client.post(
            "/discover",
            json={
                "required_input_keys": ["text"],
                "max_price": 1000,
                "min_pass_rate": 1.0,
                "max_latency_ms": 1000,
            },
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        hits = resp.json()
        self.assertEqual(len(hits), 1)
        self.assertNotIn("artifact", hits[0])
        self.assertEqual(hits[0]["name"], "uppercase-tool")
        self.assertTrue(hits[0]["scorecard"]["verified"])

        too_cheap = self.client.post("/discover", json={"max_price": 100})
        self.assertEqual(too_cheap.json(), [])

    def test_quote_locks_price_hash_and_scorecard(self):
        registered = self.client.post("/register", json=register_payload()).json()
        quote = self.client.post(
            "/quote",
            json={"buyer_agent_id": "buyer-1", "capability_id": registered["capability_id"]},
        )
        self.assertEqual(quote.status_code, 200, quote.text)
        body = quote.json()
        self.assertEqual(body["buyer_agent_id"], "buyer-1")
        self.assertEqual(body["capability_id"], registered["capability_id"])
        self.assertEqual(body["price_tokens"], 500)
        self.assertEqual(
            body["artifact_sha256"],
            registered["scorecard"]["artifact_sha256"],
        )
        self.assertEqual(body["scorecard_snapshot"]["pass_rate"], 1.0)

    def test_checkout_requires_quote_and_releases_artifact_after_debit(self):
        registered = self.client.post("/register", json=register_payload()).json()
        quote = self.client.post(
            "/quote",
            json={"buyer_agent_id": "buyer-1", "capability_id": registered["capability_id"]},
        ).json()

        checkout = self.client.post("/checkout", json={"quote_id": quote["quote_id"]})
        self.assertEqual(checkout.status_code, 200, checkout.text)
        body = checkout.json()
        self.assertEqual(body["status"], "unlocked")
        self.assertEqual(body["artifact"], GOOD_ARTIFACT)
        self.assertEqual(body["price_paid"], 500)
        self.assertEqual(
            body["remaining_balance"],
            MockCreditGuard.INITIAL_CREDIT - 500,
        )
        self.assertTrue(body["escrow_id"])

        missing = self.client.post("/checkout", json={"quote_id": "missing"})
        self.assertEqual(missing.status_code, 404)

    def test_settle_releases_or_disputes_escrow(self):
        registered = self.client.post("/register", json=register_payload()).json()
        quote = self.client.post(
            "/quote",
            json={"buyer_agent_id": "buyer-1", "capability_id": registered["capability_id"]},
        ).json()
        checkout = self.client.post("/checkout", json={"quote_id": quote["quote_id"]}).json()

        released = self.client.post(
            "/settle",
            json={
                "buyer_agent_id": "buyer-1",
                "escrow_id": checkout["escrow_id"],
                "accepted": True,
            },
        )
        self.assertEqual(released.status_code, 200, released.text)
        self.assertEqual(released.json()["status"], "released")

    def test_existing_quote_survives_later_price_change(self):
        first = self.client.post("/register", json=register_payload(price=500)).json()
        quote = self.client.post(
            "/quote",
            json={"buyer_agent_id": "buyer-1", "capability_id": first["capability_id"]},
        ).json()

        self.client.post("/register", json=register_payload(price=900))

        checkout = self.client.post("/checkout", json={"quote_id": quote["quote_id"]})
        self.assertEqual(checkout.status_code, 200, checkout.text)
        self.assertEqual(checkout.json()["price_paid"], 500)


if __name__ == "__main__":
    unittest.main(verbosity=2)
