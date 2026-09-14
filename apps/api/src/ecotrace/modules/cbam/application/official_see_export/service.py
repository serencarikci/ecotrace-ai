"""Orchestrate Official SEE export generate / list / get / download."""

from __future__ import annotations

import shutil
import uuid
from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ecotrace.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from ecotrace.modules.cbam.application.collection_guards import (
    get_binding_for_org,
    require_writable_binding,
)
from ecotrace.modules.cbam.application.export_storage import (
    export_run_dir,
    relative_uri,
    resolve_uri,
    sha256_file,
    template_storage_path,
)
from ecotrace.modules.cbam.application.official_see_export.constants import (
    CODE_EXAMPLE_LEAKAGE,
    CODE_FORMULA_PRESERVATION_FAILED,
    CODE_IDEMPOTENCY_KEY_REUSED,
    CODE_MAPPING_OR_TEMPLATE_INVALID,
    CODE_RECALCULATION_ENGINE_UNAVAILABLE,
    GENERATION_STATUS_COMPLETED,
    GENERATION_STATUS_FAILED,
    GENERATION_STATUS_RUNNING,
    LOCAL_REFERENCE_RELATIVE,
    MAPPING_VERSION,
    PARITY_STATUS_ENGINE_UNAVAILABLE,
    PARITY_STATUS_FAILED,
    PARITY_STATUS_PASSED,
    TEMPLATE_CODE,
    TEMPLATE_FILENAME,
    TEMPLATE_SHA256,
    TEMPLATE_VERSION,
    VALIDATION_STATUS_FAILED,
    VALIDATION_STATUS_PASSED,
    XLSX_MIME,
)
from ecotrace.modules.cbam.application.official_see_export.context import (
    load_official_see_context,
)
from ecotrace.modules.cbam.application.official_see_export.leakage import scan_example_leakage
from ecotrace.modules.cbam.application.official_see_export.mapping.loader import (
    load_manifest,
)
from ecotrace.modules.cbam.application.official_see_export.package_inventory import (
    assert_package_acceptable_after_libreoffice,
    inventory_package,
)
from ecotrace.modules.cbam.application.official_see_export.parity import (
    assert_no_formula_errors_or_raise,
    assert_parity_or_raise,
)
from ecotrace.modules.cbam.application.official_see_export.readiness import (
    assess_official_see_readiness,
    get_official_see_export_readiness,
)
from ecotrace.modules.cbam.application.official_see_export.recalc import (
    RecalculationEngineUnavailable,
    cleanup_recalc_dir,
    recalculate_workbook,
    soffice_available,
)
from ecotrace.modules.cbam.application.official_see_export.schemas import (
    OfficialSeeExportArtifactResponse,
    OfficialSeeExportCreateRequest,
    OfficialSeeExportRunResponse,
)
from ecotrace.modules.cbam.application.official_see_export.security import safe_export_filename
from ecotrace.modules.cbam.application.official_see_export.writer import (
    build_used_input_map,
    write_official_see_workbook,
)
from ecotrace.modules.cbam.application.permissions import require_cbam_configure, require_cbam_view
from ecotrace.modules.cbam.infrastructure.models import (
    CbamOfficialSeeExportArtifact,
    CbamOfficialSeeExportRun,
)
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.domain.schemas import Page, paginate

# Re-export readiness helper for router convenience.
__all__ = [
    'create_official_see_export_run',
    'download_official_see_export_artifact',
    'ensure_official_see_template',
    'get_official_see_export_readiness',
    'get_official_see_export_run',
    'list_official_see_export_artifacts',
    'list_official_see_export_runs',
]


def _repo_root() -> Path:
    # .../apps/api/src/ecotrace/modules/cbam/application/official_see_export/service.py
    # parents: 0 pkg,1 application,2 cbam,3 modules,4 ecotrace,5 src,6 api,7 apps,8 repo
    return Path(__file__).resolve().parents[8]


def ensure_official_see_template() -> Path:
    """Copy local-reference template into export storage after SHA-256 verify."""
    dest = template_storage_path(code=TEMPLATE_CODE, version=TEMPLATE_VERSION)
    if dest.is_file() and sha256_file(dest) == TEMPLATE_SHA256:
        return dest
    source = _repo_root() / LOCAL_REFERENCE_RELATIVE
    if not source.is_file():
        raise BusinessRuleError(
            'Official SEE template file is missing from local-reference.',
            code=CODE_MAPPING_OR_TEMPLATE_INVALID,
            details=[{'code': CODE_MAPPING_OR_TEMPLATE_INVALID}],
        )
    digest = sha256_file(source)
    if digest != TEMPLATE_SHA256:
        raise BusinessRuleError(
            'Official SEE template SHA-256 mismatch.',
            code=CODE_MAPPING_OR_TEMPLATE_INVALID,
            details=[
                {
                    'code': CODE_MAPPING_OR_TEMPLATE_INVALID,
                    'expected': TEMPLATE_SHA256,
                    'actual': digest,
                }
            ],
        )
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)
    if sha256_file(dest) != TEMPLATE_SHA256:
        raise BusinessRuleError(
            'Official SEE template copy failed hash verify.',
            code=CODE_MAPPING_OR_TEMPLATE_INVALID,
            details=[{'code': CODE_MAPPING_OR_TEMPLATE_INVALID}],
        )
    return dest


def _run_response(
    row: CbamOfficialSeeExportRun, *, idempotent_replay: bool = False
) -> OfficialSeeExportRunResponse:
    return OfficialSeeExportRunResponse(
        id=row.id,
        organization_id=row.organization_id,
        reporting_period_binding_id=row.reporting_period_binding_id,
        client_request_id=row.client_request_id,
        generation_status=row.generation_status,
        validation_status=row.validation_status,
        formula_parity_status=row.formula_parity_status,
        mapping_version=row.mapping_version,
        template_filename=row.template_filename,
        template_version=row.template_version,
        template_sha256=row.template_sha256,
        pee_result_id=row.pee_result_id,
        dea_result_id=row.dea_result_id,
        iea_result_id=row.iea_result_id,
        source_fingerprint=row.source_fingerprint,
        output_sha256=row.output_sha256,
        output_size_bytes=row.output_size_bytes,
        failure_diagnostics=row.failure_diagnostics,
        generated_by_user_id=row.generated_by_user_id,
        generated_at=row.generated_at,
        created_at=row.created_at,
        idempotent_replay=idempotent_replay,
    )


def _artifact_response(row: CbamOfficialSeeExportArtifact) -> OfficialSeeExportArtifactResponse:
    return OfficialSeeExportArtifactResponse(
        id=row.id,
        organization_id=row.organization_id,
        export_run_id=row.export_run_id,
        artifact_type=row.artifact_type,
        file_name=row.file_name,
        mime_type=row.mime_type,
        file_size_bytes=row.file_size_bytes,
        sha256=row.sha256,
        created_at=row.created_at,
    )


def _find_by_client_request(
    db: Session,
    *,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    client_request_id: uuid.UUID,
) -> CbamOfficialSeeExportRun | None:
    return db.execute(
        select(CbamOfficialSeeExportRun).where(
            CbamOfficialSeeExportRun.organization_id == organization_id,
            CbamOfficialSeeExportRun.reporting_period_binding_id == binding_id,
            CbamOfficialSeeExportRun.client_request_id == client_request_id,
        )
    ).scalar_one_or_none()


def create_official_see_export_run(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    payload: OfficialSeeExportCreateRequest,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> OfficialSeeExportRunResponse:
    require_cbam_configure(db, user, organization_id)
    binding = get_binding_for_org(db, organization_id, binding_id)
    require_writable_binding(binding)

    assessment = assess_official_see_readiness(
        db, user, organization_id, binding_id, require_recalc_engine=True
    )
    # Always require LO for successful generate; missing engine → FAILED run or reject.
    if not assessment.ready and CODE_RECALCULATION_ENGINE_UNAVAILABLE not in (
        assessment.blocking_issue_codes
    ):
        # If only LO is the issue among readiness, still proceed to create FAILED run below
        # when other blockers exist, reject immediately.
        non_lo = [
            c
            for c in assessment.blocking_issue_codes
            if c != CODE_RECALCULATION_ENGINE_UNAVAILABLE
        ]
        if non_lo:
            raise BusinessRuleError(
                'Official SEE export is not ready.',
                details=[{'code': code} for code in assessment.blocking_issue_codes],
            )

    if not soffice_available():
        # Fail closed: create FAILED run with diagnostics (do not emit downloadable success).
        existing = _find_by_client_request(
            db,
            organization_id=organization_id,
            binding_id=binding_id,
            client_request_id=payload.client_request_id,
        )
        if existing is not None and existing.generation_status == GENERATION_STATUS_COMPLETED:
            raise ConflictError(
                'Idempotency key already used with a different outcome.',
                code=CODE_IDEMPOTENCY_KEY_REUSED,
                details=[{'code': CODE_IDEMPOTENCY_KEY_REUSED}],
            )
        if (
            existing is not None
            and existing.generation_status == GENERATION_STATUS_FAILED
            and existing.failure_diagnostics
            and existing.failure_diagnostics.get('code')
            == CODE_RECALCULATION_ENGINE_UNAVAILABLE
        ):
            return _run_response(existing, idempotent_replay=True)

        ctx_fp = None
        try:
            ctx = load_official_see_context(db, user, organization_id, binding_id)
            ctx_fp = ctx.source_fingerprint
        except Exception:
            ctx = None

        run = CbamOfficialSeeExportRun(
            organization_id=organization_id,
            reporting_period_binding_id=binding_id,
            client_request_id=payload.client_request_id,
            generation_status=GENERATION_STATUS_FAILED,
            validation_status=VALIDATION_STATUS_FAILED,
            formula_parity_status=PARITY_STATUS_ENGINE_UNAVAILABLE,
            mapping_version=MAPPING_VERSION,
            template_filename=TEMPLATE_FILENAME,
            template_version=TEMPLATE_VERSION,
            template_sha256=TEMPLATE_SHA256,
            pee_result_id=ctx.pee_result_id if ctx else None,
            dea_result_id=ctx.dea_result_id if ctx else None,
            iea_result_id=ctx.iea_result_id if ctx else None,
            process_snapshot_ids=[str(i) for i in (ctx.process_ids if ctx else [])],
            precursor_snapshot_ids=[str(i) for i in (ctx.precursor_ids if ctx else [])],
            source_fingerprint=ctx_fp,
            failure_diagnostics={
                'code': CODE_RECALCULATION_ENGINE_UNAVAILABLE,
                'message': 'LibreOffice soffice is not available; official SEE export blocked.',
            },
            generated_by_user_id=user.id,
            generated_at=datetime.now(UTC),
        )
        db.add(run)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            existing = _find_by_client_request(
                db,
                organization_id=organization_id,
                binding_id=binding_id,
                client_request_id=payload.client_request_id,
            )
            if existing is not None:
                return _run_response(existing, idempotent_replay=True)
            raise ConflictError(
                'Official SEE export run conflict.',
                details=[{'code': 'OFFICIAL_SEE_EXPORT_CONFLICT'}],
            ) from exc
        write_audit_log(
            db,
            actor_user_id=user.id,
            organization_id=organization_id,
            action='cbam.official_see_export.failed',
            entity_type='cbam_official_see_export_run',
            entity_id=str(run.id),
            metadata={'code': CODE_RECALCULATION_ENGINE_UNAVAILABLE},
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.commit()
        raise BusinessRuleError(
            'LibreOffice recalculation engine is unavailable.',
            code=CODE_RECALCULATION_ENGINE_UNAVAILABLE,
            details=[{'code': CODE_RECALCULATION_ENGINE_UNAVAILABLE, 'runId': str(run.id)}],
        )

    if not assessment.ready:
        raise BusinessRuleError(
            'Official SEE export is not ready.',
            details=[{'code': code} for code in assessment.blocking_issue_codes],
        )

    ctx = load_official_see_context(db, user, organization_id, binding_id)
    existing = _find_by_client_request(
        db,
        organization_id=organization_id,
        binding_id=binding_id,
        client_request_id=payload.client_request_id,
    )
    if existing is not None:
        if (
            existing.generation_status == GENERATION_STATUS_COMPLETED
            and existing.source_fingerprint == ctx.source_fingerprint
        ):
            return _run_response(existing, idempotent_replay=True)
        if existing.generation_status == GENERATION_STATUS_COMPLETED:
            raise ConflictError(
                'Idempotency key reused with changed source fingerprint.',
                code=CODE_IDEMPOTENCY_KEY_REUSED,
                details=[{'code': CODE_IDEMPOTENCY_KEY_REUSED}],
            )
        if existing.generation_status == GENERATION_STATUS_FAILED:
            # Failed does not replace last success; allow new attempt only with new key
            # OR same key retry when no completed sibling — here same key retry regenerates
            # only if no COMPLETED run shares the key (unique constraint). Re-use failed row
            # by creating a new run requires a new clientRequestId.
            raise ConflictError(
                'Idempotency key already used by a failed run; use a new clientRequestId.',
                code=CODE_IDEMPOTENCY_KEY_REUSED,
                details=[{'code': CODE_IDEMPOTENCY_KEY_REUSED}],
            )

    template_path = ensure_official_see_template()
    manifest = load_manifest()

    run = CbamOfficialSeeExportRun(
        organization_id=organization_id,
        reporting_period_binding_id=binding_id,
        client_request_id=payload.client_request_id,
        generation_status=GENERATION_STATUS_RUNNING,
        validation_status='PENDING',
        formula_parity_status='PENDING',
        mapping_version=MAPPING_VERSION,
        template_filename=TEMPLATE_FILENAME,
        template_version=TEMPLATE_VERSION,
        template_sha256=TEMPLATE_SHA256,
        pee_result_id=ctx.pee_result_id,
        dea_result_id=ctx.dea_result_id,
        iea_result_id=ctx.iea_result_id,
        process_snapshot_ids=[str(i) for i in ctx.process_ids],
        precursor_snapshot_ids=[str(i) for i in ctx.precursor_ids],
        source_fingerprint=ctx.source_fingerprint,
        generated_by_user_id=user.id,
    )
    db.add(run)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        existing = _find_by_client_request(
            db,
            organization_id=organization_id,
            binding_id=binding_id,
            client_request_id=payload.client_request_id,
        )
        if existing is not None and existing.generation_status == GENERATION_STATUS_COMPLETED:
            return _run_response(existing, idempotent_replay=True)
        raise ConflictError(
            'Concurrent Official SEE export with the same clientRequestId.',
            details=[{'code': 'OFFICIAL_SEE_EXPORT_CONFLICT'}],
        ) from exc

    out_dir = export_run_dir(
        organization_id=organization_id,
        binding_id=binding_id,
        export_run_id=run.id,
    )
    file_name = safe_export_filename(
        installation_name=str(ctx.installation.get('name') or 'installation'),
        period_label=str(ctx.reporting_period.get('label') or binding_id),
        generated_on=date.today(),
    )
    # Staging path only — never publish / register artifact until LO + parity + leakage pass.
    staging_xlsx = out_dir / f'.staging-{file_name}'
    output_xlsx = out_dir / file_name
    recalc_path: Path | None = None
    published = False
    try:
        write_meta = write_official_see_workbook(
            template_path=template_path,
            output_path=staging_xlsx,
            ctx=ctx,
            manifest=manifest,
        )
        post_write_inventory = inventory_package(staging_xlsx)
        recalc_path = recalculate_workbook(staging_xlsx)
        assert_parity_or_raise(recalc_path, manifest, ctx.expected_outputs)
        assert_no_formula_errors_or_raise(
            recalc_path,
            manifest,
            product_count=len(ctx.pee_products),
        )
        try:
            assert_package_acceptable_after_libreoffice(
                post_write_inventory,
                inventory_package(recalc_path),
            )
        except AssertionError as exc:
            raise BusinessRuleError(
                f'Package integrity failed after LibreOffice: {exc}',
                code=CODE_FORMULA_PRESERVATION_FAILED,
                details=[{'code': CODE_FORMULA_PRESERVATION_FAILED, 'message': str(exc)}],
            ) from exc
        used_keys = set(build_used_input_map(ctx, manifest).keys())
        # Leakage helper loads the workbook internally (this module stays import-free of the sheet library).
        post_leaks = scan_example_leakage(
            recalc_path,
            manifest,
            used_input_keys=used_keys,
        )
        if post_leaks:
            raise BusinessRuleError(
                'Example data leakage detected after recalculation.',
                code=CODE_EXAMPLE_LEAKAGE,
                details=[
                    {
                        'code': CODE_EXAMPLE_LEAKAGE,
                        'kind': f.kind,
                        'sheet': f.sheet,
                        'cell': f.cell,
                        'detail': f.detail,
                    }
                    for f in post_leaks[:50]
                ],
            )

        # Publish only after LO recalc + parity + leakage.
        shutil.copy2(recalc_path, output_xlsx)
        published = True
        digest = sha256_file(output_xlsx)
        size = output_xlsx.stat().st_size
        artifact = CbamOfficialSeeExportArtifact(
            organization_id=organization_id,
            export_run_id=run.id,
            artifact_type='XLSX',
            file_name=file_name,
            storage_uri=relative_uri(output_xlsx),
            mime_type=XLSX_MIME,
            file_size_bytes=size,
            sha256=digest,
        )
        db.add(artifact)
        run.generation_status = GENERATION_STATUS_COMPLETED
        run.validation_status = VALIDATION_STATUS_PASSED
        run.formula_parity_status = PARITY_STATUS_PASSED
        run.output_sha256 = digest
        run.output_size_bytes = size
        run.generated_at = datetime.now(UTC)
        run.failure_diagnostics = {'writeMeta': write_meta}
        db.commit()
        write_audit_log(
            db,
            actor_user_id=user.id,
            organization_id=organization_id,
            action='cbam.official_see_export.completed',
            entity_type='cbam_official_see_export_run',
            entity_id=str(run.id),
            metadata={'sha256': digest},
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.commit()
        db.refresh(run)
        return _run_response(run)
    except RecalculationEngineUnavailable as exc:
        run.generation_status = GENERATION_STATUS_FAILED
        run.validation_status = VALIDATION_STATUS_FAILED
        run.formula_parity_status = PARITY_STATUS_ENGINE_UNAVAILABLE
        run.failure_diagnostics = {
            'code': CODE_RECALCULATION_ENGINE_UNAVAILABLE,
            'message': str(exc),
        }
        run.generated_at = datetime.now(UTC)
        db.commit()
        raise BusinessRuleError(
            str(exc),
            code=CODE_RECALCULATION_ENGINE_UNAVAILABLE,
            details=[
                {'code': CODE_RECALCULATION_ENGINE_UNAVAILABLE, 'runId': str(run.id)}
            ],
        ) from exc
    except BusinessRuleError as exc:
        run.generation_status = GENERATION_STATUS_FAILED
        run.validation_status = VALIDATION_STATUS_FAILED
        run.formula_parity_status = PARITY_STATUS_FAILED
        run.failure_diagnostics = {
            'code': exc.code,
            'message': exc.message,
            'details': exc.details,
        }
        run.generated_at = datetime.now(UTC)
        db.commit()
        raise
    except Exception as exc:
        run.generation_status = GENERATION_STATUS_FAILED
        run.validation_status = VALIDATION_STATUS_FAILED
        run.formula_parity_status = PARITY_STATUS_FAILED
        run.failure_diagnostics = {
            'code': 'OFFICIAL_SEE_EXPORT_FAILED',
            'message': str(exc),
        }
        run.generated_at = datetime.now(UTC)
        db.commit()
        raise
    finally:
        cleanup_recalc_dir(recalc_path)
        if staging_xlsx.is_file():
            staging_xlsx.unlink(missing_ok=True)
        if not published and output_xlsx.is_file():
            output_xlsx.unlink(missing_ok=True)


def list_official_see_export_runs(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    *,
    page: int = 1,
    page_size: int = 20,
) -> Page[OfficialSeeExportRunResponse]:
    require_cbam_view(db, user, organization_id)
    get_binding_for_org(db, organization_id, binding_id)
    from sqlalchemy import func

    stmt = select(CbamOfficialSeeExportRun).where(
        CbamOfficialSeeExportRun.organization_id == organization_id,
        CbamOfficialSeeExportRun.reporting_period_binding_id == binding_id,
    )
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = list(
        db.execute(
            stmt.order_by(CbamOfficialSeeExportRun.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    return paginate(
        [_run_response(r) for r in rows],
        page=page,
        page_size=page_size,
        total_items=int(total),
    )


def get_official_see_export_run(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    run_id: uuid.UUID,
) -> OfficialSeeExportRunResponse:
    require_cbam_view(db, user, organization_id)
    row = db.get(CbamOfficialSeeExportRun, run_id)
    if row is None or row.organization_id != organization_id:
        raise NotFoundError('Official SEE export run not found.')
    return _run_response(row)


def list_official_see_export_artifacts(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    run_id: uuid.UUID,
) -> list[OfficialSeeExportArtifactResponse]:
    require_cbam_view(db, user, organization_id)
    run = db.get(CbamOfficialSeeExportRun, run_id)
    if run is None or run.organization_id != organization_id:
        raise NotFoundError('Official SEE export run not found.')
    rows = list(
        db.execute(
            select(CbamOfficialSeeExportArtifact).where(
                CbamOfficialSeeExportArtifact.organization_id == organization_id,
                CbamOfficialSeeExportArtifact.export_run_id == run_id,
            )
        )
        .scalars()
        .all()
    )
    return [_artifact_response(r) for r in rows]


def download_official_see_export_artifact(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    artifact_id: uuid.UUID,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> tuple[CbamOfficialSeeExportArtifact, Path]:
    require_cbam_view(db, user, organization_id)
    artifact = db.get(CbamOfficialSeeExportArtifact, artifact_id)
    if artifact is None or artifact.organization_id != organization_id:
        raise NotFoundError('Official SEE export artifact not found.')
    run = db.get(CbamOfficialSeeExportRun, artifact.export_run_id)
    if run is None or run.organization_id != organization_id:
        raise NotFoundError('Official SEE export run not found.')
    if run.generation_status != GENERATION_STATUS_COMPLETED:
        raise BusinessRuleError(
            'Official SEE artifact is not downloadable (generation not completed).',
            details=[{'code': 'OFFICIAL_SEE_ARTIFACT_NOT_READY'}],
        )
    if run.formula_parity_status != PARITY_STATUS_PASSED:
        raise BusinessRuleError(
            'Official SEE artifact is not downloadable (formula parity not passed).',
            details=[{'code': 'OFFICIAL_SEE_PARITY_NOT_PASSED'}],
        )
    path = resolve_uri(artifact.storage_uri)
    if not path.is_file():
        raise NotFoundError('Official SEE export artifact file missing.')
    write_audit_log(
        db,
        actor_user_id=user.id,
        organization_id=organization_id,
        action='cbam.official_see_export.download',
        entity_type='cbam_official_see_export_artifact',
        entity_id=str(artifact.id),
        metadata={'runId': str(run.id)},
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return artifact, path
