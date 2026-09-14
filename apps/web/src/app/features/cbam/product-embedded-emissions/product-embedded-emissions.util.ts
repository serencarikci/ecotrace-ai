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

const ISSUE_CODE_MESSAGES: Record<string, string> = {
  PRODUCT_EMBEDDED_EMISSIONS_NO_ELIGIBLE_PRODUCTS: 'Complete the product profile.',
  PRODUCT_PROFILE_NOT_LINKABLE: 'Complete the product profile.',
  PRODUCT_DISTRIBUTION_UNBALANCED: 'Balance the product distribution.',
  PROCESS_MISSING_FOR_PRODUCT: 'Complete the process data.',
  PROCESS_AMBIGUOUS_FOR_PRODUCT: 'Complete the process data.',
  PROCESS_NOT_READY: 'Complete the process data.',
  PROCESS_METHOD_UNSUPPORTED: 'Complete the process data.',
  DIRECT_EMISSIONS_ALLOCATION_NOT_READY: 'Complete the direct emissions allocation.',
  DIRECT_EMISSIONS_ALLOCATION_STALE: 'Complete the direct emissions allocation.',
  DEA_PRODUCT_ROW_MISSING: 'Complete the direct emissions allocation.',
  INDIRECT_EMISSIONS_ALLOCATION_NOT_READY: 'Complete the indirect emissions allocation.',
  INDIRECT_EMISSIONS_ALLOCATION_STALE: 'Complete the indirect emissions allocation.',
  IEA_PRODUCT_ROW_MISSING: 'Complete the indirect emissions allocation.',
  PRECURSOR_NOT_READY: 'Complete the precursor data.',
  PRECURSOR_SPECIFIC_VALUES_MISSING: 'Complete the precursor data.',
  PRECURSOR_USE_UNIT_INVALID: 'Balance the precursor distribution.',
  PRECURSOR_DISTRIBUTION_UNBALANCED: 'Balance the precursor distribution.',
  PRODUCT_DENOMINATOR_ZERO: 'Check the product output quantity.',
  PRODUCT_DENOMINATOR_MISSING: 'Check the product output quantity.',
  PRODUCT_DENOMINATOR_MISMATCH: 'Check the product output quantity.',
  PRODUCTION_RECORDS_CHANGED: 'Complete the production data.',
  PRODUCTION_PROFILE_LINK_MISSING: 'Complete the production data.',
  PRODUCTION_PROFILE_LINK_INVALID: 'Complete the production data.',
  INTERNAL_PRODUCT_FLOW_SINGULAR: 'Check the internal product flows.',
  INTERNAL_PRODUCT_FLOW_INVALID: 'Check the internal product flows.',
  INTERNAL_PRODUCT_FLOW_PROFILE_MISSING: 'Check the internal product flows.',
  INTERNAL_PRODUCT_FLOW_SELF_REFERENCE: 'Check the internal product flows.',
  INTERNAL_PRODUCT_FLOW_DENOMINATOR_ZERO: 'Check the product output quantity.',
  INTERNAL_PRODUCT_FLOW_UNBALANCED: 'Check the internal product flows.',
  PROCESS_EXPORTED_ELECTRICITY_NOT_READY: 'Add the exported electricity data.',
  PROCESS_LEVEL_EXPORTED_ELECTRICITY_INPUTS_NOT_MODELED: 'Add the exported electricity data.',
};

const STALE_REASON_MESSAGES: Record<string, string> = {
  METHODOLOGY_OR_WORKBOOK_CHANGED: 'Some source data has changed.',
  DEA_CURRENT_RESULT_CHANGED: 'Direct emissions allocation changed.',
  DIRECT_EMISSIONS_ALLOCATION_STALE: 'Direct emissions allocation is out of date.',
  DEA_PRODUCT_VALUE_CHANGED: 'Direct emissions allocation changed.',
  IEA_CURRENT_RESULT_CHANGED: 'Indirect emissions allocation changed.',
  INDIRECT_EMISSIONS_ALLOCATION_STALE: 'Indirect emissions allocation is out of date.',
  IEA_PRODUCT_VALUE_CHANGED: 'Indirect emissions allocation changed.',
  PRODUCT_SET_CHANGED: 'Product profiles changed.',
  PROCESS_CHANGED: 'Process data changed.',
  PROCESS_PRODUCED_QUANTITY_CHANGED: 'Process output quantity changed.',
  PROCESS_HEAT_OR_WASTE_GAS_CHANGED: 'Process heat or waste-gas data changed.',
  PRECURSOR_SET_CHANGED: 'Purchased precursor data changed.',
  PRECURSOR_CHANGED: 'Purchased precursor data changed.',
  PRECURSOR_PRODUCT_USE_CHANGED: 'Precursor product uses changed.',
  PRECURSOR_SPECIFIC_VALUES_CHANGED: 'Precursor specific values changed.',
  PRECURSOR_DEFAULT_SNAPSHOT_CHANGED: 'Precursor default values changed.',
  PRODUCTION_RECORDS_CHANGED: 'Production data changed.',
  PRODUCT_DENOMINATOR_CHANGED: 'Product output quantity changed.',
  PRODUCT_EMBEDDED_EMISSIONS_NOT_READY: 'Product results are no longer ready.',
  INTERNAL_PRODUCT_FLOW_SET_CHANGED: 'The internal product flow cannot be calculated.',
  INTERNAL_PRODUCT_FLOW_CHANGED: 'Check the quantities used in other products.',
  PROCESS_EXPORTED_ELECTRICITY_CHANGED: 'Exported electricity data changed.',
  EXPORTED_ELECTRICITY_RECONCILIATION_CHANGED: 'Exported electricity data changed.',
};

/** Internal-flow issue/stale codes with user-safe wording (no matrix internals). */
const INTERNAL_FLOW_MESSAGES: Record<string, string> = {
  INTERNAL_PRODUCT_FLOW_SINGULAR: 'The internal product flow cannot be calculated.',
  INTERNAL_PRODUCT_FLOW_INVALID: 'The internal product flow cannot be calculated.',
  INTERNAL_PRODUCT_FLOW_PROFILE_MISSING: 'The internal product flow cannot be calculated.',
  INTERNAL_PRODUCT_FLOW_SELF_REFERENCE: 'The internal product flow cannot be calculated.',
  INTERNAL_PRODUCT_FLOW_DENOMINATOR_ZERO: 'A product output quantity is missing.',
  INTERNAL_PRODUCT_FLOW_UNBALANCED: 'Check the quantities used in other products.',
  INTERNAL_PRODUCT_FLOW_SET_CHANGED: 'The internal product flow cannot be calculated.',
  INTERNAL_PRODUCT_FLOW_CHANGED: 'Check the quantities used in other products.',
};

export function mapPeeIssueCode(code: string): string {
  if (INTERNAL_FLOW_MESSAGES[code]) {
    return INTERNAL_FLOW_MESSAGES[code];
  }
  const known = ISSUE_CODE_MESSAGES[code];
  if (known) {
    return known;
  }
  return `More information is needed. (${code})`;
}

export function mapPeeStaleReason(code: string): string {
  if (INTERNAL_FLOW_MESSAGES[code]) {
    return INTERNAL_FLOW_MESSAGES[code];
  }
  return STALE_REASON_MESSAGES[code] ?? 'Some source data has changed.';
}

export function mapExecutionStatusLabel(status: string | null | undefined): string {
  switch (status) {
    case 'COMPLETED':
      return 'Completed';
    case 'FAILED':
      return 'Failed';
    case 'READY':
      return 'Ready';
    case 'NOT_READY':
      return 'Not ready';
    default:
      return status?.trim() ? status : '—';
  }
}

export function mapMethodologyLabel(code: string | null | undefined): string {
  if (!code) {
    return '—';
  }
  if (code.includes('_V2') || code.endsWith('V2')) {
    return 'V2';
  }
  if (code.includes('_V1') || code.endsWith('V1')) {
    return 'V1';
  }
  return code;
}

export function methodologyNote(code: string | null | undefined): string | null {
  const label = mapMethodologyLabel(code);
  if (label === 'V2') {
    return 'V2 includes internal product flows.';
  }
  if (label === 'V1') {
    return 'V1 covers purchased precursors only.';
  }
  return null;
}

export type SubsystemStatus = 'Ready' | 'Not ready' | 'Out of date';

export function deriveDirectAllocationStatus(options: {
  resultId: string | null;
  stale: boolean;
  blockingIssueCodes: string[];
}): SubsystemStatus {
  const codes = options.blockingIssueCodes;
  if (
    codes.includes('DIRECT_EMISSIONS_ALLOCATION_NOT_READY') ||
    codes.includes('DEA_PRODUCT_ROW_MISSING')
  ) {
    return 'Not ready';
  }
  if (options.stale || codes.includes('DIRECT_EMISSIONS_ALLOCATION_STALE')) {
    return 'Out of date';
  }
  return options.resultId ? 'Ready' : 'Not ready';
}

export function deriveIndirectAllocationStatus(options: {
  resultId: string | null;
  stale: boolean;
  blockingIssueCodes: string[];
}): SubsystemStatus {
  const codes = options.blockingIssueCodes;
  if (
    codes.includes('INDIRECT_EMISSIONS_ALLOCATION_NOT_READY') ||
    codes.includes('IEA_PRODUCT_ROW_MISSING')
  ) {
    return 'Not ready';
  }
  if (options.stale || codes.includes('INDIRECT_EMISSIONS_ALLOCATION_STALE')) {
    return 'Out of date';
  }
  return options.resultId ? 'Ready' : 'Not ready';
}

export function deriveProcessStatus(blockingIssueCodes: string[]): SubsystemStatus {
  const processCodes = [
    'PROCESS_MISSING_FOR_PRODUCT',
    'PROCESS_AMBIGUOUS_FOR_PRODUCT',
    'PROCESS_NOT_READY',
    'PROCESS_METHOD_UNSUPPORTED',
    'PROCESS_EXPORTED_ELECTRICITY_NOT_READY',
  ];
  return processCodes.some((c) => blockingIssueCodes.includes(c)) ? 'Not ready' : 'Ready';
}

export function derivePrecursorStatus(blockingIssueCodes: string[]): SubsystemStatus {
  const precursorCodes = [
    'PRECURSOR_NOT_READY',
    'PRECURSOR_SPECIFIC_VALUES_MISSING',
    'PRECURSOR_USE_UNIT_INVALID',
    'PRECURSOR_DISTRIBUTION_UNBALANCED',
  ];
  return precursorCodes.some((c) => blockingIssueCodes.includes(c)) ? 'Not ready' : 'Ready';
}

export function deriveInternalFlowStatus(blockingIssueCodes: string[]): SubsystemStatus {
  const internalCodes = [
    'INTERNAL_PRODUCT_FLOW_SINGULAR',
    'INTERNAL_PRODUCT_FLOW_INVALID',
    'INTERNAL_PRODUCT_FLOW_DENOMINATOR_ZERO',
    'INTERNAL_PRODUCT_FLOW_PROFILE_MISSING',
    'INTERNAL_PRODUCT_FLOW_UNBALANCED',
    'INTERNAL_PRODUCT_FLOW_SELF_REFERENCE',
  ];
  return internalCodes.some((c) => blockingIssueCodes.includes(c)) ? 'Not ready' : 'Ready';
}

export function mapDataSourceLabel(mode: string | null | undefined): string {
  switch (mode) {
    case 'SUPPLIER_DATA':
      return 'Supplier data';
    case 'EU_DEFAULT':
      return 'EU default';
    default:
      return mode?.trim() ? mode : '—';
  }
}

export function mapPeeError(error: unknown): string {
  if (error && typeof error === 'object' && 'status' in error) {
    const http = error as {
      status: number;
      error?: { error?: { code?: string; details?: Array<{ code?: string }> } };
    };
    if (http.status === 401 || http.status === 403) {
      return 'You do not have permission to do this.';
    }
    if (http.status === 404) {
      return 'The product results were not found.';
    }
    const details = http.error?.error?.details ?? [];
    const detailCode = details
      .map((d) => d.code)
      .find((c): c is string => typeof c === 'string' && c.length > 0);
    const code = detailCode ?? http.error?.error?.code;
    if (code === 'IDEMPOTENCY_KEY_REUSED') {
      return 'This product results request changed. Try again.';
    }
    if (code) {
      return mapPeeIssueCode(code);
    }
    if (http.status === 0) {
      return 'The network request failed. Try again.';
    }
  }
  return 'The product results could not be calculated. Try again.';
}
