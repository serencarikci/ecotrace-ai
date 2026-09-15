import { HttpErrorResponse } from '@angular/common/http';
import { ApiErrorBody } from '../../../core/models/api.models';
import { CbamPrecursorDefaultValue } from '../cbam-api.service';
import { extractErrorCode, formatDecimalDisplay } from '../cbam-shared.util';

export { extractErrorCode, formatDecimalDisplay };

/** Backend-supported mass units for precursor quantities. */
export const PRECURSOR_MASS_UNITS = ['t', 'kg', 'Gg'] as const;

/** Whole-record modes offered in the UI. HYBRID is not offered. */
export const MODE_SUPPLIER_DATA = 'SUPPLIER_DATA';
export const MODE_EU_DEFAULT = 'EU_DEFAULT';
export const PRECURSOR_DATA_SOURCE_MODES = [MODE_SUPPLIER_DATA, MODE_EU_DEFAULT] as const;

export const SPECIFIC_DIRECT_UNIT = 'tCO2e/t';
export const SPECIFIC_INDIRECT_UNIT = 'tCO2e/t';
export const ELECTRICITY_INTENSITY_UNIT = 'MWh/t';
export const ELECTRICITY_EF_UNIT = 'tCO2e/MWh';
export const PRECURSOR_RESULT_UNIT = 'tCO2e';

export const PARAMETER_SOURCE_LIST = 'CONST_MeasDefaultUnknown';
export const ELECTRICITY_SOURCE_LIST = 'CONST_ElecSource';
export const DEFAULT_JUSTIFICATION_LIST = 'CONST_DefaultJustification';

export const PRECURSOR_STATUS_DRAFT = 'draft';
export const PRECURSOR_STATUS_ARCHIVED = 'archived';

export const UNBALANCED_HELP_MESSAGE =
  'Distribute the remaining quantity before this precursor is ready.';

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

export function mapPrecursorModeLabel(mode: string | null | undefined): string {
  switch (mode) {
    case MODE_SUPPLIER_DATA:
      return 'Supplier data';
    case MODE_EU_DEFAULT:
      return 'EU default';
    default:
      return mode?.trim() ? mode : '—';
  }
}

export function mapPrecursorReadinessStatusLabel(status: string | null | undefined): string {
  switch (status) {
    case 'EMPTY':
      return 'No data';
    case 'INCOMPLETE':
      return 'Incomplete';
    case 'UNBALANCED':
      return 'Not balanced';
    case 'UNRESOLVED':
      return 'Default not found';
    case 'AMBIGUOUS':
      return 'More details needed';
    case 'READY':
      return 'Ready';
    default:
      return status?.trim() ? status : '—';
  }
}

export function mapPrecursorBalanceStatusLabel(status: string | null | undefined): string {
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

export function precursorBalanceHelpMessage(status: string | null | undefined): string {
  if (status === 'BALANCED') {
    return 'All purchased quantity is distributed.';
  }
  if (status === 'UNBALANCED' || status === 'INCOMPLETE') {
    return UNBALANCED_HELP_MESSAGE;
  }
  return '';
}

export function mapResolutionStatusLabel(status: string | null | undefined): string {
  switch (status) {
    case 'RESOLVED':
      return 'Default value found';
    case 'UNRESOLVED':
      return 'No default value found';
    case 'AMBIGUOUS':
      return 'More than one default value matches';
    case 'NOT_APPLICABLE':
      return 'Not used';
    default:
      return status?.trim() ? status : '—';
  }
}

export function resolutionHelpMessage(status: string | null | undefined): string {
  if (status === 'UNRESOLVED') {
    return 'No EU default value matches this country, CN code and production route. Check the identity fields or search the catalog again.';
  }
  if (status === 'AMBIGUOUS') {
    return 'More than one EU default value matches. Add the goods description or pick one row from the search results.';
  }
  return '';
}

const BLOCKING_CODE_MESSAGES: Record<string, string> = {
  PRECURSOR_NAME_REQUIRED: 'Enter a precursor name.',
  PRECURSOR_CN_CODE_REQUIRED: 'Select a CN code.',
  PRECURSOR_COUNTRY_REQUIRED: 'Select the country of origin.',
  PRECURSOR_ROUTE_REQUIRED: 'Select a production route.',
  PRECURSOR_QUANTITY_REQUIRED: 'Enter the precursor quantity.',
  PRECURSOR_DISTRIBUTION_INCOMPLETE: 'Complete the product distribution.',
  PRECURSOR_DISTRIBUTION_UNBALANCED: 'Check the distributed quantities.',
  PRECURSOR_TARGET_PRODUCT_INVALID: 'Select a valid target product.',
  PRECURSOR_ARCHIVED: 'This precursor is archived.',
  PRECURSOR_MODE_REQUIRED: 'Select a data source.',
  PRECURSOR_MODE_UNSUPPORTED: 'Select a supported data source.',
  SUPPLIER_EMISSIONS_DATA_REQUIRED: 'Enter the supplier emission data.',
  SUPPLIER_PROVENANCE_REQUIRED: 'Add the supplier data source.',
  DEFAULT_VALUE_UNRESOLVED: 'No default value was found.',
  DEFAULT_VALUE_AMBIGUOUS: 'More than one default value matches.',
  DEFAULT_VALUE_NOT_NUMERIC: 'The matched EU default value has no numeric value.',
  MIXED_PRECURSOR_SOURCE_NOT_SUPPORTED:
    'Supplier and default values cannot be mixed.',
  INCOMPATIBLE_PRECURSOR_UNIT: 'Use a supported quantity unit.',
  PURCHASED_INPUT_INVALID: 'Select a purchased input from this reporting period.',
  SUPPLIER_INVALID: 'Select a valid supplier.',
  JUSTIFICATION_CODE_INVALID: 'More information is needed.',
  ELECTRICITY_SOURCE_CODE_INVALID: 'More information is needed.',
  PARAMETER_SOURCE_CODE_INVALID: 'More information is needed.',
  PRODUCT_USE_DUPLICATE: 'This product already has a distribution row.',
};

/** Unknown server codes are shown as-is so nothing is silently hidden. */
export function mapPrecursorBlockingCode(code: string): string {
  return BLOCKING_CODE_MESSAGES[code] ?? code;
}

export function mapPrecursorApiError(err: unknown): string {
  const code = extractErrorCode(err);
  if (code === 'CONFLICT' || (err instanceof HttpErrorResponse && err.status === 409)) {
    return 'This precursor changed. Reload it and try again.';
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

export function isConflictMessage(message: string): boolean {
  return message.includes('This precursor changed');
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

export function defaultValueIdentityLabel(value: CbamPrecursorDefaultValue): string {
  const parts = [value.countryName, value.cnDisplayCode ?? value.cnNormalizedCode];
  if (value.productionRoute?.trim()) {
    parts.push(value.productionRoute.trim());
  }
  if (value.goodsDescription?.trim()) {
    parts.push(value.goodsDescription.trim());
  }
  return parts.join(' · ');
}

export function defaultValueStatusLabel(status: string | null | undefined): string {
  switch (status) {
    case 'NUMERIC':
      return 'Numeric';
    case 'DASH':
      return 'Not published (—)';
    case 'NA':
      return 'Not applicable';
    case 'SEE_BELOW':
      return 'See workbook note';
    case 'BLANK':
      return 'Blank';
    case 'TEXT':
      return 'Text';
    default:
      return status?.trim() ? status : '—';
  }
}
