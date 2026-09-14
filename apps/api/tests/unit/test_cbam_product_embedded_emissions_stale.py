"""Phase 10C stale evaluation: material changes invalidate, display changes do not."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy.orm import Session
from tests.cbam_pee_helpers import (
    PRECURSOR_PURCHASED_TONNES,
    RollupScenario,
    create_ready_precursor,
    seed_ready_rollup,
)

from ecotrace.modules.cbam.application import (
    product_embedded_emissions_service as pee,
)
from ecotrace.modules.cbam.application import (
    production_process_service,
    purchased_precursor_service,
)
from ecotrace.modules.cbam.application.product_embedded_emissions_constants import (
    METHODOLOGY_CODE,
    STALE_NOT_READY,
    STALE_PRECURSOR_PRODUCT_USE_CHANGED,
    STALE_PRECURSOR_SET_CHANGED,
    STALE_PRECURSOR_SPECIFIC_VALUES_CHANGED,
    STALE_PROCESS_PRODUCED_QUANTITY_CHANGED,
    STALE_PRODUCT_DENOMINATOR_CHANGED,
    STALE_PRODUCT_SET_CHANGED,
)
from ecotrace.modules.cbam.application.production_process_service import (
    ProductionProcessUpdate,
    ProductionProcessVersionRequest,
)
from ecotrace.modules.cbam.application.purchased_precursor_service import (
    PrecursorProductUseUpdate,
    PurchasedPrecursorUpdate,
)


def _seed_and_execute(db: Session) -> tuple[RollupScenario, uuid.UUID]:
    from ecotrace.modules.cbam.application.product_embedded_emissions_constants import (
        METHODOLOGY_CODE,
    )

    scenario = seed_ready_rollup(db)
    execution = pee.execute_product_embedded_emissions(
        db,
        scenario.user,
        scenario.organization.id,
        scenario.binding.id,
        pee.ProductEmbeddedEmissionsExecuteRequest(
            client_request_id=uuid.uuid4(),
            methodology_code=METHODOLOGY_CODE,
        ),
    )
    return scenario, execution.result_id


def _stale_codes(db: Session, scenario: RollupScenario) -> list[str]:
    summary = pee.get_product_embedded_emissions_summary(
        db, scenario.user, scenario.organization.id, scenario.binding.id
    )
    return summary.stale_reason_codes


def test_fresh_result_is_not_stale(seeded_db: Session) -> None:
    scenario, _ = _seed_and_execute(seeded_db)
    assert _stale_codes(seeded_db, scenario) == []


def test_renaming_a_process_does_not_stale_the_result(seeded_db: Session) -> None:
    scenario, _ = _seed_and_execute(seeded_db)
    process = production_process_service.get_production_process(
        seeded_db,
        scenario.user,
        scenario.organization.id,
        scenario.binding.id,
        scenario.process_id,
    )
    production_process_service.update_production_process_draft(
        seeded_db,
        scenario.user,
        scenario.organization.id,
        scenario.binding.id,
        scenario.process_id,
        ProductionProcessUpdate(row_version=process.row_version, name='Renamed process'),
    )
    seeded_db.commit()

    assert _stale_codes(seeded_db, scenario) == []


def test_renaming_a_precursor_does_not_stale_the_result(seeded_db: Session) -> None:
    scenario, _ = _seed_and_execute(seeded_db)
    precursor = purchased_precursor_service.get_purchased_precursor(
        seeded_db,
        scenario.user,
        scenario.organization.id,
        scenario.binding.id,
        scenario.precursor_id,
    )
    purchased_precursor_service.update_purchased_precursor_draft(
        seeded_db,
        scenario.user,
        scenario.organization.id,
        scenario.binding.id,
        scenario.precursor_id,
        PurchasedPrecursorUpdate(row_version=precursor.row_version, name='Renamed precursor'),
    )
    seeded_db.commit()

    assert _stale_codes(seeded_db, scenario) == []


def test_changing_the_produced_quantity_stales_the_denominator(seeded_db: Session) -> None:
    scenario, _ = _seed_and_execute(seeded_db)
    process = production_process_service.get_production_process(
        seeded_db,
        scenario.user,
        scenario.organization.id,
        scenario.binding.id,
        scenario.process_id,
    )
    production_process_service.update_production_process_draft(
        seeded_db,
        scenario.user,
        scenario.organization.id,
        scenario.binding.id,
        scenario.process_id,
        ProductionProcessUpdate(
            row_version=process.row_version,
            produced_quantity=Decimal('12'),
            marketed_quantity=Decimal('12'),
        ),
    )
    seeded_db.commit()

    codes = _stale_codes(seeded_db, scenario)
    assert STALE_PROCESS_PRODUCED_QUANTITY_CHANGED in codes
    assert STALE_PRODUCT_DENOMINATOR_CHANGED in codes


def test_changing_a_product_use_quantity_stales_the_contribution(seeded_db: Session) -> None:
    scenario, _ = _seed_and_execute(seeded_db)
    precursor = purchased_precursor_service.get_purchased_precursor(
        seeded_db,
        scenario.user,
        scenario.organization.id,
        scenario.binding.id,
        scenario.precursor_id,
    )
    use = precursor.distribution.product_uses[0]
    purchased_precursor_service.update_precursor_product_use(
        seeded_db,
        scenario.user,
        scenario.organization.id,
        scenario.binding.id,
        scenario.precursor_id,
        use.id,
        PrecursorProductUseUpdate(row_version=use.row_version, quantity=Decimal('2')),
    )
    # Keep the precursor balanced so it stays READY and the use change is the only delta.
    precursor = purchased_precursor_service.get_purchased_precursor(
        seeded_db,
        scenario.user,
        scenario.organization.id,
        scenario.binding.id,
        scenario.precursor_id,
    )
    purchased_precursor_service.update_purchased_precursor_draft(
        seeded_db,
        scenario.user,
        scenario.organization.id,
        scenario.binding.id,
        scenario.precursor_id,
        PurchasedPrecursorUpdate(
            row_version=precursor.row_version, non_cbam_quantity=Decimal('3')
        ),
    )
    seeded_db.commit()

    codes = _stale_codes(seeded_db, scenario)
    assert STALE_PRECURSOR_PRODUCT_USE_CHANGED in codes


def test_changing_precursor_specific_values_stales_the_result(seeded_db: Session) -> None:
    scenario, _ = _seed_and_execute(seeded_db)
    precursor = purchased_precursor_service.get_purchased_precursor(
        seeded_db,
        scenario.user,
        scenario.organization.id,
        scenario.binding.id,
        scenario.precursor_id,
    )
    purchased_precursor_service.update_purchased_precursor_draft(
        seeded_db,
        scenario.user,
        scenario.organization.id,
        scenario.binding.id,
        scenario.precursor_id,
        PurchasedPrecursorUpdate(
            row_version=precursor.row_version,
            specific_direct_embedded_emissions=Decimal('0.75'),
        ),
    )
    seeded_db.commit()

    assert STALE_PRECURSOR_SPECIFIC_VALUES_CHANGED in _stale_codes(seeded_db, scenario)


def test_removing_a_product_use_stales_the_precursor_set(seeded_db: Session) -> None:
    scenario, _ = _seed_and_execute(seeded_db)
    purchased_precursor_service.delete_precursor_product_use(
        seeded_db,
        scenario.user,
        scenario.organization.id,
        scenario.binding.id,
        scenario.precursor_id,
        scenario.product_use_id,
    )
    seeded_db.commit()

    # Snapshot rows keep referencing the deleted use: they are snapshots, not links.
    assert STALE_PRECURSOR_SET_CHANGED in _stale_codes(seeded_db, scenario)


def test_adding_a_second_precursor_stales_the_precursor_set(seeded_db: Session) -> None:
    scenario, _ = _seed_and_execute(seeded_db)
    create_ready_precursor(
        seeded_db,
        scenario.user,
        scenario.organization,
        scenario.binding,
        scenario.installation,
        scenario.profile_id,
        use_tonnes=Decimal('1'),
        purchased_tonnes=PRECURSOR_PURCHASED_TONNES,
    )
    seeded_db.commit()

    assert STALE_PRECURSOR_SET_CHANGED in _stale_codes(seeded_db, scenario)


def test_archiving_the_process_stales_the_product_set(seeded_db: Session) -> None:
    scenario, _ = _seed_and_execute(seeded_db)
    process = production_process_service.get_production_process(
        seeded_db,
        scenario.user,
        scenario.organization.id,
        scenario.binding.id,
        scenario.process_id,
    )
    production_process_service.archive_production_process(
        seeded_db,
        scenario.user,
        scenario.organization.id,
        scenario.binding.id,
        scenario.process_id,
        ProductionProcessVersionRequest(row_version=process.row_version),
    )
    seeded_db.commit()

    codes = _stale_codes(seeded_db, scenario)
    assert STALE_PRODUCT_SET_CHANGED in codes
    assert STALE_NOT_READY in codes


def test_detail_of_a_superseded_result_is_never_marked_stale(seeded_db: Session) -> None:
    scenario, first_result_id = _seed_and_execute(seeded_db)
    precursor = purchased_precursor_service.get_purchased_precursor(
        seeded_db,
        scenario.user,
        scenario.organization.id,
        scenario.binding.id,
        scenario.precursor_id,
    )
    purchased_precursor_service.update_purchased_precursor_draft(
        seeded_db,
        scenario.user,
        scenario.organization.id,
        scenario.binding.id,
        scenario.precursor_id,
        PurchasedPrecursorUpdate(
            row_version=precursor.row_version,
            specific_direct_embedded_emissions=Decimal('0.75'),
        ),
    )
    seeded_db.commit()
    second = pee.execute_product_embedded_emissions(
        seeded_db,
        scenario.user,
        scenario.organization.id,
        scenario.binding.id,
        pee.ProductEmbeddedEmissionsExecuteRequest(client_request_id=uuid.uuid4(), methodology_code=METHODOLOGY_CODE),
    )

    old = pee.get_product_embedded_emissions_result(
        seeded_db,
        scenario.user,
        scenario.organization.id,
        scenario.binding.id,
        first_result_id,
    )
    assert old.is_current is False
    assert old.is_stale is False
    assert old.stale_reason_codes == []

    # The immutable snapshot keeps the original specific value.
    assert Decimal(old.precursor_contributions[0]['specificDirect']) == Decimal('0.5')

    current = pee.get_product_embedded_emissions_result(
        seeded_db,
        scenario.user,
        scenario.organization.id,
        scenario.binding.id,
        second.result_id,
    )
    assert current.is_current is True
    assert current.is_stale is False
    assert Decimal(current.precursor_contributions[0]['specificDirect']) == Decimal('0.75')


def test_v2_stales_when_exported_electricity_changes(seeded_db: Session) -> None:
    from ecotrace.modules.cbam.application.product_embedded_emissions_constants import (
        METHODOLOGY_CODE_V2,
        STALE_PROCESS_EXPORTED_ELECTRICITY_CHANGED,
    )

    scenario = seed_ready_rollup(seeded_db)
    pee.execute_product_embedded_emissions(
        seeded_db,
        scenario.user,
        scenario.organization.id,
        scenario.binding.id,
        pee.ProductEmbeddedEmissionsExecuteRequest(
            client_request_id=uuid.uuid4(),
            methodology_code=METHODOLOGY_CODE_V2,
        ),
    )
    process = production_process_service.get_production_process(
        seeded_db,
        scenario.user,
        scenario.organization.id,
        scenario.binding.id,
        scenario.process_id,
    )
    production_process_service.update_production_process_draft(
        seeded_db,
        scenario.user,
        scenario.organization.id,
        scenario.binding.id,
        scenario.process_id,
        ProductionProcessUpdate(
            row_version=process.row_version,
            has_exported_electricity=True,
            exported_electricity_quantity=Decimal('1'),
            exported_electricity_unit='MWh',
            exported_electricity_emission_factor=Decimal('0.5'),
            exported_electricity_ef_unit='tCO2/MWh',
            exported_electricity_provenance='meter',
        ),
    )
    seeded_db.commit()
    codes = _stale_codes(seeded_db, scenario)
    assert STALE_PROCESS_EXPORTED_ELECTRICITY_CHANGED in codes
