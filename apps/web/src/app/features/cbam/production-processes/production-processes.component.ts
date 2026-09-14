import {
  Component,
  DestroyRef,
  computed,
  effect,
  inject,
  input,
  output,
  signal,
  untracked,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatRadioModule } from '@angular/material/radio';
import { MatSelectModule } from '@angular/material/select';
import { MatTableModule } from '@angular/material/table';
import { Subject, forkJoin, of } from 'rxjs';
import { catchError, finalize, switchMap, tap } from 'rxjs/operators';
import {
  CbamApiService,
  CbamInstallation,
  CbamProductProfile,
  CbamProductionProcess,
  CbamProductionProcessControlledList,
  CbamProductionProcessCreate,
  CbamProductionProcessMetadata,
  CbamProductionProcessProductUse,
  CbamProductionProcessReadiness,
  CbamProductionProcessUpdate,
} from '../cbam-api.service';
import {
  DATA_QUALITY_JUSTIFICATION_LIST,
  DATA_QUALITY_LIST,
  DATA_VERIFICATION_LIST,
  HEAT_FACTOR_UNIT,
  HEAT_QUANTITY_UNIT,
  EXPORTED_ELECTRICITY_FACTOR_UNIT,
  EXPORTED_ELECTRICITY_QUANTITY_UNIT,
  METHOD_CONVENTIONAL,
  METHOD_MASS_BALANCE,
  METHOD_PROCESS_EMISSIONS,
  PROCESS_MASS_UNITS,
  WASTE_GAS_QUANTITY_UNIT,
  balanceHelpMessage,
  formatDecimalDisplay,
  isMethodEnabled,
  mapBalanceStatusLabel,
  mapCalculationMethodLabel,
  mapProcessApiError,
  mapProcessBlockingCode,
  mapProcessReadinessStatusLabel,
  optionalDecimalOrNull,
  optionalTextOrNull,
  profileOptionLabel,
} from './production-processes.util';

type TriState = 'unset' | 'yes' | 'no';

@Component({
  selector: 'app-cbam-production-processes',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatRadioModule,
    MatSelectModule,
    MatTableModule,
  ],
  templateUrl: './production-processes.component.html',
  styleUrl: './production-processes.component.scss',
})
export class CbamProductionProcessesComponent {
  private readonly api = inject(CbamApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly fb = inject(FormBuilder);
  private readonly load$ = new Subject<string>();
  private loadSeq = 0;

  readonly bindingId = input.required<string>();
  readonly canConfigure = input(false);
  readonly canMutate = input(false);
  readonly goToDirectEmissionsAllocation = output<void>();
  readonly goToIndirectEmissionsAllocation = output<void>();

  readonly loading = signal(false);
  readonly loadError = signal<string | null>(null);
  readonly processes = signal<CbamProductionProcess[]>([]);
  readonly selected = signal<CbamProductionProcess | null>(null);
  readonly readiness = signal<CbamProductionProcessReadiness | null>(null);
  readonly installations = signal<CbamInstallation[]>([]);
  readonly profiles = signal<CbamProductProfile[]>([]);
  readonly metadata = signal<CbamProductionProcessMetadata | null>(null);
  readonly controlledLists = signal<CbamProductionProcessControlledList[]>([]);
  readonly detailLoading = signal(false);
  readonly submitting = signal(false);
  readonly actionError = signal<string | null>(null);
  readonly conflictMessage = signal<string | null>(null);
  readonly successMessage = signal<string | null>(null);
  readonly liveMessage = signal('');
  readonly showCreateForm = signal(false);
  readonly showArchiveConfirm = signal(false);
  /** Bumps when form values change so heat/waste visibility recomputes. */
  readonly formEpoch = signal(0);

  readonly massUnits = PROCESS_MASS_UNITS;
  readonly heatQuantityUnit = HEAT_QUANTITY_UNIT;
  readonly heatFactorUnit = HEAT_FACTOR_UNIT;
  readonly wasteGasQuantityUnit = WASTE_GAS_QUANTITY_UNIT;
  readonly exportedElectricityQuantityUnit = EXPORTED_ELECTRICITY_QUANTITY_UNIT;
  readonly exportedElectricityFactorUnit = EXPORTED_ELECTRICITY_FACTOR_UNIT;
  readonly methodConventional = METHOD_CONVENTIONAL;
  readonly methodProcessEmissions = METHOD_PROCESS_EMISSIONS;
  readonly methodMassBalance = METHOD_MASS_BALANCE;

  readonly formatDecimal = formatDecimalDisplay;
  readonly readinessLabel = mapProcessReadinessStatusLabel;
  readonly balanceLabel = mapBalanceStatusLabel;
  readonly balanceHelp = balanceHelpMessage;
  readonly blockingMessage = mapProcessBlockingCode;
  readonly methodLabel = mapCalculationMethodLabel;
  readonly methodEnabled = isMethodEnabled;
  readonly profileLabel = profileOptionLabel;

  readonly listColumns = ['name', 'product', 'method', 'status', 'balance', 'actions'] as const;

  readonly form = this.fb.nonNullable.group({
    name: [''],
    identifier: [''],
    installationProfileId: [''],
    productProfileVersionId: [''],
    calculationMethod: [METHOD_CONVENTIONAL],
    producedQuantity: [''],
    producedQuantityUnit: ['t'],
    marketedQuantity: [''],
    marketedQuantityUnit: ['t'],
    nonCbamQuantity: [''],
    nonCbamQuantityUnit: ['t'],
    hasMeasurableHeat: this.fb.nonNullable.control<TriState>('unset'),
    heatImportedQuantity: [''],
    heatExportedQuantity: [''],
    heatImportedEf: [''],
    heatExportedEf: [''],
    heatFactorSource: [''],
    heatFactorDocument: [''],
    hasWasteGas: this.fb.nonNullable.control<TriState>('unset'),
    wasteGasImportedQuantity: [''],
    wasteGasExportedQuantity: [''],
    wasteGasProvenance: [''],
    hasExportedElectricity: this.fb.nonNullable.control<TriState>('unset'),
    exportedElectricityQuantity: [''],
    exportedElectricityEmissionFactor: [''],
    exportedElectricityProvenance: [''],
    dataQualityCode: [''],
    dataVerificationCode: [''],
    dataQualityJustificationCode: [''],
    notes: [''],
  });

  readonly productUseForm = this.fb.nonNullable.group({
    targetProductProfileVersionId: [''],
    quantity: [''],
    unit: ['t'],
  });

  readonly createForm = this.fb.nonNullable.group({
    installationProfileId: [''],
    name: [''],
  });

  readonly canEdit = computed(
    () => this.canConfigure() && this.canMutate() && this.selected()?.status !== 'ARCHIVED',
  );

  readonly dataQualityList = computed(
    () => this.controlledLists().find((l) => l.listCode === DATA_QUALITY_LIST) ?? null,
  );
  readonly dataVerificationList = computed(
    () => this.controlledLists().find((l) => l.listCode === DATA_VERIFICATION_LIST) ?? null,
  );
  readonly dataQualityJustificationList = computed(
    () =>
      this.controlledLists().find((l) => l.listCode === DATA_QUALITY_JUSTIFICATION_LIST) ?? null,
  );

  readonly targetProfileOptions = computed(() => {
    this.formEpoch();
    const sourceId = this.form.controls.productProfileVersionId.value || null;
    return this.profiles().filter((p) => p.id !== sourceId);
  });

  readonly heatVisible = computed(() => {
    this.formEpoch();
    return this.form.controls.hasMeasurableHeat.value === 'yes';
  });
  readonly wasteGasVisible = computed(() => {
    this.formEpoch();
    return this.form.controls.hasWasteGas.value === 'yes';
  });
  readonly exportedElectricityVisible = computed(() => {
    this.formEpoch();
    return this.form.controls.hasExportedElectricity.value === 'yes';
  });

  constructor() {
    this.form.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => {
      this.formEpoch.update((n) => n + 1);
    });

    this.load$
      .pipe(
        switchMap((bindingId) => {
          const seq = ++this.loadSeq;
          this.loading.set(true);
          this.loadError.set(null);
          this.liveMessage.set('Loading production processes.');
          return forkJoin({
            processes: this.api.listProductionProcesses(bindingId, {
              page: 1,
              pageSize: 100,
              includeArchived: false,
            }),
            installations: this.api.listInstallations({ page: 1, pageSize: 100, status: 'ACTIVE' }),
            profiles: this.api.listProductProfilesForBinding(bindingId, {
              page: 1,
              pageSize: 100,
            }),
            metadata: this.api.getProductionProcessMetadata().pipe(catchError(() => of(null))),
            lists: this.api.listProductionProcessControlledLists().pipe(catchError(() => of([]))),
          }).pipe(
            tap(({ processes, installations, profiles, metadata, lists }) => {
              if (seq !== this.loadSeq) {
                return;
              }
              this.processes.set(processes.items);
              this.installations.set(installations.items);
              this.profiles.set(profiles.items);
              this.metadata.set(metadata);
              this.controlledLists.set(lists);
              this.liveMessage.set('Production processes loaded.');
              const selectedId = this.selected()?.id;
              if (selectedId) {
                const still = processes.items.find((p) => p.id === selectedId);
                if (still) {
                  untracked(() => this.openProcess(still.id));
                } else {
                  this.selected.set(null);
                  this.readiness.set(null);
                }
              }
            }),
            catchError((err: unknown) => {
              if (seq === this.loadSeq) {
                this.loadError.set(mapProcessApiError(err));
                this.liveMessage.set('Production processes could not be loaded.');
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
        this.form.controls.installationProfileId.disable({ emitEvent: false });
        this.form.controls.calculationMethod.disable({ emitEvent: false });
      });
    });
  }

  reload(): void {
    this.load$.next(this.bindingId());
  }

  openProcess(processId: string): void {
    this.detailLoading.set(true);
    this.actionError.set(null);
    this.conflictMessage.set(null);
    this.successMessage.set(null);
    this.showArchiveConfirm.set(false);
    this.liveMessage.set('Loading process detail.');
    forkJoin({
      detail: this.api.getProductionProcess(this.bindingId(), processId),
      readiness: this.api.getProductionProcessReadiness(this.bindingId(), processId),
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
          this.liveMessage.set('Process detail loaded.');
        },
        error: (err: unknown) => {
          this.actionError.set(mapProcessApiError(err));
          this.liveMessage.set('Process detail could not be loaded.');
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
    const payload: CbamProductionProcessCreate = {
      installationProfileId,
      name: optionalTextOrNull(this.createForm.controls.name.value),
      calculationMethod: METHOD_CONVENTIONAL,
    };
    this.api
      .createProductionProcess(this.bindingId(), payload)
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.submitting.set(false)),
      )
      .subscribe({
        next: (created) => {
          this.showCreateForm.set(false);
          this.selected.set(created);
          this.successMessage.set('Draft process created.');
          this.liveMessage.set('Draft process created.');
          this.reload();
        },
        error: (err: unknown) => {
          this.handleMutationError(err);
        },
      });
  }

  saveDraft(): void {
    const row = this.selected();
    if (!row || !this.canEdit()) {
      return;
    }
    this.submitting.set(true);
    this.actionError.set(null);
    this.conflictMessage.set(null);
    this.successMessage.set(null);
    const payload = this.buildUpdatePayload(row.rowVersion);
    this.api
      .updateProductionProcessDraft(this.bindingId(), row.id, payload)
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
      .archiveProductionProcess(this.bindingId(), row.id, { rowVersion: row.rowVersion })
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.submitting.set(false)),
      )
      .subscribe({
        next: () => {
          this.showArchiveConfirm.set(false);
          this.selected.set(null);
          this.readiness.set(null);
          this.successMessage.set('Process archived.');
          this.liveMessage.set('Process archived.');
          this.reload();
        },
        error: (err: unknown) => this.handleMutationError(err),
      });
  }

  addProductUse(): void {
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
      this.actionError.set('Enter the produced quantity.');
      return;
    }
    this.submitting.set(true);
    this.actionError.set(null);
    this.api
      .createProductionProcessProductUse(this.bindingId(), row.id, {
        targetProductProfileVersionId: target,
        quantity,
        unit,
      })
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.submitting.set(false)),
      )
      .subscribe({
        next: () => {
          this.productUseForm.reset({ targetProductProfileVersionId: '', quantity: '', unit: 't' });
          this.successMessage.set('Product use added.');
          this.liveMessage.set('Product use added.');
          this.reload();
        },
        error: (err: unknown) => this.handleMutationError(err),
      });
  }

  removeProductUse(use: CbamProductionProcessProductUse): void {
    const row = this.selected();
    if (!row || !this.canEdit()) {
      return;
    }
    this.submitting.set(true);
    this.actionError.set(null);
    this.api
      .deleteProductionProcessProductUse(this.bindingId(), row.id, use.id)
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.submitting.set(false)),
      )
      .subscribe({
        next: () => {
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

  private applyDetailToForm(detail: CbamProductionProcess): void {
    const heat = detail.measurableHeat;
    const waste = detail.wasteGas;
    const exported = detail.processExportedElectricity;
    this.form.reset({
      name: detail.name ?? '',
      identifier: detail.identifier ?? '',
      installationProfileId: detail.installationProfileId,
      productProfileVersionId: detail.productProfileVersionId ?? '',
      calculationMethod: detail.calculationMethod || METHOD_CONVENTIONAL,
      producedQuantity: detail.distribution.producedQuantity ?? '',
      producedQuantityUnit: detail.distribution.producedQuantityUnit ?? 't',
      marketedQuantity: detail.distribution.marketedQuantity ?? '',
      marketedQuantityUnit: detail.distribution.marketedQuantityUnit ?? 't',
      nonCbamQuantity: detail.distribution.nonCbamQuantity ?? '',
      nonCbamQuantityUnit: detail.distribution.nonCbamQuantityUnit ?? 't',
      hasMeasurableHeat:
        heat.hasMeasurableHeat === true
          ? 'yes'
          : heat.hasMeasurableHeat === false
            ? 'no'
            : 'unset',
      heatImportedQuantity: heat.importedQuantity ?? '',
      heatExportedQuantity: heat.exportedQuantity ?? '',
      heatImportedEf: heat.importedEf ?? '',
      heatExportedEf: heat.exportedEf ?? '',
      heatFactorSource: heat.factorSource ?? '',
      heatFactorDocument: heat.factorDocument ?? '',
      hasWasteGas:
        waste.hasWasteGas === true ? 'yes' : waste.hasWasteGas === false ? 'no' : 'unset',
      wasteGasImportedQuantity: waste.importedQuantity ?? '',
      wasteGasExportedQuantity: waste.exportedQuantity ?? '',
      wasteGasProvenance: waste.provenance ?? '',
      hasExportedElectricity:
        exported.hasExportedElectricity === true
          ? 'yes'
          : exported.hasExportedElectricity === false
            ? 'no'
            : 'unset',
      exportedElectricityQuantity: exported.quantity ?? '',
      exportedElectricityEmissionFactor: exported.emissionFactor ?? '',
      exportedElectricityProvenance: exported.provenance ?? '',
      dataQualityCode: detail.dataQualityCode ?? '',
      dataVerificationCode: detail.dataVerificationCode ?? '',
      dataQualityJustificationCode: detail.dataQualityJustificationCode ?? '',
      notes: detail.notes ?? '',
    });
  }

  private buildUpdatePayload(rowVersion: number): CbamProductionProcessUpdate {
    const f = this.form.controls;
    const heatState = f.hasMeasurableHeat.value;
    const wasteState = f.hasWasteGas.value;
    const exportState = f.hasExportedElectricity.value;
    const hasHeat = heatState === 'yes' ? true : heatState === 'no' ? false : null;
    const hasWaste = wasteState === 'yes' ? true : wasteState === 'no' ? false : null;
    const hasExport = exportState === 'yes' ? true : exportState === 'no' ? false : null;

    const payload: CbamProductionProcessUpdate = {
      rowVersion,
      name: optionalTextOrNull(f.name.value),
      identifier: optionalTextOrNull(f.identifier.value),
      calculationMethod: METHOD_CONVENTIONAL,
      productProfileVersionId: optionalTextOrNull(f.productProfileVersionId.value),
      producedQuantity: optionalDecimalOrNull(f.producedQuantity.value),
      producedQuantityUnit: optionalTextOrNull(f.producedQuantityUnit.value),
      marketedQuantity: optionalDecimalOrNull(f.marketedQuantity.value),
      marketedQuantityUnit: optionalTextOrNull(f.marketedQuantityUnit.value),
      nonCbamQuantity: optionalDecimalOrNull(f.nonCbamQuantity.value),
      nonCbamQuantityUnit: optionalTextOrNull(f.nonCbamQuantityUnit.value),
      hasMeasurableHeat: hasHeat,
      hasWasteGas: hasWaste,
      hasExportedElectricity: hasExport,
      dataQualityCode: optionalTextOrNull(f.dataQualityCode.value),
      dataVerificationCode: optionalTextOrNull(f.dataVerificationCode.value),
      dataQualityJustificationCode: optionalTextOrNull(f.dataQualityJustificationCode.value),
      notes: optionalTextOrNull(f.notes.value),
    };

    if (hasHeat === true) {
      payload.heatImportedQuantity = optionalDecimalOrNull(f.heatImportedQuantity.value);
      payload.heatImportedUnit = HEAT_QUANTITY_UNIT;
      payload.heatExportedQuantity = optionalDecimalOrNull(f.heatExportedQuantity.value);
      payload.heatExportedUnit = HEAT_QUANTITY_UNIT;
      payload.heatImportedEf = optionalDecimalOrNull(f.heatImportedEf.value);
      payload.heatExportedEf = optionalDecimalOrNull(f.heatExportedEf.value);
      payload.heatEfUnit = HEAT_FACTOR_UNIT;
      payload.heatFactorSource = optionalTextOrNull(f.heatFactorSource.value);
      payload.heatFactorDocument = optionalTextOrNull(f.heatFactorDocument.value);
    } else if (hasHeat === false) {
      payload.heatImportedQuantity = null;
      payload.heatImportedUnit = null;
      payload.heatExportedQuantity = null;
      payload.heatExportedUnit = null;
      payload.heatImportedEf = null;
      payload.heatExportedEf = null;
      payload.heatEfUnit = null;
      payload.heatFactorSource = null;
      payload.heatFactorDocument = null;
    }

    if (hasWaste === true) {
      payload.wasteGasImportedQuantity = optionalDecimalOrNull(f.wasteGasImportedQuantity.value);
      payload.wasteGasImportedUnit = WASTE_GAS_QUANTITY_UNIT;
      payload.wasteGasExportedQuantity = optionalDecimalOrNull(f.wasteGasExportedQuantity.value);
      payload.wasteGasExportedUnit = WASTE_GAS_QUANTITY_UNIT;
      payload.wasteGasProvenance = optionalTextOrNull(f.wasteGasProvenance.value);
    } else if (hasWaste === false) {
      payload.wasteGasImportedQuantity = null;
      payload.wasteGasImportedUnit = null;
      payload.wasteGasExportedQuantity = null;
      payload.wasteGasExportedUnit = null;
      payload.wasteGasProvenance = null;
    }

    if (hasExport === true) {
      payload.exportedElectricityQuantity = optionalDecimalOrNull(
        f.exportedElectricityQuantity.value,
      );
      payload.exportedElectricityUnit = EXPORTED_ELECTRICITY_QUANTITY_UNIT;
      payload.exportedElectricityEmissionFactor = optionalDecimalOrNull(
        f.exportedElectricityEmissionFactor.value,
      );
      payload.exportedElectricityEfUnit = EXPORTED_ELECTRICITY_FACTOR_UNIT;
      payload.exportedElectricityProvenance = optionalTextOrNull(
        f.exportedElectricityProvenance.value,
      );
    } else if (hasExport === false) {
      payload.exportedElectricityQuantity = null;
      payload.exportedElectricityUnit = null;
      payload.exportedElectricityEmissionFactor = null;
      payload.exportedElectricityEfUnit = null;
      payload.exportedElectricityProvenance = null;
    }

    return payload;
  }

  private handleMutationError(err: unknown): void {
    const message = mapProcessApiError(err);
    if (message.includes('This process changed')) {
      this.conflictMessage.set(message);
      this.actionError.set(null);
    } else {
      this.actionError.set(message);
      this.conflictMessage.set(null);
    }
    this.liveMessage.set(message);
  }
}
