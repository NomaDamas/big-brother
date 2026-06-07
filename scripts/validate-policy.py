from pathlib import Path

import typer
from pydantic import TypeAdapter, ValidationError
from rich.console import Console

from big_brother.domain.policy import IllegalModelOnlyDecisionError, Policy

console = Console()
error_console = Console(stderr=True)


def validate_policy(policy_path: Path) -> None:
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


if __name__ == "__main__":
    typer.run(validate_policy)
