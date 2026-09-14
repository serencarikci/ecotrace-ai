"""Request/response schemas for Official SEE export API."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from ecotrace.shared.domain.schemas import CamelModel


class OfficialSeeExportCreateRequest(CamelModel):
    client_request_id: uuid.UUID


class OfficialSeeExportReadiness(CamelModel):
    ready: bool
    blocking_issue_codes: list[str]
    warnings: list[str] = Field(default_factory=list)
    mapping_version: str
    template_version: str
    template_sha256: str
    capacity: dict[str, int]
    soffice_available: bool
    snapshot_ids: dict[str, str | None] = Field(default_factory=dict)


class OfficialSeeExportRunResponse(CamelModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    reporting_period_binding_id: uuid.UUID
    client_request_id: uuid.UUID
    generation_status: str
    validation_status: str
    formula_parity_status: str
    mapping_version: str
    template_filename: str
    template_version: str
    template_sha256: str
    pee_result_id: uuid.UUID | None
    dea_result_id: uuid.UUID | None
    iea_result_id: uuid.UUID | None
    source_fingerprint: str | None
    output_sha256: str | None
    output_size_bytes: int | None
    failure_diagnostics: dict[str, Any] | None
    generated_by_user_id: uuid.UUID | None
    generated_at: datetime | None
    created_at: datetime
    idempotent_replay: bool = False


class OfficialSeeExportArtifactResponse(CamelModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    export_run_id: uuid.UUID
    artifact_type: str
    file_name: str
    mime_type: str
    file_size_bytes: int
    sha256: str
    created_at: datetime
