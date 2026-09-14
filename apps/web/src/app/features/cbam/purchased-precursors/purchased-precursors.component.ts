import {
  Component,
  DestroyRef,
  computed,
  effect,
  inject,
  input,
  signal,
  untracked,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { MatAutocompleteModule, MatAutocompleteSelectedEvent } from '@angular/material/autocomplete';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatRadioModule } from '@angular/material/radio';
import { MatSelectModule } from '@angular/material/select';
import { MatTableModule } from '@angular/material/table';
import { Subject, forkJoin, of } from 'rxjs';
import { catchError, debounceTime, distinctUntilChanged, finalize, switchMap, tap } from 'rxjs/operators';
import { Supplier, ProductSustainabilityService } from '../../../core/services/product-sustainability.service';
import {
  CbamApiService,
  CbamCnCode,
  CbamInstallation,
  CbamPrecursorDefaultResolution,
  CbamPrecursorDefaultValue,
  CbamPrecursorProductUse,
  CbamProductProfile,
  CbamPurchasedInput,
  CbamPurchasedPrecursor,
  CbamPurchasedPrecursorCreate,
  CbamPurchasedPrecursorMetadata,
  CbamPurchasedPrecursorReadiness,
  CbamPurchasedPrecursorUpdate,
} from '../cbam-api.service';
import {
  DEFAULT_JUSTIFICATION_LIST,
  ELECTRICITY_EF_UNIT,
  ELECTRICITY_INTENSITY_UNIT,
  ELECTRICITY_SOURCE_LIST,
  MODE_EU_DEFAULT,
  MODE_SUPPLIER_DATA,
  PARAMETER_SOURCE_LIST,
  PRECURSOR_MASS_UNITS,
  PRECURSOR_RESULT_UNIT,
  PRECURSOR_STATUS_ARCHIVED,
  SPECIFIC_DIRECT_UNIT,
  SPECIFIC_INDIRECT_UNIT,
  defaultValueIdentityLabel,
  defaultValueStatusLabel,
  formatDecimalDisplay,
  isConflictMessage,
  mapPrecursorApiError,
  mapPrecursorBalanceStatusLabel,
  mapPrecursorBlockingCode,
  mapPrecursorModeLabel,
  mapPrecursorReadinessStatusLabel,
  mapResolutionStatusLabel,
  optionalDecimalOrNull,
  optionalTextOrNull,
  precursorBalanceHelpMessage,
  profileOptionLabel,
  resolutionHelpMessage,
} from './purchased-precursors.util';

@Component({
  selector: 'app-cbam-purchased-precursors',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatAutocompleteModule,
    MatButtonModule,
    MatCheckboxModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatRadioModule,
    MatSelectModule,
    MatTableModule,
  ],
  templateUrl: './purchased-precursors.component.html',
  styleUrl: './purchased-precursors.component.scss',
})
export class CbamPurchasedPrecursorsComponent {
  private readonly api = inject(CbamApiService);
  private readonly productsApi = inject(ProductSustainabilityService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly fb = inject(FormBuilder);
  private readonly load$ = new Subject<string>();
  private readonly cnSearch$ = new Subject<string>();
  private loadSeq = 0;

  readonly bindingId = input.required<string>();
  readonly canConfigure = input(false);
  readonly canMutate = input(false);

  readonly loading = signal(false);
  readonly loadError = signal<string | null>(null);
  readonly precursors = signal<CbamPurchasedPrecursor[]>([]);
  readonly selected = signal<CbamPurchasedPrecursor | null>(null);
  readonly readiness = signal<CbamPurchasedPrecursorReadiness | null>(null);
  readonly installations = signal<CbamInstallation[]>([]);
  readonly profiles = signal<CbamProductProfile[]>([]);
  readonly purchasedInputs = signal<CbamPurchasedInput[]>([]);
  readonly suppliers = signal<Supplier[]>([]);
  readonly metadata = signal<CbamPurchasedPrecursorMetadata | null>(null);
  readonly detailLoading = signal(false);
  readonly submitting = signal(false);
  readonly actionError = signal<string | null>(null);
  readonly conflictMessage = signal<string | null>(null);
  readonly successMessage = signal<string | null>(null);
  readonly liveMessage = signal('');
  readonly showCreateForm = signal(false);
  readonly showArchiveConfirm = signal(false);
  /** Bumps when form values change so mode-dependent sections recompute. */
  readonly formEpoch = signal(0);

  readonly cnResults = signal<CbamCnCode[]>([]);
  readonly cnSearchLoading = signal(false);
  readonly cnSearchError = signal<string | null>(null);
  readonly selectedCnCode = signal<string | null>(null);

  readonly defaultResults = signal<CbamPrecursorDefaultValue[]>([]);
  readonly defaultSearchLoading = signal(false);
  readonly defaultSearchError = signal<string | null>(null);
  readonly defaultSearchDone = signal(false);
  readonly resolution = signal<CbamPrecursorDefaultResolution | null>(null);
  readonly resolving = signal(false);
  readonly selectedDefaultValue = signal<CbamPrecursorDefaultValue | null>(null);
  readonly selectedDefaultValueId = signal<string | null>(null);
  readonly editingUseId = signal<string | null>(null);

  readonly massUnits = PRECURSOR_MASS_UNITS;
  readonly modeSupplierData = MODE_SUPPLIER_DATA;
  readonly modeEuDefault = MODE_EU_DEFAULT;
  readonly resultUnit = PRECURSOR_RESULT_UNIT;

  readonly formatDecimal = formatDecimalDisplay;
  readonly modeLabel = mapPrecursorModeLabel;
  readonly readinessLabel = mapPrecursorReadinessStatusLabel;
  readonly balanceLabel = mapPrecursorBalanceStatusLabel;
  readonly balanceHelp = precursorBalanceHelpMessage;
  readonly blockingMessage = mapPrecursorBlockingCode;
  readonly resolutionLabel = mapResolutionStatusLabel;
  readonly resolutionHelp = resolutionHelpMessage;
  readonly profileLabel = profileOptionLabel;
  readonly defaultIdentityLabel = defaultValueIdentityLabel;
  readonly defaultStatusLabel = defaultValueStatusLabel;

  readonly listColumns = ['name', 'mode', 'quantity', 'status', 'balance', 'actions'] as const;
  readonly defaultColumns = ['identity', 'direct', 'indirect', 'actions'] as const;

  readonly createForm = this.fb.nonNullable.group({
    installationProfileId: [''],
    name: [''],
    dataSourceMode: [MODE_SUPPLIER_DATA],
  });

  readonly form = this.fb.nonNullable.group({
    name: [''],
    identifier: [''],
    aggregatedGoodsCategory: [''],
    purchasedInputRecordId: [''],
    supplierId: [''],
    cnSearch: [''],
    countryOfOrigin: [''],
    productionRoute: [''],
    quantity: [''],
    quantityUnit: ['t'],
    nonCbamQuantity: [''],
    nonCbamQuantityUnit: ['t'],
    dataSourceMode: [MODE_SUPPLIER_DATA],
    specificDirectEmbeddedEmissions: [''],
    specificDirectSourceCode: [''],
    electricityConsumptionIntensity: [''],
    electricityIntensitySourceCode: [''],
    electricityEmissionFactor: [''],
    electricityEfSourceCode: [''],
    defaultJustificationCode: [''],
    provenanceNotes: [''],
    evidenceReference: [''],
    notes: [''],
  });

  readonly productUseForm = this.fb.nonNullable.group({
    targetProductProfileVersionId: [''],
    quantity: [''],
    unit: ['t'],
  });

  readonly defaultSearchForm = this.fb.nonNullable.group({
    country: [''],
    cn: [''],
    route: [''],
    description: [''],
    includeOtherCountries: [false],
  });

  readonly canEdit = computed(
    () =>
      this.canConfigure() &&
      this.canMutate() &&
      this.selected()?.status !== PRECURSOR_STATUS_ARCHIVED,
  );

  readonly currentMode = computed(() => {
    this.formEpoch();
    return this.form.controls.dataSourceMode.value;
  });
  readonly supplierModeActive = computed(() => this.currentMode() === MODE_SUPPLIER_DATA);
  readonly euDefaultModeActive = computed(() => this.currentMode() === MODE_EU_DEFAULT);

  readonly parameterSourceList = computed(
    () =>
      this.metadata()?.controlledLists.find((l) => l.listCode === PARAMETER_SOURCE_LIST) ?? null,
  );
  readonly electricitySourceList = computed(
    () =>
      this.metadata()?.controlledLists.find((l) => l.listCode === ELECTRICITY_SOURCE_LIST) ?? null,
  );
  readonly justificationList = computed(
    () =>
      this.metadata()?.controlledLists.find((l) => l.listCode === DEFAULT_JUSTIFICATION_LIST) ??
      null,
  );

  readonly specificDirectUnit = computed(
    () => this.metadata()?.units?.['specificDirect'] ?? SPECIFIC_DIRECT_UNIT,
  );
  readonly specificIndirectUnit = computed(
    () => this.metadata()?.units?.['specificIndirect'] ?? SPECIFIC_INDIRECT_UNIT,
  );
  readonly electricityIntensityUnit = computed(
    () => this.metadata()?.units?.['electricityIntensity'] ?? ELECTRICITY_INTENSITY_UNIT,
  );
  readonly electricityEfUnit = computed(
    () => this.metadata()?.units?.['electricityEmissionFactor'] ?? ELECTRICITY_EF_UNIT,
  );

  constructor() {
    this.form.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => {
      this.formEpoch.update((n) => n + 1);
    });

    this.form.controls.dataSourceMode.valueChanges
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((mode) => this.applyModeSwitch(mode));

    this.cnSearch$
      .pipe(
        debounceTime(250),
        distinctUntilChanged(),
        switchMap((raw) => {
          const query = raw.trim();
          if (!query) {
            this.cnResults.set([]);
            this.cnSearchLoading.set(false);
            this.cnSearchError.set(null);
            return of(null);
          }
          this.cnSearchLoading.set(true);
          this.cnSearchError.set(null);
          return this.api.listCnCodes({ page: 1, pageSize: 20, q: query }).pipe(
            catchError((err: unknown) => {
              this.cnSearchError.set(mapPrecursorApiError(err));
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

    this.load$
      .pipe(
        switchMap((bindingId) => {
          const seq = ++this.loadSeq;
          this.loading.set(true);
          this.loadError.set(null);
          this.liveMessage.set('Loading purchased precursors.');
          return forkJoin({
            precursors: this.api.listPurchasedPrecursors(bindingId, {
              page: 1,
              pageSize: 100,
              includeArchived: false,
            }),
            installations: this.api.listInstallations({ page: 1, pageSize: 100, status: 'ACTIVE' }),
            profiles: this.api.listProductProfilesForBinding(bindingId, {
              page: 1,
              pageSize: 100,
            }),
            purchasedInputs: this.api
              .listPurchasedInputs(bindingId, { page: 1, pageSize: 100 })
              .pipe(catchError(() => of(null))),
            suppliers: this.productsApi
              .listSuppliers({ page: 1 })
              .pipe(catchError(() => of(null))),
            metadata: this.api.getPurchasedPrecursorMetadata().pipe(catchError(() => of(null))),
          }).pipe(
            tap((result) => {
              if (seq !== this.loadSeq) {
                return;
              }
              this.precursors.set(result.precursors.items);
              this.installations.set(result.installations.items);
              this.profiles.set(result.profiles.items);
              this.purchasedInputs.set(result.purchasedInputs?.items ?? []);
              this.suppliers.set(result.suppliers?.items ?? []);
              this.metadata.set(result.metadata);
              this.liveMessage.set('Purchased precursors loaded.');
              const selectedId = this.selected()?.id;
              if (selectedId) {
                const still = result.precursors.items.find((p) => p.id === selectedId);
                if (still) {
                  untracked(() => this.openPrecursor(still.id));
                } else {
                  this.selected.set(null);
                  this.readiness.set(null);
                }
              }
            }),
            catchError((err: unknown) => {
              if (seq === this.loadSeq) {
                this.loadError.set(mapPrecursorApiError(err));
                this.liveMessage.set('Purchased precursors could not be loaded.');
              }
              return of(null);
            }),
            finalize(() => {
              if (seq === this.loadSeq) {
                this.loading.set(false);
              }
            }),
          );
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe();

    effect(() => {
      const id = this.bindingId();
      if (id) {
        untracked(() => this.reload());
      }
    });

    effect(() => {
      const editable = this.canEdit();
      untracked(() => {
        if (editable) {
          this.form.enable({ emitEvent: false });
          this.productUseForm.enable({ emitEvent: false });
        } else {
          this.form.disable({ emitEvent: false });
          this.productUseForm.disable({ emitEvent: false });
        }
      });
    });
  }

  reload(): void {
    this.load$.next(this.bindingId());
  }

  openPrecursor(precursorId: string): void {
    this.detailLoading.set(true);
    this.actionError.set(null);
    this.conflictMessage.set(null);
    this.successMessage.set(null);
    this.showArchiveConfirm.set(false);
    this.editingUseId.set(null);
    this.liveMessage.set('Loading precursor detail.');
    forkJoin({
      detail: this.api.getPurchasedPrecursor(this.bindingId(), precursorId),
      readiness: this.api.getPurchasedPrecursorReadiness(this.bindingId(), precursorId),
    })
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.detailLoading.set(false)),
      )
      .subscribe({
        next: ({ detail, readiness }) => {
          this.selected.set(detail);
          this.readiness.set(readiness);
          this.applyDetailToForm(detail);
          this.liveMessage.set('Precursor detail loaded.');
        },
        error: (err: unknown) => {
          this.actionError.set(mapPrecursorApiError(err));
          this.liveMessage.set('Precursor detail could not be loaded.');
        },
      });
  }

  startCreate(): void {
    if (!this.canConfigure() || !this.canMutate()) {
      return;
    }
    this.showCreateForm.set(true);
    this.selected.set(null);
    this.readiness.set(null);
    this.createForm.reset({
      installationProfileId: this.installations()[0]?.id ?? '',
      name: '',
      dataSourceMode: MODE_SUPPLIER_DATA,
    });
  }

  cancelCreate(): void {
    this.showCreateForm.set(false);
  }

  createDraft(): void {
    if (!this.canConfigure() || !this.canMutate()) {
      return;
    }
    const installationProfileId = this.createForm.controls.installationProfileId.value.trim();
    if (!installationProfileId) {
      this.actionError.set('Select an installation.');
      return;
    }
    this.submitting.set(true);
    this.actionError.set(null);
    const payload: CbamPurchasedPrecursorCreate = {
      installationProfileId,
      name: optionalTextOrNull(this.createForm.controls.name.value),
      dataSourceMode: this.createForm.controls.dataSourceMode.value,
    };
    this.api
      .createPurchasedPrecursor(this.bindingId(), payload)
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.submitting.set(false)),
      )
      .subscribe({
        next: (created) => {
          this.showCreateForm.set(false);
          this.selected.set(created);
          this.applyDetailToForm(created);
          this.successMessage.set('Draft precursor created.');
          this.liveMessage.set('Draft precursor created.');
          this.reload();
        },
        error: (err: unknown) => this.handleMutationError(err),
      });
  }

  saveDraft(): void {
    const row = this.selected();
    if (!row || !this.canEdit()) {
      return;
    }
    if (this.form.controls.cnSearch.value.trim() && !this.selectedCnCode()) {
      this.actionError.set('Select a CN code from the list. Free text is not allowed.');
      return;
    }
    this.submitting.set(true);
    this.actionError.set(null);
    this.conflictMessage.set(null);
    this.successMessage.set(null);
    const payload = this.buildUpdatePayload(row.rowVersion);
    this.api
      .updatePurchasedPrecursorDraft(this.bindingId(), row.id, payload)
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.submitting.set(false)),
      )
      .subscribe({
        next: () => {
          this.successMessage.set('Draft saved.');
          this.liveMessage.set('Draft saved.');
          this.reload();
        },
        error: (err: unknown) => this.handleMutationError(err),
      });
  }

  requestArchive(): void {
    if (!this.selected() || !this.canEdit()) {
      return;
    }
    this.showArchiveConfirm.set(true);
  }

  cancelArchive(): void {
    this.showArchiveConfirm.set(false);
  }

  confirmArchive(): void {
    const row = this.selected();
    if (!row || !this.canEdit()) {
      return;
    }
    this.submitting.set(true);
    this.actionError.set(null);
    this.conflictMessage.set(null);
    this.api
      .archivePurchasedPrecursor(this.bindingId(), row.id, { rowVersion: row.rowVersion })
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.submitting.set(false)),
      )
      .subscribe({
        next: () => {
          this.showArchiveConfirm.set(false);
          this.selected.set(null);
          this.readiness.set(null);
          this.successMessage.set('Precursor archived.');
          this.liveMessage.set('Precursor archived.');
          this.reload();
        },
        error: (err: unknown) => this.handleMutationError(err),
      });
  }

  onCnSearchInput(value: string): void {
    this.form.controls.cnSearch.setValue(value, { emitEvent: false });
    this.selectedCnCode.set(null);
    this.cnSearch$.next(value);
  }

  onCnSelected(event: MatAutocompleteSelectedEvent): void {
    const id = String(event.option.value);
    const picked = this.cnResults().find((c) => c.id === id) ?? null;
    if (!picked) {
      return;
    }
    this.selectedCnCode.set(picked.normalizedCode);
    this.form.controls.cnSearch.setValue(this.cnOptionLabel(picked), { emitEvent: false });
    this.defaultSearchForm.controls.cn.setValue(picked.normalizedCode, { emitEvent: false });
  }

  cnOptionLabel(code: CbamCnCode): string {
    return `${code.normalizedCode} — ${code.descriptionEn}`;
  }

  searchDefaultValues(): void {
    const v = this.defaultSearchForm.getRawValue();
    this.defaultSearchLoading.set(true);
    this.defaultSearchError.set(null);
    this.api
      .searchPrecursorDefaultValues({
        page: 1,
        pageSize: 20,
        country: optionalTextOrNull(v.country),
        cn: optionalTextOrNull(v.cn),
        route: optionalTextOrNull(v.route),
        description: optionalTextOrNull(v.description),
        includeOtherCountriesGroup: v.includeOtherCountries,
      })
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.defaultSearchLoading.set(false)),
      )
      .subscribe({
        next: (page) => {
          // Never auto-select: the declarant picks a row explicitly.
          this.defaultResults.set(page.items);
          this.defaultSearchDone.set(true);
          this.liveMessage.set(`${page.items.length} default values found.`);
        },
        error: (err: unknown) => {
          this.defaultResults.set([]);
          this.defaultSearchDone.set(true);
          this.defaultSearchError.set(mapPrecursorApiError(err));
        },
      });
  }

  useDefaultCandidate(value: CbamPrecursorDefaultValue): void {
    if (!this.canEdit()) {
      return;
    }
    this.form.patchValue(
      {
        countryOfOrigin: value.countryName,
        productionRoute: value.productionRoute ?? '',
        cnSearch: value.cnDisplayCode ?? value.cnNormalizedCode,
      },
      { emitEvent: false },
    );
    this.selectedCnCode.set(value.cnNormalizedCode);
    this.defaultSearchForm.patchValue(
      {
        country: value.countryName,
        cn: value.cnNormalizedCode,
        route: value.productionRoute ?? '',
        description: value.goodsDescription ?? '',
      },
      { emitEvent: false },
    );
    this.selectedDefaultValue.set(value);
    this.selectedDefaultValueId.set(value.id);
    this.formEpoch.update((n) => n + 1);
    this.resolveDefaultValue();
  }

  resolveDefaultValue(): void {
    const country = optionalTextOrNull(this.form.controls.countryOfOrigin.value);
    const cn = this.selectedCnCode() ?? optionalTextOrNull(this.defaultSearchForm.controls.cn.value);
    if (!country || !cn) {
      this.actionError.set('Enter the country of origin and select a CN code first.');
      return;
    }
    this.resolving.set(true);
    this.actionError.set(null);
    this.api
      .resolvePrecursorDefaultValue({
        countryOfOrigin: country,
        cnCode: cn,
        productionRoute: optionalTextOrNull(this.form.controls.productionRoute.value),
        goodsDescription: optionalTextOrNull(this.defaultSearchForm.controls.description.value),
      })
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.resolving.set(false)),
      )
      .subscribe({
        next: (resolution) => {
          this.resolution.set(resolution);
          if (resolution.status === 'RESOLVED' && resolution.value) {
            this.selectedDefaultValue.set(resolution.value);
            this.selectedDefaultValueId.set(resolution.value.id);
          } else {
            this.selectedDefaultValue.set(null);
            this.selectedDefaultValueId.set(null);
            if (resolution.status === 'AMBIGUOUS') {
              // Show every candidate; the declarant must pick one.
              this.defaultResults.set(resolution.candidates);
              this.defaultSearchDone.set(true);
            }
          }
          this.liveMessage.set(mapResolutionStatusLabel(resolution.status));
        },
        error: (err: unknown) => {
          this.resolution.set(null);
          this.actionError.set(mapPrecursorApiError(err));
        },
      });
  }

  startEditProductUse(use: CbamPrecursorProductUse): void {
    if (!this.canEdit()) {
      return;
    }
    this.editingUseId.set(use.id);
    this.productUseForm.setValue({
      targetProductProfileVersionId: use.targetProductProfileVersionId,
      quantity: use.quantity,
      unit: use.unit,
    });
  }

  cancelEditProductUse(): void {
    this.editingUseId.set(null);
    this.productUseForm.reset({ targetProductProfileVersionId: '', quantity: '', unit: 't' });
  }

  submitProductUse(): void {
    const row = this.selected();
    if (!row || !this.canEdit()) {
      return;
    }
    const target = this.productUseForm.controls.targetProductProfileVersionId.value.trim();
    const quantity = optionalDecimalOrNull(this.productUseForm.controls.quantity.value);
    const unit = this.productUseForm.controls.unit.value || 't';
    if (!target) {
      this.actionError.set('Select a valid target product.');
      return;
    }
    if (quantity == null) {
      this.actionError.set('Enter the distributed quantity.');
      return;
    }
    const editingId = this.editingUseId();
    const existing = editingId
      ? row.distribution.productUses.find((u) => u.id === editingId)
      : undefined;
    this.submitting.set(true);
    this.actionError.set(null);
    const request$ =
      existing != null
        ? this.api.updatePrecursorProductUse(this.bindingId(), row.id, existing.id, {
            rowVersion: existing.rowVersion,
            targetProductProfileVersionId: target,
            quantity,
            unit,
          })
        : this.api.createPrecursorProductUse(this.bindingId(), row.id, {
            targetProductProfileVersionId: target,
            quantity,
            unit,
          });
    request$
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.submitting.set(false)),
      )
      .subscribe({
        next: () => {
          const message = existing != null ? 'Product use updated.' : 'Product use added.';
          this.cancelEditProductUse();
          this.successMessage.set(message);
          this.liveMessage.set(message);
          this.reload();
        },
        error: (err: unknown) => this.handleMutationError(err),
      });
  }

  removeProductUse(use: CbamPrecursorProductUse): void {
    const row = this.selected();
    if (!row || !this.canEdit()) {
      return;
    }
    this.submitting.set(true);
    this.actionError.set(null);
    this.api
      .deletePrecursorProductUse(this.bindingId(), row.id, use.id)
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.submitting.set(false)),
      )
      .subscribe({
        next: () => {
          if (this.editingUseId() === use.id) {
            this.cancelEditProductUse();
          }
          this.successMessage.set('Product use removed.');
          this.liveMessage.set('Product use removed.');
          this.reload();
        },
        error: (err: unknown) => this.handleMutationError(err),
      });
  }

  installationLabel(id: string): string {
    const found = this.installations().find((i) => i.id === id);
    return found ? `${found.name} (${found.code})` : id;
  }

  profileName(versionId: string | null | undefined): string {
    if (!versionId) {
      return '—';
    }
    const found = this.profiles().find((p) => p.id === versionId);
    return found ? profileOptionLabel(found) : versionId;
  }

  cnLabel(row: CbamPurchasedPrecursor): string {
    return row.cnDisplayCode ?? row.cnNormalizedCode ?? '—';
  }

  snapshotDatasetVersion(row: CbamPurchasedPrecursor): string {
    return row.defaultSource.datasetVersion ?? '—';
  }

  private applyDetailToForm(detail: CbamPurchasedPrecursor): void {
    const supplier = detail.supplierData;
    this.form.reset(
      {
        name: detail.name ?? '',
        identifier: detail.identifier ?? '',
        aggregatedGoodsCategory: detail.aggregatedGoodsCategory ?? '',
        purchasedInputRecordId: detail.purchasedInputRecordId ?? '',
        supplierId: detail.supplierId ?? '',
        cnSearch: detail.cnDisplayCode ?? detail.cnNormalizedCode ?? '',
        countryOfOrigin: detail.countryOfOrigin ?? '',
        productionRoute: detail.productionRoute ?? '',
        quantity: detail.distribution.quantity ?? '',
        quantityUnit: detail.distribution.quantityUnit ?? 't',
        nonCbamQuantity: detail.distribution.nonCbamQuantity ?? '',
        nonCbamQuantityUnit: detail.distribution.nonCbamQuantityUnit ?? 't',
        dataSourceMode: detail.dataSourceMode || MODE_SUPPLIER_DATA,
        specificDirectEmbeddedEmissions: supplier.specificDirectEmbeddedEmissions ?? '',
        specificDirectSourceCode: supplier.specificDirectSourceCode ?? '',
        electricityConsumptionIntensity: supplier.electricityConsumptionIntensity ?? '',
        electricityIntensitySourceCode: supplier.electricityIntensitySourceCode ?? '',
        electricityEmissionFactor: supplier.electricityEmissionFactor ?? '',
        electricityEfSourceCode: supplier.electricityEfSourceCode ?? '',
        defaultJustificationCode: detail.defaultSource.justificationCode ?? '',
        provenanceNotes: supplier.provenanceNotes ?? '',
        evidenceReference: supplier.evidenceReference ?? '',
        notes: detail.notes ?? '',
      },
      { emitEvent: false },
    );
    this.selectedCnCode.set(detail.cnNormalizedCode);
    this.selectedDefaultValueId.set(detail.defaultSource.defaultValueId);
    this.selectedDefaultValue.set(null);
    this.resolution.set(null);
    this.defaultResults.set([]);
    this.defaultSearchDone.set(false);
    this.cnResults.set([]);
    this.defaultSearchForm.reset(
      {
        country: detail.countryOfOrigin ?? '',
        cn: detail.cnNormalizedCode ?? '',
        route: detail.productionRoute ?? '',
        description: '',
        includeOtherCountries: false,
      },
      { emitEvent: false },
    );
    this.formEpoch.update((n) => n + 1);
  }

  /** Switching mode must drop the other mode's inputs before they reach the payload. */
  private applyModeSwitch(mode: string): void {
    if (mode === MODE_SUPPLIER_DATA) {
      this.form.patchValue({ defaultJustificationCode: '' }, { emitEvent: false });
      this.selectedDefaultValue.set(null);
      this.selectedDefaultValueId.set(null);
      this.resolution.set(null);
      this.defaultResults.set([]);
      this.defaultSearchDone.set(false);
    } else {
      this.form.patchValue(
        {
          specificDirectEmbeddedEmissions: '',
          specificDirectSourceCode: '',
          electricityConsumptionIntensity: '',
          electricityIntensitySourceCode: '',
          electricityEmissionFactor: '',
          electricityEfSourceCode: '',
        },
        { emitEvent: false },
      );
    }
    this.formEpoch.update((n) => n + 1);
  }

  private buildUpdatePayload(rowVersion: number): CbamPurchasedPrecursorUpdate {
    const f = this.form.controls;
    const mode = f.dataSourceMode.value;
    const payload: CbamPurchasedPrecursorUpdate = {
      rowVersion,
      dataSourceMode: mode,
      name: optionalTextOrNull(f.name.value),
      identifier: optionalTextOrNull(f.identifier.value),
      aggregatedGoodsCategory: optionalTextOrNull(f.aggregatedGoodsCategory.value),
      purchasedInputRecordId: optionalTextOrNull(f.purchasedInputRecordId.value),
      supplierId: optionalTextOrNull(f.supplierId.value),
      cnCode: this.selectedCnCode(),
      countryOfOrigin: optionalTextOrNull(f.countryOfOrigin.value),
      productionRoute: optionalTextOrNull(f.productionRoute.value),
      quantity: optionalDecimalOrNull(f.quantity.value),
      quantityUnit: optionalTextOrNull(f.quantityUnit.value),
      nonCbamQuantity: optionalDecimalOrNull(f.nonCbamQuantity.value),
      nonCbamQuantityUnit: optionalTextOrNull(f.nonCbamQuantityUnit.value),
      provenanceNotes: optionalTextOrNull(f.provenanceNotes.value),
      evidenceReference: optionalTextOrNull(f.evidenceReference.value),
      notes: optionalTextOrNull(f.notes.value),
    };

    if (mode === MODE_SUPPLIER_DATA) {
      const specificDirect = optionalDecimalOrNull(f.specificDirectEmbeddedEmissions.value);
      const intensity = optionalDecimalOrNull(f.electricityConsumptionIntensity.value);
      const emissionFactor = optionalDecimalOrNull(f.electricityEmissionFactor.value);
      payload.specificDirectEmbeddedEmissions = specificDirect;
      payload.specificDirectUnit = specificDirect == null ? null : this.specificDirectUnit();
      payload.specificDirectSourceCode = optionalTextOrNull(f.specificDirectSourceCode.value);
      payload.electricityConsumptionIntensity = intensity;
      payload.electricityIntensityUnit = intensity == null ? null : this.electricityIntensityUnit();
      payload.electricityIntensitySourceCode = optionalTextOrNull(
        f.electricityIntensitySourceCode.value,
      );
      payload.electricityEmissionFactor = emissionFactor;
      payload.electricityEfUnit = emissionFactor == null ? null : this.electricityEfUnit();
      payload.electricityEfSourceCode = optionalTextOrNull(f.electricityEfSourceCode.value);
      payload.defaultValueId = null;
      payload.defaultJustificationCode = null;
    } else {
      payload.specificDirectEmbeddedEmissions = null;
      payload.specificDirectUnit = null;
      payload.specificDirectSourceCode = null;
      payload.electricityConsumptionIntensity = null;
      payload.electricityIntensityUnit = null;
      payload.electricityIntensitySourceCode = null;
      payload.electricityEmissionFactor = null;
      payload.electricityEfUnit = null;
      payload.electricityEfSourceCode = null;
      payload.defaultValueId = this.selectedDefaultValueId();
      payload.defaultJustificationCode = optionalTextOrNull(f.defaultJustificationCode.value);
    }

    return payload;
  }

  private handleMutationError(err: unknown): void {
    const message = mapPrecursorApiError(err);
    if (isConflictMessage(message)) {
      this.conflictMessage.set(message);
      this.actionError.set(null);
    } else {
      this.actionError.set(message);
      this.conflictMessage.set(null);
    }
    this.liveMessage.set(message);
  }
}
