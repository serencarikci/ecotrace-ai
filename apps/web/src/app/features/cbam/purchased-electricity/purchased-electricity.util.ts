import { HttpErrorResponse } from '@angular/common/http';
import { CbamActivityRecord } from '../cbam-api.service';
import {
  createClientRequestId,
  extractErrorCode,
  formatDecimalDisplay,
  mapResultLifecycleLabel,
} from '../cbam-shared.util';

export {
  createClientRequestId,
  extractErrorCode,
  formatDecimalDisplay,
  mapResultLifecycleLabel,
};

export const ELECTRICITY_ACTIVITY_TYPE = 'ELECTRICITY';
export const ELECTRICITY_QUANTITY_UNITS = new Set(['kWh', 'MWh']);
export const ELECTRICITY_FACTOR_UNITS = [
  'tCO2e/MWh',
  'tCO2/MWh',
  'kgCO2e/kWh',
  'kgCO2e/MWh',
  'tCO2e/kWh',
  'kgCO2/kWh',
  'kgCO2/MWh',
  'tCO2/kWh',
] as const;

export function isEligibleElectricityActivity(activity: CbamActivityRecord): boolean {
  if (activity.status !== 'active') {
    return false;
  }
  if (activity.activityType !== ELECTRICITY_ACTIVITY_TYPE) {
    return false;
  }
  if (!ELECTRICITY_QUANTITY_UNITS.has(activity.unit)) {
    return false;
  }
  const qty = activity.quantity?.trim() ?? '';
  if (qty === '' || qty.startsWith('-')) {
    return false;
  }
  return true;
}

export function isBlankDecimalInput(raw: string | null | undefined): boolean {
  return raw == null || raw.trim() === '';
}

/** Zero is a valid explicit value; blank is not. Does not use Number(). */
export function isZeroDecimalString(raw: string): boolean {
  const t = raw.trim();
  if (t === '' || t.startsWith('-')) {
    return false;
  }
  return /^0+(\.0+)?$/.test(t);
}

export function isNegativeDecimalString(raw: string): boolean {
  const t = raw.trim();
  return t.startsWith('-') && /^-0*([1-9]\d*|0*\.\d*[1-9]\d*)/.test(t);
}

export function optionalTextOrNull(raw: string | null | undefined): string | null {
  if (raw == null) {
    return null;
  }
  const trimmed = raw.trim();
  return trimmed === '' ? null : trimmed;
}

export function optionalDecimalOrNull(raw: string | null | undefined): string | null {
  return optionalTextOrNull(raw);
}

const ISSUE_CODE_MESSAGES: Record<string, string> = {
  ELECTRICITY_ACTIVITIES_REQUIRED: 'Add an electricity record.',
  ELECTRICITY_RESULTS_INCOMPLETE: 'Select an emission factor.',
  ELECTRICITY_RESULTS_STALE: 'Update the out-of-date calculation.',
  ACTIVITY_DATE_REQUIRED: 'Add a date to the electricity record.',
  UNRESOLVED_PLATFORM_DEFAULT: 'The default factor is not available.',
  AMBIGUOUS_PLATFORM_DEFAULT: 'The default factor is not available.',
  MANUAL_FACTOR_REQUIRED: 'Enter the factor source.',
  MANUAL_FACTOR_SOURCE_REQUIRED: 'Enter the factor source.',
  MISSING_FACTOR: 'Select an emission factor.',
  MISSING_FACTOR_UNIT: 'Check the electricity unit.',
  INCOMPATIBLE_FACTOR_UNIT: 'Check the electricity unit.',
  INCOMPATIBLE_ELECTRICITY_UNIT: 'Check the electricity unit.',
  INCOMPATIBLE_ACTIVITY_TYPE: 'Check the electricity unit.',
  INCOMPATIBLE_ACTIVITY_UNIT: 'Check the electricity unit.',
  NEGATIVE_ELECTRICITY_QUANTITY: 'Check the electricity unit.',
  NEGATIVE_FACTOR_VALUE: 'Select an emission factor.',
};

const INFO_CODE_MESSAGES: Record<string, string> = {
  TURKEY_ELECTRICITY_DEFAULT_FACTOR_PROVENANCE_MISSING:
    'A verified Turkey default factor is not available yet.',
};

const STALE_REASON_MESSAGES: Record<string, string> = {
  ACTIVITY_INPUT_CHANGED: 'The electricity quantity or unit changed.',
  ACTIVITY_DATE_CHANGED: 'The electricity record date changed.',
  ACTIVITY_NOT_ACTIVE: 'The electricity record is no longer active.',
  ACTIVITY_TYPE_CHANGED: 'The activity type changed.',
};

export function mapElectricityIssueCode(code: string): string {
  return ISSUE_CODE_MESSAGES[code] ?? 'More information is needed.';
}

export function mapElectricityInfoCode(code: string): string {
  return INFO_CODE_MESSAGES[code] ?? 'More information is needed.';
}

export function mapElectricityStaleReason(code: string): string {
  return STALE_REASON_MESSAGES[code] ?? 'Some source data has changed.';
}

export function mapFactorSourceLabel(mode: string | null | undefined): string {
  switch (mode) {
    case 'PLATFORM_DEFAULT':
      return 'Platform default';
    case 'MANUAL':
      return 'Manual factor';
    default:
      return mode?.trim() ? mode : '—';
  }
}

export function mapReadinessStatusLabel(status: string | null | undefined): string {
  switch (status) {
    case 'EMPTY':
      return 'No electricity data';
    case 'INCOMPLETE':
      return 'Incomplete';
    case 'STALE':
      return 'Out of date';
    case 'READY':
      return 'Ready';
    default:
      return status?.trim() ? status : '—';
  }
}

export function mapPurchasedElectricityError(error: unknown): string {
  if (error instanceof HttpErrorResponse) {
    if (error.status === 401 || error.status === 403) {
      return 'You do not have permission to do this.';
    }
    if (error.status === 404) {
      return 'The requested electricity record or result was not found.';
    }
    if (error.status === 0) {
      return 'The network request failed. Try again.';
    }
    const code = extractErrorCode(error);
    switch (code) {
      case 'UNRESOLVED_PLATFORM_DEFAULT':
        return 'A verified default factor is not available. Enter a manual factor and its source.';
      case 'AMBIGUOUS_PLATFORM_DEFAULT':
        return 'More than one default factor was found. Enter a manual factor instead.';
      case 'MANUAL_FACTOR_REQUIRED':
      case 'MANUAL_FACTOR_SOURCE_REQUIRED':
      case 'MISSING_FACTOR':
        return 'Enter a manual factor and its source.';
      case 'MISSING_FACTOR_UNIT':
      case 'INCOMPATIBLE_FACTOR_UNIT':
        return 'The factor unit is not valid for electricity.';
      case 'INCOMPATIBLE_ELECTRICITY_UNIT':
      case 'INCOMPATIBLE_ACTIVITY_TYPE':
        return 'This activity is not a valid electricity consumption record.';
      case 'NEGATIVE_ELECTRICITY_QUANTITY':
      case 'NEGATIVE_FACTOR_VALUE':
        return 'Enter a value that is zero or greater.';
      case 'ACTIVITY_BINDING_MISMATCH':
        return 'This electricity record does not belong to this period.';
      case 'IDEMPOTENCY_KEY_REUSED':
        return 'This calculation request changed. Start a new calculation.';
      case 'ELECTRICITY_RESULTS_STALE':
      case 'ACTIVITY_INPUT_CHANGED':
        return 'Update the out-of-date calculation.';
      default:
        return 'The calculation could not be completed. Try again.';
    }
  }
  return 'The calculation could not be completed. Try again.';
}

export type SelectedActivityCalcState = 'missing' | 'valid' | 'stale' | 'unknown';

export function mapSelectedCalcState(
  currentForActivity: { isStale: boolean } | null | undefined,
): SelectedActivityCalcState {
  if (!currentForActivity) {
    return 'missing';
  }
  return currentForActivity.isStale ? 'stale' : 'valid';
}
