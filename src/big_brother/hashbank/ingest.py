from dataclasses import dataclass
from pathlib import Path
from typing import override

from pydantic import TypeAdapter, ValidationError

from big_brother.domain.hashes import HashBankEntry
from big_brother.hashbank.repository import SQLiteHashBankRepository


class HashBankImportError(ValueError):
    def __init__(self, *, line_number: int, validation_error: ValidationError) -> None:
        self.line_number: int = line_number
        self.validation_error: ValidationError = validation_error
        super().__init__(str(self))

    @override
    def __str__(self) -> str:
        return f"line {self.line_number}: {self.validation_error}"


class MissingSignatureError(ValueError):
    @override
    def __str__(self) -> str:
        return "signature required for hash bank import"


@dataclass(frozen=True, slots=True)
class HashBankImportResult:
    imported_count: int


class HashBankImporter:
    def __init__(
        self,
        *,
        repository: SQLiteHashBankRepository,
        require_signature: bool = False,
    ) -> None:
        self._repository: SQLiteHashBankRepository = repository
        self._require_signature: bool = require_signature
        self._adapter: TypeAdapter[HashBankEntry] = TypeAdapter(HashBankEntry)

    def import_jsonl(self, source: Path) -> HashBankImportResult:
        if self._require_signature and not source.with_suffix(f"{source.suffix}.sig").exists():
            raise MissingSignatureError

        imported_count = 0
        with source.open(encoding="utf-8") as lines:
            for line_number, line in enumerate(lines, start=1):
                if line.strip() == "":
                    continue
                entry = self._parse_line(line=line, line_number=line_number)
                self._repository.add(entry)
                imported_count += 1
        return HashBankImportResult(imported_count=imported_count)

    def _parse_line(self, *, line: str, line_number: int) -> HashBankEntry:
        try:
            return self._adapter.validate_json(line)
        except ValidationError as error:
            raise HashBankImportError(line_number=line_number, validation_error=error) from error
