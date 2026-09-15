import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { HttpErrorResponse, provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { signal } from '@angular/core';
import { By } from '@angular/platform-browser';
import { environment } from '../../../../environments/environment';
import { AuthService } from '../../../core/services/auth.service';
import {
  CbamInstallation,
  CbamPrecursorDefaultDataset,
  CbamPrecursorDefaultValue,
  CbamProductProfile,
  CbamPurchasedPrecursor,
  CbamPurchasedPrecursorMetadata,
  CbamPurchasedPrecursorReadiness,
} from '../cbam-api.service';
import { CbamPurchasedPrecursorsComponent } from './purchased-precursors.component';
import {
  MODE_EU_DEFAULT,
  MODE_SUPPLIER_DATA,
  formatDecimalDisplay,
  isBlankDecimalInput,
  mapPrecursorApiError,
  mapPrecursorBalanceStatusLabel,
  mapPrecursorBlockingCode,
  mapPrecursorModeLabel,
  mapPrecursorReadinessStatusLabel,
  mapResolutionStatusLabel,
  optionalDecimalOrNull,
  precursorBalanceHelpMessage,
} from './purchased-precursors.util';

describe('CbamPurchasedPrecursorsComponent', () => {
  let fixture: ComponentFixture<CbamPurchasedPrecursorsComponent>;
  let component: CbamPurchasedPrecursorsComponent;
  let httpMock: HttpTestingController;

  const apiBase = `${environment.apiUrl}${environment.apiV1Prefix}`;
  const orgBase = `${apiBase}/cbam/organizations/org-1`;
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
    status: 'active',
    validFrom: null,
    validTo: null,
    classificationReady: true,
    productName: 'Screws',
    cnCodeId: 'cn-1',
    cnNormalizedCode: '73181595',
    cnDisplayCode: '7318 15 95',
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
    cnDisplayCode: '7318 16 91',
  };

  const dataset: CbamPrecursorDefaultDataset = {
    id: 'ds-1',
    datasetCode: 'CBAM_EU_DEFAULT_VALUES',
    datasetVersion: 'IR_2025_2621_v20260204',
    contentChecksum: 'checksum-1',
    sourceWorkbookName: 'DVs_as_adopted_v20260204.xlsx',
    sourceWorkbookSha256: 'sha-1',
    sourceTemplateVersion: 'v20260204',
    regulationReference: 'Implementing Regulation (EU) 2025/2621',
    validFrom: '2026-01-01',
    validUntil: null,
    status: 'ACTIVE',
    valueCount: 12532,
  };

  const metadata: CbamPurchasedPrecursorMetadata = {
    methodologyCode: 'PURCHASED_PRECURSOR_V1',
    methodologyVersion: '1.0.0',
    workbookFilename: 'CBAM SEE V2.1.xlsx',
    workbookSha256: 'sha-see',
    workbookPrimarySheet: 'E_PurchPrec',
    workbookFormulaRefs: 'L52=L50*L51',
    supportedDataSourceModes: ['EU_DEFAULT', 'SUPPLIER_DATA'],
    units: {
      quantity: 't',
      specificDirect: 'tCO2e/t',
      specificIndirect: 'tCO2e/t',
      electricityIntensity: 'MWh/t',
      electricityEmissionFactor: 'tCO2e/MWh',
      result: 'tCO2e',
    },
    fieldMap: {},
    extraction: {},
    controlledLists: [
      {
        listCode: 'CONST_MeasDefaultUnknown',
        titleEn: 'Determination of the parameter',
        workbookNamedRange: 'CONST_MeasDefaultUnknown',
        workbookSheet: 'Parameters_Constants',
        helpEn: null,
        items: [
          {
            code: 'MEASURED',
            labelEn: 'Measured',
            descriptionEn: null,
            sortOrder: 1,
            workbookRef: 'ref',
          },
        ],
      },
      {
        listCode: 'CONST_ElecSource',
        titleEn: 'Source of the emission factor of the electricity',
        workbookNamedRange: 'CONST_ElecSource',
        workbookSheet: 'Parameters_Constants',
        helpEn: null,
        items: [
          {
            code: 'D.4(a)',
            labelEn: 'D.4(a)',
            descriptionEn: null,
            sortOrder: 1,
            workbookRef: 'ref',
          },
        ],
      },
      {
        listCode: 'CONST_DefaultJustification',
        titleEn: 'Justification for using default values',
        workbookNamedRange: 'CONST_DataQualityJustification',
        workbookSheet: 'Parameters_Constants',
        helpEn: null,
        items: [
          {
            code: 'SUPPLIER_DATA_UNAVAILABLE',
            labelEn: 'Data gaps',
            descriptionEn: null,
            sortOrder: 1,
            workbookRef: 'ref',
          },
        ],
      },
    ],
    defaultValueDataset: dataset,
    otherCountriesNote:
      'The "Other Countries and Territories" group is never selected automatically.',
    rollupNote:
      'Phase 10A keeps purchased-precursor embedded emissions standalone. They are not rolled up into product totals or any allocation result.',
  };

  function makeDefaultValue(
    overrides: Partial<CbamPrecursorDefaultValue> = {},
  ): CbamPrecursorDefaultValue {
    return {
      id: 'dv-1',
      datasetId: 'ds-1',
      countryName: 'Türkiye',
      isOtherCountriesGroup: false,
      cnNormalizedCode: '72071100',
      cnDisplayCode: '7207 11 00',
      goodsCategory: 'Iron and steel',
      goodsDescription: 'Semi-finished products of iron',
      productionRoute: 'Basic oxygen furnace',
      directValue: '1.60000000',
      directValueStatus: 'NUMERIC',
      indirectValue: '0.40000000',
      indirectValueStatus: 'NUMERIC',
      totalValue: '2.00000000',
      totalValueStatus: 'NUMERIC',
      directUnit: 'tCO2e/t',
      indirectUnit: 'tCO2e/t',
      unitNote: null,
      markedUpTotals: {},
      originalKeys: {},
      lookupKey: 'türkiye|72071100|basic oxygen furnace|',
      sourceSheet: 'Türkiye',
      sourceRow: 12,
      ...overrides,
    };
  }

  const supplierReadiness: CbamPurchasedPrecursorReadiness = {
    precursorId: 'prec-1',
    reportingPeriodBindingId: 'binding-1',
    status: 'INCOMPLETE',
    blockingIssueCodes: ['PRECURSOR_DISTRIBUTION_UNBALANCED'],
    informationalCodes: [],
    balanceStatus: 'UNBALANCED',
    remainingTonnes: '10',
    resolutionStatus: 'NOT_APPLICABLE',
  };

  function makePrecursor(
    overrides: Partial<CbamPurchasedPrecursor> = {},
  ): CbamPurchasedPrecursor {
    return {
      id: 'prec-1',
      organizationId: 'org-1',
      reportingPeriodBindingId: 'binding-1',
      installationProfileId: 'inst-1',
      purchasedInputRecordId: null,
      supplierId: null,
      name: 'Hot rolled coil',
      identifier: 'PRE-1',
      aggregatedGoodsCategory: 'Iron and steel',
      cnNormalizedCode: '72071100',
      cnDisplayCode: '7207 11 00',
      countryOfOrigin: 'Türkiye',
      productionRoute: 'Basic oxygen furnace',
      dataSourceMode: MODE_SUPPLIER_DATA,
      status: 'draft',
      notes: null,
      rowVersion: 1,
      readiness: supplierReadiness,
      distribution: {
        quantity: '100',
        quantityUnit: 't',
        purchasedTonnes: '100',
        nonCbamQuantity: null,
        nonCbamQuantityUnit: null,
        nonCbamTonnes: null,
        productUseTonnes: '90',
        distributedTonnes: '90',
        remainingTonnes: '10',
        balanceStatus: 'UNBALANCED',
        formulaRef: 'E_PurchPrec!L39=L25-SUM(L28:L38)',
        productUses: [],
      },
      supplierData: {
        applicable: true,
        specificDirectEmbeddedEmissions: '1.20000000',
        specificDirectUnit: 'tCO2e/t',
        specificDirectSourceCode: 'MEASURED',
        electricityConsumptionIntensity: '2',
        electricityIntensityUnit: 'MWh/t',
        electricityIntensitySourceCode: 'MEASURED',
        electricityEmissionFactor: '0.5',
        electricityEfUnit: 'tCO2e/MWh',
        electricityEfSourceCode: 'D.4(a)',
        specificIndirectEmbeddedEmissions: '0.75000000',
        specificIndirectUnit: 'tCO2e/t',
        provenanceNotes: 'Supplier letter',
        evidenceReference: 'DOC-1',
      },
      defaultSource: {
        applicable: false,
        resolutionStatus: 'NOT_APPLICABLE',
        issueCode: null,
        fromSnapshot: false,
        datasetId: null,
        datasetCode: null,
        datasetVersion: null,
        contentChecksum: null,
        defaultValueId: null,
        lookupKey: null,
        specificDirectEmbeddedEmissions: null,
        specificDirectStatus: null,
        specificDirectUnit: null,
        specificIndirectEmbeddedEmissions: null,
        specificIndirectStatus: null,
        specificIndirectUnit: null,
        justificationCode: null,
        candidateCount: 0,
        snapshot: null,
        otherCountriesNote:
          'The "Other Countries and Territories" group is never selected automatically.',
      },
      calculation: {
        status: 'CALCULATED',
        valueSource: MODE_SUPPLIER_DATA,
        quantityTonnes: '100',
        specificDirectEmbeddedEmissions: '1.20000000',
        specificIndirectEmbeddedEmissions: '0.75000000',
        totalDirectEmbeddedEmissions: '120.00000000',
        totalIndirectEmbeddedEmissions: '75.00000000',
        totalEmbeddedEmissions: '195.00000000',
        resultUnit: 'tCO2e',
        formulaRefs: 'T49=L25*L49; T52=L25*L52',
        rollupNote: metadata.rollupNote,
      },
      ...overrides,
    };
  }

  function makeEuDefaultPrecursor(
    overrides: Partial<CbamPurchasedPrecursor> = {},
  ): CbamPurchasedPrecursor {
    const base = makePrecursor();
    return {
      ...base,
      dataSourceMode: MODE_EU_DEFAULT,
      supplierData: {
        ...base.supplierData,
        applicable: false,
        specificDirectEmbeddedEmissions: null,
        specificDirectUnit: null,
        specificDirectSourceCode: null,
        electricityConsumptionIntensity: null,
        electricityIntensityUnit: null,
        electricityIntensitySourceCode: null,
        electricityEmissionFactor: null,
        electricityEfUnit: null,
        electricityEfSourceCode: null,
        specificIndirectEmbeddedEmissions: null,
        specificIndirectUnit: null,
      },
      defaultSource: {
        ...base.defaultSource,
        applicable: true,
        resolutionStatus: 'UNRESOLVED',
        issueCode: 'DEFAULT_VALUE_UNRESOLVED',
      },
      ...overrides,
    };
  }

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CbamPurchasedPrecursorsComponent],
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

    fixture = TestBed.createComponent(CbamPurchasedPrecursorsComponent);
    component = fixture.componentInstance;
    httpMock = TestBed.inject(HttpTestingController);
    fixture.componentRef.setInput('bindingId', 'binding-1');
    fixture.componentRef.setInput('canConfigure', true);
    fixture.componentRef.setInput('canMutate', true);
  });

  afterEach(() => {
    httpMock.verify();
  });

  function flushListLoad(items: CbamPurchasedPrecursor[] = []): void {
    fixture.detectChanges();
    for (const req of httpMock.match(() => true)) {
      const url = req.request.url;
      if (req.request.method !== 'GET') {
        continue;
      }
      if (url.includes('/purchased-precursors/metadata')) {
        req.flush(metadata);
      } else if (/purchased-precursors(\?|$)/.test(url)) {
        req.flush({
          items,
          page: 1,
          pageSize: 100,
          totalItems: items.length,
          totalPages: 1,
        });
      } else if (url.includes('/installations')) {
        req.flush({ items: [installation], page: 1, pageSize: 100, totalItems: 1, totalPages: 1 });
      } else if (url.includes('/product-profiles')) {
        req.flush({
          items: [profileA, profileB],
          page: 1,
          pageSize: 100,
          totalItems: 2,
          totalPages: 1,
        });
      } else if (url.includes('/purchased-inputs')) {
        req.flush({ items: [], page: 1, pageSize: 100, totalItems: 0, totalPages: 0 });
      } else if (url.includes('/suppliers')) {
        req.flush({ items: [], page: 1, pageSize: 20, totalItems: 0, totalPages: 0 });
      }
    }
    fixture.detectChanges();
  }

  function flushDetail(
    precursor: CbamPurchasedPrecursor,
    readiness?: CbamPurchasedPrecursorReadiness,
  ): void {
    for (const req of httpMock.match(() => true)) {
      const url = req.request.url;
      if (req.request.method !== 'GET') {
        continue;
      }
      if (url.endsWith(`/purchased-precursors/${precursor.id}`)) {
        req.flush(precursor);
      } else if (url.endsWith(`/purchased-precursors/${precursor.id}/readiness`)) {
        req.flush(readiness ?? precursor.readiness);
      }
    }
    fixture.detectChanges();
  }

  function flushAfterMutation(
    items: CbamPurchasedPrecursor[],
    detail: CbamPurchasedPrecursor,
  ): void {
    flushListLoad(items);
    flushDetail(detail);
  }

  function openDetail(precursor: CbamPurchasedPrecursor): void {
    component.openPrecursor(precursor.id);
    flushDetail(precursor);
  }

  it('renders the Purchased precursors section with an empty state', fakeAsync(() => {
    flushListLoad([]);
    tick();
    const host = fixture.nativeElement.querySelector(
      '[data-testid="purchased-precursors"]',
    ) as HTMLElement;
    expect(host).toBeTruthy();
    expect(host.textContent).toContain('Purchased precursors');
    expect(fixture.nativeElement.querySelector('[data-testid="ppc-empty"]')).toBeTruthy();
    expect(host.textContent).toContain(
      'No purchased precursors have been added for this period.',
    );
  }));

  it('lists precursors from the API and opens a detail form', fakeAsync(() => {
    const precursor = makePrecursor();
    flushListLoad([precursor]);
    tick();
    expect(fixture.nativeElement.textContent).toContain('Hot rolled coil');
    expect(fixture.nativeElement.textContent).toContain('Supplier data');
    const openBtn = Array.from(fixture.nativeElement.querySelectorAll('button')).find((b) =>
      (b as HTMLElement).textContent?.includes('Open'),
    ) as HTMLElement;
    openBtn.click();
    flushDetail(precursor);
    tick();
    expect(fixture.nativeElement.querySelector('[data-testid="ppc-detail"]')).toBeTruthy();
    expect(component.form.controls.name.value).toBe('Hot rolled coil');
    expect(component.form.controls.quantity.value).toBe('100');
  }));

  it('offers Supplier data and EU default only, never HYBRID', fakeAsync(() => {
    const precursor = makePrecursor();
    flushListLoad([precursor]);
    tick();
    openDetail(precursor);
    tick();
    const modeSection = fixture.nativeElement.querySelector(
      '[data-testid="ppc-mode"]',
    ) as HTMLElement;
    const radios = fixture.debugElement
      .queryAll(By.css('[data-testid="ppc-mode"] mat-radio-button'))
      .map((r) => (r.nativeElement as HTMLElement).textContent?.trim());
    expect(radios).toEqual(['Supplier data', 'EU default']);
    expect(modeSection.textContent?.toUpperCase()).not.toContain('HYBRID');
    expect((fixture.nativeElement.textContent as string).toUpperCase()).not.toContain('HYBRID');
  }));

  it('hides mutations when view-only', fakeAsync(() => {
    fixture.componentRef.setInput('canConfigure', false);
    fixture.componentRef.setInput('canMutate', false);
    const precursor = makePrecursor();
    flushListLoad([precursor]);
    tick();
    expect(fixture.nativeElement.textContent).not.toContain('Create draft precursor');
    openDetail(precursor);
    tick();
    expect(fixture.nativeElement.querySelector('[data-testid="ppc-save-draft"]')).toBeFalsy();
    expect(fixture.nativeElement.querySelector('[data-testid="ppc-submit-product-use"]'))
      .toBeFalsy();
    expect(component.canEdit()).toBeFalse();
  }));

  it('hides edit actions for an archived precursor', fakeAsync(() => {
    const archived = makePrecursor({ status: 'archived' });
    flushListLoad([archived]);
    tick();
    openDetail(archived);
    tick();
    expect(component.canEdit()).toBeFalse();
    expect(fixture.nativeElement.querySelector('[data-testid="ppc-save-draft"]')).toBeFalsy();
  }));

  it('creates a draft precursor with installation, name and mode', fakeAsync(() => {
    flushListLoad([]);
    tick();
    component.startCreate();
    fixture.detectChanges();
    component.createForm.setValue({
      installationProfileId: 'inst-1',
      name: 'Draft precursor',
      dataSourceMode: MODE_EU_DEFAULT,
    });
    component.createDraft();
    const req = httpMock.expectOne(
      (r) => r.url === `${bindingBase}/purchased-precursors` && r.method === 'POST',
    );
    expect(req.request.body.installationProfileId).toBe('inst-1');
    expect(req.request.body.name).toBe('Draft precursor');
    expect(req.request.body.dataSourceMode).toBe(MODE_EU_DEFAULT);
    const created = makeEuDefaultPrecursor({ id: 'prec-new', name: 'Draft precursor' });
    req.flush(created);
    flushAfterMutation([created], created);
    tick();
    expect(component.selected()?.id).toBe('prec-new');
  }));

  it('clears supplier fields when switching to EU default', fakeAsync(() => {
    const precursor = makePrecursor();
    flushListLoad([precursor]);
    tick();
    openDetail(precursor);
    tick();
    expect(component.form.controls.specificDirectEmbeddedEmissions.value).toBe('1.20000000');
    component.form.controls.dataSourceMode.setValue(MODE_EU_DEFAULT);
    fixture.detectChanges();
    expect(component.form.controls.specificDirectEmbeddedEmissions.value).toBe('');
    expect(component.form.controls.electricityConsumptionIntensity.value).toBe('');
    expect(component.form.controls.electricityEmissionFactor.value).toBe('');
    expect(component.form.controls.electricityEfSourceCode.value).toBe('');
    expect(fixture.nativeElement.querySelector('[data-testid="ppc-supplier"]')).toBeFalsy();

    component.saveDraft();
    const req = httpMock.expectOne(
      (r) => r.method === 'PATCH' && r.url.endsWith(`/purchased-precursors/${precursor.id}`),
    );
    expect(req.request.body.dataSourceMode).toBe(MODE_EU_DEFAULT);
    expect(req.request.body.specificDirectEmbeddedEmissions).toBeNull();
    expect(req.request.body.electricityConsumptionIntensity).toBeNull();
    expect(req.request.body.electricityEmissionFactor).toBeNull();
    expect(req.request.body.electricityEfSourceCode).toBeNull();
    const updated = makeEuDefaultPrecursor({ rowVersion: 2 });
    req.flush(updated);
    flushAfterMutation([updated], updated);
    tick();
  }));

  it('clears EU default selection when switching to supplier data', fakeAsync(() => {
    const precursor = makeEuDefaultPrecursor({
      defaultSource: {
        ...makeEuDefaultPrecursor().defaultSource,
        resolutionStatus: 'RESOLVED',
        fromSnapshot: true,
        defaultValueId: 'dv-1',
        datasetId: 'ds-1',
        datasetVersion: 'IR_2025_2621_v20260204',
        justificationCode: 'SUPPLIER_DATA_UNAVAILABLE',
        specificDirectEmbeddedEmissions: '1.60000000',
        specificDirectStatus: 'NUMERIC',
        specificDirectUnit: 'tCO2e/t',
        specificIndirectEmbeddedEmissions: '0.40000000',
        specificIndirectStatus: 'NUMERIC',
        specificIndirectUnit: 'tCO2e/t',
        lookupKey: 'türkiye|72071100|basic oxygen furnace|',
      },
    });
    flushListLoad([precursor]);
    tick();
    openDetail(precursor);
    tick();
    expect(component.selectedDefaultValueId()).toBe('dv-1');
    expect(component.form.controls.defaultJustificationCode.value).toBe(
      'SUPPLIER_DATA_UNAVAILABLE',
    );

    component.form.controls.dataSourceMode.setValue(MODE_SUPPLIER_DATA);
    fixture.detectChanges();
    expect(component.selectedDefaultValueId()).toBeNull();
    expect(component.form.controls.defaultJustificationCode.value).toBe('');
    expect(fixture.nativeElement.querySelector('[data-testid="ppc-default"]')).toBeFalsy();

    component.saveDraft();
    const req = httpMock.expectOne(
      (r) => r.method === 'PATCH' && r.url.endsWith(`/purchased-precursors/${precursor.id}`),
    );
    expect(req.request.body.dataSourceMode).toBe(MODE_SUPPLIER_DATA);
    expect(req.request.body.defaultValueId).toBeNull();
    expect(req.request.body.defaultJustificationCode).toBeNull();
    const updated = makePrecursor({ rowVersion: 2 });
    req.flush(updated);
    flushAfterMutation([updated], updated);
    tick();
  }));

  it('shows the server specific indirect value without multiplying intensity by factor', fakeAsync(() => {
    const precursor = makePrecursor();
    flushListLoad([precursor]);
    tick();
    openDetail(precursor);
    tick();
    const indirect = fixture.nativeElement.querySelector(
      '[data-testid="ppc-specific-indirect"]',
    ) as HTMLElement;
    // Intensity 2 × factor 0.5 would be 1; the server value 0.75 must win.
    expect(indirect.textContent).toContain('0.75000000');
    expect(indirect.querySelector('input')).toBeFalsy();
    expect(
      (component as unknown as { computeSpecificIndirect?: unknown }).computeSpecificIndirect,
    ).toBeUndefined();
    expect(
      (component as unknown as { calculateEmbeddedEmissions?: unknown })
        .calculateEmbeddedEmissions,
    ).toBeUndefined();
  }));

  it('searches EU default values from the API and never auto-selects a row', fakeAsync(() => {
    const precursor = makeEuDefaultPrecursor();
    flushListLoad([precursor]);
    tick();
    openDetail(precursor);
    tick();
    expect(component.defaultSearchForm.controls.includeOtherCountries.value).toBeFalse();
    component.searchDefaultValues();
    const req = httpMock.expectOne(
      (r) =>
        r.method === 'GET' && r.url === `${orgBase}/purchased-precursors/default-values/search`,
    );
    expect(req.request.params.get('country')).toBe('Türkiye');
    expect(req.request.params.get('cn')).toBe('72071100');
    expect(req.request.params.get('includeOtherCountriesGroup')).toBe('false');
    const rows = [makeDefaultValue(), makeDefaultValue({ id: 'dv-2', productionRoute: 'EAF' })];
    req.flush({ items: rows, page: 1, pageSize: 20, totalItems: 2, totalPages: 1 });
    fixture.detectChanges();
    tick();
    expect(component.defaultResults().length).toBe(2);
    expect(component.selectedDefaultValueId()).toBeNull();
    expect(fixture.nativeElement.querySelector('[data-testid="ppc-default-results"]')).toBeTruthy();
  }));

  it('shows an UNRESOLVED message from the server', fakeAsync(() => {
    const precursor = makeEuDefaultPrecursor();
    flushListLoad([precursor]);
    tick();
    openDetail(precursor);
    tick();
    const status = fixture.nativeElement.querySelector(
      '[data-testid="ppc-resolution-status"]',
    ) as HTMLElement;
    expect(status.textContent).toContain('No default value found');
    expect(fixture.nativeElement.textContent).toContain(
      'No EU default value matches this country, CN code and production route.',
    );
  }));

  it('lists AMBIGUOUS candidates and requires an explicit pick', fakeAsync(() => {
    const precursor = makeEuDefaultPrecursor();
    flushListLoad([precursor]);
    tick();
    openDetail(precursor);
    tick();
    component.resolveDefaultValue();
    const req = httpMock.expectOne(
      (r) =>
        r.method === 'POST' && r.url === `${orgBase}/purchased-precursors/default-values/resolve`,
    );
    expect(req.request.body.countryOfOrigin).toBe('Türkiye');
    expect(req.request.body.cnCode).toBe('72071100');
    req.flush({
      status: 'AMBIGUOUS',
      issueCode: 'DEFAULT_VALUE_AMBIGUOUS',
      lookupKey: 'türkiye|72071100||',
      countryOfOrigin: 'Türkiye',
      cnNormalizedCode: '72071100',
      productionRoute: null,
      goodsDescription: null,
      dataset,
      value: null,
      candidateCount: 2,
      candidates: [makeDefaultValue(), makeDefaultValue({ id: 'dv-2', goodsDescription: 'Blooms' })],
      otherCountriesNote: metadata.otherCountriesNote,
    });
    fixture.detectChanges();
    tick();
    expect(component.selectedDefaultValueId()).toBeNull();
    expect(component.defaultResults().length).toBe(2);
    expect(fixture.nativeElement.textContent).toContain(
      'More than one EU default value matches',
    );
  }));

  it('previews a RESOLVED default value and saves defaultValueId', fakeAsync(() => {
    const precursor = makeEuDefaultPrecursor();
    flushListLoad([precursor]);
    tick();
    openDetail(precursor);
    tick();
    const candidate = makeDefaultValue();
    component.useDefaultCandidate(candidate);
    const resolveReq = httpMock.expectOne(
      (r) =>
        r.method === 'POST' && r.url === `${orgBase}/purchased-precursors/default-values/resolve`,
    );
    expect(resolveReq.request.body.goodsDescription).toBe('Semi-finished products of iron');
    resolveReq.flush({
      status: 'RESOLVED',
      issueCode: null,
      lookupKey: candidate.lookupKey,
      countryOfOrigin: 'Türkiye',
      cnNormalizedCode: '72071100',
      productionRoute: 'Basic oxygen furnace',
      goodsDescription: 'Semi-finished products of iron',
      dataset,
      value: candidate,
      candidateCount: 1,
      candidates: [candidate],
      otherCountriesNote: metadata.otherCountriesNote,
    });
    fixture.detectChanges();
    tick();
    const preview = fixture.nativeElement.querySelector(
      '[data-testid="ppc-default-preview"]',
    ) as HTMLElement;
    expect(preview.textContent).toContain('Default value found');
    expect(preview.textContent).toContain('1.60000000');
    expect(preview.textContent).toContain('0.40000000');
    expect(preview.textContent).toContain('IR_2025_2621_v20260204');
    expect(preview.querySelector('input')).toBeFalsy();

    component.form.controls.defaultJustificationCode.setValue('SUPPLIER_DATA_UNAVAILABLE');
    component.saveDraft();
    const patch = httpMock.expectOne(
      (r) => r.method === 'PATCH' && r.url.endsWith(`/purchased-precursors/${precursor.id}`),
    );
    expect(patch.request.body.defaultValueId).toBe('dv-1');
    expect(patch.request.body.defaultJustificationCode).toBe('SUPPLIER_DATA_UNAVAILABLE');
    expect(patch.request.body.cnCode).toBe('72071100');
    const saved = makeEuDefaultPrecursor({ rowVersion: 2 });
    patch.flush(saved);
    flushAfterMutation([saved], saved);
    tick();
  }));

  it('shows the immutable snapshot for a saved EU default value', fakeAsync(() => {
    const snapshotted = makeEuDefaultPrecursor({
      defaultSource: {
        ...makeEuDefaultPrecursor().defaultSource,
        resolutionStatus: 'RESOLVED',
        issueCode: null,
        fromSnapshot: true,
        datasetId: 'ds-1',
        datasetCode: 'CBAM_EU_DEFAULT_VALUES',
        datasetVersion: 'IR_2025_2621_v20260204',
        defaultValueId: 'dv-1',
        lookupKey: 'türkiye|72071100|basic oxygen furnace|',
        specificDirectEmbeddedEmissions: '1.60000000',
        specificDirectStatus: 'NUMERIC',
        specificDirectUnit: 'tCO2e/t',
        specificIndirectEmbeddedEmissions: '0.40000000',
        specificIndirectStatus: 'NUMERIC',
        specificIndirectUnit: 'tCO2e/t',
        candidateCount: 1,
        snapshot: { snapshotVersion: 1 },
      },
    });
    flushListLoad([snapshotted]);
    tick();
    openDetail(snapshotted);
    tick();
    const snapshot = fixture.nativeElement.querySelector(
      '[data-testid="ppc-snapshot"]',
    ) as HTMLElement;
    expect(snapshot.textContent).toContain('IR_2025_2621_v20260204');
    expect(snapshot.textContent).toContain('1.60000000');
    expect(snapshot.textContent).toContain('0.40000000');
    expect(fixture.nativeElement.textContent).toContain(
      'Saved default values are a snapshot.',
    );
  }));

  it('adds, updates and removes product uses', fakeAsync(() => {
    const withUse = makePrecursor({
      distribution: {
        ...makePrecursor().distribution,
        productUses: [
          {
            id: 'use-1',
            precursorId: 'prec-1',
            organizationId: 'org-1',
            reportingPeriodBindingId: 'binding-1',
            targetProductProfileVersionId: 'prof-b',
            quantity: '90',
            unit: 't',
            quantityTonnes: '90',
            notes: null,
            rowVersion: 1,
          },
        ],
      },
    });
    flushListLoad([withUse]);
    tick();
    openDetail(withUse);
    tick();
    expect(fixture.nativeElement.textContent).toContain('Nuts');

    component.productUseForm.setValue({
      targetProductProfileVersionId: 'prof-a',
      quantity: '5',
      unit: 't',
    });
    component.submitProductUse();
    const created = httpMock.expectOne(
      (r) => r.method === 'POST' && r.url.endsWith('/product-uses'),
    );
    expect(created.request.body.targetProductProfileVersionId).toBe('prof-a');
    expect(created.request.body.quantity).toBe('5');
    created.flush(withUse.distribution.productUses[0]);
    flushAfterMutation([withUse], withUse);
    tick();

    component.startEditProductUse(withUse.distribution.productUses[0]);
    component.productUseForm.controls.quantity.setValue('95');
    component.submitProductUse();
    const updated = httpMock.expectOne(
      (r) => r.method === 'PATCH' && r.url.endsWith('/product-uses/use-1'),
    );
    expect(updated.request.body.rowVersion).toBe(1);
    expect(updated.request.body.quantity).toBe('95');
    updated.flush({ ...withUse.distribution.productUses[0], quantity: '95', rowVersion: 2 });
    flushAfterMutation([withUse], withUse);
    tick();

    component.removeProductUse(withUse.distribution.productUses[0]);
    httpMock
      .expectOne((r) => r.method === 'DELETE' && r.url.endsWith('/product-uses/use-1'))
      .flush(null);
    const plain = makePrecursor();
    flushAfterMutation([plain], plain);
    tick();
    expect(component.editingUseId()).toBeNull();
  }));

  it('does not preselect a target product profile', fakeAsync(() => {
    const precursor = makePrecursor();
    flushListLoad([precursor]);
    tick();
    openDetail(precursor);
    tick();
    expect(component.productUseForm.controls.targetProductProfileVersionId.value).toBe('');
    component.submitProductUse();
    expect(component.actionError()).toBe('Select a valid target product.');
    expect(httpMock.match((r) => r.url.includes('/product-uses')).length).toBe(0);
  }));

  it('shows the server balance and allows saving an unbalanced draft', fakeAsync(() => {
    const precursor = makePrecursor();
    flushListLoad([precursor]);
    tick();
    openDetail(precursor);
    tick();
    expect(
      fixture.nativeElement.querySelector('[data-testid="ppc-balance-status"]')?.textContent,
    ).toContain('Not balanced');
    expect(fixture.nativeElement.textContent).toContain(
      'Distribute the remaining quantity before this precursor is ready.',
    );
    expect(fixture.nativeElement.querySelector('[data-testid="ppc-save-draft"]')).toBeTruthy();
    component.saveDraft();
    httpMock
      .expectOne(
        (r) => r.method === 'PATCH' && r.url.endsWith(`/purchased-precursors/${precursor.id}`),
      )
      .flush(precursor);
    flushAfterMutation([precursor], precursor);
    tick();
    expect(component.actionError()).toBeNull();
    expect(component.conflictMessage()).toBeNull();
  }));

  it('shows read-only calculated emissions with the roll-up note', fakeAsync(() => {
    const precursor = makePrecursor();
    flushListLoad([precursor]);
    tick();
    openDetail(precursor);
    tick();
    const panel = fixture.nativeElement.querySelector(
      '[data-testid="ppc-calculation"]',
    ) as HTMLElement;
    expect(panel.textContent).toContain('120.00000000');
    expect(panel.textContent).toContain('75.00000000');
    expect(panel.textContent).toContain('195.00000000');
    expect(panel.textContent).toContain('tCO2e');
    expect(panel.querySelector('input')).toBeFalsy();
    expect(
      fixture.nativeElement.querySelector('[data-testid="ppc-rollup-note"]')?.textContent,
    ).toContain('not rolled up into product totals');
  }));

  it('adds an EU default note to the calculation panel in EU default mode', fakeAsync(() => {
    const precursor = makeEuDefaultPrecursor();
    flushListLoad([precursor]);
    tick();
    openDetail(precursor);
    tick();
    expect(
      fixture.nativeElement.querySelector('[data-testid="ppc-default-calc-note"]'),
    ).toBeTruthy();
  }));

  it('shows a conflict message and Reload on a 409 response', fakeAsync(() => {
    const precursor = makePrecursor();
    flushListLoad([precursor]);
    tick();
    openDetail(precursor);
    tick();
    component.saveDraft();
    const req = httpMock.expectOne(
      (r) => r.method === 'PATCH' && r.url.endsWith(`/purchased-precursors/${precursor.id}`),
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
    expect(component.conflictMessage()).toBe('This precursor changed. Reload it and try again.');
    const reload = fixture.nativeElement.querySelector(
      '[data-testid="ppc-conflict-reload"]',
    ) as HTMLElement;
    expect(reload).toBeTruthy();
    reload.click();
    flushDetail(precursor);
    tick();
  }));

  it('requires archive confirmation', fakeAsync(() => {
    const precursor = makePrecursor();
    flushListLoad([precursor]);
    tick();
    openDetail(precursor);
    tick();
    component.requestArchive();
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Archive this precursor?');
    component.cancelArchive();
    fixture.detectChanges();
    expect(component.showArchiveConfirm()).toBeFalse();
    component.requestArchive();
    component.confirmArchive();
    httpMock
      .expectOne(
        (r) =>
          r.method === 'POST' &&
          r.url.endsWith(`/purchased-precursors/${precursor.id}/archive`),
      )
      .flush({ ...precursor, status: 'archived' });
    flushListLoad([]);
    tick();
    expect(component.selected()).toBeNull();
  }));

  it('sends the normalized CN code chosen from the autocomplete', fakeAsync(() => {
    const precursor = makePrecursor();
    flushListLoad([precursor]);
    tick();
    openDetail(precursor);
    tick();
    component.onCnSearchInput('7207');
    tick(300);
    const search = httpMock.expectOne(
      (r) => r.method === 'GET' && r.url === `${orgBase}/cn-codes`,
    );
    expect(search.request.params.get('q')).toBe('7207');
    search.flush({
      items: [
        {
          id: 'cn-9',
          datasetId: 'ds-cn',
          cnKey: '72071900',
          normalizedCode: '72071900',
          displayCode: '7207 19 00',
          descriptionEn: 'Other semi-finished products',
          cbamSector: 'Iron and Steel',
          numberingLabel: null,
          sourceSheet: 'CN',
          sourceRow: 3,
          status: 'ACTIVE',
          datasetCode: 'SEE',
          datasetVersion: '2.1',
          contentChecksum: 'x',
          fieldApplicability: profileA.fieldApplicability,
        },
      ],
      page: 1,
      pageSize: 20,
      totalItems: 1,
      totalPages: 1,
    });
    fixture.detectChanges();
    tick();
    expect(component.selectedCnCode()).toBeNull();
    component.onCnSelected({ option: { value: 'cn-9' } } as never);
    component.saveDraft();
    const patch = httpMock.expectOne(
      (r) => r.method === 'PATCH' && r.url.endsWith(`/purchased-precursors/${precursor.id}`),
    );
    expect(patch.request.body.cnCode).toBe('72071900');
    patch.flush(precursor);
    flushAfterMutation([precursor], precursor);
    tick();
  }));

  it('blocks saving free-text CN input that was not chosen from the list', fakeAsync(() => {
    const precursor = makePrecursor();
    flushListLoad([precursor]);
    tick();
    openDetail(precursor);
    tick();
    component.onCnSearchInput('not a code');
    tick(300);
    const search = httpMock.expectOne(
      (r) => r.method === 'GET' && r.url === `${orgBase}/cn-codes`,
    );
    search.flush({ items: [], page: 1, pageSize: 20, totalItems: 0, totalPages: 0 });
    fixture.detectChanges();
    component.saveDraft();
    expect(component.actionError()).toBe(
      'Select a CN code from the list. Free text is not allowed.',
    );
    expect(
      httpMock.match((r) => r.method === 'PATCH' && r.url.includes('/purchased-precursors/'))
        .length,
    ).toBe(0);
    tick();
  }));

  it('surfaces server blocking issue codes as readable messages', fakeAsync(() => {
    const precursor = makePrecursor({
      readiness: {
        ...supplierReadiness,
        status: 'UNBALANCED',
        blockingIssueCodes: [
          'PRECURSOR_DISTRIBUTION_UNBALANCED',
          'SUPPLIER_PROVENANCE_REQUIRED',
          'SOME_NEW_SERVER_CODE',
        ],
      },
    });
    flushListLoad([precursor]);
    tick();
    openDetail(precursor);
    tick();
    const text = fixture.nativeElement.textContent as string;
    expect(
      fixture.nativeElement.querySelector('[data-testid="ppc-readiness-status"]')?.textContent,
    ).toContain('Not balanced');
    expect(text).toContain('Add the supplier data source.');
    expect(text).toContain('SOME_NEW_SERVER_CODE');
  }));
});

describe('purchased-precursors.util', () => {
  it('maps readiness, balance, mode and resolution labels', () => {
    expect(mapPrecursorReadinessStatusLabel('EMPTY')).toBe('No data');
    expect(mapPrecursorReadinessStatusLabel('UNBALANCED')).toBe('Not balanced');
    expect(mapPrecursorReadinessStatusLabel('UNRESOLVED')).toBe('Default not found');
    expect(mapPrecursorReadinessStatusLabel('AMBIGUOUS')).toBe('More details needed');
    expect(mapPrecursorReadinessStatusLabel('READY')).toBe('Ready');
    expect(mapPrecursorBalanceStatusLabel('BALANCED')).toBe('Balanced');
    expect(precursorBalanceHelpMessage('UNBALANCED')).toBe(
      'Distribute the remaining quantity before this precursor is ready.',
    );
    expect(mapPrecursorModeLabel(MODE_SUPPLIER_DATA)).toBe('Supplier data');
    expect(mapPrecursorModeLabel(MODE_EU_DEFAULT)).toBe('EU default');
    expect(mapResolutionStatusLabel('RESOLVED')).toBe('Default value found');
  });

  it('shows unknown blocking codes as-is', () => {
    expect(mapPrecursorBlockingCode('PRECURSOR_NAME_REQUIRED')).toBe('Enter a precursor name.');
    expect(mapPrecursorBlockingCode('MIXED_PRECURSOR_SOURCE_NOT_SUPPORTED')).toBe(
      'Supplier and default values cannot be mixed.',
    );
    expect(mapPrecursorBlockingCode('UNKNOWN_CODE_X')).toBe('UNKNOWN_CODE_X');
  });

  it('keeps Decimal strings intact', () => {
    expect(optionalDecimalOrNull('')).toBeNull();
    expect(optionalDecimalOrNull('  ')).toBeNull();
    expect(optionalDecimalOrNull('0')).toBe('0');
    expect(optionalDecimalOrNull('12.3400')).toBe('12.3400');
    expect(isBlankDecimalInput(null)).toBeTrue();
    expect(formatDecimalDisplay(null)).toBe('—');
    expect(formatDecimalDisplay('0')).toBe('0');
    expect(formatDecimalDisplay('1.60000000')).toBe('1.60000000');
  });

  it('maps conflict errors', () => {
    const err = new HttpErrorResponse({
      status: 409,
      error: { error: { code: 'CONFLICT', message: 'conflict' } },
    });
    expect(mapPrecursorApiError(err)).toBe('This precursor changed. Reload it and try again.');
  });
});
