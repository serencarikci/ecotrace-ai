export {
  createClientRequestId,
  extractErrorCode,
  formatDecimalDisplay,
  formatMonthLabel,
  mapBalanceStatusLabel,
  mapExecutionStatusLabel,
  mapResultLifecycleLabel,
  mapSubsystemStatusLabel,
} from '../cbam-shared.util';

const ISSUE_CODE_MESSAGES: Record<string, string> = {
  DIRECT_EMISSIONS_NOT_READY: 'Complete the direct emissions calculations.',
  DIRECT_EMISSIONS_STALE: 'Update the out-of-date direct emissions.',
  MONTHLY_PRODUCTION_BASIS_NOT_READY: 'Enter monthly production data.',
  MONTHLY_PRODUCTION_BASIS_MISSING: 'Enter monthly production data.',
  TOTAL_PRODUCTION_REQUIRED: 'Enter monthly production data.',
  CBAM_QUANTITY_REQUIRED: 'Check the monthly importer amounts.',
  CBAM_QUANTITY_EXCEEDS_TOTAL: 'Check the monthly importer amounts.',
  TOTAL_PRODUCTION_MUST_BE_POSITIVE: 'Enter monthly production data.',
  PRODUCTION_RECONCILIATION_MISMATCH: 'Check the monthly importer amounts.',
  PRODUCTION_RECONCILIATION_UNAVAILABLE: 'Check the monthly importer amounts.',
  COMBUSTION_ACTIVITY_DATE_REQUIRED: 'Add dates to the fuel records.',
  COMBUSTION_MONTH_NOT_COVERED: 'Add dates to the fuel records.',
  PRODUCTION_DATE_REQUIRED: 'Add dates to the production records.',
  PRODUCTION_PROFILE_LINK_MISSING: 'Link valid product profiles.',
  PRODUCTION_PROFILE_LINK_INVALID: 'Link valid product profiles.',
  INCOMPATIBLE_PRODUCTION_UNIT: 'Check the production units.',
  NO_ELIGIBLE_PRODUCTION: 'Add eligible production records.',
  ZERO_ALLOCATION_DENOMINATOR: 'Add eligible production records.',
};

const STALE_REASON_MESSAGES: Record<string, string> = {
  DIRECT_EMISSIONS_STALE: 'Direct emissions results changed.',
  MONTHLY_PRODUCTION_BASIS_CHANGED: 'Monthly production data changed.',
  PRODUCTION_SET_CHANGED: 'Production records changed.',
  PRODUCTION_MATERIAL_CHANGED: 'Production quantities or units changed.',
  PRODUCTION_PROFILE_LINK_INVALID: 'A product profile link is no longer valid.',
  PRODUCTION_PROFILE_LINK_MISSING: 'A product profile link is missing.',
  METHODOLOGY_OR_WORKBOOK_CHANGED: 'The allocation method or workbook reference changed.',
};

export function mapAllocationIssueCode(code: string): string {
  return ISSUE_CODE_MESSAGES[code] ?? 'More information is needed.';
}

export function mapAllocationStaleReason(code: string): string {
  return STALE_REASON_MESSAGES[code] ?? 'Some source data has changed.';
}

export function mapAllocationError(error: unknown): string {
  if (error && typeof error === 'object' && 'status' in error) {
    const http = error as {
      status: number;
      error?: { error?: { code?: string; details?: Array<{ code?: string }> } };
    };
    if (http.status === 401 || http.status === 403) {
      return 'You do not have permission to do this.';
    }
    if (http.status === 404) {
      return 'The allocation result was not found.';
    }
    const details = http.error?.error?.details ?? [];
    const detailCode = details
      .map((d) => d.code)
      .find((c): c is string => typeof c === 'string' && c.length > 0);
    const code = detailCode ?? http.error?.error?.code;
    switch (code) {
      case 'DIRECT_EMISSIONS_NOT_READY':
        return 'Complete the direct emissions calculations.';
      case 'DIRECT_EMISSIONS_STALE':
        return 'Update the out-of-date direct emissions.';
      case 'MONTHLY_PRODUCTION_BASIS_NOT_READY':
        return 'Enter monthly production data.';
      case 'PRODUCTION_RECONCILIATION_MISMATCH':
        return 'Check the monthly importer amounts.';
      case 'PRODUCTION_RECONCILIATION_UNAVAILABLE':
        return 'Check the monthly importer amounts.';
      case 'PRODUCTION_DATE_REQUIRED':
        return 'Add dates to the production records.';
      case 'PRODUCTION_PROFILE_LINK_MISSING':
      case 'PRODUCTION_PROFILE_LINK_INVALID':
        return 'Link valid product profiles.';
      case 'ZERO_ALLOCATION_DENOMINATOR':
      case 'NO_ELIGIBLE_PRODUCTION':
        return 'Add eligible production records.';
      case 'INCOMPATIBLE_PRODUCTION_UNIT':
        return 'Check the production units.';
      case 'IDEMPOTENCY_KEY_REUSED':
        return 'This allocation request changed. Try again.';
      case 'COMBUSTION_ACTIVITY_DATE_REQUIRED':
        return 'Add dates to the fuel records.';
      default:
        break;
    }
    if (http.status === 0) {
      return 'The network request failed. Try again.';
    }
  }
  return 'The allocation could not be completed. Try again.';
}

/** Read CBAM monthly total from backend totalsByMonth without Number math. */
export function monthCbamTotal(
  totalsByMonth: Record<string, unknown> | null | undefined,
  monthStart: string,
): string | null {
  if (!totalsByMonth) {
    return null;
  }
  const entry = totalsByMonth[monthStart];
  if (entry == null) {
    return null;
  }
  if (typeof entry === 'string' || typeof entry === 'number') {
    return String(entry);
  }
  if (typeof entry === 'object') {
    const obj = entry as Record<string, unknown>;
    for (const key of [
      'cbamFossilCo2Tonnes',
      'cbam_fossil_co2_tonnes',
      'value',
      'total',
    ]) {
      const v = obj[key];
      if (typeof v === 'string' || typeof v === 'number') {
        return String(v);
      }
    }
  }
  return null;
}
