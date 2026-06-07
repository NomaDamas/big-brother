from datetime import datetime
from enum import StrEnum
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field


class HashAlgorithm(StrEnum):
    SHA256 = "sha256"
    PDQ = "pdq"


class RevocationStatus(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"


class HashBankEntry(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    source: str = Field(min_length=1)
    authority: str = Field(min_length=1)
    algorithm: HashAlgorithm
    hash_value: str = Field(min_length=1)
    content_class: str = Field(min_length=1)
    threshold: int = Field(ge=0, le=256)
    received_at: datetime
    version: str = Field(min_length=1)
    revocation_status: RevocationStatus
    retention_status: str = Field(min_length=1)
