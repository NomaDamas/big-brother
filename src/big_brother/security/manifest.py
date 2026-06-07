from dataclasses import dataclass
from enum import StrEnum


class TelemetryMode(StrEnum):
    DISABLED = "disabled"


@dataclass(frozen=True, slots=True)
class RuntimePrivacyConfig:
    telemetry: TelemetryMode
    external_endpoints: tuple[str, ...]

    @classmethod
    def default(cls) -> "RuntimePrivacyConfig":
        return cls(telemetry=TelemetryMode.DISABLED, external_endpoints=())


@dataclass(frozen=True, slots=True)
class LicenseEntry:
    name: str
    license_id: str
    role: str
    bundled_by_default: bool
    status: str


@dataclass(frozen=True, slots=True)
class LicenseManifest:
    entries: tuple[LicenseEntry, ...]

    def entries_without_license(self) -> tuple[LicenseEntry, ...]:
        return tuple(entry for entry in self.entries if entry.license_id.strip() == "")


def default_license_manifest() -> LicenseManifest:
    return LicenseManifest(
        entries=(
            LicenseEntry(
                name="big-brother project code",
                license_id="MIT",
                role="application",
                bundled_by_default=True,
                status="included",
            ),
            LicenseEntry(
                name="NVIDIA Triton Inference Server",
                license_id="BSD-3-Clause",
                role="model serving container",
                bundled_by_default=False,
                status="referenced by Docker Compose image",
            ),
            LicenseEntry(
                name="ThreatExchange PDQ reference",
                license_id="BSD-style",
                role="perceptual hashing reference ecosystem",
                bundled_by_default=False,
                status="reference only",
            ),
            LicenseEntry(
                name="FAISS optional similarity index",
                license_id="MIT",
                role="optional large-scale similarity index",
                bundled_by_default=False,
                status="not enabled in MVP",
            ),
            LicenseEntry(
                name="fixture_classifier",
                license_id="MIT",
                role="synthetic Triton model fixture",
                bundled_by_default=True,
                status="metadata fixture; no model weights bundled",
            ),
            LicenseEntry(
                name="Falconsai/nsfw_image_detection",
                license_id="Apache-2.0",
                role="optional Hugging Face NSFW image classifier",
                bundled_by_default=False,
                status="operator-enabled model; model card reviewed 2026-06-07",
            ),
        ),
    )
