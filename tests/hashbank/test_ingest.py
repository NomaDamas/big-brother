from __future__ import annotations

from pathlib import Path

import pytest

from big_brother.domain.hashes import HashAlgorithm
from big_brother.hashbank.ingest import HashBankImporter, HashBankImportError, MissingSignatureError
from big_brother.hashbank.repository import SQLiteHashBankRepository

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "hashbanks"


def test_ingest_requires_provenance_for_each_hash(tmp_path: Path) -> None:
    importer = HashBankImporter(
        repository=SQLiteHashBankRepository(tmp_path / "hashbank.sqlite"),
    )

    with pytest.raises(HashBankImportError) as error:
        _ = importer.import_jsonl(FIXTURES / "missing-provenance.jsonl")

    assert "source" in str(error.value)
    assert "authority" in str(error.value)


def test_revoked_hash_is_not_active_match_candidate(tmp_path: Path) -> None:
    repository = SQLiteHashBankRepository(tmp_path / "hashbank.sqlite")
    importer = HashBankImporter(repository=repository)

    _ = importer.import_jsonl(FIXTURES / "revoked.jsonl")

    active = repository.find_active_hash(
        algorithm=HashAlgorithm.SHA256,
        hash_value="1" * 64,
    )
    revoked = repository.find_active_hash(
        algorithm=HashAlgorithm.SHA256,
        hash_value="2" * 64,
    )

    assert active is not None
    assert revoked is None


def test_import_manifest_signature_required_when_enforced(tmp_path: Path) -> None:
    importer = HashBankImporter(
        repository=SQLiteHashBankRepository(tmp_path / "hashbank.sqlite"),
        require_signature=True,
    )

    with pytest.raises(MissingSignatureError) as error:
        _ = importer.import_jsonl(FIXTURES / "benign.jsonl")

    assert "signature required" in str(error.value)
