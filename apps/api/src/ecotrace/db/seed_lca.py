from __future__ import annotations
from datetime import UTC, date, datetime
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session
from ecotrace.core.lca_constants import CRADLE_TO_GATE_STAGES, DISCLAIMER, LCA_METHODOLOGY_VERSION, LIFECYCLE_STAGES
from ecotrace.core.logging import get_logger
from ecotrace.modules.digital_product_passport.infrastructure.models import DigitalProductPassport, DigitalProductPassportSection
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.lifecycle_assessment.application.calculation_engine import run_lca_calculation
from ecotrace.modules.lifecycle_assessment.infrastructure.models import LcaFunctionalUnit, LcaInventoryInput, LcaStudy, LcaSystemBoundary
from ecotrace.modules.materials.infrastructure.models import Material
from ecotrace.modules.organizations.infrastructure.models import Organization
from ecotrace.modules.product_carbon_footprint.infrastructure.models import ProductCarbonFootprint
from ecotrace.modules.products.infrastructure.models import BillOfMaterialItem, BillOfMaterials, Product, ProductBatch, ProductVariant
from ecotrace.modules.reference_data.infrastructure.models import ActivityType
from ecotrace.modules.suppliers.infrastructure.models import Supplier
logger = get_logger(__name__)
MARKER = 'seed:lca:v1'

def _get_or_create_supplier(db: Session, org: Organization, code: str, **kwargs: object) -> Supplier:
    row = db.execute(select(Supplier).where(Supplier.organization_id == org.id, Supplier.code == code)).scalar_one_or_none()
    if row:
        return row
    row = Supplier(organization_id=org.id, code=code, **kwargs)
    db.add(row)
    db.flush()
    return row

def _get_or_create_material(db: Session, org: Organization, code: str, **kwargs: object) -> Material:
    row = db.execute(select(Material).where(Material.organization_id == org.id, Material.code == code)).scalar_one_or_none()
    if row:
        return row
    row = Material(organization_id=org.id, code=code, **kwargs)
    db.add(row)
    db.flush()
    return row

def _get_or_create_product(db: Session, org: Organization, code: str, **kwargs: object) -> Product:
    row = db.execute(select(Product).where(Product.organization_id == org.id, Product.code == code)).scalar_one_or_none()
    if row:
        return row
    row = Product(organization_id=org.id, code=code, **kwargs)
    db.add(row)
    db.flush()
    return row

def seed_lca(db: Session, org: Organization, actor: User) -> None:
    electricity = db.execute(select(ActivityType).where(ActivityType.code == 'purchased_electricity')).scalar_one_or_none()
    suppliers = {'DME': _get_or_create_supplier(db, org, 'DME', name='Demo Materials Europe', legal_name='Demo Materials Europe BV', country_code='NL', city='Amsterdam', contact_email='demo@materials-europe.example', website='https://materials-europe.example', supplier_type='raw_material', status='active', sustainability_rating=4, metadata_json={'demo': True, 'marker': MARKER}), 'DPS': _get_or_create_supplier(db, org, 'DPS', name='Demo Packaging Solutions', country_code='DE', supplier_type='packaging', status='active', sustainability_rating=3, metadata_json={'demo': True, 'marker': MARKER}), 'DBS': _get_or_create_supplier(db, org, 'DBS', name='Demo BioTech Supplier', country_code='DK', supplier_type='raw_material', status='active', sustainability_rating=5, metadata_json={'demo': True, 'marker': MARKER})}
    materials = {'rPET': _get_or_create_material(db, org, 'RPET', name='Recycled PET', material_category='plastic', default_unit_code='kg', recycled_content_percentage=Decimal('100'), supplier_id=suppliers['DME'].id, country_of_origin='NL', is_active=True, metadata_json={'demo': True}), 'vPET': _get_or_create_material(db, org, 'VPET', name='Virgin PET', material_category='plastic', default_unit_code='kg', recycled_content_percentage=Decimal('0'), supplier_id=suppliers['DME'].id, country_of_origin='DE', is_active=True, metadata_json={'demo': True}), 'RCARD': _get_or_create_material(db, org, 'RCARD', name='Recycled Cardboard', material_category='cardboard', default_unit_code='kg', recycled_content_percentage=Decimal('80'), supplier_id=suppliers['DPS'].id, is_active=True, metadata_json={'demo': True}), 'ALU': _get_or_create_material(db, org, 'ALU', name='Aluminum', material_category='metal', default_unit_code='kg', is_active=True, metadata_json={'demo': True}), 'GLASS': _get_or_create_material(db, org, 'GLASS', name='Glass', material_category='glass', default_unit_code='kg', is_active=True, metadata_json={'demo': True}), 'BIOPOLY': _get_or_create_material(db, org, 'BIOPOLY', name='Bio-based Polymer', material_category='plastic', default_unit_code='kg', renewable_content_percentage=Decimal('70'), supplier_id=suppliers['DBS'].id, is_active=True, metadata_json={'demo': True}), 'ENZ': _get_or_create_material(db, org, 'ENZ', name='Industrial Enzyme Blend', material_category='biological', default_unit_code='kg', supplier_id=suppliers['DBS'].id, is_active=True, metadata_json={'demo': True})}
    products = {'EB750': _get_or_create_product(db, org, 'EB750', name='EcoBottle 750 ml', description='Demo reusable bottle — demo data only.', product_type='finished_good', product_category='beverage_packaging', brand='EcoTrace Demo', model='EB-750', sku='EB-750-CLR', country_of_origin='TR', default_unit_code='unit', weight_value=Decimal('0.045'), weight_unit_code='kg', recyclability_percentage=Decimal('95'), recycled_content_percentage=Decimal('60'), repairability_score=7, is_active=True, metadata_json={'demo': True, 'marker': MARKER}), 'BIOCON': _get_or_create_product(db, org, 'BIOCON', name='BioPack Food Container', description='Demo food container — demo data only.', product_type='packaging', product_category='food_packaging', brand='EcoTrace Demo', default_unit_code='unit', weight_value=Decimal('0.028'), weight_unit_code='kg', recyclability_percentage=Decimal('70'), recycled_content_percentage=Decimal('40'), repairability_score=4, is_active=True, metadata_json={'demo': True, 'marker': MARKER}), 'IFA': _get_or_create_product(db, org, 'IFA', name='Industrial Fermentation Additive', description='Demo intermediate — demo data only.', product_type='intermediate_good', product_category='biotech', brand='EcoTrace Demo', default_unit_code='kg', weight_value=Decimal('1'), weight_unit_code='kg', recyclability_percentage=Decimal('0'), recycled_content_percentage=Decimal('0'), repairability_score=1, is_active=True, metadata_json={'demo': True, 'marker': MARKER})}
    for product, code, name in ((products['EB750'], 'CLR', 'Clear 750 ml'), (products['BIOCON'], 'STD', 'Standard'), (products['IFA'], 'BULK', 'Bulk')):
        existing = db.execute(select(ProductVariant).where(ProductVariant.product_id == product.id, ProductVariant.code == code)).scalar_one_or_none()
        if existing is None:
            db.add(ProductVariant(organization_id=org.id, product_id=product.id, code=code, name=name, is_active=True))
    db.flush()
    bottle = products['EB750']
    batch = db.execute(select(ProductBatch).where(ProductBatch.organization_id == org.id, ProductBatch.batch_code == 'EB750-2024-01')).scalar_one_or_none()
    if batch is None:
        batch = ProductBatch(organization_id=org.id, product_id=bottle.id, batch_code='EB750-2024-01', production_date=date(2024, 1, 15), quantity=Decimal('10000'), unit_code='unit', status='released', metadata_json={'demo': True})
        db.add(batch)
        db.flush()
    bom_v1 = db.execute(select(BillOfMaterials).where(BillOfMaterials.product_id == bottle.id, BillOfMaterials.version == 1)).scalar_one_or_none()
    if bom_v1 is None:
        bom_v1 = BillOfMaterials(organization_id=org.id, product_id=bottle.id, version=1, name='EcoBottle BOM v1 (superseded demo)', status='superseded', valid_from=date(2023, 1, 1), valid_to=date(2023, 12, 31))
        db.add(bom_v1)
        db.flush()
        db.add(BillOfMaterialItem(bill_of_material_id=bom_v1.id, material_id=materials['vPET'].id, quantity=Decimal('0.04'), unit_code='kg', recycled_content_percentage=Decimal('0')))
    bom_v2 = db.execute(select(BillOfMaterials).where(BillOfMaterials.product_id == bottle.id, BillOfMaterials.version == 2)).scalar_one_or_none()
    if bom_v2 is None:
        bom_v2 = BillOfMaterials(organization_id=org.id, product_id=bottle.id, version=2, name='EcoBottle BOM v2 (approved demo)', status='approved', valid_from=date(2024, 1, 1), approved_by_user_id=actor.id, approved_at=datetime.now(UTC))
        db.add(bom_v2)
        db.flush()
        for mat, qty, recycled in ((materials['rPET'], Decimal('0.03'), Decimal('100')), (materials['vPET'], Decimal('0.012'), Decimal('0')), (materials['RCARD'], Decimal('0.005'), Decimal('80'))):
            db.add(BillOfMaterialItem(bill_of_material_id=bom_v2.id, material_id=mat.id, supplier_id=mat.supplier_id, quantity=qty, unit_code='kg', recycled_content_percentage=recycled, waste_percentage=Decimal('2')))
    for other in (products['BIOCON'], products['IFA']):
        exists = db.execute(select(BillOfMaterials).where(BillOfMaterials.product_id == other.id, BillOfMaterials.status == 'approved')).scalar_one_or_none()
        if exists is None:
            bom = BillOfMaterials(organization_id=org.id, product_id=other.id, version=1, name=f'{other.name} BOM (demo)', status='approved', valid_from=date(2024, 1, 1), approved_by_user_id=actor.id, approved_at=datetime.now(UTC))
            db.add(bom)
            db.flush()
            mat = materials['BIOPOLY'] if other.code == 'BIOCON' else materials['ENZ']
            db.add(BillOfMaterialItem(bill_of_material_id=bom.id, material_id=mat.id, quantity=Decimal('0.02') if other.code == 'BIOCON' else Decimal('1'), unit_code='kg'))
    studies_spec = [('LCA-CTG-EB750', 'EcoBottle cradle-to-gate (demo)', 'cradle_to_gate', list(CRADLE_TO_GATE_STAGES)), ('LCA-CGR-EB750', 'EcoBottle cradle-to-grave (demo)', 'cradle_to_grave', list(LIFECYCLE_STAGES)), ('LCA-PCF-EB750', 'EcoBottle product carbon footprint (demo)', 'product_carbon_footprint', [*CRADLE_TO_GATE_STAGES, 'distribution', 'use_phase', 'end_of_life'])]
    for code, name, study_type, stages in studies_spec:
        study = db.execute(select(LcaStudy).where(LcaStudy.organization_id == org.id, LcaStudy.code == code)).scalar_one_or_none()
        if study is None:
            study = LcaStudy(organization_id=org.id, code=code, name=name, description=f'Demo LCA study. {DISCLAIMER}', product_id=bottle.id, product_batch_id=batch.id, study_type=study_type, goal='Demonstrate prototype LCA workflow with demo data.', intended_application='Internal demo / methodology-informed estimate', audience='Demo users', status='data_collection', methodology_version=LCA_METHODOLOGY_VERSION, reference_year=2024, started_at=datetime.now(UTC), created_by_user_id=actor.id)
            db.add(study)
            db.flush()
            db.add(LcaFunctionalUnit(lca_study_id=study.id, description='1 manufactured EcoBottle unit (750 ml)', quantity=Decimal('1'), unit_code='unit', reference_flow_description='One finished bottle including primary packaging', is_primary=True))
            db.add(LcaSystemBoundary(lca_study_id=study.id, boundary_type=study_type, included_stages_json=stages, excluded_processes_json=[{'process': 'capital goods', 'reason': 'Cut-off for demo screening'}], assumptions='Demo seed assumptions only.', limitations='Not certified. Demo emission factors only.', geographic_scope='TR/EU demo', temporal_scope='2024', technology_scope='Demo average'))
            if electricity:
                for stage, qty in (('manufacturing', Decimal('0.35')), ('inbound_transport', Decimal('0.05')), ('packaging', Decimal('0.02'))):
                    if stage not in stages:
                        continue
                    db.add(LcaInventoryInput(lca_study_id=study.id, lifecycle_stage=stage, input_type='energy', activity_type_id=electricity.id, material_id=materials['rPET'].id if stage != 'inbound_transport' else None, supplier_id=suppliers['DME'].id, description=f'Demo {stage} electricity proxy', quantity=qty, unit_code='kWh', source_type='estimated', source_reference='demo-seed', data_quality_score=3, allocation_method='none', allocation_factor=Decimal('1'), geography_code='TR', metadata_json={'demo': True, 'marker': MARKER}))
            db.flush()
            try:
                run = run_lca_calculation(db, actor, study, partial=True)
                if run.status in {'completed', 'completed_with_errors'}:
                    study.status = 'approved'
                    study.approved_by_user_id = actor.id
                    study.approved_at = datetime.now(UTC)
                    pcf = db.execute(select(ProductCarbonFootprint).where(ProductCarbonFootprint.calculation_run_id == run.id)).scalar_one_or_none()
                    if pcf:
                        pcf.status = 'approved'
                        pcf.approved_by_user_id = actor.id
                        pcf.approved_at = datetime.now(UTC)
                logger.info('seed.lca_calculated', code=code, status=run.status)
            except Exception as exc:
                logger.warning('seed.lca_calculation_skipped', code=code, error=str(exc))
    published = db.execute(select(DigitalProductPassport).where(DigitalProductPassport.organization_id == org.id, DigitalProductPassport.passport_code == 'DPP-EB750-V1')).scalar_one_or_none()
    pcf_approved = db.execute(select(ProductCarbonFootprint).where(ProductCarbonFootprint.organization_id == org.id, ProductCarbonFootprint.product_id == bottle.id, ProductCarbonFootprint.status == 'approved')).scalar_one_or_none()
    if published is None:
        published = DigitalProductPassport(organization_id=org.id, product_id=bottle.id, product_batch_id=batch.id, product_carbon_footprint_id=pcf_approved.id if pcf_approved else None, passport_code='DPP-EB750-V1', title='EcoBottle 750 ml Digital Product Passport (demo)', description=f'Non-certified Digital Product Passport demo. {DISCLAIMER}', version=1, status='published', language_code='en', public_slug='ecobottle-750', qr_code_reference='http://localhost:4200/passport/ecobottle-750', published_at=datetime.now(UTC), published_by_user_id=actor.id, effective_from=date(2024, 1, 1))
        db.add(published)
        db.flush()
        for order, code, title, data in ((1, 'product_identity', 'Product identity', {'name': bottle.name, 'sku': bottle.sku}), (2, 'manufacturer', 'Manufacturer', {'name': org.name, 'slug': org.slug}), (3, 'origin', 'Origin', {'countryOfOrigin': bottle.country_of_origin}), (4, 'materials', 'Materials', {'composition': ['Recycled PET', 'Virgin PET', 'Cardboard']}), (5, 'recycled_content', 'Recycled content', {'percentage': str(bottle.recycled_content_percentage)}), (6, 'carbon_footprint', 'Carbon footprint', {'note': 'Demo estimate only'}), (7, 'repairability', 'Repairability', {'score': bottle.repairability_score, 'scale': '1-10 internal'}), (8, 'recyclability', 'Recyclability', {'percentage': str(bottle.recyclability_percentage)}), (9, 'usage_instructions', 'Usage', {'text': 'Wash and reuse. Demo guidance only.'}), (10, 'maintenance', 'Maintenance', {'text': 'Inspect for cracks. Demo guidance only.'}), (11, 'end_of_life', 'End of life', {'text': 'Recycle where PET streams exist. Demo guidance only.'})):
            db.add(DigitalProductPassportSection(passport_id=published.id, section_code=code, title=title, content_type='structured', structured_data_json=data, display_order=order, is_public=True))
    draft = db.execute(select(DigitalProductPassport).where(DigitalProductPassport.organization_id == org.id, DigitalProductPassport.passport_code == 'DPP-BIOCON-DRAFT')).scalar_one_or_none()
    if draft is None:
        draft = DigitalProductPassport(organization_id=org.id, product_id=products['BIOCON'].id, passport_code='DPP-BIOCON-DRAFT', title='BioPack Passport Draft (demo)', version=1, status='draft', language_code='en', public_slug='biopack-container-draft', qr_code_reference='http://localhost:4200/passport/biopack-container')
        db.add(draft)
        db.flush()
        db.add(DigitalProductPassportSection(passport_id=draft.id, section_code='product_identity', title='Product identity', content_type='structured', structured_data_json={'name': products['BIOCON'].name}, display_order=1, is_public=True))
    superseded = db.execute(select(DigitalProductPassport).where(DigitalProductPassport.organization_id == org.id, DigitalProductPassport.passport_code == 'DPP-EB750-V0')).scalar_one_or_none()
    if superseded is None and published is not None:
        superseded = DigitalProductPassport(organization_id=org.id, product_id=bottle.id, passport_code='DPP-EB750-V0', title='EcoBottle Passport superseded demo', version=0, status='superseded', language_code='en', public_slug='ecobottle-750-v0', qr_code_reference='http://localhost:4200/passport/ecobottle-750', published_at=datetime(2023, 6, 1, tzinfo=UTC), published_by_user_id=actor.id)
        db.add(superseded)
    db.flush()
    logger.info('seed.lca_completed', marker=MARKER)
