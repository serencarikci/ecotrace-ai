import { HttpErrorResponse } from '@angular/common/http';
import {
  Component,
  DestroyRef,
  OnInit,
  computed,
  inject,
  input,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { MatAutocompleteModule, MatAutocompleteSelectedEvent } from '@angular/material/autocomplete';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatTableModule } from '@angular/material/table';
import { RouterLink } from '@angular/router';
import {
  Subject,
  catchError,
  debounceTime,
  distinctUntilChanged,
  finalize,
  of,
  switchMap,
} from 'rxjs';
import { ApiErrorBody } from '../../../core/models/api.models';
import { extractApiErrorMessage } from '../../../core/services/error.util';
import {
  Product,
  ProductSustainabilityService,
} from '../../../core/services/product-sustainability.service';
import {
  CbamApiService,
  CbamCnCode,
  CbamCnControlledListValue,
  CbamFieldApplicability,
  CbamProductProfile,
  CbamProductProfileCreate,
  CbamProductProfileIssue,
  CbamProductProfileUpdate,
} from '../cbam-api.service';

export const EMPTY_FIELD_APPLICABILITY: CbamFieldApplicability = {
  reducingAgent: false,
  steelMillIdentificationNumber: false,
  percentMn: false,
  percentCr: false,
  percentNi: false,
  percentOtherAlloys: false,
  percentOtherMaterials: false,
};

export const REDUCING_AGENT_LIST_CODE = 'REDUCING_AGENT';

const PERCENT_KEYS = [
  'percentMn',
  'percentCr',
  'percentNi',
  'percentOtherAlloys',
  'percentOtherMaterials',
] as const;

const REQUIREMENT_MESSAGES: Record<string, string> = {
  PRODUCT_NAME_REQUIRED: 'Enter a product name.',
  CN_CODE_REQUIRED: 'Select a CN code.',
  REDUCING_AGENT_REQUIRED: 'Select a reducing material.',
  STEEL_MILL_ID_REQUIRED: 'Enter the steel mill ID.',
  REDUCING_AGENT_INVALID: 'Choose a reducing material from the list.',
  REDUCING_AGENT_NOT_APPLICABLE: 'This field is not used for the selected CN code.',
  STEEL_MILL_ID_NOT_APPLICABLE: 'This field is not used for the selected CN code.',
  PERCENT_MN_NOT_APPLICABLE: 'This field is not used for the selected CN code.',
  PERCENT_CR_NOT_APPLICABLE: 'This field is not used for the selected CN code.',
  PERCENT_NI_NOT_APPLICABLE: 'This field is not used for the selected CN code.',
  PERCENT_OTHER_ALLOYS_NOT_APPLICABLE: 'This field is not used for the selected CN code.',
  PERCENT_OTHER_MATERIALS_NOT_APPLICABLE: 'This field is not used for the selected CN code.',
  PERCENT_MN_BELOW_ZERO: 'Enter a percentage between 0 and 100.',
  PERCENT_MN_ABOVE_100: 'Enter a percentage between 0 and 100.',
  PERCENT_CR_BELOW_ZERO: 'Enter a percentage between 0 and 100.',
  PERCENT_CR_ABOVE_100: 'Enter a percentage between 0 and 100.',
  PERCENT_NI_BELOW_ZERO: 'Enter a percentage between 0 and 100.',
  PERCENT_NI_ABOVE_100: 'Enter a percentage between 0 and 100.',
  PERCENT_OTHER_ALLOYS_BELOW_ZERO: 'Enter a percentage between 0 and 100.',
  PERCENT_OTHER_ALLOYS_ABOVE_100: 'Enter a percentage between 0 and 100.',
  PERCENT_OTHER_MATERIALS_BELOW_ZERO: 'Enter a percentage between 0 and 100.',
  PERCENT_OTHER_MATERIALS_ABOVE_100: 'Enter a percentage between 0 and 100.',
  PERCENTAGE_SUM_ABOVE_100: 'Check the material percentages.',
  PERCENTAGE_SUM_NOT_100: 'Check the material percentages.',
  PROFILE_NOT_READY: 'This profile is not ready yet.',
  PROFILE_NOT_DRAFT: 'Only a draft profile can be changed.',
  CLASSIFICATION_READY_CLIENT_WRITE_FORBIDDEN: 'Readiness is calculated by the server.',
  AMBIGUOUS_CN_CODE: 'More than one CN code matches. Choose a more specific code.',
};

export function emptyFieldApplicability(): CbamFieldApplicability {
  return { ...EMPTY_FIELD_APPLICABILITY };
}

export function normalizeFieldApplicability(
  raw: CbamFieldApplicability | null | undefined,
): CbamFieldApplicability {
  const base = emptyFieldApplicability();
  if (!raw) {
    return base;
  }
  return {
    reducingAgent: !!raw.reducingAgent,
    steelMillIdentificationNumber: !!raw.steelMillIdentificationNumber,
    percentMn: !!raw.percentMn,
    percentCr: !!raw.percentCr,
    percentNi: !!raw.percentNi,
    percentOtherAlloys: !!raw.percentOtherAlloys,
    percentOtherMaterials: !!raw.percentOtherMaterials,
  };
}

export function formatCnOption(code: CbamCnCode): string {
  return `${code.normalizedCode} — ${code.descriptionEn}`;
}

export function blankToNull(value: string | null | undefined): string | null {
  if (value === null || value === undefined) {
    return null;
  }
  const trimmed = String(value).trim();
  return trimmed === '' ? null : trimmed;
}

/** Parse a percent string without floating-point authoritative math. */
export function parsePercentInput(value: string | null | undefined): {
  ok: boolean;
  nullValue: boolean;
  belowZero: boolean;
  above100: boolean;
  normalized: string | null;
} {
  const raw = blankToNull(value);
  if (raw === null) {
    return { ok: true, nullValue: true, belowZero: false, above100: false, normalized: null };
  }
  if (!/^-?\d+(\.\d+)?$/.test(raw)) {
    return { ok: false, nullValue: false, belowZero: false, above100: false, normalized: null };
  }
  // Compare as decimal strings against bounds using Number only for range UX warnings.
  const n = Number(raw);
  if (!Number.isFinite(n)) {
    return { ok: false, nullValue: false, belowZero: false, above100: false, normalized: null };
  }
  if (n < 0) {
    return { ok: false, nullValue: false, belowZero: true, above100: false, normalized: null };
  }
  if (n > 100) {
    return { ok: false, nullValue: false, belowZero: false, above100: true, normalized: null };
  }
  return { ok: true, nullValue: false, belowZero: false, above100: false, normalized: raw };
}

export function sumEnteredPercents(values: Array<string | null>): {
  hasAny: boolean;
  exceeds100: boolean;
} {
  let sum = 0;
  let hasAny = false;
  for (const value of values) {
    const parsed = parsePercentInput(value);
    if (parsed.nullValue || !parsed.ok || parsed.normalized === null) {
      continue;
    }
    hasAny = true;
    sum += Number(parsed.normalized);
  }
  return { hasAny, exceeds100: hasAny && sum > 100 + 1e-9 };
}

export function profileStatusLabel(status: string): string {
  switch (status) {
    case 'draft':
      return 'Draft';
    case 'active':
      return 'Active';
    case 'superseded':
      return 'Superseded';
    case 'archived':
      return 'Archived';
    default:
      return status;
  }
}

export function readinessLabel(ready: boolean): string {
  return ready ? 'Ready' : 'Not ready';
}

export function mapRequirementCode(code: string): string {
  return REQUIREMENT_MESSAGES[code] ?? 'More information is needed.';
}

export function mapProductProfileError(error: unknown): string {
  if (error instanceof HttpErrorResponse) {
    if (error.status === 403 || error.status === 401) {
      return 'You do not have permission to do this.';
    }
    if (error.status === 404) {
      return 'This profile or CN code was not found.';
    }
    if (error.status === 0) {
      return 'Unable to reach the EcoTrace API. Check that the backend is running.';
    }
    const body = error.error as ApiErrorBody | null;
    const details = body?.error?.details ?? [];
    for (const detail of details) {
      const code = (detail as { code?: string }).code;
      if (typeof code === 'string' && code in REQUIREMENT_MESSAGES) {
        return REQUIREMENT_MESSAGES[code];
      }
      if (typeof code === 'string' && code.endsWith('_NOT_APPLICABLE')) {
        return 'This field is not used for the selected CN code.';
      }
    }
    const top = body?.error?.code;
    if (typeof top === 'string' && top in REQUIREMENT_MESSAGES) {
      return REQUIREMENT_MESSAGES[top];
    }
    return extractApiErrorMessage(error, 'The product profile could not be saved. Try again.');
  }
  return 'The product profile could not be saved. Try again.';
}

export function buildCreatePayloadFromProfile(
  productId: string,
  source: CbamProductProfile,
): CbamProductProfileCreate {
  return {
    productId,
    productName: source.productName,
    cnCode: source.cnNormalizedCode ?? source.cnDisplayCode,
    reducingAgent: source.reducingAgent,
    steelMillIdentificationNumber: source.steelMillIdentificationNumber,
    percentMn: source.percentMn,
    percentCr: source.percentCr,
    percentNi: source.percentNi,
    percentOtherAlloys: source.percentOtherAlloys,
    percentOtherMaterials: source.percentOtherMaterials,
    validFrom: source.validFrom,
    validTo: source.validTo,
  };
}

export function buildDraftUpdatePayload(
  rowVersion: number,
  form: {
    productName: string | null;
    cnCode: string | null;
    reducingAgent: string | null;
    steelMillIdentificationNumber: string | null;
    percentMn: string | null;
    percentCr: string | null;
    percentNi: string | null;
    percentOtherAlloys: string | null;
    percentOtherMaterials: string | null;
    validFrom: string | null;
    validTo: string | null;
  },
  applicability: CbamFieldApplicability,
): CbamProductProfileUpdate {
  const fa = normalizeFieldApplicability(applicability);
  const payload: CbamProductProfileUpdate = {
    rowVersion,
    productName: blankToNull(form.productName),
    cnCode: blankToNull(form.cnCode),
    validFrom: blankToNull(form.validFrom),
    validTo: blankToNull(form.validTo),
  };
  if (fa.reducingAgent) {
    payload.reducingAgent = blankToNull(form.reducingAgent);
  } else {
    payload.reducingAgent = null;
  }
  if (fa.steelMillIdentificationNumber) {
    payload.steelMillIdentificationNumber = blankToNull(form.steelMillIdentificationNumber);
  } else {
    payload.steelMillIdentificationNumber = null;
  }
  for (const key of PERCENT_KEYS) {
    if (fa[key]) {
      payload[key] = blankToNull(form[key]);
    } else {
      payload[key] = null;
    }
  }
  return payload;
}

@Component({
  selector: 'app-cbam-product-profiles',
  standalone: true,
  imports: [
    RouterLink,
    ReactiveFormsModule,
    MatAutocompleteModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatTableModule,
  ],
  templateUrl: './product-profiles.component.html',
  styleUrl: './product-profiles.component.scss',
})
export class CbamProductProfilesComponent implements OnInit {
  private readonly api = inject(CbamApiService);
  private readonly productsApi = inject(ProductSustainabilityService);
  private readonly fb = inject(FormBuilder);
  private readonly destroyRef = inject(DestroyRef);

  readonly canConfigure = input(false);

  /** Template helpers (exported functions). */
  readonly formatCnOption = formatCnOption;
  readonly profileStatusLabel = profileStatusLabel;
  readonly readinessLabel = readinessLabel;

  readonly products = signal<Product[]>([]);
  readonly productsLoading = signal(false);
  readonly productsError = signal<string | null>(null);

  readonly selectedProductId = signal<string | null>(null);
  readonly versions = signal<CbamProductProfile[]>([]);
  readonly versionsLoading = signal(false);
  readonly versionsError = signal<string | null>(null);

  readonly selectedProfile = signal<CbamProductProfile | null>(null);
  readonly profileLoading = signal(false);
  readonly saving = signal(false);
  readonly feedback = signal<string | null>(null);
  readonly errorMessage = signal<string | null>(null);
  readonly percentWarning = signal<string | null>(null);

  readonly fieldApplicability = signal<CbamFieldApplicability>(emptyFieldApplicability());
  readonly selectedCn = signal<CbamCnCode | null>(null);
  readonly cnResults = signal<CbamCnCode[]>([]);
  readonly cnSearchLoading = signal(false);
  readonly cnSearchError = signal<string | null>(null);
  readonly cnDetailLoading = signal(false);

  readonly reducingAgents = signal<CbamCnControlledListValue[]>([]);
  readonly reducingAgentsLoading = signal(false);
  readonly reducingAgentsError = signal<string | null>(null);

  private readonly cnSearch$ = new Subject<string>();
  private cnDetailSeq = 0;
  private profileLoadSeq = 0;

  readonly versionColumns = ['version', 'status', 'cn', 'ready', 'actions'];

  readonly form = this.fb.nonNullable.group({
    productName: [''],
    cnSearch: [''],
    reducingAgent: [''],
    steelMillIdentificationNumber: [''],
    percentMn: [''],
    percentCr: [''],
    percentNi: [''],
    percentOtherAlloys: [''],
    percentOtherMaterials: [''],
    validFrom: [''],
    validTo: [''],
  });

  readonly isDraft = computed(() => this.selectedProfile()?.status === 'draft');
  readonly isReadOnly = computed(() => {
    const profile = this.selectedProfile();
    if (!this.canConfigure()) {
      return true;
    }
    return !profile || profile.status !== 'draft';
  });
  readonly readinessSummary = computed(() => {
    const profile = this.selectedProfile();
    if (!profile) {
      return null;
    }
    return profile.classificationReady
      ? 'This profile is ready.'
      : 'This profile is not ready yet.';
  });

  ngOnInit(): void {
    this.cnSearch$
      .pipe(
        debounceTime(300),
        distinctUntilChanged(),
        switchMap((q) => {
          const query = q.trim();
          if (!query) {
            this.cnResults.set([]);
            this.cnSearchLoading.set(false);
            this.cnSearchError.set(null);
            return of(null);
          }
          this.cnSearchLoading.set(true);
          this.cnSearchError.set(null);
          return this.api.listCnCodes({ page: 1, pageSize: 20, q: query }).pipe(
            catchError((err) => {
              this.cnSearchError.set(mapProductProfileError(err));
              this.cnResults.set([]);
              return of(null);
            }),
            finalize(() => this.cnSearchLoading.set(false)),
          );
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((page) => {
        if (page) {
          this.cnResults.set(page.items);
        }
      });

    this.loadProducts();
  }

  loadProducts(): void {
    this.productsLoading.set(true);
    this.productsError.set(null);
    this.productsApi
      .listProducts({ page: 1, pageSize: 100, isActive: true })
      .pipe(
        catchError((err) => {
          this.productsError.set(mapProductProfileError(err));
          this.products.set([]);
          return of(null);
        }),
        finalize(() => this.productsLoading.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((page) => {
        if (!page) {
          return;
        }
        this.products.set(page.items);
        if (page.items.length === 0) {
          this.selectedProductId.set(null);
          this.versions.set([]);
          this.selectedProfile.set(null);
          return;
        }
        const current = this.selectedProductId();
        if (!current || !page.items.some((p) => p.id === current)) {
          this.selectProduct(page.items[0].id);
        }
      });
  }

  selectProduct(productId: string): void {
    this.selectedProductId.set(productId);
    this.errorMessage.set(null);
    this.feedback.set(null);
    this.loadVersions(productId);
  }

  loadVersions(productId: string, preferProfileId?: string | null): void {
    const seq = ++this.profileLoadSeq;
    this.versionsLoading.set(true);
    this.versionsError.set(null);
    this.api
      .listProductProfiles({ page: 1, pageSize: 100, productId })
      .pipe(
        catchError((err) => {
          if (seq !== this.profileLoadSeq) {
            return of(null);
          }
          this.versionsError.set(mapProductProfileError(err));
          this.versions.set([]);
          return of(null);
        }),
        finalize(() => {
          if (seq === this.profileLoadSeq) {
            this.versionsLoading.set(false);
          }
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((page) => {
        if (!page || seq !== this.profileLoadSeq) {
          return;
        }
        const items = [...page.items].sort((a, b) => b.version - a.version);
        this.versions.set(items);
        if (items.length === 0) {
          this.selectedProfile.set(null);
          this.resetFormForNewDraft(productId);
          return;
        }
        const preferred =
          (preferProfileId ? items.find((i) => i.id === preferProfileId) : null) ??
          items.find((i) => i.status === 'draft') ??
          items.find((i) => i.status === 'active') ??
          items[0];
        this.selectProfile(preferred.id);
      });
  }

  selectProfile(profileId: string, options?: { keepError?: boolean }): void {
    const seq = ++this.profileLoadSeq;
    this.profileLoading.set(true);
    if (!options?.keepError) {
      this.errorMessage.set(null);
    }
    this.api
      .getProductProfile(profileId)
      .pipe(
        catchError((err) => {
          if (seq !== this.profileLoadSeq) {
            return of(null);
          }
          this.errorMessage.set(mapProductProfileError(err));
          return of(null);
        }),
        finalize(() => {
          if (seq === this.profileLoadSeq) {
            this.profileLoading.set(false);
          }
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((profile) => {
        if (!profile || seq !== this.profileLoadSeq) {
          return;
        }
        this.applyProfile(profile);
      });
  }

  onCnSearchInput(value: string): void {
    this.form.controls.cnSearch.setValue(value, { emitEvent: false });
    // Free-text is search only; clear selected CN until a list item is chosen.
    if (this.selectedCn() && formatCnOption(this.selectedCn()!) !== value) {
      this.selectedCn.set(null);
    }
    this.cnSearch$.next(value);
  }

  onCnSelected(event: MatAutocompleteSelectedEvent): void {
    const id = String(event.option.value);
    const fromList = this.cnResults().find((c) => c.id === id) ?? null;
    if (fromList) {
      this.form.controls.cnSearch.setValue(formatCnOption(fromList), { emitEvent: false });
      this.loadCnDetail(fromList.id, fromList);
    }
  }

  retryCnSearch(): void {
    this.cnSearch$.next(this.form.controls.cnSearch.value);
  }

  retryReducingAgents(): void {
    this.loadReducingAgents(true);
  }

  createDraft(): void {
    if (!this.canConfigure()) {
      return;
    }
    const productId = this.selectedProductId();
    if (!productId) {
      return;
    }
    this.saving.set(true);
    this.errorMessage.set(null);
    this.feedback.set(null);
    const product = this.products().find((p) => p.id === productId);
    this.api
      .createProductProfile({
        productId,
        productName: product?.name ?? null,
      })
      .pipe(
        catchError((err) => {
          this.errorMessage.set(mapProductProfileError(err));
          return of(null);
        }),
        finalize(() => this.saving.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((created) => {
        if (!created) {
          return;
        }
        this.feedback.set('Draft saved.');
        this.loadVersions(productId, created.id);
      });
  }

  saveDraft(): void {
    if (!this.canConfigure() || this.isReadOnly()) {
      return;
    }
    const profile = this.selectedProfile();
    if (!profile || profile.status !== 'draft') {
      return;
    }
    const selected = this.selectedCn();
    if (this.form.controls.cnSearch.value.trim() && !selected) {
      this.errorMessage.set('Select a CN code from the list. Free text is not allowed.');
      return;
    }
    const clientPercentError = this.validatePercentsClientSide();
    if (clientPercentError) {
      this.errorMessage.set(clientPercentError);
      return;
    }
    const payload = this.buildUpdateFromForm(profile.rowVersion);
    this.saving.set(true);
    this.errorMessage.set(null);
    this.feedback.set(null);
    this.api
      .updateProductProfileDraft(profile.id, payload)
      .pipe(
        catchError((err) => {
          this.handleNotApplicableError(err);
          this.errorMessage.set(mapProductProfileError(err));
          return of(null);
        }),
        finalize(() => this.saving.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((updated) => {
        if (!updated) {
          return;
        }
        this.feedback.set('Draft saved.');
        this.applyProfile(updated);
        this.refreshVersionsKeepSelection(updated.productId, updated.id);
      });
  }

  publish(): void {
    if (!this.canConfigure()) {
      return;
    }
    const profile = this.selectedProfile();
    if (!profile || profile.status !== 'draft') {
      return;
    }
    if (
      !confirm(
        'Publish this profile?\n\nAfter publishing, this version cannot be changed. You can create a new version later.',
      )
    ) {
      return;
    }
    this.saving.set(true);
    this.errorMessage.set(null);
    this.feedback.set(null);
    this.api
      .publishProductProfile(profile.id, { rowVersion: profile.rowVersion })
      .pipe(
        catchError((err) => {
          this.errorMessage.set(mapProductProfileError(err));
          // Reload to show server missingRequirements if present.
          this.selectProfile(profile.id, { keepError: true });
          return of(null);
        }),
        finalize(() => this.saving.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((published) => {
        if (!published) {
          return;
        }
        this.feedback.set('Profile published.');
        this.applyProfile(published);
        this.refreshVersionsKeepSelection(published.productId, published.id);
      });
  }

  createNewVersion(): void {
    if (!this.canConfigure()) {
      return;
    }
    const source = this.selectedProfile();
    const productId = this.selectedProductId();
    if (!source || !productId) {
      return;
    }
    this.saving.set(true);
    this.errorMessage.set(null);
    this.feedback.set(null);
    const payload = buildCreatePayloadFromProfile(productId, source);
    // Strip non-applicable fields using source applicability before create.
    const fa = normalizeFieldApplicability(source.fieldApplicability);
    if (!fa.reducingAgent) {
      payload.reducingAgent = null;
    }
    if (!fa.steelMillIdentificationNumber) {
      payload.steelMillIdentificationNumber = null;
    }
    for (const key of PERCENT_KEYS) {
      if (!fa[key]) {
        payload[key] = null;
      }
    }
    this.api
      .createProductProfile(payload)
      .pipe(
        catchError((err) => {
          this.errorMessage.set(mapProductProfileError(err));
          return of(null);
        }),
        finalize(() => this.saving.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((created) => {
        if (!created) {
          return;
        }
        this.feedback.set('New draft version created.');
        this.loadVersions(productId, created.id);
      });
  }

  archive(): void {
    if (!this.canConfigure()) {
      return;
    }
    const profile = this.selectedProfile();
    if (!profile || profile.status === 'archived') {
      return;
    }
    if (!confirm('Archive this profile version?')) {
      return;
    }
    this.saving.set(true);
    this.errorMessage.set(null);
    this.feedback.set(null);
    this.api
      .archiveProductProfile(profile.id, { rowVersion: profile.rowVersion })
      .pipe(
        catchError((err) => {
          this.errorMessage.set(mapProductProfileError(err));
          return of(null);
        }),
        finalize(() => this.saving.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((archived) => {
        if (!archived) {
          return;
        }
        this.feedback.set('Profile archived.');
        this.applyProfile(archived);
        this.refreshVersionsKeepSelection(archived.productId, archived.id);
      });
  }

  cancelEdits(): void {
    const profile = this.selectedProfile();
    if (profile) {
      this.applyProfile(profile);
      this.feedback.set(null);
      this.errorMessage.set(null);
      return;
    }
    const productId = this.selectedProductId();
    if (productId) {
      this.resetFormForNewDraft(productId);
    }
  }

  displayRequirement(issue: CbamProductProfileIssue): string {
    return mapRequirementCode(issue.code);
  }

  cnLabel(profile: CbamProductProfile): string {
    if (!profile.cnNormalizedCode) {
      return '—';
    }
    return profile.cnDisplayCode ?? profile.cnNormalizedCode;
  }

  productLabel(product: Product): string {
    return `${product.code} — ${product.name}`;
  }

  private applyProfile(profile: CbamProductProfile): void {
    this.selectedProfile.set(profile);
    this.selectedProductId.set(profile.productId);
    const fa = normalizeFieldApplicability(profile.fieldApplicability);
    this.fieldApplicability.set(fa);
    this.form.setValue({
      productName: profile.productName ?? '',
      cnSearch: profile.cnNormalizedCode
        ? `${profile.cnNormalizedCode} — ${profile.cnDescription ?? ''}`.trim()
        : '',
      reducingAgent: profile.reducingAgent ?? '',
      steelMillIdentificationNumber: profile.steelMillIdentificationNumber ?? '',
      percentMn: profile.percentMn ?? '',
      percentCr: profile.percentCr ?? '',
      percentNi: profile.percentNi ?? '',
      percentOtherAlloys: profile.percentOtherAlloys ?? '',
      percentOtherMaterials: profile.percentOtherMaterials ?? '',
      validFrom: profile.validFrom ?? '',
      validTo: profile.validTo ?? '',
    });
    this.percentWarning.set(null);
    if (profile.cnCodeId) {
      this.loadCnDetail(profile.cnCodeId, null);
    } else {
      this.selectedCn.set(null);
      if (fa.reducingAgent) {
        this.loadReducingAgents(true);
      }
    }
    if (this.isReadOnly()) {
      this.form.disable({ emitEvent: false });
    } else {
      this.form.enable({ emitEvent: false });
    }
  }

  private resetFormForNewDraft(productId: string): void {
    const product = this.products().find((p) => p.id === productId);
    this.selectedProfile.set(null);
    this.selectedCn.set(null);
    this.fieldApplicability.set(emptyFieldApplicability());
    this.form.reset({
      productName: product?.name ?? '',
      cnSearch: '',
      reducingAgent: '',
      steelMillIdentificationNumber: '',
      percentMn: '',
      percentCr: '',
      percentNi: '',
      percentOtherAlloys: '',
      percentOtherMaterials: '',
      validFrom: '',
      validTo: '',
    });
    if (this.canConfigure()) {
      this.form.enable({ emitEvent: false });
    } else {
      this.form.disable({ emitEvent: false });
    }
  }

  private loadCnDetail(cnCodeId: string, seed: CbamCnCode | null): void {
    const seq = ++this.cnDetailSeq;
    if (seed) {
      this.selectedCn.set(seed);
      this.applyApplicability(seed.fieldApplicability);
    }
    this.cnDetailLoading.set(true);
    this.api
      .getCnCode(cnCodeId)
      .pipe(
        catchError((err) => {
          if (seq !== this.cnDetailSeq) {
            return of(null);
          }
          this.errorMessage.set(mapProductProfileError(err));
          return of(null);
        }),
        finalize(() => {
          if (seq === this.cnDetailSeq) {
            this.cnDetailLoading.set(false);
          }
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((detail) => {
        if (!detail || seq !== this.cnDetailSeq) {
          return;
        }
        this.selectedCn.set(detail);
        this.form.controls.cnSearch.setValue(formatCnOption(detail), { emitEvent: false });
        this.applyApplicability(detail.fieldApplicability);
      });
  }

  private applyApplicability(raw: CbamFieldApplicability): void {
    const fa = normalizeFieldApplicability(raw);
    this.fieldApplicability.set(fa);
    // Clear non-applicable form controls immediately.
    if (!fa.reducingAgent) {
      this.form.controls.reducingAgent.setValue('', { emitEvent: false });
    } else {
      this.loadReducingAgents();
    }
    if (!fa.steelMillIdentificationNumber) {
      this.form.controls.steelMillIdentificationNumber.setValue('', { emitEvent: false });
    }
    for (const key of PERCENT_KEYS) {
      if (!fa[key]) {
        this.form.controls[key].setValue('', { emitEvent: false });
      }
    }
    this.updatePercentWarning();
  }

  private loadReducingAgents(force = false): void {
    if (!force && (this.reducingAgentsLoading() || this.reducingAgents().length > 0)) {
      return;
    }
    this.reducingAgentsLoading.set(true);
    this.reducingAgentsError.set(null);
    this.api
      .listCnControlledListValues(REDUCING_AGENT_LIST_CODE)
      .pipe(
        catchError((err) => {
          this.reducingAgentsError.set(mapProductProfileError(err));
          this.reducingAgents.set([]);
          return of(null);
        }),
        finalize(() => this.reducingAgentsLoading.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((rows) => {
        if (!rows) {
          return;
        }
        this.reducingAgents.set(rows);
      });
  }

  private buildUpdateFromForm(rowVersion: number): CbamProductProfileUpdate {
    const fa = this.fieldApplicability();
    const selected = this.selectedCn();
    const raw = this.form.getRawValue();
    return buildDraftUpdatePayload(
      rowVersion,
      {
        productName: raw.productName,
        cnCode: selected?.normalizedCode ?? null,
        reducingAgent: raw.reducingAgent,
        steelMillIdentificationNumber: raw.steelMillIdentificationNumber,
        percentMn: raw.percentMn,
        percentCr: raw.percentCr,
        percentNi: raw.percentNi,
        percentOtherAlloys: raw.percentOtherAlloys,
        percentOtherMaterials: raw.percentOtherMaterials,
        validFrom: raw.validFrom,
        validTo: raw.validTo,
      },
      fa,
    );
  }

  private validatePercentsClientSide(): string | null {
    const fa = this.fieldApplicability();
    const raw = this.form.getRawValue();
    const entered: string[] = [];
    for (const key of PERCENT_KEYS) {
      if (!fa[key]) {
        continue;
      }
      const parsed = parsePercentInput(raw[key]);
      if (!parsed.ok) {
        if (parsed.belowZero || parsed.above100) {
          return 'Enter a percentage between 0 and 100.';
        }
        return 'Enter a valid percentage.';
      }
      if (parsed.normalized !== null) {
        entered.push(parsed.normalized);
      }
    }
    const sum = sumEnteredPercents(entered);
    if (sum.exceeds100) {
      this.percentWarning.set('The entered percentages add up to more than 100.');
      return 'The entered percentages add up to more than 100.';
    }
    this.percentWarning.set(null);
    return null;
  }

  updatePercentWarning(): void {
    const fa = this.fieldApplicability();
    const raw = this.form.getRawValue();
    const values: Array<string | null> = [];
    for (const key of PERCENT_KEYS) {
      if (fa[key]) {
        values.push(blankToNull(raw[key]));
      }
    }
    const sum = sumEnteredPercents(values);
    this.percentWarning.set(
      sum.exceeds100 ? 'The entered percentages add up to more than 100.' : null,
    );
  }

  private refreshVersionsKeepSelection(productId: string, profileId: string): void {
    this.api
      .listProductProfiles({ page: 1, pageSize: 100, productId })
      .pipe(
        catchError(() => of(null)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((page) => {
        if (!page) {
          return;
        }
        this.versions.set([...page.items].sort((a, b) => b.version - a.version));
        const current = page.items.find((i) => i.id === profileId);
        if (current) {
          // Keep selectedProfile in sync without clobbering fresher detail if already applied.
          this.selectedProfile.update((prev) =>
            prev && prev.id === current.id && prev.rowVersion >= current.rowVersion
              ? prev
              : current,
          );
        }
      });
  }

  private handleNotApplicableError(error: unknown): void {
    if (!(error instanceof HttpErrorResponse)) {
      return;
    }
    const details = (error.error as ApiErrorBody | null)?.error?.details ?? [];
    const hasNa = details.some((d) => {
      const code = (d as { code?: string }).code;
      return typeof code === 'string' && code.endsWith('_NOT_APPLICABLE');
    });
    if (!hasNa) {
      return;
    }
    const cn = this.selectedCn();
    if (cn) {
      this.loadCnDetail(cn.id, cn);
    }
    const profile = this.selectedProfile();
    if (profile) {
      this.selectProfile(profile.id);
    }
  }
}
