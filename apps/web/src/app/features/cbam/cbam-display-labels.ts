export function calculationStatusLabel(status: string): string {
  const map: Record<string, string> = {
    CALCULATED: 'Calculated',
    BLOCKED: 'Blocked',
    INVALID_INPUT: 'Invalid Input',
    INCOMPATIBLE_UNIT: 'Unit Does Not Match',
    UNRESOLVED_FACTOR: 'Factor Not Resolved',
    AMBIGUOUS_FACTOR: 'More Than One Factor Match',
    UNSUPPORTED_FORMULA: 'Formula Not Supported',
  };
  return map[status] ?? status;
}

export function resolutionStatusLabel(status: string): string {
  const map: Record<string, string> = {
    RESOLVED_PRIMARY: 'Primary Data Used',
    RESOLVED_DEFAULT: 'Default Reference Used',
    UNRESOLVED: 'Not Resolved',
    AMBIGUOUS: 'More Than One Match',
    INCOMPATIBLE_UNIT: 'Unit Does Not Match',
    OUTSIDE_VALIDITY: 'Value Is Not Valid for This Date',
    BLOCKED: 'Blocked',
  };
  return map[status] ?? status;
}

export function factorSourceLabel(status: string | null): string {
  if (status === 'RESOLVED_PRIMARY') {
    return 'Primary';
  }
  if (status === 'RESOLVED_DEFAULT') {
    return 'Default';
  }
  return status || '—';
}

export function readinessStatusLabel(status: string): string {
  const map: Record<string, string> = {
    READY: 'Ready',
    READY_WITH_WARNINGS: 'Ready with Warnings',
    NOT_READY: 'Not Ready',
  };
  return map[status] ?? status;
}

export function readinessCheckLabel(status: string): string {
  const map: Record<string, string> = {
    OK: 'OK',
    WARNING: 'Warning',
    MISSING: 'Missing',
  };
  return map[status] ?? status;
}
