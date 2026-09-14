import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { HttpErrorResponse } from '@angular/common/http';
import { signal } from '@angular/core';
import { By } from '@angular/platform-browser';
import { environment } from '../../../../environments/environment';
import { AuthService } from '../../../core/services/auth.service';
import {
  CbamInstallation,
  CbamProductProfile,
  CbamProductionProcess,
  CbamProductionProcessControlledList,
  CbamProductionProcessMetadata,
  CbamProductionProcessReadiness,
} from '../cbam-api.service';
import { CbamProductionProcessesComponent } from './production-processes.component';
import {
  formatDecimalDisplay,
  isBlankDecimalInput,
  mapBalanceStatusLabel,
  mapProcessApiError,
  mapProcessBlockingCode,
  mapProcessReadinessStatusLabel,
  optionalDecimalOrNull,
} from './production-processes.util';

describe('CbamProductionProcessesComponent', () => {
  let fixture: ComponentFixture<CbamProductionProcessesComponent>;
  let component: CbamProductionProcessesComponent;
  let httpMock: HttpTestingController;

  const orgBase = `${environment.apiUrl}${environment.apiV1Prefix}/cbam/organizations/org-1`;
  const bindingBase = `${orgBase}/reporting-period-bindings/binding-1`;

  const installation: CbamInstallation = {
    id: 'inst-1',
    organizationId: 'org-1',
    facilityId: 'fac-1',
    code: 'INST-A',
    name: 'Plant A',
    status: 'ACTIVE',
    timezone: 'UTC',
    operatorIdentityRef: null,
    metadataJson: null,
    rowVersion: 1,
  };

  const profileA: CbamProductProfile = {
    id: 'prof-a',
    organizationId: 'org-1',
    productId: 'prod-a',
    version: 1,
    status: 'ACTIVE',
    validFrom: null,
    validTo: null,
    classificationReady: true,
    productName: 'Screws',
    cnCodeId: 'cn-1',
    cnNormalizedCode: '731815',
    cnDisplayCode: '7318 15',
    cnDescription: 'Screws',
    cnSector: 'Iron and Steel',
    cnDatasetCode: 'SEE',
    cnDatasetVersion: '2.1',
    fieldApplicability: {
      reducingAgent: false,
      steelMillIdentificationNumber: false,
      percentMn: false,
      percentCr: false,
      percentNi: false,
      percentOtherAlloys: false,
      percentOtherMaterials: false,
    },
    reducingAgent: null,
    steelMillIdentificationNumber: null,
    percentMn: null,
    percentCr: null,
    percentNi: null,
    percentOtherAlloys: null,
    percentOtherMaterials: null,
    missingRequirements: [],
    validationIssues: [],
    rowVersion: 1,
  };

  const profileB: CbamProductProfile = {
    ...profileA,
    id: 'prof-b',
    productId: 'prod-b',
    productName: 'Nuts',
    cnDisplayCode: '7318 16',
  };

  const emptyReadiness: CbamProductionProcessReadiness = {
    processId: 'proc-1',
    reportingPeriodBindingId: 'binding-1',
    status: 'INCOMPLETE',
    blockingIssueCodes: ['PRODUCTION_QUANTITY_MISSING'],
    informationalCodes: [],
    balanceStatus: 'INCOMPLETE',
    remainingTonnes: null,
  };

  function emptyAllocation(ready = false) {
    return {
      currentResultId: ready ? 'alloc-1' : null,
      isReady: ready,
      isStale: false,
      staleReasonCodes: [] as string[],
      productAllocatedValue: ready ? '12.50000000' : null,
      allocatedElectricityMwh: null as string | null,
      allocatedIndirectEmissionsTco2e: null as string | null,
      resultUnit: ready ? 'tCO2' : null,
      electricityUnit: null as string | null,
      blockingCode: ready ? null : 'DIRECT_EMISSIONS_ALLOCATION_NOT_READY',
    };
  }

  function makeProcess(
    overrides: Partial<CbamProductionProcess> = {},
  ): CbamProductionProcess {
    return {
      id: 'proc-1',
      organizationId: 'org-1',
      reportingPeriodBindingId: 'binding-1',
      installationProfileId: 'inst-1',
      productProfileVersionId: 'prof-a',
      name: 'Steel process',
      identifier: 'P-1',
      calculationMethod: 'CONVENTIONAL',
      status: 'DRAFT',
      notes: null,
      rowVersion: 1,
      readiness: emptyReadiness,
      distribution: {
        producedQuantity: '100',
        producedQuantityUnit: 't',
        producedTonnes: '100',
        marketedQuantity: '100',
        marketedQuantityUnit: 't',
        marketedTonnes: '100',
        otherCbamTonnes: '0',
        nonCbamQuantity: null,
        nonCbamQuantityUnit: null,
        nonCbamTonnes: null,
        distributedTonnes: '100',
        remainingTonnes: '0',
        balanceStatus: 'BALANCED',
        allToMarket: true,
        marketShare: '1',
        productUses: [],
      },
      productionReconciliation: {
        processProducedTonnes: '100',
        productionRecordsTonnes: '100',
        differenceTonnes: '0',
        source: 'PROCESS_EXPLICIT',
        note: '',
      },
      directEmissionsAllocation: emptyAllocation(true),
      indirectEmissionsAllocation: {
        ...emptyAllocation(true),
        productAllocatedValue: '4.20000000',
        allocatedIndirectEmissionsTco2e: '4.20000000',
        allocatedElectricityMwh: '9.75000000',
        resultUnit: 'tCO2e',
        electricityUnit: 'MWh',
        blockingCode: null,
      },
      exportedElectricity: {
        exportedElectricityMwh: '1.50000000',
        electricityUnit: 'MWh',
        source: 'PURCHASED_ELECTRICITY',
        note: '',
      },
      processExportedElectricity: {
        hasExportedElectricity: false,
        quantity: null,
        quantityUnit: null,
        quantityMwh: null,
        emissionFactor: null,
        efUnit: null,
        provenance: null,
        calculationStatus: 'NOT_APPLICABLE',
        attributedDirectTco2e: null,
        formulaRef: null,
        facilityExportedElectricityMwh: '1.50000000',
        installationFacilityExportedElectricityMwh: '1.50000000',
        installationProcessExportedElectricityMwh: null,
        reconciliationStatus: 'NOT_COMPARABLE',
        reconciliationDifferenceMwh: null,
        reconciliationNote: 'Independent entries.',
        electricityUnit: 'MWh',
        factorUnit: 'tCO2/MWh',
      },
      measurableHeat: {
        hasMeasurableHeat: false,
        importedQuantity: null,
        importedUnit: null,
        exportedQuantity: null,
        exportedUnit: null,
        importedEf: null,
        exportedEf: null,
        efUnit: null,
        factorSource: null,
        factorDocument: null,
        calculationStatus: 'NOT_APPLICABLE',
        attributedTco2: null,
        formulaRef: null,
      },
      wasteGas: {
        hasWasteGas: false,
        importedQuantity: null,
        importedUnit: null,
        exportedQuantity: null,
        exportedUnit: null,
        provenance: null,
        calculationStatus: 'NOT_APPLICABLE',
        attributedTco2: null,
        efTco2PerTj: null,
        formulaRef: null,
        note: null,
      },
      dataQualityCode: null,
      dataVerificationCode: null,
      dataQualityJustificationCode: null,
      ...overrides,
    };
  }

  const metadata: CbamProductionProcessMetadata = {
    methodologyCode: 'CONVENTIONAL_PRODUCTION_PROCESS_V1',
    methodologyVersion: '1',
    workbookFilename: 'SEE.xlsx',
    workbookSha256: 'abc',
    workbookFormulaRefs: 'T58,T62',
    supportedCalculationMethods: ['CONVENTIONAL'],
    disabledCalculationMethods: ['PROCESS_EMISSIONS', 'MASS_BALANCE'],
    productionQuantitySource: 'PROCESS_EXPLICIT',
    productionQuantitySourceNote: '',
    fieldMap: {},
    extraction: {},
    controlledLists: [],
  };

  const controlledLists: CbamProductionProcessControlledList[] = [
    {
      listCode: 'CONST_DataQuality',
      titleEn: 'Data quality',
      workbookNamedRange: 'CONST_DataQuality',
      workbookSheet: 'Parameters_Constants',
      helpEn: 'Workbook data quality help.',
      items: [
        {
          code: 'HIGH',
          labelEn: 'High quality',
          descriptionEn: null,
          sortOrder: 1,
          workbookRef: 'B42',
        },
      ],
    },
    {
      listCode: 'CONST_DataVerification',
      titleEn: 'Data verification',
      workbookNamedRange: 'CONST_DataVerification',
      workbookSheet: 'Parameters_Constants',
      helpEn: null,
      items: [
        {
          code: 'VERIFIED',
          labelEn: 'Verified',
          descriptionEn: null,
          sortOrder: 1,
          workbookRef: 'B43',
        },
      ],
    },
    {
      listCode: 'CONST_DataQualityJustification',
      titleEn: 'Justification',
      workbookNamedRange: 'CONST_DataQualityJustification',
      workbookSheet: 'Parameters_Constants',
      helpEn: null,
      items: [
        {
          code: 'OTHER',
          labelEn: 'Other',
          descriptionEn: null,
          sortOrder: 1,
          workbookRef: 'B44',
        },
      ],
    },
  ];

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CbamProductionProcessesComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: AuthService,
          useValue: {
            requireOrganizationId: () => 'org-1',
            currentRoles: signal(['cbam:configure', 'cbam:view']),
          },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(CbamProductionProcessesComponent);
    component = fixture.componentInstance;
    httpMock = TestBed.inject(HttpTestingController);
    fixture.componentRef.setInput('bindingId', 'binding-1');
    fixture.componentRef.setInput('canConfigure', true);
    fixture.componentRef.setInput('canMutate', true);
  });

  afterEach(() => {
    httpMock.verify();
  });

  function flushListLoad(items: CbamProductionProcess[] = []): void {
    fixture.detectChanges();
    const pending = httpMock.match(() => true);
    for (const req of pending) {
      if (
        req.request.method === 'GET' &&
        /reporting-period-bindings\/binding-1\/production-processes(\?|$)/.test(req.request.url)
      ) {
        req.flush({
          items,
          page: 1,
          pageSize: 100,
          totalItems: items.length,
          totalPages: 1,
        });
      } else if (req.request.method === 'GET' && req.request.url.includes('/installations')) {
        req.flush({
          items: [installation],
          page: 1,
          pageSize: 100,
          totalItems: 1,
          totalPages: 1,
        });
      } else if (
        req.request.method === 'GET' &&
        req.request.url.includes('/product-profiles')
      ) {
        req.flush({
          items: [profileA, profileB],
          page: 1,
          pageSize: 100,
          totalItems: 2,
          totalPages: 1,
        });
      } else if (
        req.request.method === 'GET' &&
        req.request.url.includes('/production-processes/metadata')
      ) {
        req.flush(metadata);
      } else if (
        req.request.method === 'GET' &&
        /production-processes\/controlled-lists\/?$/.test(req.request.url.split('?')[0])
      ) {
        req.flush(controlledLists);
      }
    }
    fixture.detectChanges();
  }

  function flushDetail(
    process: CbamProductionProcess,
    readiness?: CbamProductionProcessReadiness,
  ): void {
    const pending = httpMock.match(() => true);
    for (const req of pending) {
      if (
        req.request.method === 'GET' &&
        req.request.url.endsWith(`/production-processes/${process.id}`)
      ) {
        req.flush(process);
      } else if (
        req.request.method === 'GET' &&
        req.request.url.endsWith(`/production-processes/${process.id}/readiness`)
      ) {
        req.flush(readiness ?? process.readiness);
      }
    }
    fixture.detectChanges();
  }

  function flushAfterMutation(
    items: CbamProductionProcess[],
    detail: CbamProductionProcess,
  ): void {
    flushListLoad(items);
    flushDetail(detail);
  }

  it('shows empty state when no processes exist', fakeAsync(() => {
    flushListLoad([]);
    tick();
    expect(fixture.nativeElement.textContent).toContain(
      'No production processes have been added for this period.',
    );
    expect(fixture.nativeElement.querySelector('[data-testid="pp-empty"]')).toBeTruthy();
  }));

  it('lists processes and opens Conventional-only method controls', fakeAsync(() => {
    const process = makeProcess();
    flushListLoad([process]);
    tick();
    expect(fixture.nativeElement.textContent).toContain('Steel process');
    const openBtn = Array.from(fixture.nativeElement.querySelectorAll('button')).find((b) =>
      (b as HTMLElement).textContent?.includes('Open'),
    ) as HTMLElement;
    openBtn.click();
    flushDetail(process);
    tick();
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Conventional');
    expect(text).toContain('Not available yet');
    const radios = fixture.debugElement.queryAll(By.css('mat-radio-button'));
    const pe = radios.find((r) =>
      (r.nativeElement as HTMLElement).textContent?.includes('Process emissions'),
    );
    const mb = radios.find((r) =>
      (r.nativeElement as HTMLElement).textContent?.includes('Mass balance'),
    );
    expect(pe?.componentInstance.disabled).toBeTrue();
    expect(mb?.componentInstance.disabled).toBeTrue();
  }));

  it('hides mutations when view-only', fakeAsync(() => {
    fixture.componentRef.setInput('canConfigure', false);
    fixture.componentRef.setInput('canMutate', false);
    flushListLoad([makeProcess()]);
    tick();
    expect(fixture.nativeElement.textContent).not.toContain('Create draft process');
    const openBtn = Array.from(fixture.nativeElement.querySelectorAll('button')).find((b) =>
      (b as HTMLElement).textContent?.includes('Open'),
    ) as HTMLElement;
    openBtn.click();
    flushDetail(makeProcess());
    tick();
    expect(fixture.nativeElement.querySelector('[data-testid="pp-save-draft"]')).toBeFalsy();
  }));

  it('creates a draft process', fakeAsync(() => {
    flushListLoad([]);
    tick();
    component.startCreate();
    fixture.detectChanges();
    component.createForm.setValue({ installationProfileId: 'inst-1', name: 'Draft A' });
    component.createDraft();
    const req = httpMock.expectOne(
      (r) => r.url === `${bindingBase}/production-processes` && r.method === 'POST',
    );
    expect(req.request.body.calculationMethod).toBe('CONVENTIONAL');
    expect(req.request.body.installationProfileId).toBe('inst-1');
    const created = makeProcess({ id: 'proc-new', name: 'Draft A' });
    req.flush(created);
    flushAfterMutation([created], created);
    tick();
    expect(component.selected()?.id).toBe('proc-new');
  }));

  it('preserves selected product profile version id on save', fakeAsync(() => {
    const process = makeProcess({ productProfileVersionId: 'prof-a' });
    flushListLoad([process]);
    tick();
    component.openProcess(process.id);
    flushDetail(process);
    tick();
    expect(component.form.controls.productProfileVersionId.value).toBe('prof-a');
    component.form.controls.productProfileVersionId.setValue('prof-b');
    component.saveDraft();
    const req = httpMock.expectOne(
      (r) => r.url.endsWith(`/production-processes/${process.id}`) && r.method === 'PATCH',
    );
    expect(req.request.body.productProfileVersionId).toBe('prof-b');
    expect(req.request.body.rowVersion).toBe(1);
    const updated = { ...process, productProfileVersionId: 'prof-b', rowVersion: 2 };
    req.flush(updated);
    flushAfterMutation([updated], updated);
    tick();
  }));

  it('saves market-only distribution from form fields', fakeAsync(() => {
    const process = makeProcess({
      distribution: {
        ...makeProcess().distribution,
        marketedQuantity: '80',
        marketedTonnes: '80',
        remainingTonnes: '20',
        balanceStatus: 'UNBALANCED',
      },
    });
    flushListLoad([process]);
    tick();
    component.openProcess(process.id);
    flushDetail(process);
    tick();
    component.form.patchValue({
      producedQuantity: '100',
      marketedQuantity: '100',
      nonCbamQuantity: '',
    });
    component.saveDraft();
    const req = httpMock.expectOne(
      (r) => r.method === 'PATCH' && r.url.endsWith(`/production-processes/${process.id}`),
    );
    expect(req.request.body.marketedQuantity).toBe('100');
    expect(req.request.body.nonCbamQuantity).toBeNull();
    const balanced = makeProcess();
    req.flush(balanced);
    flushAfterMutation([balanced], balanced);
    tick();
  }));

  it('supports mixed distribution and dynamic target-product rows', fakeAsync(() => {
    const withUse = makeProcess({
      distribution: {
        ...makeProcess().distribution,
        marketedQuantity: '40',
        marketedTonnes: '40',
        nonCbamQuantity: '10',
        nonCbamTonnes: '10',
        otherCbamTonnes: '50',
        distributedTonnes: '100',
        remainingTonnes: '0',
        balanceStatus: 'BALANCED',
        productUses: [
          {
            id: 'use-1',
            processId: 'proc-1',
            organizationId: 'org-1',
            reportingPeriodBindingId: 'binding-1',
            sourceProductProfileVersionId: 'prof-a',
            targetProductProfileVersionId: 'prof-b',
            quantity: '50',
            unit: 't',
            quantityTonnes: '50',
            notes: null,
            rowVersion: 1,
          },
        ],
      },
    });
    flushListLoad([withUse]);
    tick();
    component.openProcess(withUse.id);
    flushDetail(withUse);
    tick();
    expect(fixture.nativeElement.textContent).toContain('Nuts');
    const targets = component.targetProfileOptions().map((p) => p.id);
    expect(targets).toContain('prof-b');
    expect(targets).not.toContain('prof-a');

    component.productUseForm.setValue({
      targetProductProfileVersionId: 'prof-b',
      quantity: '5',
      unit: 't',
    });
    component.addProductUse();
    const createUse = httpMock.expectOne(
      (r) => r.url.endsWith('/product-uses') && r.method === 'POST',
    );
    expect(createUse.request.body.targetProductProfileVersionId).toBe('prof-b');
    expect(createUse.request.body.quantity).toBe('5');
    createUse.flush(withUse.distribution.productUses[0]);
    flushAfterMutation([withUse], withUse);
    tick();

    component.removeProductUse(withUse.distribution.productUses[0]);
    httpMock
      .expectOne((r) => r.url.includes('/product-uses/use-1') && r.method === 'DELETE')
      .flush(null);
    const plain = makeProcess();
    flushAfterMutation([plain], plain);
    tick();
  }));

  it('shows backend balance status and allows unbalanced draft save', fakeAsync(() => {
    const unbalanced = makeProcess({
      readiness: {
        ...emptyReadiness,
        status: 'UNBALANCED',
        blockingIssueCodes: ['PRODUCT_DISTRIBUTION_UNBALANCED'],
        balanceStatus: 'UNBALANCED',
        remainingTonnes: '25',
      },
      distribution: {
        ...makeProcess().distribution,
        marketedQuantity: '75',
        marketedTonnes: '75',
        distributedTonnes: '75',
        remainingTonnes: '25',
        balanceStatus: 'UNBALANCED',
      },
    });
    flushListLoad([unbalanced]);
    tick();
    component.openProcess(unbalanced.id);
    flushDetail(unbalanced);
    tick();
    expect(fixture.nativeElement.querySelector('[data-testid="pp-balance-status"]')?.textContent)
      .toContain('Not balanced');
    expect(fixture.nativeElement.textContent).toContain(
      'Distribute the remaining quantity before this process is ready.',
    );
    expect(fixture.nativeElement.querySelector('[data-testid="pp-readiness-status"]')?.textContent)
      .toContain('Not balanced');
    expect(fixture.nativeElement.querySelector('[data-testid="pp-save-draft"]')).toBeTruthy();
    component.saveDraft();
    httpMock
      .expectOne(
        (r) => r.method === 'PATCH' && r.url.endsWith(`/production-processes/${unbalanced.id}`),
      )
      .flush(unbalanced);
    flushAfterMutation([unbalanced], unbalanced);
    tick();
  }));

  it('shows direct/indirect values read-only and allocation links when missing', fakeAsync(() => {
    const missing = makeProcess({
      directEmissionsAllocation: emptyAllocation(false),
      indirectEmissionsAllocation: {
        ...emptyAllocation(false),
        blockingCode: 'INDIRECT_EMISSIONS_ALLOCATION_NOT_READY',
        resultUnit: null,
        electricityUnit: 'MWh',
      },
    });
    flushListLoad([missing]);
    tick();
    component.openProcess(missing.id);
    flushDetail(missing);
    tick();
    const emissions = fixture.nativeElement.querySelector(
      '[data-testid="pp-emissions"]',
    ) as HTMLElement;
    expect(emissions.textContent).toContain('tCO2');
    expect(emissions.querySelector('input')).toBeFalsy();
    expect(emissions.textContent).toContain('Complete the direct emissions allocation.');
    expect(emissions.textContent).toContain('Direct Emissions Allocation');
    expect(emissions.textContent).toContain('Indirect Emissions Allocation');
    spyOn(component.goToDirectEmissionsAllocation, 'emit');
    const deaBtn = Array.from(emissions.querySelectorAll('button')).find((b) =>
      (b as HTMLElement).textContent?.includes('Direct Emissions Allocation'),
    ) as HTMLElement;
    deaBtn.click();
    expect(component.goToDirectEmissionsAllocation.emit).toHaveBeenCalled();
  }));

  it('displays allocated electricity and indirect emissions from process response only', fakeAsync(() => {
    const process = makeProcess();
    flushListLoad([process]);
    tick();
    component.openProcess(process.id);
    flushDetail(process);
    tick();
    const elec = fixture.nativeElement.querySelector(
      '[data-testid="pp-allocated-electricity"]',
    ) as HTMLElement;
    const em = fixture.nativeElement.querySelector(
      '[data-testid="pp-allocated-indirect"]',
    ) as HTMLElement;
    expect(elec.textContent).toContain('9.75000000');
    expect(elec.textContent).toContain('MWh');
    expect(elec.querySelector('input')).toBeFalsy();
    expect(em.textContent).toContain('4.20000000');
    expect(em.textContent).toContain('tCO2e');
    expect(em.querySelector('input')).toBeFalsy();
    const pending = httpMock.match((r) => r.url.includes('/indirect-emissions-allocation/'));
    expect(pending.length).toBe(0);
  }));

  it('shows product-allocation-missing readiness message without joining IEA detail', fakeAsync(() => {
    const missing = makeProcess({
      indirectEmissionsAllocation: {
        ...emptyAllocation(false),
        currentResultId: 'iea-1',
        isReady: false,
        isStale: false,
        allocatedElectricityMwh: null,
        allocatedIndirectEmissionsTco2e: null,
        productAllocatedValue: null,
        resultUnit: 'tCO2e',
        electricityUnit: 'MWh',
        blockingCode: 'INDIRECT_EMISSIONS_PRODUCT_ALLOCATION_MISSING',
      },
      readiness: {
        ...emptyReadiness,
        status: 'INCOMPLETE',
        blockingIssueCodes: ['INDIRECT_EMISSIONS_PRODUCT_ALLOCATION_MISSING'],
      },
    });
    flushListLoad([missing]);
    tick();
    component.openProcess(missing.id);
    flushDetail(missing);
    tick();
    expect(fixture.nativeElement.textContent).toContain(
      'Complete the indirect emissions allocation for this product.',
    );
    expect(
      fixture.nativeElement.querySelector('[data-testid="pp-allocated-electricity"]')?.textContent,
    ).toContain('—');
    expect(httpMock.match((r) => r.url.includes('/indirect-emissions-allocation/')).length).toBe(0);
  }));

  it('does not implement client electricity allocation math', () => {
    expect((component as unknown as { allocateElectricity?: unknown }).allocateElectricity)
      .toBeUndefined();
    expect(formatDecimalDisplay('9.75000000')).toBe('9.75000000');
  });

  it('toggles measurable heat fields and clears nulls on No', fakeAsync(() => {
    const process = makeProcess();
    flushListLoad([process]);
    tick();
    component.openProcess(process.id);
    flushDetail(process);
    tick();
    component.form.controls.hasMeasurableHeat.setValue('yes');
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('[data-testid="pp-heat"]')?.textContent).toContain(
      'Imported heat amount',
    );
    component.form.patchValue({
      heatImportedQuantity: '1',
      heatImportedEf: '2',
      heatExportedQuantity: '0',
      heatExportedEf: '2',
    });
    component.form.controls.hasMeasurableHeat.setValue('no');
    component.saveDraft();
    const req = httpMock.expectOne(
      (r) => r.method === 'PATCH' && r.url.endsWith(`/production-processes/${process.id}`),
    );
    expect(req.request.body.hasMeasurableHeat).toBeFalse();
    expect(req.request.body.heatImportedQuantity).toBeNull();
    expect(req.request.body.heatImportedEf).toBeNull();
    expect(JSON.stringify(req.request.body)).not.toContain('input heat');
    req.flush(process);
    flushAfterMutation([process], process);
    tick();
  }));

  it('does not implement client heat calculation constants in component source path', () => {
    // Guard: util/component must not hard-code workbook heat arithmetic.
    expect(formatDecimalDisplay('1.25')).toBe('1.25');
    expect((component as unknown as { calculateHeat?: unknown }).calculateHeat).toBeUndefined();
  });

  it('toggles waste-gas fields and clears nulls on No without client constants', fakeAsync(() => {
    const process = makeProcess();
    flushListLoad([process]);
    tick();
    component.openProcess(process.id);
    flushDetail(process);
    tick();
    component.form.controls.hasWasteGas.setValue('yes');
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Imported waste gas');
    component.form.controls.hasWasteGas.setValue('no');
    component.saveDraft();
    const req = httpMock.expectOne(
      (r) => r.method === 'PATCH' && r.url.endsWith(`/production-processes/${process.id}`),
    );
    expect(req.request.body.hasWasteGas).toBeFalse();
    expect(req.request.body.wasteGasImportedQuantity).toBeNull();
    expect(JSON.stringify(req.request.body)).not.toContain('56.1');
    expect(JSON.stringify(req.request.body)).not.toContain('0.667');
    req.flush(process);
    flushAfterMutation([process], process);
    tick();
  }));

  it('toggles exported-electricity fields and never multiplies qty×EF on the client', fakeAsync(() => {
    const process = makeProcess({
      processExportedElectricity: {
        ...makeProcess().processExportedElectricity,
        hasExportedElectricity: true,
        quantity: '2.5',
        quantityUnit: 'MWh',
        quantityMwh: '2.50000000',
        emissionFactor: '0.4',
        efUnit: 'tCO2/MWh',
        provenance: 'meter',
        calculationStatus: 'CALCULATED',
        attributedDirectTco2e: '-1.00000000',
        formulaRef: 'D_Processes!T72=-L71*L72',
        reconciliationStatus: 'MATCHED',
      },
    });
    flushListLoad([process]);
    tick();
    component.openProcess(process.id);
    flushDetail(process);
    tick();
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Does this process export electricity?');
    expect(fixture.nativeElement.querySelector('[data-testid="pp-export-elec-attributed"]')?.textContent)
      .toContain('-1.00000000');
    component.form.controls.hasExportedElectricity.setValue('yes');
    component.form.controls.exportedElectricityQuantity.setValue('2.5');
    component.form.controls.exportedElectricityEmissionFactor.setValue('0.4');
    component.form.controls.exportedElectricityProvenance.setValue('meter');
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('[data-testid="pp-export-elec-qty"]')).toBeTruthy();
    component.saveDraft();
    const req = httpMock.expectOne(
      (r) => r.method === 'PATCH' && r.url.endsWith(`/production-processes/${process.id}`),
    );
    expect(req.request.body.hasExportedElectricity).toBeTrue();
    expect(req.request.body.exportedElectricityQuantity).toBe('2.5');
    expect(req.request.body.exportedElectricityEmissionFactor).toBe('0.4');
    expect(req.request.body.exportedElectricityUnit).toBe('MWh');
    expect(req.request.body.exportedElectricityEfUnit).toBe('tCO2/MWh');
    // T72 is server-only: never send attributedDirectTco2e or a client product.
    expect(Object.keys(req.request.body)).not.toContain('attributedDirectTco2e');
    expect(Object.keys(req.request.body)).not.toContain('attributedDirectTco2');
    req.flush(process);
    flushAfterMutation([process], process);
    tick();

    component.form.controls.hasExportedElectricity.setValue('no');
    component.saveDraft();
    const clearReq = httpMock.expectOne(
      (r) => r.method === 'PATCH' && r.url.endsWith(`/production-processes/${process.id}`),
    );
    expect(clearReq.request.body.hasExportedElectricity).toBeFalse();
    expect(clearReq.request.body.exportedElectricityQuantity).toBeNull();
    expect(clearReq.request.body.exportedElectricityEmissionFactor).toBeNull();
    clearReq.flush(process);
    flushAfterMutation([process], process);
    tick();
  }));

  it('shows exported-electricity reconciliation warning when MISMATCHED', fakeAsync(() => {
    const process = makeProcess({
      processExportedElectricity: {
        ...makeProcess().processExportedElectricity,
        hasExportedElectricity: true,
        reconciliationStatus: 'MISMATCHED',
        reconciliationDifferenceMwh: '1.00000000',
        attributedDirectTco2e: '-0.50000000',
      },
    });
    flushListLoad([process]);
    tick();
    component.openProcess(process.id);
    flushDetail(process);
    tick();
    fixture.detectChanges();
    expect(
      fixture.nativeElement.querySelector('[data-testid="pp-export-elec-recon-warn"]')?.textContent,
    ).toContain('Process and facility exported electricity totals do not match.');
  }));

  it('does not implement client T72 calculation on the component', () => {
    expect((component as unknown as { calculateT72?: unknown }).calculateT72).toBeUndefined();
    expect((component as unknown as { computeExportedElectricity?: unknown }).computeExportedElectricity)
      .toBeUndefined();
  });

  it('loads controlled list options from API', fakeAsync(() => {
    const process = makeProcess();
    flushListLoad([process]);
    tick();
    component.openProcess(process.id);
    flushDetail(process);
    tick();
    expect(component.dataQualityList()?.items[0].labelEn).toBe('High quality');
    expect(fixture.nativeElement.querySelector('[data-testid="pp-data-quality"]')?.textContent)
      .toContain('Data quality');
    expect(fixture.nativeElement.textContent).toContain('Workbook data quality help.');
  }));

  it('preserves decimal string / blank-null / zero behavior', () => {
    expect(optionalDecimalOrNull('')).toBeNull();
    expect(optionalDecimalOrNull('  ')).toBeNull();
    expect(optionalDecimalOrNull('0')).toBe('0');
    expect(optionalDecimalOrNull('12.3400')).toBe('12.3400');
    expect(isBlankDecimalInput(null)).toBeTrue();
    expect(formatDecimalDisplay(null)).toBe('—');
    expect(formatDecimalDisplay('0')).toBe('0');
  });

  it('shows conflict message and Reload on rowVersion conflict', fakeAsync(() => {
    const process = makeProcess();
    flushListLoad([process]);
    tick();
    component.openProcess(process.id);
    flushDetail(process);
    tick();
    component.saveDraft();
    const req = httpMock.expectOne(
      (r) => r.method === 'PATCH' && r.url.endsWith(`/production-processes/${process.id}`),
    );
    req.flush(
      {
        error: {
          code: 'CONFLICT',
          message: 'row version mismatch',
          details: [{ code: 'CONFLICT' }],
        },
      },
      { status: 409, statusText: 'Conflict' },
    );
    fixture.detectChanges();
    expect(component.conflictMessage()).toBe(
      'This process changed. Reload it and try again.',
    );
    expect(fixture.nativeElement.textContent).toContain('Reload');
  }));

  it('requires archive confirmation', fakeAsync(() => {
    const process = makeProcess();
    flushListLoad([process]);
    tick();
    component.openProcess(process.id);
    flushDetail(process);
    tick();
    component.requestArchive();
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Archive this process?');
    component.cancelArchive();
    fixture.detectChanges();
    expect(component.showArchiveConfirm()).toBeFalse();
    component.requestArchive();
    component.confirmArchive();
    httpMock
      .expectOne(
        (r) => r.url.endsWith(`/production-processes/${process.id}/archive`) && r.method === 'POST',
      )
      .flush({ ...process, status: 'ARCHIVED' });
    flushListLoad([]);
    tick();
    expect(component.selected()).toBeNull();
  }));
});

describe('production-processes.util', () => {
  it('maps readiness and blocking codes', () => {
    expect(mapProcessReadinessStatusLabel('EMPTY')).toBe('No data');
    expect(mapProcessReadinessStatusLabel('READY')).toBe('Ready');
    expect(mapProcessReadinessStatusLabel('STALE')).toBe('Needs update');
    expect(mapBalanceStatusLabel('BALANCED')).toBe('Balanced');
    expect(mapBalanceStatusLabel('UNBALANCED')).toBe('Not balanced');
    expect(mapProcessBlockingCode('PROCESS_PRODUCT_REQUIRED')).toBe('Select a product.');
    expect(mapProcessBlockingCode('UNKNOWN_CODE_X')).toBe('UNKNOWN_CODE_X');
  });

  it('maps conflict errors', () => {
    const err = new HttpErrorResponse({
      status: 409,
      error: { error: { code: 'CONFLICT', message: 'conflict' } },
    });
    expect(mapProcessApiError(err)).toBe('This process changed. Reload it and try again.');
  });
});
