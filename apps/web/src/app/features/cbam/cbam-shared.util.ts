import { HttpErrorResponse } from '@angular/common/http';
import { ApiErrorBody } from '../../core/models/api.models';

/** Display backend Decimal strings without JavaScript Number conversion. */
export function formatDecimalDisplay(value: string | null | undefined): string {
  if (value == null) {
    return '—';
  }
  const trimmed = value.trim();
  return trimmed === '' ? '—' : trimmed;
}

export function createClientRequestId(): string {
  return crypto.randomUUID();
}

export function extractErrorCode(error: unknown): string | null {
  if (!error || typeof error !== 'object') {
    return null;
  }
  let payload: ApiErrorBody | Record<string, unknown> | null = null;
  if (error instanceof HttpErrorResponse) {
    payload = error.error as ApiErrorBody | null;
  } else if ('error' in error) {
    payload = (error as { error?: ApiErrorBody | Record<string, unknown> | null }).error ?? null;
  }
  if (!payload || typeof payload !== 'object') {
    return null;
  }
  const nested = (payload as ApiErrorBody).error;
  const details = nested?.details ?? [];
  const detailCode = details
    .map((d) => (d as { code?: string }).code)
    .find((c): c is string => typeof c === 'string' && c.length > 0);
  return detailCode ?? nested?.code ?? null;
}

const MONTH_NAMES = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
] as const;

export function formatMonthLabel(monthStart: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(monthStart.trim());
  if (!m) {
    return monthStart;
  }
  const year = m[1];
  const monthIndex = Number(m[2]) - 1;
  if (monthIndex < 0 || monthIndex > 11) {
    return monthStart;
  }
  return `${MONTH_NAMES[monthIndex]} ${year}`;
}

export function mapResultLifecycleLabel(isCurrent: boolean, isStale: boolean): string {
  if (isCurrent && isStale) {
    return 'Out of date';
  }
  if (isCurrent) {
    return 'Current';
  }
  return 'History';
}

export function mapBalanceStatusLabel(status: string | null | undefined): string {
  switch (status) {
    case 'BALANCED':
      return 'Balanced';
    case 'UNBALANCED':
      return 'Not balanced';
    default:
      return status?.trim() ? status : '—';
  }
}

export function mapExecutionStatusLabel(status: string | null | undefined): string {
  switch (status) {
    case 'COMPLETED':
      return 'Completed';
    case 'FAILED':
      return 'Failed';
    default:
      return status?.trim() ? status : '—';
  }
}

export function mapSubsystemStatusLabel(status: string | null | undefined): string {
  switch (status) {
    case 'READY':
      return 'Ready';
    case 'NOT_READY':
      return 'Not ready';
    case 'EMPTY':
      return 'Empty';
    case 'INCOMPLETE':
      return 'Incomplete';
    case 'STALE':
      return 'Out of date';
    case 'EXACT_MATCH':
      return 'Matched';
    case 'MISMATCH':
      return 'Mismatch';
    case 'UNAVAILABLE':
      return 'Unavailable';
    default:
      return status?.trim() ? status : '—';
  }
}
