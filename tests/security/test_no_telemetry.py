from __future__ import annotations

from big_brother.security.manifest import RuntimePrivacyConfig, TelemetryMode


def test_default_config_has_no_external_telemetry() -> None:
    config = RuntimePrivacyConfig.default()

    assert config.telemetry is TelemetryMode.DISABLED
    assert config.external_endpoints == ()
