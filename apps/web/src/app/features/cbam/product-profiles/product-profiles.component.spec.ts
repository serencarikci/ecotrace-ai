import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { By } from '@angular/platform-browser';
import { HttpErrorResponse } from '@angular/common/http';
import { environment } from '../../../../environments/environment';
import { AuthService } from '../../../core/services/auth.service';
import {
  CbamCnCode,
  CbamFieldApplicability,
  CbamProductProfile,
} from '../cbam-api.service';
import {
  CbamProductProfilesComponent,
  blankToNull,
  buildCreatePayloadFromProfile,
  buildDraftUpdatePayload,
  emptyFieldApplicability,
  formatCnOption,
  mapProductProfileError,
  mapRequirementCode,
  normalizeFieldApplicability,
  parsePercentInput,
  profileStatusLabel,
  readinessLabel,
  sumEnteredPercents,
} from './product-profiles.component';

describe('CbamProductProfilesComponent', () => {
  let fixture: ComponentFixture<CbamProductProfilesComponent>;
  let component: CbamProductProfilesComponent;
  let httpMock: HttpTestingController;

  const orgBase = `${environment.apiUrl}${environment.apiV1Prefix}/cbam/organizations/org-1`;
  const productsBase = `${environment.apiUrl}${environment.apiV1Prefix}/organizations/org-1/products`;

  const allApplicable: CbamFieldApplicability = {
    reducingAgent: true,
    steelMillIdentificationNumber: true,
    percentMn: true,
    percentCr: true,
    percentNi: true,
    percentOtherAlloys: true,
    percentOtherMaterials: true,
  };

  const noneApplicable: CbamFieldApplicability = emptyFieldApplicability();

  const steelCn: CbamCnCode = {
    id: 'cn-steel',
    datasetId: 'ds-1',
    cnKey: 'K73181595',
    normalizedCode: '73181595',
    displayCode: '7318 15 95',
    descriptionEn: 'Other screws and bolts',
    cbamSector: 'Iron or steel products',
    numberingLabel: null,
    sourceSheet: 'Parameters_CNCodes',
    sourceRow: 10,
    status: 'ACTIVE',
    datasetCode: 'CBAM_SEE_CN_CODES',
    datasetVersion: 'SEE_V2.1',
    contentChecksum: 'abc',
    fieldApplicability: allApplicable,
  };

  const cementCn: CbamCnCode = {
    ...steelCn,
    id: 'cn-cement',
    cnKey: 'K25232900',
    normalizedCode: '25232900',
    displayCode: '2523 29 00',
    descriptionEn: 'Other portland cement',
    cbamSector: 'Cement',
    fieldApplicability: noneApplicable,
  };

  const draftProfile: CbamProductProfile = {
    id: 'prof-1',
    organizationId: 'org-1',
    productId: 'prod-1',
    version: 1,
    status: 'draft',
    validFrom: null,
    validTo: null,
    classificationReady: false,
    productName: 'Screws',
    cnCodeId: steelCn.id,
    cnNormalizedCode: steelCn.normalizedCode,
    cnDisplayCode: steelCn.displayCode,
    cnDescription: steelCn.descriptionEn,
    cnSector: steelCn.cbamSector,
    cnDatasetCode: steelCn.datasetCode,
    cnDatasetVersion: steelCn.datasetVersion,
    fieldApplicability: allApplicable,
    reducingAgent: null,
    steelMillIdentificationNumber: null,
    percentMn: null,
    percentCr: null,
    percentNi: null,
    percentOtherAlloys: null,
    percentOtherMaterials: null,
    missingRequirements: [
      { code: 'REDUCING_AGENT_REQUIRED', message: 'Select agent' },
      { code: 'UNKNOWN_CODE_XYZ', message: 'server' },
    ],
    validationIssues: [],
    rowVersion: 1,
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CbamProductProfilesComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        {
          provide: AuthService,
          useValue: {
            requireOrganizationId: () => 'org-1',
            currentRoles: () => ['org_admin'],
          },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(CbamProductProfilesComponent);
    component = fixture.componentInstance;
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  function flushProducts(items = [{ id: 'prod-1', organizationId: 'org-1', code: 'P1', name: 'Product 1', productType: 'finished_good', defaultUnitCode: 't', isActive: true }]): void {
    const req = httpMock.expectOne((r) => r.url.startsWith(productsBase));
    req.flush({
      items,
      page: 1,
      pageSize: 100,
      totalItems: items.length,
      totalPages: 1,
    });
  }

  function flushVersions(items: CbamProductProfile[] = [draftProfile]): void {
    const req = httpMock.expectOne(
      (r) =>
        r.url === `${orgBase}/product-profile-versions` &&
        r.params.get('productId') === 'prod-1',
    );
    req.flush({
      items,
      page: 1,
      pageSize: 100,
      totalItems: items.length,
      totalPages: 1,
    });
  }

  function flushProfile(profile: CbamProductProfile = draftProfile): void {
    const req = httpMock.expectOne(`${orgBase}/product-profile-versions/${profile.id}`);
    expect(req.request.method).toBe('GET');
    req.flush(profile);
  }

  function flushCnDetail(cn: CbamCnCode = steelCn): void {
    const req = httpMock.expectOne(`${orgBase}/cn-codes/${cn.id}`);
    req.flush(cn);
  }

  function flushReducingAgentsIfPending(): void {
    const pending = httpMock.match(`${orgBase}/cn-controlled-lists/REDUCING_AGENT`);
    for (const req of pending) {
      req.flush([
        {
          listCode: 'REDUCING_AGENT',
          valueCode: 'Natural gas',
          valueLabel: 'Natural gas',
          sortOrder: 1,
        },
        {
          listCode: 'REDUCING_AGENT',
          valueCode: 'Hydrogen',
          valueLabel: 'Hydrogen',
          sortOrder: 2,
        },
      ]);
    }
  }

  function flushReducingAgents(): void {
    const req = httpMock.expectOne(`${orgBase}/cn-controlled-lists/REDUCING_AGENT`);
    req.flush([
      { listCode: 'REDUCING_AGENT', valueCode: 'Natural gas', valueLabel: 'Natural gas', sortOrder: 1 },
      { listCode: 'REDUCING_AGENT', valueCode: 'Hydrogen', valueLabel: 'Hydrogen', sortOrder: 2 },
    ]);
  }

  function bootstrapConfigure(): void {
    fixture.componentRef.setInput('canConfigure', true);
    fixture.detectChanges();
    flushProducts();
    fixture.detectChanges();
    flushVersions();
    fixture.detectChanges();
    flushProfile();
    fixture.detectChanges();
    flushCnDetail();
    flushReducingAgents();
    fixture.detectChanges();
  }

  it('shows the Product Profiles UI for view users and hides mutations', () => {
    fixture.componentRef.setInput('canConfigure', false);
    fixture.detectChanges();
    flushProducts();
    fixture.detectChanges();
    flushVersions();
    fixture.detectChanges();
    flushProfile();
    fixture.detectChanges();
    flushCnDetail();
    // reducing agent applicable → still loads list for display context
    flushReducingAgents();
    fixture.detectChanges();

    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Product Profiles');
    expect(text).toContain('This profile is not ready yet.');
    expect(text).not.toContain('Save draft');
    expect(text).not.toContain('Publish');
    expect(text).not.toContain('Create new version');
    expect(text).not.toContain('Archive');
  });

  it('shows empty product state with management link', () => {
    fixture.componentRef.setInput('canConfigure', true);
    fixture.detectChanges();
    flushProducts([]);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('No products are available.');
    const link = fixture.debugElement.query(By.css('a[routerLink="/app/products"]'));
    expect(link).toBeTruthy();
  });

  it('shows empty profile state and create draft for configure', () => {
    fixture.componentRef.setInput('canConfigure', true);
    fixture.detectChanges();
    flushProducts();
    fixture.detectChanges();
    flushVersions([]);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain(
      'This product does not have a profile yet.',
    );
    expect(fixture.nativeElement.textContent).toContain('Create draft profile');
  });

  it('debounces CN search and preserves leading zeros', fakeAsync(() => {
    bootstrapConfigure();
    component.onCnSearchInput('0');
    component.onCnSearchInput('01');
    component.onCnSearchInput('012');
    tick(299);
    httpMock.expectNone((r) => r.url === `${orgBase}/cn-codes`);
    tick(1);
    const req = httpMock.expectOne((r) => r.url === `${orgBase}/cn-codes`);
    expect(req.request.params.get('q')).toBe('012');
    req.flush({
      items: [
        {
          ...cementCn,
          normalizedCode: '01234567',
          displayCode: '0123 45 67',
          descriptionEn: 'Leading zero code',
        },
      ],
      page: 1,
      pageSize: 20,
      totalItems: 1,
      totalPages: 1,
    });
    fixture.detectChanges();
    expect(component.cnResults()[0].normalizedCode).toBe('01234567');
    expect(formatCnOption(component.cnResults()[0])).toContain('01234567');
  }));

  it('ignores stale CN detail responses', fakeAsync(() => {
    bootstrapConfigure();
    component['loadCnDetail'](steelCn.id, steelCn);
    component['loadCnDetail'](cementCn.id, cementCn);
    const first = httpMock.expectOne(`${orgBase}/cn-codes/${steelCn.id}`);
    const second = httpMock.expectOne(`${orgBase}/cn-codes/${cementCn.id}`);
    first.flush(steelCn);
    second.flush(cementCn);
    expect(component.selectedCn()?.id).toBe(cementCn.id);
    expect(component.fieldApplicability().reducingAgent).toBe(false);
  }));

  it('does not allow free-text CN save without selection', () => {
    bootstrapConfigure();
    component.selectedCn.set(null);
    component.form.controls.cnSearch.setValue('73181595 — typed');
    component.saveDraft();
    httpMock.expectNone(
      (r) =>
        r.method === 'PATCH' && r.url === `${orgBase}/product-profile-versions/${draftProfile.id}`,
    );
    expect(component.errorMessage()).toContain('Select a CN code from the list');
  });

  it('renders special fields only from fieldApplicability', () => {
    bootstrapConfigure();
    expect(fixture.nativeElement.textContent).toContain('Reducing material');
    expect(fixture.nativeElement.textContent).toContain('Steel mill ID');
    expect(fixture.nativeElement.textContent).toContain('Manganese (Mn), %');

    component['applyApplicability'](noneApplicable);
    fixture.detectChanges();
    const text = fixture.nativeElement.textContent as string;
    expect(text).not.toContain('Reducing material');
    expect(text).not.toContain('Steel mill ID');
    expect(text).not.toContain('Manganese (Mn), %');
    // Must not infer from sector string
    expect(component.fieldApplicability().reducingAgent).toBe(false);
    expect(steelCn.cbamSector.toLowerCase()).toContain('steel');
  });

  it('loads reducing agents from the controlled-list API', () => {
    bootstrapConfigure();
    expect(component.reducingAgents().map((a) => a.valueCode)).toEqual([
      'Natural gas',
      'Hydrogen',
    ]);
    expect(component.reducingAgents()[0].valueLabel).toBe('Natural gas');
  });

  it('keeps blank percentages as null in payload', () => {
    const payload = buildDraftUpdatePayload(
      1,
      {
        productName: 'X',
        cnCode: '73181595',
        reducingAgent: 'Natural gas',
        steelMillIdentificationNumber: 'TR-1',
        percentMn: '',
        percentCr: '  ',
        percentNi: null,
        percentOtherAlloys: '10',
        percentOtherMaterials: '',
        validFrom: null,
        validTo: null,
      },
      allApplicable,
    );
    expect(payload.percentMn).toBeNull();
    expect(payload.percentCr).toBeNull();
    expect(payload.percentNi).toBeNull();
    expect(payload.percentOtherAlloys).toBe('10');
    expect(payload.percentOtherMaterials).toBeNull();
  });

  it('clears non-applicable fields from the update payload', () => {
    const payload = buildDraftUpdatePayload(
      2,
      {
        productName: 'Cement',
        cnCode: '25232900',
        reducingAgent: 'Natural gas',
        steelMillIdentificationNumber: 'X',
        percentMn: '5',
        percentCr: '5',
        percentNi: '5',
        percentOtherAlloys: '5',
        percentOtherMaterials: '5',
        validFrom: null,
        validTo: null,
      },
      noneApplicable,
    );
    expect(payload.reducingAgent).toBeNull();
    expect(payload.steelMillIdentificationNumber).toBeNull();
    expect(payload.percentMn).toBeNull();
    expect(payload.percentOtherMaterials).toBeNull();
  });

  it('saves draft while not ready and uses backend readiness', () => {
    bootstrapConfigure();
    expect(component.selectedProfile()?.classificationReady).toBe(false);
    component.selectedCn.set(steelCn);
    component.form.patchValue({
      productName: 'Screws',
      reducingAgent: 'Natural gas',
      steelMillIdentificationNumber: 'TR-1',
    });
    component.saveDraft();
    const req = httpMock.expectOne(`${orgBase}/product-profile-versions/${draftProfile.id}`);
    expect(req.request.method).toBe('PATCH');
    expect(req.request.body.rowVersion).toBe(1);
    const saved: CbamProductProfile = {
      ...draftProfile,
      classificationReady: false,
      reducingAgent: 'Natural gas',
      steelMillIdentificationNumber: 'TR-1',
      rowVersion: 2,
      missingRequirements: [],
    };
    req.flush(saved);
    const refresh = httpMock.expectOne(
      (r) => r.url === `${orgBase}/product-profile-versions`,
    );
    refresh.flush({
      items: [saved],
      page: 1,
      pageSize: 100,
      totalItems: 1,
      totalPages: 1,
    });
    // CN detail reload from applyProfile (agents already cached)
    flushCnDetail();
    flushReducingAgentsIfPending();
    fixture.detectChanges();
    expect(component.selectedProfile()?.classificationReady).toBe(false);
    expect(component.feedback()).toContain('Draft saved');
  });

  it('publishes with confirmation and refreshes', () => {
    bootstrapConfigure();
    const ready: CbamProductProfile = { ...draftProfile, classificationReady: true };
    component.selectedProfile.set(ready);
    spyOn(window, 'confirm').and.returnValue(true);
    component.publish();
    const req = httpMock.expectOne(
      `${orgBase}/product-profile-versions/${draftProfile.id}/publish`,
    );
    expect(req.request.body).toEqual({ rowVersion: 1 });
    const published: CbamProductProfile = { ...ready, status: 'active', rowVersion: 2 };
    req.flush(published);
    const refresh = httpMock.expectOne(
      (r) => r.url === `${orgBase}/product-profile-versions`,
    );
    refresh.flush({
      items: [published],
      page: 1,
      pageSize: 100,
      totalItems: 1,
      totalPages: 1,
    });
    flushCnDetail();
    flushReducingAgentsIfPending();
    fixture.detectChanges();
    expect(component.selectedProfile()?.status).toBe('active');
    expect(fixture.nativeElement.textContent).not.toContain('Save draft');
  });

  it('shows backend requirements when publish is rejected', () => {
    bootstrapConfigure();
    spyOn(window, 'confirm').and.returnValue(true);
    component.publish();
    const req = httpMock.expectOne(
      `${orgBase}/product-profile-versions/${draftProfile.id}/publish`,
    );
    req.flush(
      {
        error: {
          code: 'BUSINESS_RULE_ERROR',
          message: 'not ready',
          details: [{ code: 'PROFILE_NOT_READY' }],
        },
      },
      { status: 400, statusText: 'Bad Request' },
    );
    // reload profile
    flushProfile();
    flushCnDetail();
    flushReducingAgentsIfPending();
    expect(component.errorMessage()).toContain('not ready');
  });

  it('creates a new version without mutating the source profile', () => {
    bootstrapConfigure();
    const published: CbamProductProfile = {
      ...draftProfile,
      status: 'active',
      classificationReady: true,
      reducingAgent: 'Natural gas',
      steelMillIdentificationNumber: 'TR-1',
    };
    component.selectedProfile.set(published);
    component.createNewVersion();
    const req = httpMock.expectOne(`${orgBase}/product-profile-versions`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body.productId).toBe('prod-1');
    expect(req.request.body.cnCode).toBe('73181595');
    expect(req.request.body.reducingAgent).toBe('Natural gas');
    expect(req.request.body.id).toBeUndefined();
    expect(req.request.body.classificationReady).toBeUndefined();
    const created: CbamProductProfile = {
      ...published,
      id: 'prof-2',
      version: 2,
      status: 'draft',
      rowVersion: 1,
    };
    req.flush(created);
    flushVersions([created, published]);
    flushProfile(created);
    flushCnDetail();
    flushReducingAgentsIfPending();
    expect(component.selectedProfile()?.id).toBe('prof-2');
    expect(component.selectedProfile()?.status).toBe('draft');
  });

  it('archives with confirmation and refreshes', () => {
    bootstrapConfigure();
    spyOn(window, 'confirm').and.returnValue(true);
    component.archive();
    const req = httpMock.expectOne(
      `${orgBase}/product-profile-versions/${draftProfile.id}/archive`,
    );
    const archived: CbamProductProfile = {
      ...draftProfile,
      status: 'archived',
      rowVersion: 2,
    };
    req.flush(archived);
    const refresh = httpMock.expectOne(
      (r) => r.url === `${orgBase}/product-profile-versions`,
    );
    refresh.flush({
      items: [archived],
      page: 1,
      pageSize: 100,
      totalItems: 1,
      totalPages: 1,
    });
    flushCnDetail();
    flushReducingAgentsIfPending();
    expect(component.selectedProfile()?.status).toBe('archived');
  });

  it('maps unknown readiness codes to a safe fallback', () => {
    expect(mapRequirementCode('UNKNOWN_CODE_XYZ')).toBe('More information is needed.');
    bootstrapConfigure();
    expect(fixture.nativeElement.textContent).toContain('More information is needed.');
    expect(fixture.nativeElement.textContent).toContain('Select a reducing material.');
  });

  it('view-only users never issue mutations', () => {
    fixture.componentRef.setInput('canConfigure', false);
    fixture.detectChanges();
    flushProducts();
    fixture.detectChanges();
    flushVersions();
    fixture.detectChanges();
    flushProfile();
    fixture.detectChanges();
    flushCnDetail();
    flushReducingAgents();
    component.saveDraft();
    component.publish();
    component.createNewVersion();
    component.archive();
    component.createDraft();
    httpMock.expectNone((r) => r.method !== 'GET');
  });

  it('exposes readable status labels beyond color', () => {
    expect(profileStatusLabel('draft')).toBe('Draft');
    expect(profileStatusLabel('active')).toBe('Active');
    expect(readinessLabel(true)).toBe('Ready');
    expect(readinessLabel(false)).toBe('Not ready');
    bootstrapConfigure();
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Draft');
    expect(text).toContain('Not ready');
    expect(fixture.debugElement.query(By.css('label, mat-label, .pp-title'))).toBeTruthy();
  });
});

describe('product profile helpers', () => {
  it('normalizes applicability without sector inference', () => {
    expect(normalizeFieldApplicability(undefined).reducingAgent).toBe(false);
    expect(normalizeFieldApplicability({ ...emptyFieldApplicability(), percentMn: true }).percentMn)
      .toBe(true);
  });

  it('parses percent blanks and bounds', () => {
    expect(blankToNull('')).toBeNull();
    expect(blankToNull('  ')).toBeNull();
    expect(parsePercentInput('').nullValue).toBe(true);
    expect(parsePercentInput('-1').belowZero).toBe(true);
    expect(parsePercentInput('100.1').above100).toBe(true);
    expect(sumEnteredPercents(['60', '50']).exceeds100).toBe(true);
  });

  it('maps API errors', () => {
    const err = new HttpErrorResponse({
      status: 422,
      error: {
        error: {
          code: 'VALIDATION_ERROR',
          message: 'bad',
          details: [{ code: 'REDUCING_AGENT_NOT_APPLICABLE' }],
        },
      },
    });
    expect(mapProductProfileError(err)).toContain('not used for the selected CN code');
  });

  it('builds create-from-profile without server fields', () => {
    const payload = buildCreatePayloadFromProfile('prod-1', {
      id: 'x',
      organizationId: 'o',
      productId: 'prod-1',
      version: 3,
      status: 'active',
      validFrom: null,
      validTo: null,
      classificationReady: true,
      productName: 'A',
      cnCodeId: 'cn',
      cnNormalizedCode: '73181595',
      cnDisplayCode: '7318 15 95',
      cnDescription: 'Screws',
      cnSector: 'Iron or steel products',
      cnDatasetCode: 'CBAM_SEE_CN_CODES',
      cnDatasetVersion: 'SEE_V2.1',
      fieldApplicability: emptyFieldApplicability(),
      reducingAgent: 'Hydrogen',
      steelMillIdentificationNumber: null,
      percentMn: null,
      percentCr: null,
      percentNi: null,
      percentOtherAlloys: null,
      percentOtherMaterials: null,
      missingRequirements: [],
      validationIssues: [],
      rowVersion: 9,
    });
    expect(payload).toEqual({
      productId: 'prod-1',
      productName: 'A',
      cnCode: '73181595',
      reducingAgent: 'Hydrogen',
      steelMillIdentificationNumber: null,
      percentMn: null,
      percentCr: null,
      percentNi: null,
      percentOtherAlloys: null,
      percentOtherMaterials: null,
      validFrom: null,
      validTo: null,
    });
  });
});
