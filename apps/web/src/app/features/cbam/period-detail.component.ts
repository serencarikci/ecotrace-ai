import { Component, inject, OnInit, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatTabsModule } from '@angular/material/tabs';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';
import { AuthService } from '../../core/services/auth.service';
import { extractApiErrorMessage } from '../../core/services/error.util';
import { canConfigureCbam } from '../../core/services/roles.util';
import {
  calculationStatusLabel as mapCalculationStatusLabel,
  factorSourceLabel as mapFactorSourceLabel,
  readinessCheckLabel as mapReadinessCheckLabel,
  readinessStatusLabel as mapReadinessStatusLabel,
  resolutionStatusLabel as mapResolutionStatusLabel,
} from './cbam-display-labels';
import {
  CbamActivityRecord,
  CbamActivityType,
  CbamAllocationResult,
  CbamAllocationRule,
  CbamApiService,
  CbamCalculationResult,
  CbamCalculationRun,
  CbamExportArtifact,
  CbamExportReadiness,
  CbamExportRun,
  CbamExportTemplate,
  CbamFactorDefinition,
  CbamFactorResolution,
  CbamFactorValue,
  CbamInstallation,
  CbamPeriodBinding,
  CbamPeriodSummary,
  CbamProductionRecord,
  CbamPurchasedInput,
  CbamReferenceSource,
  CbamUnit,
} from './cbam-api.service';

@Component({
  selector: 'app-cbam-period-detail',
  standalone: true,
  imports: [
    RouterLink,
    ReactiveFormsModule,
    DatePipe,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatTabsModule,
    MatTableModule,
    MatTooltipModule,
  ],
  templateUrl: './period-detail.component.html',
  styleUrl: './cbam-pages.scss',
})
export class CbamPeriodDetailComponent implements OnInit {
  private readonly api = inject(CbamApiService);
  private readonly auth = inject(AuthService);
  private readonly route = inject(ActivatedRoute);
  private readonly fb = inject(FormBuilder);

  readonly item = signal<CbamPeriodBinding | null>(null);
  readonly loading = signal(true);
  readonly errorMessage = signal<string | null>(null);
  readonly canConfigure = canConfigureCbam(this.auth.currentRoles());

  readonly installations = signal<CbamInstallation[]>([]);
  readonly activityTypes = signal<CbamActivityType[]>([]);
  readonly units = signal<CbamUnit[]>([]);
  readonly productionRecords = signal<CbamProductionRecord[]>([]);
  readonly activityRecords = signal<CbamActivityRecord[]>([]);
  readonly purchasedInputs = signal<CbamPurchasedInput[]>([]);
  readonly allocationRules = signal<CbamAllocationRule[]>([]);
  readonly allocationResults = signal<CbamAllocationResult[]>([]);
  readonly factorResolutions = signal<CbamFactorResolution[]>([]);
  readonly factorDefinitions = signal<CbamFactorDefinition[]>([]);
  readonly referenceSources = signal<CbamReferenceSource[]>([]);
  readonly defaultFactorValues = signal<CbamFactorValue[]>([]);
  readonly calculationRuns = signal<CbamCalculationRun[]>([]);
  readonly selectedRun = signal<CbamCalculationRun | null>(null);
  readonly calculationResults = signal<CbamCalculationResult[]>([]);
  readonly exportTemplates = signal<CbamExportTemplate[]>([]);
  readonly selectedTemplateId = signal<string | null>(null);
  readonly exportReadiness = signal<CbamExportReadiness | null>(null);
  readonly periodSummary = signal<CbamPeriodSummary | null>(null);
  readonly exportRuns = signal<CbamExportRun[]>([]);
  readonly exportBusy = signal(false);

  readonly productionColumns = ['installation', 'quantity', 'unit', 'date', 'status', 'actions'];
  readonly activityColumns = [
    'type',
    'quantity',
    'unit',
    'dataSource',
    'status',
    'actions',
  ];
  readonly purchasedColumns = [
    'name',
    'quantity',
    'consumed',
    'embedded',
    'status',
    'actions',
  ];
  readonly allocationRuleColumns = [
    'name',
    'method',
    'ratio',
    'status',
    'actions',
  ];
  readonly allocationResultColumns = [
    'sourceType',
    'sourceQuantity',
    'method',
    'ratio',
    'allocated',
    'rule',
    'created',
    'actions',
  ];
  readonly factorColumns = [
    'source',
    'activity',
    'factor',
    'dataSource',
    'status',
    'value',
    'unit',
    'reference',
    'actions',
  ];
  readonly calculationResultColumns = [
    'source',
    'quantity',
    'factor',
    'factorSource',
    'result',
    'unit',
    'status',
    'error',
    'actions',
  ];
  readonly exportHistoryColumns = [
    'date',
    'template',
    'calc',
    'status',
    'checksum',
    'actions',
  ];

  readonly productionForm = this.fb.nonNullable.group({
    installationProfileId: ['', Validators.required],
    quantity: ['', Validators.required],
    unit: ['t', Validators.required],
    productionDate: [''],
    notes: [''],
  });

  readonly activityForm = this.fb.nonNullable.group({
    installationProfileId: ['', Validators.required],
    activityType: ['ELECTRICITY', Validators.required],
    quantity: ['', Validators.required],
    unit: ['kWh', Validators.required],
    dataSourceType: ['PRIMARY', Validators.required],
    sourceReference: [''],
    measurementMethod: [''],
    supplierName: [''],
    certificateReference: [''],
    notes: [''],
  });

  readonly purchasedForm = this.fb.nonNullable.group({
    installationProfileId: ['', Validators.required],
    inputName: ['', Validators.required],
    supplierName: [''],
    quantity: ['', Validators.required],
    unit: ['t', Validators.required],
    consumedQuantity: [''],
    consumedUnit: [''],
    embeddedEmissionValue: [''],
    embeddedEmissionUnit: [''],
    embeddedEmissionSourceType: ['NOT_PROVIDED'],
    notes: [''],
  });

  readonly allocationForm = this.fb.nonNullable.group({
    installationProfileId: ['', Validators.required],
    allocationMethod: ['PRODUCTION_QUANTITY_RATIO', Validators.required],
    name: ['', Validators.required],
    description: [''],
    numeratorProductionRecordId: [''],
    denominatorProductionRecordId: [''],
    allocationRatio: [''],
    rationale: [''],
    sourceReference: [''],
    allocateActivityRecordId: [''],
    allocatePurchasedInputId: [''],
  });

  readonly primaryPropertyForm = this.fb.nonNullable.group({
    activityRecordId: ['', Validators.required],
    propertyCode: ['NET_CALORIFIC_VALUE', Validators.required],
    numericValue: ['', Validators.required],
    unit: ['MJ/L', Validators.required],
    sourceReference: [''],
    notes: [''],
  });

  readonly resolveForm = this.fb.nonNullable.group({
    activityRecordId: [''],
    purchasedInputId: [''],
    allocationResultId: [''],
    factorDefinitionCode: ['NET_CALORIFIC_VALUE', Validators.required],
  });

  private bindingId = '';

  ngOnInit(): void {
    this.bindingId = this.route.snapshot.paramMap.get('bindingId') ?? '';
    this.reload();
    this.api.listInstallations({ page: 1, pageSize: 100 }).subscribe({
      next: (page) => this.installations.set(page.items.filter((i) => i.status !== 'archived')),
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
    this.api.listActivityTypes().subscribe({
      next: (items) => this.activityTypes.set(items),
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
    this.api.listUnits().subscribe({
      next: (items) => this.units.set(items),
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }

  reload(): void {
    this.loading.set(true);
    this.errorMessage.set(null);
    this.api.getPeriodBinding(this.bindingId).subscribe({
      next: (row) => {
        this.item.set(row);
        this.loading.set(false);
        this.reloadCollections();
      },
      error: (err: unknown) => {
        this.loading.set(false);
        this.errorMessage.set(extractApiErrorMessage(err));
      },
    });
  }

  reloadCollections(): void {
    this.api.listProductionRecords(this.bindingId).subscribe({
      next: (page) => this.productionRecords.set(page.items),
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
    this.api.listActivityRecords(this.bindingId).subscribe({
      next: (page) => this.activityRecords.set(page.items),
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
    this.api.listPurchasedInputs(this.bindingId).subscribe({
      next: (page) => this.purchasedInputs.set(page.items),
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
    this.api.listAllocationRules(this.bindingId).subscribe({
      next: (page) => this.allocationRules.set(page.items),
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
    this.api.listAllocationResults(this.bindingId).subscribe({
      next: (page) => this.allocationResults.set(page.items),
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
    this.api.listFactorResolutions(this.bindingId).subscribe({
      next: (page) => this.factorResolutions.set(page.items),
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
    this.api.listFactorDefinitions().subscribe({
      next: (page) => {
        this.factorDefinitions.set(page.items);
        const ncv = page.items.find((d) => d.code === 'NET_CALORIFIC_VALUE');
        if (ncv) {
          this.api.listFactorValues(ncv.id).subscribe({
            next: (values) =>
              this.defaultFactorValues.set(
                values.items.filter((v) => v.dataSourceType === 'DEFAULT_REFERENCE'),
              ),
            error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
          });
        }
      },
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
    this.api.listReferenceSources().subscribe({
      next: (page) => this.referenceSources.set(page.items),
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
    this.api.listCalculationRuns(this.bindingId).subscribe({
      next: (page) => {
        this.calculationRuns.set(page.items);
        const latest = page.items[0] ?? null;
        this.selectedRun.set(latest);
        if (latest) {
          this.loadCalculationResults(latest.id);
        } else {
          this.calculationResults.set([]);
        }
      },
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
    this.reloadExportPanel();
  }

  reloadExportPanel(): void {
    this.api.listExportTemplates().subscribe({
      next: (page) => {
        const active = page.items.filter((t) => t.status === 'ACTIVE');
        this.exportTemplates.set(active);
        const current = this.selectedTemplateId();
        if (!current || !active.some((t) => t.id === current)) {
          this.selectedTemplateId.set(active[0]?.id ?? null);
        }
        this.loadExportReadiness();
      },
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
    this.api.getPeriodSummary(this.bindingId).subscribe({
      next: (summary) => this.periodSummary.set(summary),
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
    this.api.listExportRuns(this.bindingId).subscribe({
      next: (page) => this.exportRuns.set(page.items),
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }

  loadExportReadiness(): void {
    const templateId = this.selectedTemplateId() ?? undefined;
    this.api
      .getExportReadiness(this.bindingId, {
        templateId,
        calculationRunId: this.selectedRun()?.id,
      })
      .subscribe({
        next: (body) => this.exportReadiness.set(body),
        error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
      });
  }

  loadCalculationResults(runId: string): void {
    this.api.listCalculationResults(runId).subscribe({
      next: (page) => this.calculationResults.set(page.items),
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }

  startAndExecuteCalculation(): void {
    this.errorMessage.set(null);
    this.api.createCalculationRun(this.bindingId).subscribe({
      next: (run) => {
        this.api
          .executeCalculationRun(run.id, { allowUnallocatedActivity: true })
          .subscribe({
            next: (executed) => {
              this.selectedRun.set(executed);
              this.reloadCollections();
            },
            error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
          });
      },
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }

  selectCalculationRun(run: CbamCalculationRun): void {
    this.selectedRun.set(run);
    this.loadCalculationResults(run.id);
  }

  recalculateCalculationResult(row: CbamCalculationResult): void {
    this.errorMessage.set(null);
    this.api.recalculateCalculationResult(row.id).subscribe({
      next: () => {
        const run = this.selectedRun();
        if (run) {
          this.loadCalculationResults(run.id);
        }
        this.reloadCollections();
      },
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }

  calculationStatusLabel(status: string): string {
    return mapCalculationStatusLabel(status);
  }

  factorSourceLabel(status: string | null): string {
    return mapFactorSourceLabel(status);
  }

  resolutionStatusLabel(status: string): string {
    return mapResolutionStatusLabel(status);
  }

  factorDefinitionCode(id: string): string {
    return this.factorDefinitions().find((d) => d.id === id)?.code ?? id;
  }

  sourceLabel(sourceType: string, sourceId: string): string {
    if (sourceType === 'ACTIVITY_RECORD') {
      const a = this.activityRecords().find((r) => r.id === sourceId);
      return a ? `${a.activityType} (${a.quantity} ${a.unit})` : sourceId;
    }
    if (sourceType === 'PURCHASED_INPUT_RECORD') {
      const p = this.purchasedInputs().find((r) => r.id === sourceId);
      return p ? p.inputName : sourceId;
    }
    return sourceId;
  }

  referenceLabel(sourceId: string | null): string {
    if (!sourceId) {
      return '—';
    }
    const found = this.referenceSources().find((s) => s.id === sourceId);
    return found ? found.code : '—';
  }

  submitPrimaryProperty(): void {
    if (!this.canMutateData || this.primaryPropertyForm.invalid) {
      this.primaryPropertyForm.markAllAsTouched();
      return;
    }
    const v = this.primaryPropertyForm.getRawValue();
    this.api
      .addActivityProperty(v.activityRecordId, {
        propertyCode: v.propertyCode,
        numericValue: v.numericValue,
        unit: v.unit,
        sourceType: 'PRIMARY',
        sourceReference: v.sourceReference || null,
      })
      .subscribe({
        next: () => {
          this.primaryPropertyForm.patchValue({ numericValue: '', sourceReference: '', notes: '' });
          this.reloadCollections();
          this.errorMessage.set(null);
        },
        error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
      });
  }

  resolveSelected(): void {
    if (!this.canMutateData) {
      return;
    }
    const v = this.resolveForm.getRawValue();
    const code = v.factorDefinitionCode;
    if (v.activityRecordId) {
      this.api.resolveActivityFactor(v.activityRecordId, code).subscribe({
        next: () => {
          this.reloadCollections();
          this.errorMessage.set(null);
        },
        error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
      });
      return;
    }
    if (v.purchasedInputId) {
      this.api.resolvePurchasedFactor(v.purchasedInputId, code).subscribe({
        next: () => {
          this.reloadCollections();
          this.errorMessage.set(null);
        },
        error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
      });
      return;
    }
    if (v.allocationResultId) {
      this.api.resolveAllocationFactor(v.allocationResultId, code).subscribe({
        next: () => {
          this.reloadCollections();
          this.errorMessage.set(null);
        },
        error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
      });
      return;
    }
    this.errorMessage.set('Select a source to resolve.');
  }

  reresolve(row: CbamFactorResolution): void {
    if (!this.canMutateData) {
      return;
    }
    const code = this.factorDefinitionCode(row.factorDefinitionId);
    if (row.sourceType === 'ACTIVITY_RECORD') {
      this.api.resolveActivityFactor(row.sourceId, code).subscribe({
        next: () => this.reloadCollections(),
        error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
      });
    } else if (row.sourceType === 'PURCHASED_INPUT_RECORD') {
      this.api.resolvePurchasedFactor(row.sourceId, code).subscribe({
        next: () => this.reloadCollections(),
        error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
      });
    } else if (row.sourceType === 'ALLOCATION_RESULT') {
      this.api.resolveAllocationFactor(row.sourceId, code).subscribe({
        next: () => this.reloadCollections(),
        error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
      });
    }
  }

  get allocationMethod(): string {
    return this.allocationForm.controls.allocationMethod.value;
  }

  productionRatioPreview(): { target: string; base: string; ratioPct: string } | null {
    if (this.allocationMethod !== 'PRODUCTION_QUANTITY_RATIO') {
      return null;
    }
    const numId = this.allocationForm.controls.numeratorProductionRecordId.value;
    const denId = this.allocationForm.controls.denominatorProductionRecordId.value;
    const num = this.productionRecords().find((r) => r.id === numId);
    const den = this.productionRecords().find((r) => r.id === denId);
    if (!num || !den || num.unit !== den.unit) {
      return null;
    }
    const n = Number(num.quantity);
    const d = Number(den.quantity);
    if (!(d > 0) || n < 0 || n > d) {
      return null;
    }
    const pct = ((n / d) * 100).toFixed(2);
    return {
      target: `${num.quantity} ${num.unit}`,
      base: `${den.quantity} ${den.unit}`,
      ratioPct: `${pct}%`,
    };
  }

  ruleLabel(ruleId: string): string {
    const found = this.allocationRules().find((r) => r.id === ruleId);
    return found ? found.name : ruleId;
  }

  formatRatioPercent(ratio: string | null): string {
    if (ratio == null || ratio === '') {
      return '—';
    }
    const value = Number(ratio);
    if (Number.isNaN(value)) {
      return ratio;
    }
    return `${(value * 100).toFixed(2)}%`;
  }

  get canMutateData(): boolean {
    const status = this.item()?.status;
    return this.canConfigure && (status === 'draft' || status === 'data_collection');
  }

  selectedTemplate(): CbamExportTemplate | null {
    const id = this.selectedTemplateId();
    return this.exportTemplates().find((t) => t.id === id) ?? null;
  }

  summaryMetricEntries(): Array<[string, string]> {
    const metrics = this.periodSummary()?.metrics ?? {};
    return Object.entries(metrics).map(([key, value]) => [key, String(value)]);
  }

  readinessStatusLabel(status: string): string {
    return mapReadinessStatusLabel(status);
  }

  readinessCheckLabel(status: string): string {
    return mapReadinessCheckLabel(status);
  }

  canGenerateExport(): boolean {
    const readiness = this.exportReadiness();
    return (
      !!this.selectedTemplateId() &&
      !!readiness &&
      readiness.status !== 'NOT_READY' &&
      !this.exportBusy()
    );
  }

  onTemplateSelected(templateId: string): void {
    this.selectedTemplateId.set(templateId);
    this.loadExportReadiness();
  }

  generateExport(): void {
    if (!this.canConfigure || !this.canGenerateExport()) {
      return;
    }
    this.exportBusy.set(true);
    this.errorMessage.set(null);
    this.api
      .createExportRun(this.bindingId, {
        exportTemplateId: this.selectedTemplateId() ?? undefined,
        calculationRunId: this.selectedRun()?.id,
      })
      .subscribe({
        next: () => {
          this.exportBusy.set(false);
          this.reloadExportPanel();
        },
        error: (err: unknown) => {
          this.exportBusy.set(false);
          this.errorMessage.set(extractApiErrorMessage(err));
        },
      });
  }

  downloadLatestXlsx(run: CbamExportRun): void {
    this.api.listExportArtifacts(run.id).subscribe({
      next: (artifacts) => {
        const xlsx =
          artifacts.find((a) => a.artifactType === 'XLSX') ??
          artifacts.find((a) => a.fileName.endsWith('.xlsx'));
        if (!xlsx) {
          this.errorMessage.set('Excel file not found.');
          return;
        }
        this.downloadArtifact(xlsx);
      },
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }

  downloadArtifact(artifact: CbamExportArtifact): void {
    this.api.downloadExportArtifact(artifact.id).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = artifact.fileName;
        a.click();
        URL.revokeObjectURL(url);
      },
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }

  openDataCollection(): void {
    const current = this.item();
    if (!current || !this.canConfigure) {
      return;
    }
    this.api.openDataCollection(current.id, current.rowVersion).subscribe({
      next: (row) => {
        this.item.set(row);
        this.errorMessage.set(null);
      },
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }

  archive(): void {
    const current = this.item();
    if (!current || !this.canConfigure) {
      return;
    }
    if (!confirm('Archive this draft binding?')) {
      return;
    }
    this.api.archivePeriodBinding(current.id, current.rowVersion).subscribe({
      next: (row) => this.item.set(row),
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }

  submitProduction(): void {
    if (!this.canMutateData || this.productionForm.invalid) {
      this.productionForm.markAllAsTouched();
      return;
    }
    const v = this.productionForm.getRawValue();
    this.api
      .createProductionRecord(this.bindingId, {
        installationProfileId: v.installationProfileId,
        quantity: v.quantity,
        unit: v.unit,
        productionDate: v.productionDate || null,
        notes: v.notes || null,
      })
      .subscribe({
        next: () => {
          this.productionForm.patchValue({ quantity: '', notes: '', productionDate: '' });
          this.reloadCollections();
          this.errorMessage.set(null);
        },
        error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
      });
  }

  archiveProduction(row: CbamProductionRecord): void {
    if (!this.canMutateData) {
      return;
    }
    this.api.archiveProductionRecord(row.id, row.rowVersion).subscribe({
      next: () => this.reloadCollections(),
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }

  submitActivity(): void {
    if (!this.canMutateData || this.activityForm.invalid) {
      this.activityForm.markAllAsTouched();
      return;
    }
    const v = this.activityForm.getRawValue();
    this.api
      .createActivityRecord(this.bindingId, {
        installationProfileId: v.installationProfileId,
        activityType: v.activityType,
        quantity: v.quantity,
        unit: v.unit,
        dataSourceType: v.dataSourceType,
        sourceReference: v.sourceReference || null,
        measurementMethod: v.measurementMethod || null,
        supplierName: v.supplierName || null,
        certificateReference: v.certificateReference || null,
        notes: v.notes || null,
      })
      .subscribe({
        next: () => {
          this.activityForm.patchValue({
            quantity: '',
            sourceReference: '',
            measurementMethod: '',
            supplierName: '',
            certificateReference: '',
            notes: '',
          });
          this.reloadCollections();
          this.errorMessage.set(null);
        },
        error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
      });
  }

  archiveActivity(row: CbamActivityRecord): void {
    if (!this.canMutateData) {
      return;
    }
    this.api.archiveActivityRecord(row.id, row.rowVersion).subscribe({
      next: () => this.reloadCollections(),
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }

  submitPurchased(): void {
    if (!this.canMutateData || this.purchasedForm.invalid) {
      this.purchasedForm.markAllAsTouched();
      return;
    }
    const v = this.purchasedForm.getRawValue();
    this.api
      .createPurchasedInput(this.bindingId, {
        installationProfileId: v.installationProfileId,
        inputName: v.inputName,
        supplierName: v.supplierName || null,
        quantity: v.quantity,
        unit: v.unit,
        consumedQuantity: v.consumedQuantity || null,
        consumedUnit: v.consumedUnit || null,
        embeddedEmissionValue: v.embeddedEmissionValue || null,
        embeddedEmissionUnit: v.embeddedEmissionUnit || null,
        embeddedEmissionSourceType: v.embeddedEmissionSourceType,
        notes: v.notes || null,
      })
      .subscribe({
        next: () => {
          this.purchasedForm.patchValue({
            inputName: '',
            supplierName: '',
            quantity: '',
            consumedQuantity: '',
            consumedUnit: '',
            embeddedEmissionValue: '',
            embeddedEmissionUnit: '',
            notes: '',
          });
          this.reloadCollections();
          this.errorMessage.set(null);
        },
        error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
      });
  }

  archivePurchased(row: CbamPurchasedInput): void {
    if (!this.canMutateData) {
      return;
    }
    this.api.archivePurchasedInput(row.id, row.rowVersion).subscribe({
      next: () => this.reloadCollections(),
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }

  installationLabel(id: string): string {
    const found = this.installations().find((i) => i.id === id);
    return found ? `${found.code} — ${found.name}` : id;
  }

  submitAllocationRule(): void {
    if (!this.canMutateData || this.allocationForm.invalid) {
      this.allocationForm.markAllAsTouched();
      return;
    }
    const v = this.allocationForm.getRawValue();
    if (v.allocationMethod === 'MANUAL_RATIO' && !v.rationale.trim()) {
      this.errorMessage.set('Reason is required.');
      return;
    }
    if (
      v.allocationMethod === 'PRODUCTION_QUANTITY_RATIO' &&
      (!v.numeratorProductionRecordId || !v.denominatorProductionRecordId)
    ) {
      this.errorMessage.set('Select target production and total base production.');
      return;
    }
    this.api
      .createAllocationRule(this.bindingId, {
        installationProfileId: v.installationProfileId,
        allocationMethod: v.allocationMethod,
        name: v.name,
        description: v.description || null,
        allocationRatio:
          v.allocationMethod === 'MANUAL_RATIO' ? v.allocationRatio || null : null,
        numeratorProductionRecordId:
          v.allocationMethod === 'PRODUCTION_QUANTITY_RATIO'
            ? v.numeratorProductionRecordId || null
            : null,
        denominatorProductionRecordId:
          v.allocationMethod === 'PRODUCTION_QUANTITY_RATIO'
            ? v.denominatorProductionRecordId || null
            : null,
        rationale: v.allocationMethod === 'MANUAL_RATIO' ? v.rationale || null : null,
        sourceReference:
          v.allocationMethod === 'MANUAL_RATIO' ? v.sourceReference || null : null,
      })
      .subscribe({
        next: () => {
          this.allocationForm.patchValue({
            name: '',
            description: '',
            allocationRatio: '',
            rationale: '',
            sourceReference: '',
            numeratorProductionRecordId: '',
            denominatorProductionRecordId: '',
          });
          this.reloadCollections();
          this.errorMessage.set(null);
        },
        error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
      });
  }

  activateAllocationRule(rule: CbamAllocationRule): void {
    if (!this.canMutateData || rule.status !== 'DRAFT') {
      return;
    }
    this.api.activateAllocationRule(rule.id, rule.rowVersion).subscribe({
      next: () => {
        this.reloadCollections();
        this.errorMessage.set(null);
      },
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }

  archiveAllocationRule(rule: CbamAllocationRule): void {
    if (!this.canMutateData || rule.status === 'ARCHIVED') {
      return;
    }
    this.api.archiveAllocationRule(rule.id, rule.rowVersion).subscribe({
      next: () => this.reloadCollections(),
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }

  allocateSelectedActivity(rule: CbamAllocationRule): void {
    if (!this.canMutateData || rule.status !== 'ACTIVE') {
      return;
    }
    const activityId = this.allocationForm.controls.allocateActivityRecordId.value;
    if (!activityId) {
      this.errorMessage.set('Select an activity record for allocation.');
      return;
    }
    this.api.allocateActivityRecord(rule.id, activityId).subscribe({
      next: () => {
        this.reloadCollections();
        this.errorMessage.set(null);
      },
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }

  allocateSelectedPurchased(rule: CbamAllocationRule): void {
    if (!this.canMutateData || rule.status !== 'ACTIVE') {
      return;
    }
    const inputId = this.allocationForm.controls.allocatePurchasedInputId.value;
    if (!inputId) {
      this.errorMessage.set('Select a purchased input for allocation.');
      return;
    }
    this.api.allocatePurchasedInput(rule.id, inputId).subscribe({
      next: () => {
        this.reloadCollections();
        this.errorMessage.set(null);
      },
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }

  recalculateResult(row: CbamAllocationResult): void {
    if (!this.canMutateData || !row.isCurrent) {
      return;
    }
    this.api.recalculateAllocationResult(row.id).subscribe({
      next: () => {
        this.reloadCollections();
        this.errorMessage.set(null);
      },
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }
}
