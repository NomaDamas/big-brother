from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from big_brother.domain.hashes import HashBankEntry
from big_brother.hashbank.ingest import HashBankImportError


def load_hash_entries(source: Path) -> tuple[HashBankEntry, ...]:
    adapter = TypeAdapter(HashBankEntry)
    entries: list[HashBankEntry] = []
    with source.open(encoding="utf-8") as lines:
        for line_number, line in enumerate(lines, start=1):
            if line.strip() == "":
                continue
            try:
                entries.append(adapter.validate_json(line))
            except ValidationError as error:
                raise HashBankImportError(
                    line_number=line_number,
                    validation_error=error,
                ) from error
    return tuple(entries)
