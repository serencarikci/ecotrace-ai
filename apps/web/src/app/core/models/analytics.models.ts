export interface AnalyticsMetadata {
  organizationId: string;
  inventoryId: string;
  inventoryName: string;
  inventoryStatus: string;
  reportingPeriodId: string;
  reportingPeriodCode: string | null;
  calculationRunId: string | null;
  calculatedAt: string | null;
  methodologyVersion: string | null;
  gwpDataset: string | null;
  provisional: boolean;
  engineVersion: string | null;
}

export interface RankedTotal {
  name: string;
  totalKgCo2e: string;
  totalTCo2e?: string;
  sharePercentage?: string;
}

export interface AnalyticsDashboard {
  metadata: AnalyticsMetadata;
  summary: {
    totalEmissionsKgCo2e: string;
    totalEmissionsTCo2e: string;
    scope1KgCo2e: string;
    scope2KgCo2e: string;
    scope3KgCo2e: string;
    approvedActivityRecordCount: number;
    calculationErrorCount: number;
    largestEmissionSource: RankedTotal | null;
    highestEmittingFacility: RankedTotal | null;
  };
  scopeDistribution: Record<string, string>;
  categoryDistribution: RankedTotal[];
  facilityTotals: RankedTotal[];
  activityTypeTotals: RankedTotal[];
  greenhouseGasTotals: Record<string, string>;
  comparison: Record<string, unknown> | null;
  empty: boolean;
}

export interface TrendPoint {
  period: string;
  totalKgCo2e: string;
  scope1KgCo2e: string;
  scope2KgCo2e: string;
  scope3KgCo2e: string;
}

export interface Recommendation {
  code: string;
  title: string;
  description: string;
  recommendationType: string;
  priority: string;
  evidence: unknown;
}

export interface Baseline {
  id: string;
  organizationId: string;
  code: string;
  name: string;
  description: string | null;
  baselineType: string;
  baselineValue: string | null;
  baselineUnit: string | null;
  status: string;
  isPrimary: boolean;
}

export interface SustainabilityTarget {
  id: string;
  organizationId: string;
  code: string;
  name: string;
  description: string | null;
  targetType: string;
  baselineValue: string;
  targetValue: string;
  targetUnit: string;
  targetYear: number;
  targetDirection: string;
  status: string;
}

export interface ReductionInitiative {
  id: string;
  organizationId: string;
  code: string;
  name: string;
  initiativeType: string;
  expectedReductionKgCo2e: string;
  status: string;
}

export interface Scenario {
  id: string;
  organizationId: string;
  code: string;
  name: string;
  scenarioType: string;
  baselineInventoryId: string;
  status: string;
}

export interface ScenarioRun {
  id: string;
  scenarioId: string;
  runNumber: number;
  status: string;
  baselineTotalKgCo2e: string | null;
  scenarioTotalKgCo2e: string | null;
  reductionKgCo2e: string | null;
  reductionPercentage: string | null;
}
