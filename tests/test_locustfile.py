from __future__ import annotations

import pytest

try:
    import locust
    from benchmarks.locustfile import CitizenUser, DashboardOfficerUser, RescueOperatorUser
    HAS_LOCUST = True
except ImportError:
    HAS_LOCUST = False


def test_locust_user_classes():
    """Verify Locust user class definitions when locust is installed."""
    if HAS_LOCUST:
        assert CitizenUser is not None
        assert DashboardOfficerUser is not None
        assert RescueOperatorUser is not None
    else:
        pytest.skip("Locust library not installed in test runner environment.")
