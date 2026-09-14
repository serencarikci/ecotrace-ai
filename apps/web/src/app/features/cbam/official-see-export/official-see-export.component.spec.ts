import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { By } from '@angular/platform-browser';
import { signal } from '@angular/core';
import { environment } from '../../../../environments/environment';
import { AuthService } from '../../../core/services/auth.service';
import {
  CbamOfficialSeeExportArtifact,
  CbamOfficialSeeExportReadiness,
  CbamOfficialSeeExportRun,
} from '../cbam-api.service';
import { CbamOfficialSeeExportComponent } from './official-see-export.component';
import {
  canDownloadOfficialSeeRun,
  createClientRequestId,
  extractErrorCode,
  mapBlockingIssue,
  mapGenerationUiStatus,
  mapOfficialSeeError,
  mapOfficialSeeErrorCode,
  sanitizeDownloadFileName,
} from './official-see-export.util';

describe('CbamOfficialSeeExportComponent', () => {
  let fixture: ComponentFixture<CbamOfficialSeeExportComponent>;
  let component: CbamOfficialSeeExportComponent;
  let httpMock: HttpTestingController;

  const orgBase = `${environment.apiUrl}${environment.apiV1Prefix}/cbam/organizations/org-1`;
  const bindingBase = `${orgBase}/reporting-period-bindings/binding-1/official-see-export`;

  const notReady: CbamOfficialSeeExportReadiness = {
    ready: false,
    blockingIssueCodes: ['PEE_V2_MISSING_OR_STALE', 'PROCESSES_NOT_READY'],
    warnings: [],
    mappingVersion: 'official-see-mapping-v1',
    templateVersion: 'CBAM_SEE_V2.1',
    templateSha256: '83170fde547c418dcae7f6a32852555d6874e092769f387b263108a231b2dd64',
    capacity: {
      installations: 1,
      goods: 2,
      processes: 2,
      precursors: 1,
      fuelActivities: 1,
    },
    sofficeAvailable: true,
    snapshotIds: {},
  };

  const readyBody: CbamOfficialSeeExportReadiness = {
    ...notReady,
    ready: true,
    blockingIssueCodes: [],
  };

  function runBody(overrides: Partial<CbamOfficialSeeExportRun> = {}): CbamOfficialSeeExportRun {
    return {
      id: 'run-1',
      organizationId: 'org-1',
      reportingPeriodBindingId: 'binding-1',
      clientRequestId: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
      generationStatus: 'COMPLETED',
      validationStatus: 'PASSED',
      formulaParityStatus: 'PASSED',
      mappingVersion: 'official-see-mapping-v1',
      templateFilename: 'template.xlsx',
      templateVersion: 'CBAM_SEE_V2.1',
      templateSha256: notReady.templateSha256,
      peeResultId: 'pee-1',
      deaResultId: 'dea-1',
      ieaResultId: 'iea-1',
      sourceFingerprint: 'abc',
      outputSha256: 'def',
      outputSizeBytes: 1024000,
      failureDiagnostics: null,
      generatedByUserId: 'user-1',
      generatedAt: '2026-08-31T00:00:00Z',
      createdAt: '2026-08-31T00:00:00Z',
      idempotentReplay: false,
      ...overrides,
    };
  }

  const artifactBody: CbamOfficialSeeExportArtifact = {
    id: 'art-1',
    organizationId: 'org-1',
    exportRunId: 'run-1',
    artifactType: 'XLSX',
    fileName: 'CBAM_SEE_Demo.xlsx',
    mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    fileSizeBytes: 1024000,
    sha256: 'def',
    createdAt: '2026-08-31T00:00:00Z',
  };

  function flushLoad(readiness: CbamOfficialSeeExportReadiness, runs: CbamOfficialSeeExportRun[] = []): void {
    const readinessReq = httpMock.expectOne(`${bindingBase}/readiness`);
    const runsReq = httpMock.expectOne(
      (r) => r.url.startsWith(`${bindingBase}/runs`) && r.method === 'GET',
    );
    readinessReq.flush(readiness);
    runsReq.flush({
      items: runs,
      page: 1,
      pageSize: 20,
      totalItems: runs.length,
      totalPages: 1,
    });
    fixture.detectChanges();
  }

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CbamOfficialSeeExportComponent],
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

    fixture = TestBed.createComponent(CbamOfficialSeeExportComponent);
    component = fixture.componentInstance;
    httpMock = TestBed.inject(HttpTestingController);
    fixture.componentRef.setInput('bindingId', 'binding-1');
    fixture.componentRef.setInput('canConfigure', true);
    fixture.componentRef.setInput('canMutate', true);
    fixture.detectChanges();
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('shows NOT_READY with blocking links and hides generate when not ready', () => {
    flushLoad(notReady);
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Not ready');
    expect(text).toContain('Calculate product embedded emissions');
    expect(text).toContain('Complete the production processes');
    expect(text).toContain('Products: 2 / 10');
    const generate = fixture.nativeElement.querySelector(
      '[data-official-generate]',
    ) as HTMLButtonElement;
    expect(generate.disabled).toBeTrue();
    expect(text).toContain('Official Excel is not ready');
  });

  it('shows READY and enables generate for configure + writable period', () => {
    flushLoad(readyBody);
    const generate = fixture.nativeElement.querySelector(
      '[data-official-generate]',
    ) as HTMLButtonElement;
    expect(generate.disabled).toBeFalse();
    expect(fixture.nativeElement.textContent).toContain('Ready');
    expect(fixture.nativeElement.textContent).toContain('CBAM_SEE_V2.1');
    expect(fixture.nativeElement.textContent).toContain('official-see-mapping-v1');
    expect(fixture.nativeElement.textContent).toContain('83170fde547c');
  });

  it('disables generate for locked period and view-only permission', () => {
    flushLoad(readyBody);
    fixture.componentRef.setInput('canMutate', false);
    fixture.detectChanges();
    expect(
      (fixture.nativeElement.querySelector('[data-official-generate]') as HTMLButtonElement)
        .disabled,
    ).toBeTrue();
    expect(fixture.nativeElement.textContent).toContain('locked');

    fixture.componentRef.setInput('canConfigure', false);
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('[data-official-generate]')).toBeNull();
    expect(fixture.nativeElement.textContent).toContain('Configure permission is required');
  });

  it('first generation uses a new clientRequestId and enables download after success', fakeAsync(() => {
    flushLoad(readyBody);
    const uuidSpy = spyOn(crypto, 'randomUUID').and.returnValue(
      'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa' as `${string}-${string}-${string}-${string}-${string}`,
    );
    (
      fixture.nativeElement.querySelector('[data-official-generate]') as HTMLButtonElement
    ).click();
    fixture.detectChanges();

    const exec = httpMock.expectOne(`${bindingBase}/executions`);
    expect(exec.request.method).toBe('POST');
    expect(exec.request.body.clientRequestId).toBe('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa');
    exec.flush(runBody());
    fixture.detectChanges();

    httpMock.expectOne(`${orgBase}/official-see-export/runs/run-1/artifacts`).flush([artifactBody]);
    httpMock.expectOne(`${bindingBase}/readiness`).flush(readyBody);
    httpMock
      .expectOne((r) => r.url.startsWith(`${bindingBase}/runs`) && r.method === 'GET')
      .flush({ items: [runBody()], page: 1, pageSize: 20, totalItems: 1, totalPages: 1 });
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Ready to download');
    expect(fixture.nativeElement.textContent).toContain('CBAM_SEE_Demo.xlsx');
    expect(uuidSpy).toHaveBeenCalled();
  }));

  it('reuses clientRequestId on transport retry and clears on IDEMPOTENCY_KEY_REUSED', fakeAsync(() => {
    flushLoad(readyBody);
    spyOn(crypto, 'randomUUID').and.returnValues(
      'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa' as `${string}-${string}-${string}-${string}-${string}`,
      'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb' as `${string}-${string}-${string}-${string}-${string}`,
    );

    component.generate();
    const first = httpMock.expectOne(`${bindingBase}/executions`);
    expect(first.request.body.clientRequestId).toBe('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa');
    first.flush(
      {
        error: {
          code: 'NETWORK',
          message: 'fail',
        },
      },
      { status: 0, statusText: 'Unknown Error' },
    );
    fixture.detectChanges();

    component.generate();
    const retry = httpMock.expectOne(`${bindingBase}/executions`);
    expect(retry.request.body.clientRequestId).toBe('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa');
    retry.flush(
      {
        error: {
          code: 'IDEMPOTENCY_KEY_REUSED',
          details: [{ code: 'IDEMPOTENCY_KEY_REUSED' }],
        },
      },
      { status: 409, statusText: 'Conflict' },
    );
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('This export request changed');

    component.generate();
    const again = httpMock.expectOne(`${bindingBase}/executions`);
    expect(again.request.body.clientRequestId).toBe('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb');
    again.flush(runBody({ clientRequestId: 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb' }));
    httpMock.expectOne(`${orgBase}/official-see-export/runs/run-1/artifacts`).flush([artifactBody]);
    httpMock.expectOne(`${bindingBase}/readiness`).flush(readyBody);
    httpMock
      .expectOne((r) => r.url.startsWith(`${bindingBase}/runs`) && r.method === 'GET')
      .flush({ items: [runBody()], page: 1, pageSize: 20, totalItems: 1, totalPages: 1 });
  }));

  it('prevents duplicate submit while in flight', () => {
    flushLoad(readyBody);
    spyOn(crypto, 'randomUUID').and.returnValue(
      'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa' as `${string}-${string}-${string}-${string}-${string}`,
    );
    component.generate();
    component.generate();
    const execs = httpMock.match(`${bindingBase}/executions`);
    expect(execs.length).toBe(1);
    execs[0].flush(runBody());
    httpMock.expectOne(`${orgBase}/official-see-export/runs/run-1/artifacts`).flush([artifactBody]);
    httpMock.expectOne(`${bindingBase}/readiness`).flush(readyBody);
    httpMock
      .expectOne((r) => r.url.startsWith(`${bindingBase}/runs`) && r.method === 'GET')
      .flush({ items: [runBody()], page: 1, pageSize: 20, totalItems: 1, totalPages: 1 });
  });

  it('handles idempotent replay without duplicating history rows', () => {
    flushLoad(readyBody, [runBody()]);
    httpMock.expectOne(`${orgBase}/official-see-export/runs/run-1/artifacts`).flush([artifactBody]);
    fixture.detectChanges();

    spyOn(crypto, 'randomUUID').and.returnValue(
      'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa' as `${string}-${string}-${string}-${string}-${string}`,
    );
    component.generate();
    httpMock.expectOne(`${bindingBase}/executions`).flush(
      runBody({ idempotentReplay: true }),
    );
    httpMock.expectOne(`${orgBase}/official-see-export/runs/run-1/artifacts`).flush([artifactBody]);
    httpMock.expectOne(`${bindingBase}/readiness`).flush(readyBody);
    httpMock
      .expectOne((r) => r.url.startsWith(`${bindingBase}/runs`) && r.method === 'GET')
      .flush({ items: [runBody()], page: 1, pageSize: 20, totalItems: 1, totalPages: 1 });
    fixture.detectChanges();
    expect(component.runs().length).toBe(1);
    expect(fixture.nativeElement.textContent).toContain('Using the existing official Excel');
  });

  it('polls while PENDING/RUNNING and stops on COMPLETED', fakeAsync(() => {
    flushLoad(readyBody);
    spyOn(crypto, 'randomUUID').and.returnValue(
      'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa' as `${string}-${string}-${string}-${string}-${string}`,
    );
    component.generate();
    httpMock.expectOne(`${bindingBase}/executions`).flush(
      runBody({ generationStatus: 'PENDING', formulaParityStatus: 'PENDING' }),
    );
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Preparing');

    tick(0);
    httpMock
      .expectOne(`${orgBase}/official-see-export/runs/run-1`)
      .flush(runBody({ generationStatus: 'RUNNING', formulaParityStatus: 'PENDING' }));
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Checking workbook');

    tick(2000);
    httpMock.expectOne(`${orgBase}/official-see-export/runs/run-1`).flush(runBody());
    httpMock.expectOne(`${orgBase}/official-see-export/runs/run-1/artifacts`).flush([artifactBody]);
    httpMock.expectOne(`${bindingBase}/readiness`).flush(readyBody);
    httpMock
      .expectOne((r) => r.url.startsWith(`${bindingBase}/runs`) && r.method === 'GET')
      .flush({ items: [runBody()], page: 1, pageSize: 20, totalItems: 1, totalPages: 1 });
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Ready to download');

    tick(2000);
    httpMock.expectNone(`${orgBase}/official-see-export/runs/run-1`);
  }));

  it('downloads with backend filename and revokes object URL', () => {
    flushLoad(readyBody, [runBody()]);
    httpMock.expectOne(`${orgBase}/official-see-export/runs/run-1/artifacts`).flush([artifactBody]);
    fixture.detectChanges();

    const createUrl = spyOn(URL, 'createObjectURL').and.returnValue('blob:mock');
    const revokeUrl = spyOn(URL, 'revokeObjectURL');
    const clickSpy = jasmine.createSpy('click');
    spyOn(document, 'createElement').and.callFake((tag: string) => {
      if (tag === 'a') {
        return { href: '', download: '', rel: '', click: clickSpy } as unknown as HTMLAnchorElement;
      }
      return document.createElement(tag);
    });

    (
      fixture.nativeElement.querySelector('[data-official-download-run="run-1"]') as HTMLButtonElement
    ).click();
    httpMock.expectOne(`${orgBase}/official-see-export/runs/run-1/artifacts`).flush([artifactBody]);
    const dl = httpMock.expectOne(`${orgBase}/official-see-export/artifacts/art-1/download`);
    expect(dl.request.responseType).toBe('blob');
    dl.flush(new Blob(['PK'], { type: artifactBody.mimeType }));
    expect(createUrl).toHaveBeenCalled();
    expect(revokeUrl).toHaveBeenCalledWith('blob:mock');
    expect(clickSpy).toHaveBeenCalled();
  });

  it('does not allow download when formula parity failed', () => {
    const failed = runBody({
      id: 'run-fail',
      generationStatus: 'FAILED',
      formulaParityStatus: 'FAILED',
      validationStatus: 'FAILED',
      failureDiagnostics: { code: 'FORMULA_PARITY_FAILED' },
      outputSizeBytes: null,
    });
    flushLoad(readyBody, [failed]);
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('[data-official-download-run="run-fail"]')).toBeNull();
    expect(fixture.nativeElement.textContent).toContain('Not available');
  });

  it('keeps previous successful artifact after a new failed generation', () => {
    flushLoad(readyBody, [runBody()]);
    httpMock.expectOne(`${orgBase}/official-see-export/runs/run-1/artifacts`).flush([artifactBody]);
    fixture.detectChanges();
    expect(component.currentArtifact()?.id).toBe('art-1');

    spyOn(crypto, 'randomUUID').and.returnValue(
      'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb' as `${string}-${string}-${string}-${string}-${string}`,
    );
    component.generate();
    httpMock.expectOne(`${bindingBase}/executions`).flush(
      runBody({
        id: 'run-2',
        clientRequestId: 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
        generationStatus: 'FAILED',
        formulaParityStatus: 'FAILED',
        failureDiagnostics: { code: 'FORMULA_PARITY_FAILED' },
        outputSizeBytes: null,
      }),
    );
    httpMock.expectOne(`${bindingBase}/readiness`).flush(readyBody);
    httpMock
      .expectOne((r) => r.url.startsWith(`${bindingBase}/runs`) && r.method === 'GET')
      .flush({
        items: [
          runBody({
            id: 'run-2',
            generationStatus: 'FAILED',
            formulaParityStatus: 'FAILED',
            outputSizeBytes: null,
          }),
          runBody(),
        ],
        page: 1,
        pageSize: 20,
        totalItems: 2,
        totalPages: 1,
      });
    fixture.detectChanges();
    expect(component.currentArtifact()?.id).toBe('art-1');
    expect(fixture.nativeElement.querySelector('[data-official-download-current]')).toBeTruthy();
  });

  it('sanitizes filenames and never shows filesystem paths', () => {
    expect(sanitizeDownloadFileName('/tmp/secret/path/file.xlsx')).toBe('file.xlsx');
    expect(sanitizeDownloadFileName('..\\..\\evil.xlsx')).toBe('evil.xlsx');
    flushLoad(readyBody, [runBody()]);
    httpMock.expectOne(`${orgBase}/official-see-export/runs/run-1/artifacts`).flush([
      { ...artifactBody, fileName: '/var/export/CBAM_SEE_Demo.xlsx' },
    ]);
    fixture.detectChanges();
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('CBAM_SEE_Demo.xlsx');
    expect(text).not.toContain('/var/export');
    expect(text).not.toContain('storageUri');
  });

  it('maps unknown errors to a safe fallback', () => {
    flushLoad(notReady);
    expect(mapOfficialSeeError({ status: 500, error: { error: { message: 'SQL boom' } } })).toBe(
      'The official Excel could not be generated. Try again.',
    );
    expect(mapOfficialSeeErrorCode('FORMULA_PARITY_FAILED')).toContain('did not match');
    expect(mapOfficialSeeErrorCode('EXAMPLE_LEAKAGE_DETECTED')).toContain('Example data');
    expect(mapOfficialSeeError({ status: 401 })).toContain('permission');
    expect(mapOfficialSeeError({ status: 404 })).toContain('not found');
    expect(mapBlockingIssue('CAPACITY_EXCEEDED_GOODS').message).toContain('Too many products');
    expect(canDownloadOfficialSeeRun(runBody())).toBeTrue();
    expect(canDownloadOfficialSeeRun(runBody({ formulaParityStatus: 'FAILED' }))).toBeFalse();
    expect(mapGenerationUiStatus(runBody({ generationStatus: 'PENDING' }))).toBe('Preparing');
    expect(extractErrorCode({ error: { error: { code: 'IDEMPOTENCY_KEY_REUSED' } } })).toBe(
      'IDEMPOTENCY_KEY_REUSED',
    );
    expect(createClientRequestId()).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i,
    );
  });

  it('cancels old requests when the period binding changes', fakeAsync(() => {
    flushLoad(readyBody);
    spyOn(crypto, 'randomUUID').and.returnValue(
      'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa' as `${string}-${string}-${string}-${string}-${string}`,
    );
    component.generate();
    httpMock.expectOne(`${bindingBase}/executions`).flush(
      runBody({ generationStatus: 'PENDING', formulaParityStatus: 'PENDING' }),
    );
    fixture.detectChanges();
    expect(component.generationStatusLabel()).toBe('Preparing');

    fixture.componentRef.setInput('bindingId', 'binding-2');
    fixture.detectChanges();
    const newBase = `${orgBase}/reporting-period-bindings/binding-2/official-see-export`;
    httpMock.expectOne(`${newBase}/readiness`).flush(readyBody);
    httpMock
      .expectOne((r) => r.url.startsWith(`${newBase}/runs`) && r.method === 'GET')
      .flush({ items: [], page: 1, pageSize: 20, totalItems: 0, totalPages: 0 });

    tick(2000);
    httpMock.expectNone(`${orgBase}/official-see-export/runs/run-1`);
    expect(component.runs().length).toBe(0);
  }));
  it('emits navigation for blocking issue links', () => {
    flushLoad(notReady);
    const spy = jasmine.createSpy('goToProductResults');
    component.goToProductResults.subscribe(spy);
    const buttons = fixture.debugElement.queryAll(By.css('.blocking-list button'));
    expect(buttons.length).toBeGreaterThan(0);
    buttons[0].nativeElement.click();
    expect(spy).toHaveBeenCalled();
  });
});
