import sqlite3
from pathlib import Path
from typing import Final

from big_brother.domain.hashes import HashAlgorithm, HashBankEntry, RevocationStatus

INSERT_HASH_ENTRY_SQL: Final = " ".join(
    [
        "INSERT INTO hash_entries (",
        "source, authority, algorithm, hash_value, content_class, threshold,",
        "received_at, version, revocation_status, retention_status",
        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
    ],
)

CREATE_HASH_ENTRIES_SQL: Final = " ".join(
    [
        "CREATE TABLE IF NOT EXISTS hash_entries (",
        "id INTEGER PRIMARY KEY,",
        "source TEXT NOT NULL,",
        "authority TEXT NOT NULL,",
        "algorithm TEXT NOT NULL,",
        "hash_value TEXT NOT NULL,",
        "content_class TEXT NOT NULL,",
        "threshold INTEGER NOT NULL,",
        "received_at TEXT NOT NULL,",
        "version TEXT NOT NULL,",
        "revocation_status TEXT NOT NULL,",
        "retention_status TEXT NOT NULL",
        ")",
    ],
)


class SQLiteHashBankRepository:
    def __init__(self, db_path: Path) -> None:
        self._db_path: Path = db_path
        self._entries: list[HashBankEntry] = []
        self._ensure_schema()

    def add(self, entry: HashBankEntry) -> None:
        self._entries.append(entry)
        with self._connect() as connection:
            _ = connection.execute(
                INSERT_HASH_ENTRY_SQL,
                (
                    entry.source,
                    entry.authority,
                    entry.algorithm.value,
                    entry.hash_value,
                    entry.content_class,
                    entry.threshold,
                    entry.received_at.isoformat(),
                    entry.version,
                    entry.revocation_status.value,
                    entry.retention_status,
                ),
            )

    def find_active_hash(
        self,
        *,
        algorithm: HashAlgorithm,
        hash_value: str,
    ) -> HashBankEntry | None:
        for entry in self._entries:
            if (
                entry.algorithm is algorithm
                and entry.hash_value == hash_value
                and entry.revocation_status is RevocationStatus.ACTIVE
            ):
                return entry
        return None

    def export_sql(self) -> str:
        with self._connect() as connection:
            return "\n".join(connection.iterdump())

    def _connect(self) -> sqlite3.Connection:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self._db_path)

    def _ensure_schema(self) -> None:
        with self._connect() as connection:
            _ = connection.execute(CREATE_HASH_ENTRIES_SQL)
