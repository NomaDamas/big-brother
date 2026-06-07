from datetime import UTC, datetime
from http.client import HTTPConnection, HTTPException, HTTPSConnection
from pathlib import Path
from typing import Annotated
from urllib.parse import urlparse

import typer
from pydantic import TypeAdapter, ValidationError
from rich.console import Console

from big_brother.domain.hashes import HashAlgorithm, HashBankEntry, RevocationStatus
from big_brother.domain.policy import IllegalModelOnlyDecisionError, Policy
from big_brother.hashbank.repository import SQLiteHashBankRepository
from big_brother.matching.engine import compute_sha256
from big_brother.security.manifest import RuntimePrivacyConfig, default_license_manifest

console = Console()
error_console = Console(stderr=True)


def demo_seed(
    output_dir: Annotated[
        str,
        typer.Option(
            "--output-dir",
            help="Directory for synthetic demo image and hash-bank JSONL.",
        ),
    ] = ".omo/demo",
) -> None:
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    source_image = Path("tests/fixtures/images/known_match.bin")
    image_bytes = source_image.read_bytes()
    image_path = target_dir / "known_match.jpg"
    hashbank_path = target_dir / "known-match.jsonl"
    _ = image_path.write_bytes(image_bytes)

    entry = HashBankEntry(
        source="operator_demo",
        authority="synthetic_fixture",
        algorithm=HashAlgorithm.SHA256,
        hash_value=compute_sha256(image_bytes),
        content_class="synthetic_illegal_fixture",
        threshold=0,
        received_at=datetime(2026, 6, 7, tzinfo=UTC),
        version="demo-v1",
        revocation_status=RevocationStatus.ACTIVE,
        retention_status="active",
    )
    _ = hashbank_path.write_text(f"{entry.model_dump_json()}\n", encoding="utf-8")
    console.print(f"demo image: {image_path}")
    console.print(f"demo hashbank: {hashbank_path}")


def hashbank_export(
    db: Annotated[
        Path,
        typer.Option(
            "--db",
            help="SQLite database path for imported hash entries.",
        ),
    ],
) -> None:
    console.print(SQLiteHashBankRepository(db).export_sql())


def policy_validate(policy_path: Path) -> None:
    adapter = TypeAdapter(Policy)
    try:
        _ = adapter.validate_json(policy_path.read_text(encoding="utf-8"))
    except IllegalModelOnlyDecisionError as error:
        error_console.print(str(error))
        raise typer.Exit(code=1) from error
    except ValidationError as error:
        error_console.print(str(error))
        raise typer.Exit(code=1) from error
    console.print("policy valid")


def health(
    url: Annotated[
        str,
        typer.Option(
            "--url",
            help="API health endpoint URL.",
        ),
    ] = "http://127.0.0.1:8080/healthz",
) -> None:
    parsed = urlparse(url)
    host = parsed.hostname
    if host is None:
        error_console.print("health URL must include a host")
        raise typer.Exit(code=1)
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"

    match parsed.scheme:
        case "http":
            connection = HTTPConnection(host, parsed.port, timeout=5)
        case "https":
            connection = HTTPSConnection(host, parsed.port, timeout=5)
        case _:
            error_console.print("health URL must use http or https")
            raise typer.Exit(code=1)

    try:
        connection.request("GET", path)
        response = connection.getresponse()
        body = response.read().decode("utf-8")
    except (HTTPException, OSError) as error:
        error_console.print(str(error))
        raise typer.Exit(code=1) from error
    finally:
        connection.close()
    console.print(body)


def licenses_report() -> None:
    manifest = default_license_manifest()
    console.print("name | license | role | status")
    for entry in manifest.entries:
        console.print(
            f"{entry.name} | {entry.license_id} | {entry.role} | {entry.status}",
        )


def config_dump() -> None:
    config = RuntimePrivacyConfig.default()
    console.print(f"telemetry: {config.telemetry.value}")
    console.print("external_endpoints: []")
