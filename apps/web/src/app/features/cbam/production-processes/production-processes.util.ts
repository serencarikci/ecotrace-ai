import { HttpErrorResponse } from '@angular/common/http';
import { ApiErrorBody } from '../../../core/models/api.models';
import { extractErrorCode, formatDecimalDisplay } from '../cbam-shared.util';

export { extractErrorCode, formatDecimalDisplay };

/** Backend-supported mass units for process quantities. */
export const PROCESS_MASS_UNITS = ['t', 'kg', 'Gg'] as const;

export const HEAT_QUANTITY_UNIT = 'TJ';
export const HEAT_FACTOR_UNIT = 'tCO2/TJ';
export const WASTE_GAS_QUANTITY_UNIT = 'TJ';
export const EXPORTED_ELECTRICITY_QUANTITY_UNIT = 'MWh';
export const EXPORTED_ELECTRICITY_FACTOR_UNIT = 'tCO2/MWh';

export const METHOD_CONVENTIONAL = 'CONVENTIONAL';
export const METHOD_PROCESS_EMISSIONS = 'PROCESS_EMISSIONS';
export const METHOD_MASS_BALANCE = 'MASS_BALANCE';

export const DATA_QUALITY_LIST = 'CONST_DataQuality';
export const DATA_VERIFICATION_LIST = 'CONST_DataVerification';
export const DATA_QUALITY_JUSTIFICATION_LIST = 'CONST_DataQualityJustification';

export function isBlankDecimalInput(raw: string | null | undefined): boolean {
  return raw == null || raw.trim() === '';
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

export function mapProcessReadinessStatusLabel(status: string): string {
  switch (status) {
    case 'EMPTY':
      return 'No data';
    case 'INCOMPLETE':
      return 'Incomplete';
    case 'UNBALANCED':
      return 'Not balanced';
    case 'STALE':
      return 'Needs update';
    case 'READY':
      return 'Ready';
    default:
      return status;
  }
}

export function mapBalanceStatusLabel(status: string | null | undefined): string {
  switch (status) {
    case 'BALANCED':
      return 'Balanced';
    case 'UNBALANCED':
      return 'Not balanced';
    case 'INCOMPLETE':
      return 'Incomplete';
    default:
      return status?.trim() ? status : '—';
  }
}

export function balanceHelpMessage(status: string | null | undefined): string {
  if (status === 'BALANCED') {
    return 'All produced quantity is distributed.';
  }
  if (status === 'UNBALANCED') {
    return 'Distribute the remaining quantity before this process is ready.';
  }
  return '';
}

const BLOCKING_CODE_MESSAGES: Record<string, string> = {
  PROCESS_PRODUCT_REQUIRED: 'Select a product.',
  PROCESS_METHOD_REQUIRED: 'Select a calculation method.',
  PROCESS_METHOD_UNSUPPORTED: 'Select a calculation method.',
  PROCESS_NAME_REQUIRED: 'Enter a process name.',
  PRODUCTION_QUANTITY_MISSING: 'Enter the produced quantity.',
  PRODUCT_DISTRIBUTION_INCOMPLETE: 'Complete the product distribution.',
  PRODUCT_DISTRIBUTION_UNBALANCED: 'Check the distributed quantities.',
  TARGET_PRODUCT_INVALID: 'Select a valid target product.',
  DIRECT_EMISSIONS_ALLOCATION_NOT_READY: 'Complete the direct emissions allocation.',
  INDIRECT_EMISSIONS_ALLOCATION_NOT_READY: 'Complete the indirect emissions allocation.',
  INDIRECT_EMISSIONS_PRODUCT_ALLOCATION_MISSING:
    'Complete the indirect emissions allocation for this product.',
  MEASURABLE_HEAT_DATA_INCOMPLETE: 'Complete the measurable heat data.',
  WASTE_GAS_DATA_INCOMPLETE: 'Complete the waste gas data.',
  EXPORTED_ELECTRICITY_DATA_INCOMPLETE: 'Complete the exported electricity quantity.',
  EXPORTED_ELECTRICITY_FACTOR_REQUIRED: 'Enter the exported electricity emission factor.',
  EXPORTED_ELECTRICITY_PROVENANCE_REQUIRED: 'Enter the exported electricity provenance.',
  EXPORTED_ELECTRICITY_RECONCILIATION_MISMATCH:
    'Process and facility exported electricity totals do not match.',
  EXPORTED_ELECTRICITY_FIELDS_NOT_ALLOWED:
    'Clear exported electricity fields when this process does not export electricity.',
  DATA_QUALITY_ANSWER_REQUIRED: 'More information is needed.',
  DATA_QUALITY_CODE_INVALID: 'More information is needed.',
  PROCESS_ARCHIVED: 'This process is archived.',
  INCOMPATIBLE_MASS_UNIT: 'Choose a supported mass unit (kg, t, or Gg).',
  HEAT_FIELDS_NOT_ALLOWED: 'Clear measurable heat fields when heat is not used.',
  WASTE_GAS_FIELDS_NOT_ALLOWED: 'Clear waste gas fields when waste gas is not used.',
};

export function mapProcessBlockingCode(code: string): string {
  return BLOCKING_CODE_MESSAGES[code] ?? code;
}

export function mapCalculationMethodLabel(method: string): string {
  switch (method) {
    case METHOD_CONVENTIONAL:
      return 'Conventional';
    case METHOD_PROCESS_EMISSIONS:
      return 'Process emissions (Not available yet)';
    case METHOD_MASS_BALANCE:
      return 'Mass balance (Not available yet)';
    default:
      return method;
  }
}

export function isMethodEnabled(method: string): boolean {
  return method === METHOD_CONVENTIONAL;
}

export function mapProcessApiError(err: unknown): string {
  const code = extractErrorCode(err);
  if (code === 'CONFLICT' || (err instanceof HttpErrorResponse && err.status === 409)) {
    return 'This process changed. Reload it and try again.';
  }
  if (code && BLOCKING_CODE_MESSAGES[code]) {
    return BLOCKING_CODE_MESSAGES[code];
  }
  if (err instanceof HttpErrorResponse) {
    const body = err.error as ApiErrorBody | undefined;
    const msg = body?.error?.message;
    if (typeof msg === 'string' && msg.trim()) {
      return msg;
    }
  }
  return 'Something went wrong. Try again.';
}

export function profileOptionLabel(profile: {
  productName: string | null;
  cnDisplayCode: string | null;
  version: number;
  id: string;
}): string {
  const name = profile.productName?.trim() || 'Product';
  const cn = profile.cnDisplayCode?.trim();
  const parts = [name];
  if (cn) {
    parts.push(cn);
  }
  parts.push(`v${profile.version}`);
  return parts.join(' · ');
}
