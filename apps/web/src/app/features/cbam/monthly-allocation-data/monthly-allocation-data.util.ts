export type MonthlyCoverageUi = 'MISSING' | 'INCOMPLETE' | 'INVALID' | 'READY' | 'UNKNOWN';

export { formatMonthLabel } from '../cbam-shared.util';

export const MASS_UNIT_OPTIONS = ['kg', 't', 'Gg'] as const;

export const MONTHLY_ISSUE_CODE_MESSAGES: Record<string, string> = {
  MONTHLY_PRODUCTION_BASIS_MISSING: 'Enter data for all required months.',
  TOTAL_PRODUCTION_REQUIRED: 'Enter total production.',
  CBAM_QUANTITY_REQUIRED: 'Enter the amount sent to the importer.',
  TOTAL_PRODUCTION_MUST_BE_POSITIVE: 'Total production must be higher than zero.',
  CBAM_QUANTITY_EXCEEDS_TOTAL:
    'The amount sent to the importer cannot be higher than total production.',
  INCOMPATIBLE_PRODUCTION_UNIT: 'Use a supported mass unit.',
  MONTH_OUTSIDE_REPORTING_PERIOD: 'This month is outside the reporting period.',
  COMBUSTION_ACTIVITY_DATE_REQUIRED: 'A fuel record does not have a date.',
  MONTHLY_PRODUCTION_BASIS_NOT_READY: 'Monthly production data is not ready for a fuel record.',
  COMBUSTION_MONTH_NOT_COVERED: 'A fuel record is outside the entered months.',
};

export function mapCoverageLabel(coverage: string | null | undefined): string {
  switch (coverage) {
    case 'MISSING':
      return 'Not entered';
    case 'INCOMPLETE':
      return 'Incomplete';
    case 'INVALID':
      return 'Check values';
    case 'READY':
      return 'Ready';
    default:
      return 'Not ready';
  }
}

export function mapIssueCodeMessage(code: string): string {
  return MONTHLY_ISSUE_CODE_MESSAGES[code] ?? 'More information is needed.';
}

export function mapReconciliationLabel(status: string | null | undefined): string {
  switch (status) {
    case 'EXACT_MATCH':
      return 'Matches product records';
    case 'MISMATCH':
      return 'Does not match product records';
    case 'UNAVAILABLE':
      return 'Cannot compare yet';
    default:
      return 'Cannot compare yet';
  }
}

/** Move decimal point two places right without using Number. */
export function formatCbamShareDisplay(share: string | null | undefined): string {
  if (share == null || share === '') {
    return '—';
  }
  const trimmed = share.trim();
  if (!/^-?\d+(\.\d+)?$/.test(trimmed)) {
    return `Share ${trimmed}`;
  }
  const negative = trimmed.startsWith('-');
  const abs = negative ? trimmed.slice(1) : trimmed;
  const [intPart, fracPart = ''] = abs.split('.');
  const paddedFrac = fracPart.padEnd(2, '0');
  const wholeDigits = `${intPart}${paddedFrac.slice(0, 2)}`.replace(/^0+(?=\d)/, '') || '0';
  const remFrac = paddedFrac.slice(2).replace(/0+$/, '');
  const percent = remFrac.length > 0 ? `${wholeDigits}.${remFrac}` : wholeDigits;
  return `${negative ? '-' : ''}${percent}%`;
}

export function isBlankQuantity(value: string): boolean {
  return value.trim() === '';
}

export function isNegativeQuantitySyntax(value: string): boolean {
  const t = value.trim();
  if (t === '') {
    return false;
  }
  return t.startsWith('-');
}

export function isValidQuantitySyntax(value: string): boolean {
  const t = value.trim();
  if (t === '') {
    return true;
  }
  return /^\d+(\.\d+)?$/.test(t);
}

export function quantityPayloadValue(value: string): string | null {
  const t = value.trim();
  return t === '' ? null : t;
}
