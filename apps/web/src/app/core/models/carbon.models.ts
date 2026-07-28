export interface EmissionFactorSource {
  id: string;
  code: string;
  name: string;
  publisher: string | null;
  description: string | null;
  sourceUrl: string | null;
  methodology: string | null;
  geographicCoverage: string | null;
  licenseName: string | null;
  licenseUrl: string | null;
  releaseVersion: string | null;
  publishedAt: string | null;
  validFrom: string | null;
  validTo: string | null;
  isActive: boolean;
  isDemo: boolean;
}

export interface EmissionFactor {
  id: string;
  sourceId: string;
  code: string;
  name: string;
  description: string | null;
  activityTypeId: string;
  scope: string;
  category: string;
  subcategory: string | null;
  geographyCode: string;
  facilityType: string | null;
  technologyCode: string | null;
  fuelType: string | null;
  transportationMode: string | null;
  vehicleType: string | null;
  unitCode: string;
  factorValue: string | null;
  co2Factor: string | null;
  ch4Factor: string | null;
  n2oFactor: string | null;
  otherGasesJson: Record<string, unknown> | null;
  biogenicCo2Factor: string | null;
  uncertaintyPercentage: string | null;
  validFrom: string | null;
  validTo: string | null;
  version: number;
  status: string;
  isActive: boolean;
  isDemo: boolean;
  supersedesFactorId: string | null;
  metadataJson: Record<string, unknown> | null;
  usageCount: number;
}

export interface FactorPreference {
  id: string;
  organizationId: string;
  activityTypeId: string;
  emissionFactorId: string;
  priority: number;
  validFrom: string | null;
  validTo: string | null;
  reason: string | null;
  approvedByUserId: string | null;
  isActive: boolean;
}

export interface CarbonInventory {
  id: string;
  organizationId: string;
  reportingPeriodId: string;
  name: string;
  description: string | null;
  status: string;
  calculationMethodologyVersion: string;
  gwpDatasetCode: string;
  version: number;
  partialCalculation: boolean;
  calculatedAt: string | null;
  calculatedByUserId: string | null;
  approvedAt: string | null;
  approvedByUserId: string | null;
  lockedAt: string | null;
  latestRunId: string | null;
  errorSummaryJson: Record<string, unknown> | null;
}

export interface CalculationRun {
  id: string;
  inventoryId: string;
  runNumber: number;
  status: string;
  startedAt: string | null;
  completedAt: string | null;
  triggeredByUserId: string | null;
  activityRecordCount: number;
  calculatedRecordCount: number;
  skippedRecordCount: number;
  failedRecordCount: number;
  totalKgCo2e: string | null;
  totalTCo2e: string | null;
  errorSummaryJson: Record<string, unknown> | null;
  engineVersion: string;
  partialCalculation: boolean;
}

export interface CalculationItem {
  id: string;
  calculationRunId: string;
  inventoryId: string;
  activityRecordId: string;
  emissionFactorId: string | null;
  factorSourceId: string | null;
  activityQuantity: string;
  activityUnitCode: string;
  normalizedQuantity: string | null;
  normalizedUnitCode: string | null;
  factorValue: string | null;
  factorUnitCode: string | null;
  scope: string | null;
  category: string | null;
  subcategory: string | null;
  co2Kg: string | null;
  ch4Kg: string | null;
  n2oKg: string | null;
  biogenicCo2Kg: string | null;
  totalKgCo2e: string | null;
  totalTCo2e: string | null;
  matchingPriority: number | null;
  matchingReason: string | null;
  calculationFormula: string | null;
  calculationSnapshotJson: Record<string, unknown> | null;
  status: string;
  validationErrorsJson: unknown;
}

export interface InventorySummary {
  inventoryId: string;
  status: string;
  totalKgCo2e: string;
  totalTCo2e: string;
  scope1TotalKgCo2e: string;
  scope2TotalKgCo2e: string;
  scope3TotalKgCo2e: string;
  scope1TotalTCo2e?: string;
  scope2TotalTCo2e?: string;
  scope3TotalTCo2e?: string;
  categoryTotals: Array<{ category: string; kgCo2e: string; tCo2e: string }>;
  facilityTotals: Array<{ facility: string; kgCo2e: string; tCo2e: string }>;
  activityTypeTotals: Array<{ activityType: string; kgCo2e: string; tCo2e: string }>;
  greenhouseGasTotals: Record<string, string>;
  itemCounts: { calculated: number; failed: number; skipped: number };
  errorCounts: number;
  partialCalculation?: boolean;
}

export interface ValidationResult {
  valid: unknown[];
  missingFactors: unknown[];
  ambiguousFactors: unknown[];
  incompatibleUnits: unknown[];
  invalidDates: unknown[];
  incompleteRecords: unknown[];
  unapprovedRecords: unknown[];
  duplicateRecords: unknown[];
  blockingErrorCount: number;
  warningCount: number;
  activityRecordCount: number;
}
