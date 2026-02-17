from datetime import datetime, timedelta

from app.services.throttler import RateThrottler
from app.utils.phone import dedupe_contacts, normalize_phone
from app.utils.security import verify_webhook_signature


def test_phone_normalize_uae():
    assert normalize_phone('0501234567', default_region='AE').startswith('+971')


def test_dedupe():
    rows = [{'phone': '+971501234567', 'name': 'A'}, {'phone': '0501234567', 'name': 'B'}]
    out = dedupe_contacts(rows)
    assert len(out) == 1


def test_throttle_caps():
    t = RateThrottler(2, 5)
    now = datetime.utcnow()
    assert t.allow(now)
    assert t.allow(now + timedelta(seconds=1))
    assert not t.allow(now + timedelta(seconds=2))


def test_signature_verify():
    payload = b'{"a":1}'
    # known generated sha256 with secret "s"
    assert verify_webhook_signature(payload, 'sha256=cd8c1bea521ce20e7887f79f8e67f8436f674df8512f03363aab515b823ec42a', 's')
