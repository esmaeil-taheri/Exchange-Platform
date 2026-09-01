"""
Unit tests for the idempotency primitives.

These cover the pieces in isolation — fingerprinting, header parsing, and the
claim/replay/conflict decision. The end-to-end proof that a duplicate order
produces one financial effect lives in
apps/exchange/tests/test_idempotency_exchange.py.
"""

from decimal import Decimal

import pytest
from django.db import transaction
from django.test import override_settings
from unittest.mock import MagicMock

from apps.accounts.models.user import CustomUser
from apps.core.exceptions.idempotency_exceptions import (
    IdempotencyKeyConflict,
    IdempotencyKeyRequired,
    IdempotentRequestInProgress,
    InvalidIdempotencyKey,
)
from apps.core.models.idempotency import IdempotencyRecord
from apps.core.services.idempotency import IdempotencyService, NullGuard
from apps.core.utils.idempotency_utils import (
    build_request_fingerprint,
    extract_idempotency_key,
)


KEY = 'a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d'


@pytest.fixture
def user(db):
    return CustomUser.objects.create(
        username='idem-user',
        phone_number='09121112233',
        last_ip_address='127.0.0.1',
    )


def _request_with(header_value):
    req = MagicMock()
    req.headers = {} if header_value is None else {'Idempotency-Key': header_value}
    return req


# ═════════════════════════════════════════════════════════════════════════════
# Fingerprinting
# ═════════════════════════════════════════════════════════════════════════════

class TestRequestFingerprint:

    def test_key_order_does_not_change_the_fingerprint(self):
        """JSON key order is a serialisation detail, not a difference in intent."""
        a = build_request_fingerprint({'asset': 'XAU18', 'amount': 5})
        b = build_request_fingerprint({'amount': 5, 'asset': 'XAU18'})
        assert a == b

    def test_equal_decimals_with_different_scale_match(self):
        """
        A retry that serialises 5.0 as 5.00 is the same request.

        Without normalisation this would raise a spurious 422 on exactly the
        retry path idempotency exists to serve.
        """
        a = build_request_fingerprint({'amount': Decimal('5.0')})
        b = build_request_fingerprint({'amount': Decimal('5.00')})
        assert a == b

    def test_different_amount_changes_the_fingerprint(self):
        a = build_request_fingerprint({'amount': Decimal('5.0')})
        b = build_request_fingerprint({'amount': Decimal('5.1')})
        assert a != b

    def test_none_and_missing_are_distinguishable(self):
        a = build_request_fingerprint({'amount': 5, 'bank_card_id': None})
        b = build_request_fingerprint({'amount': 5, 'bank_card_id': 3})
        assert a != b


# ═════════════════════════════════════════════════════════════════════════════
# Header parsing
# ═════════════════════════════════════════════════════════════════════════════

class TestKeyExtraction:

    def test_absent_header_is_allowed_by_default(self):
        """Endpoints keep their current behaviour until clients opt in."""
        assert extract_idempotency_key(_request_with(None)) is None

    def test_blank_header_is_treated_as_absent(self):
        assert extract_idempotency_key(_request_with('   ')) is None

    @override_settings(IDEMPOTENCY_REQUIRED=True)
    def test_absent_header_is_rejected_when_required(self):
        with pytest.raises(IdempotencyKeyRequired):
            extract_idempotency_key(_request_with(None))

    def test_valid_key_is_returned_stripped(self):
        assert extract_idempotency_key(_request_with(f'  {KEY} ')) == KEY

    @pytest.mark.parametrize('bad', ['short', 'has spaces here', 'x' * 65, 'drop;table'])
    def test_malformed_keys_are_rejected(self, bad):
        with pytest.raises(InvalidIdempotencyKey):
            extract_idempotency_key(_request_with(bad))


# ═════════════════════════════════════════════════════════════════════════════
# Claim / replay / conflict
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestAcquire:

    PARAMS = {'asset': 'XAU18', 'amount': Decimal('0.5')}

    def _acquire(self, user, key=KEY, params=None, external=False):
        return IdempotencyService.acquire(
            user_id=user.id,
            endpoint=IdempotencyRecord.Endpoint.SELL,
            key=key,
            params=self.PARAMS if params is None else params,
            external=external,
        )

    def test_no_key_yields_a_null_guard(self, user):
        """Without a key the call site must behave exactly as it did before."""
        guard = self._acquire(user, key=None)

        assert isinstance(guard, NullGuard)
        assert guard.replayed is False
        guard.complete({'message': 'ok'})          # no-op, must not raise
        assert IdempotencyRecord.objects.count() == 0

    def test_first_call_claims_the_key(self, user):
        guard = self._acquire(user)

        assert guard.replayed is False
        assert guard.record.status == IdempotencyRecord.Status.IN_PROGRESS

    def test_second_call_replays_the_stored_response(self, user):
        first = self._acquire(user)
        first.complete({'message': 'done'}, reference='transaction:7')

        second = self._acquire(user)

        assert second.replayed is True
        assert second.response == {'message': 'done'}
        assert second.record.reference == 'transaction:7'
        assert IdempotencyRecord.objects.count() == 1

    def test_same_key_with_different_params_is_a_conflict(self, user):
        """
        Never replay here: the client reused one key for a different request,
        and returning the first response would silently drop the second.
        """
        self._acquire(user).complete({'message': 'done'})

        with pytest.raises(IdempotencyKeyConflict):
            self._acquire(user, params={'asset': 'XAU18', 'amount': Decimal('9.9')})

    def test_key_is_scoped_per_user(self, user, db):
        other = CustomUser.objects.create(
            username='other', phone_number='09129998877', last_ip_address='127.0.0.1')
        self._acquire(user).complete({'message': 'mine'})

        guard = IdempotencyService.acquire(
            user_id=other.id,
            endpoint=IdempotencyRecord.Endpoint.SELL,
            key=KEY,
            params=self.PARAMS,
        )

        assert guard.replayed is False

    def test_key_is_scoped_per_endpoint(self, user):
        self._acquire(user).complete({'message': 'sell'})

        guard = IdempotencyService.acquire(
            user_id=user.id,
            endpoint=IdempotencyRecord.Endpoint.BUY,
            key=KEY,
            params=self.PARAMS,
        )

        assert guard.replayed is False

    def test_in_progress_external_claim_rejects_a_concurrent_request(self, user):
        self._acquire(user, external=True)          # claimed, never completed

        with pytest.raises(IdempotentRequestInProgress):
            self._acquire(user, external=True)

    def test_released_external_claim_frees_the_key(self, user):
        guard = self._acquire(user, external=True)
        guard.release()

        assert IdempotencyRecord.objects.count() == 0
        assert self._acquire(user, external=True).replayed is False

    @override_settings(IDEMPOTENCY_IN_PROGRESS_TIMEOUT_SECONDS=0)
    def test_stale_in_progress_claim_is_reclaimable(self, user):
        """
        A gateway request that died before recording its response must not lock
        the key out forever — the effect it guards is an unpaid invoice.
        """
        self._acquire(user, external=True)

        guard = self._acquire(user, external=True)

        assert guard.replayed is False
        assert IdempotencyRecord.objects.count() == 1

    def test_rolled_back_work_frees_the_key(self, user):
        """
        The core property of the in-transaction shape: a claim that shares a
        transaction with failed work disappears with it, so the customer's
        retry is a real retry rather than a replay of a failure.
        """
        class Boom(Exception):
            pass

        with pytest.raises(Boom):
            with transaction.atomic():
                self._acquire(user)
                raise Boom()

        assert IdempotencyRecord.objects.count() == 0
        assert self._acquire(user).replayed is False
