"""T08 — payment gateway seam (ADR-007).

`PaymentGateway` is the interface the router programs against. Production
uses `RazorpayGateway` (test-mode keys from `.env`); tests inject
`FakeGateway`, which honors the same signature contract without money.
"""

import hashlib
import hmac
from typing import Protocol

from app.config import settings


class PaymentGateway(Protocol):
    # Which checkout the frontend must open: "demo" (in-app fake) or
    # "razorpay_test" (real Razorpay account in test mode — never live money).
    checkout_mode: str

    def create_order(self, booking_ref: str, amount: int) -> dict:
        ...

    def verify_signature(self, order_id: str, payment_id: str, signature: str) -> bool:
        ...


class FakeGateway:
    """Test double: deterministic orders, non-transactional by design.

    A deployment without a gateway must never be able to mark a booking paid
    or issue a ticket, so verification always fails here. Suites that exercise
    the full paid path use `RazorpayGateway` with test-mode keys and stubbed
    outbound HTTP instead.
    """

    checkout_mode = "demo"

    def create_order(self, booking_ref: str, amount: int) -> dict:
        return {
            "order_id": deterministic_fake_order_id(booking_ref),
            "amount": amount,
            "currency": "INR",
        }

    def verify_signature(self, order_id: str, payment_id: str, signature: str) -> bool:
        return False


def deterministic_fake_order_id(booking_ref: str) -> str:
    digest = hashlib.sha256(booking_ref.encode()).hexdigest()[:12]
    return f"order_{digest}"


_TEST_KEY_PREFIX = "rzp_test_"


class RazorpayGateway:
    """Real Razorpay gateway. Test-mode keys only (ADR-007): a live key would
    move real money, so constructing one with anything but a configured
    `rzp_test_` key id + secret fails fast, before any network call."""

    checkout_mode = "razorpay_test"

    def __init__(self, key_id: str | None = None, key_secret: str | None = None):
        self.key_id = key_id or settings.razorpay_key_id
        self.key_secret = key_secret or settings.razorpay_key_secret
        if not (
            isinstance(self.key_id, str)
            and self.key_id.startswith(_TEST_KEY_PREFIX)
            and len(self.key_id) > len(_TEST_KEY_PREFIX)
        ):
            raise ValueError(
                "Razorpay gateway requires a configured test-mode key_id "
                f"({_TEST_KEY_PREFIX}...); refusing live or unknown keys"
            )
        if not self.key_secret:
            raise ValueError(
                "Razorpay gateway requires a configured test-mode key_secret"
            )

    def create_order(self, booking_ref: str, amount: int) -> dict:
        import requests

        response = requests.post(
            "https://api.razorpay.com/v1/orders",
            auth=(self.key_id, self.key_secret),
            json={
                "amount": amount * 100,
                "currency": "INR",
                "receipt": booking_ref,
            },
            timeout=15,
        )
        response.raise_for_status()
        body = response.json()
        return {
            "order_id": body["id"],
            "amount": body["amount"] // 100,
            "currency": body.get("currency", "INR"),
        }

    def verify_signature(self, order_id: str, payment_id: str, signature: str) -> bool:
        expected = hmac.new(
            self.key_secret.encode(),
            f"{order_id}|{payment_id}".encode(),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)


_gateway: PaymentGateway | None = None


def get_gateway() -> PaymentGateway:
    global _gateway
    if _gateway is None:
        if settings.razorpay_key_id or settings.razorpay_key_secret:
            # Any configured Razorpay key must be a valid test-mode pair;
            # RazorpayGateway raises ValueError for live/unknown/incomplete
            # configuration before any network call can happen.
            _gateway = RazorpayGateway()
        else:
            _gateway = FakeGateway()
    return _gateway


def set_gateway(gateway: PaymentGateway) -> None:
    global _gateway
    _gateway = gateway


def use_live_gateway_if_configured() -> None:
    if settings.razorpay_key_id or settings.razorpay_key_secret:
        set_gateway(RazorpayGateway())
