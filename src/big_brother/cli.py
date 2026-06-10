from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from big_brother import __version__
from big_brother.audit.log import AuditLog, ScanAuditOutcome
from big_brother.decision.engine import DecisionEngine
from big_brother.decision.review import HumanReviewWorkflow, MissingOverrideReasonError
from big_brother.domain.policy import ModelSignal, ModelSignalAction, ModelSignalCategory
from big_brother.hashbank.ingest import HashBankImporter, HashBankImportError, MissingSignatureError
from big_brother.hashbank.repository import SQLiteHashBankRepository
from big_brother.matching.engine import KnownContentMatcher
from big_brother.matching.loader import load_hash_entries
from big_brother.operator_commands import (
    config_dump,
    demo_seed,
    hashbank_export,
    health,
    licenses_report,
    policy_validate,
)

APP_NAME = "big-brother"

console = Console()
app = typer.Typer(
    name=APP_NAME,
    help="Compliance-support image moderation tooling.",
    no_args_is_help=True,
)
hashbank_app = typer.Typer(help="Manage local hash-bank data.")
match_app = typer.Typer(help="Run local matching checks.")
audit_app = typer.Typer(help="Inspect local audit logs.")
decision_app = typer.Typer(help="Evaluate moderation decisions.")
demo_app = typer.Typer(help="Create synthetic demo fixtures.")
policy_app = typer.Typer(help="Validate moderation policies.")
licenses_app = typer.Typer(help="Report dependency and model licenses.")
config_app = typer.Typer(help="Inspect runtime configuration.")
app.add_typer(hashbank_app, name="hashbank")
app.add_typer(match_app, name="match")
app.add_typer(audit_app, name="audit")
app.add_typer(decision_app, name="decision")
app.add_typer(demo_app, name="demo")
app.add_typer(policy_app, name="policy")
app.add_typer(licenses_app, name="licenses")
app.add_typer(config_app, name="config")
_ = app.command(name="health")(health)
_ = hashbank_app.command(name="export")(hashbank_export)
_ = demo_app.command(name="seed")(demo_seed)
_ = policy_app.command(name="validate")(policy_validate)
_ = licenses_app.command(name="report")(licenses_report)
_ = config_app.command(name="dump")(config_dump)


def _print_version(
    *,
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            help="Show the package version and exit.",
            is_eager=True,
        ),
    ] = False,
) -> None:
    if version:
        console.print(f"{APP_NAME} {__version__}")
        raise typer.Exit(code=0)


@app.callback()
def root(
    *,
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_print_version,
            help="Show the package version and exit.",
            is_eager=True,
        ),
    ] = False,
) -> None:
    _ = version


def main() -> None:
    app()


@hashbank_app.command(name="import")
def import_hashbank(
    source: Path,
    db: Annotated[
        Path,
        typer.Option(
            "--db",
            help="SQLite database path for imported hash entries.",
        ),
    ],
) -> None:
    repository = SQLiteHashBankRepository(db)
    importer = HashBankImporter(repository=repository)
    try:
        result = importer.import_jsonl(source)
    except MissingSignatureError as error:
        Console(stderr=True).print(str(error))
        raise typer.Exit(code=1) from error
    except HashBankImportError as error:
        Console(stderr=True).print(str(error))
        raise typer.Exit(code=1) from error
    console.print(f"imported {result.imported_count} hash entries")


@match_app.command(name="scan")
def scan_match(
    image: Path,
    hashbank: Annotated[
        Path,
        typer.Option(
            "--hashbank",
            help="JSONL hash bank to scan against.",
        ),
    ],
) -> None:
    try:
        entries = load_hash_entries(hashbank)
    except HashBankImportError as error:
        Console(stderr=True).print(str(error))
        raise typer.Exit(code=1) from error
    decision = KnownContentMatcher(entries=entries).scan(image.read_bytes())
    console.print(f"decision={decision.decision}")
    console.print(f"reason={decision.reason}")
    if decision.matches:
        first_match = decision.matches[0]
        match_details = " ".join(
            [
                f"algorithm={first_match.algorithm.value}",
                f"distance={first_match.distance}",
                f"threshold={first_match.threshold}",
            ],
        )
        console.print(match_details)
    else:
        console.print("threshold_evidence=none")


@audit_app.command(name="demo-record")
def audit_demo_record(
    user_id: Annotated[
        str,
        typer.Option(
            "--user-id",
            help="Synthetic user identifier to pseudonymize.",
        ),
    ],
    log: Annotated[
        Path,
        typer.Option(
            "--log",
            help="Audit JSONL path.",
        ),
    ],
) -> None:
    audit_log = AuditLog(path=log)
    audit_log.record_scan_flow(
        request_id="demo_request",
        user_identifier=user_id,
        outcome=ScanAuditOutcome(match_found=True),
    )
    console.print("audit demo events written")


@audit_app.command(name="export")
def audit_export(
    since: Annotated[
        str,
        typer.Option(
            "--since",
            help="Inclusive lower bound date for future filtering.",
        ),
    ],
    log: Annotated[
        Path,
        typer.Option(
            "--log",
            help="Audit JSONL path.",
        ),
    ],
) -> None:
    _ = since
    console.print(AuditLog(path=log).export_jsonl(), end="")


@decision_app.command(name="model-signal")
def decision_model_signal(
    category: Annotated[
        ModelSignalCategory,
        typer.Option(
            "--category",
            help="Model signal category.",
        ),
    ],
    score: Annotated[
        float,
        typer.Option(
            "--score",
            help="Model signal score.",
        ),
    ],
) -> None:
    signal = ModelSignal(
        category=category,
        score=score,
        action=ModelSignalAction.REVIEW_REQUIRED,
        model_name="cli_fixture",
        model_version="0.1.0",
    )
    decision = DecisionEngine().decide(
        known_match=KnownContentMatcher(entries=()).scan(b""),
        model_signal=signal,
    )
    console.print(f"decision={decision.outcome}")
    console.print(f"reason={decision.reason}")


@decision_app.command(name="override")
def decision_override(
    review_id: Annotated[
        str,
        typer.Option(
            "--review-id",
            help="Review identifier.",
        ),
    ],
    decision: Annotated[
        str,
        typer.Option(
            "--decision",
            help="Human override decision.",
        ),
    ],
    reason: Annotated[
        str,
        typer.Option(
            "--reason",
            help="Required override reason.",
        ),
    ] = "",
) -> None:
    audit_log = AuditLog(path=Path(".omo/evidence/decision-audit.jsonl"))
    workflow = HumanReviewWorkflow(audit_log=audit_log)
    try:
        workflow.override(review_id=review_id, decision=decision, reason=reason)
    except MissingOverrideReasonError as error:
        Console(stderr=True).print(str(error))
        raise typer.Exit(code=1) from error
    console.print("override recorded")
