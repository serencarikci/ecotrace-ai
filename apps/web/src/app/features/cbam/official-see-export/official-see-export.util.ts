import { createClientRequestId, extractErrorCode } from '../cbam-shared.util';

export { createClientRequestId, extractErrorCode };

/** Capacity limits matching backend official_see_export.constants (display only). */
export const OFFICIAL_SEE_CAPACITY_LIMITS = {
  installations: 1,
  goods: 10,
  processes: 10,
  precursors: 20,
  fuelActivities: 75,
} as const;

export const OFFICIAL_SEE_XLSX_MIME =
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';

export function isActiveGenerationStatus(status: string | null | undefined): boolean {
  return status === 'PENDING' || status === 'RUNNING';
}

export function canDownloadOfficialSeeRun(run: {
  generationStatus: string;
  formulaParityStatus: string;
}): boolean {
  return run.generationStatus === 'COMPLETED' && run.formulaParityStatus === 'PASSED';
}

export function mapGenerationUiStatus(run: {
  generationStatus: string;
  formulaParityStatus: string;
  validationStatus: string;
} | null): string {
  if (!run) {
    return '';
  }
  if (run.generationStatus === 'PENDING') {
    return 'Preparing';
  }
  if (run.generationStatus === 'RUNNING') {
    return 'Checking workbook';
  }
  if (run.generationStatus === 'FAILED') {
    return 'Failed';
  }
  if (canDownloadOfficialSeeRun(run)) {
    return 'Ready to download';
  }
  if (run.generationStatus === 'COMPLETED') {
    return 'Failed';
  }
  return run.generationStatus;
}

export function mapParityLabel(status: string | null | undefined): string {
  switch (status) {
    case 'PASSED':
      return 'Passed';
    case 'FAILED':
      return 'Failed';
    case 'PENDING':
      return 'Pending';
    case 'ENGINE_UNAVAILABLE':
      return 'Engine unavailable';
    case 'SKIPPED':
      return 'Skipped';
    default:
      return status?.trim() ? status : '—';
  }
}

export function mapValidationLabel(status: string | null | undefined): string {
  switch (status) {
    case 'PASSED':
      return 'Passed';
    case 'FAILED':
      return 'Failed';
    case 'PENDING':
      return 'Pending';
    case 'SKIPPED':
      return 'Skipped';
    default:
      return status?.trim() ? status : '—';
  }
}

export function formatFileSizeBytes(bytes: number | null | undefined): string {
  if (bytes == null || Number.isNaN(bytes)) {
    return '—';
  }
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/** Safe download basename: no path separators or traversal. */
export function sanitizeDownloadFileName(fileName: string | null | undefined): string {
  const raw = (fileName ?? '').trim() || 'official-see.xlsx';
  const base = raw.split(/[/\\]/).pop() ?? 'official-see.xlsx';
  const cleaned = base.replace(/\.\./g, '').trim();
  return cleaned || 'official-see.xlsx';
}

export type OfficialSeeNavTarget =
  | 'productProfiles'
  | 'production'
  | 'directEmissions'
  | 'indirectEmissions'
  | 'processes'
  | 'purchasedInputs'
  | 'productResults'
  | 'allocation';

export interface OfficialSeeBlockingIssue {
  code: string;
  message: string;
  navTarget: OfficialSeeNavTarget | null;
}

const BLOCKING_MESSAGES: Record<
  string,
  { message: string; navTarget: OfficialSeeNavTarget | null }
> = {
  ORG_BINDING_INVALID: {
    message: 'This reporting period is not available.',
    navTarget: null,
  },
  PRODUCT_PROFILES_NOT_READY: {
    message: 'Publish classification-ready product profiles.',
    navTarget: 'productProfiles',
  },
  PRODUCTION_PROFILE_LINK_NOT_READY: {
    message: 'Link production records to product profiles.',
    navTarget: 'production',
  },
  MONTHLY_PRODUCTION_BASIS_NOT_READY: {
    message: 'Complete monthly production data (D/E).',
    navTarget: 'production',
  },
  DEA_MISSING_OR_STALE: {
    message: 'Complete the direct emissions allocation.',
    navTarget: 'allocation',
  },
  DEA_NOT_BALANCED: {
    message: 'Complete the direct emissions allocation.',
    navTarget: 'allocation',
  },
  IEA_MISSING_OR_STALE: {
    message: 'Complete the indirect emissions allocation.',
    navTarget: 'allocation',
  },
  IEA_NOT_BALANCED: {
    message: 'Complete the indirect emissions allocation.',
    navTarget: 'allocation',
  },
  PROCESSES_NOT_READY: {
    message: 'Complete the production processes.',
    navTarget: 'processes',
  },
  PRECURSORS_NOT_READY_OR_UNBALANCED: {
    message: 'Complete the purchased precursors.',
    navTarget: 'purchasedInputs',
  },
  PEE_V2_MISSING_OR_STALE: {
    message: 'Calculate product embedded emissions (V2).',
    navTarget: 'productResults',
  },
  INTERNAL_FLOW_INVALID: {
    message: 'Fix internal product flows in processes.',
    navTarget: 'processes',
  },
  CAPACITY_EXCEEDED_GOODS: {
    message: 'Too many products for the official workbook.',
    navTarget: 'productProfiles',
  },
  CAPACITY_EXCEEDED_PROCESSES: {
    message: 'Too many processes for the official workbook.',
    navTarget: 'processes',
  },
  CAPACITY_EXCEEDED_PRECURSORS: {
    message: 'Too many precursors for the official workbook.',
    navTarget: 'purchasedInputs',
  },
  CAPACITY_EXCEEDED_PROCESS_USES: {
    message: 'Too many process product uses for the official workbook.',
    navTarget: 'processes',
  },
  CAPACITY_EXCEEDED_PRECURSOR_USES: {
    message: 'Too many precursor product uses for the official workbook.',
    navTarget: 'purchasedInputs',
  },
  CAPACITY_EXCEEDED_FUELS: {
    message: 'Too many fuel activities for the official workbook.',
    navTarget: 'directEmissions',
  },
  CAPACITY_EXCEEDED_INSTALLATIONS: {
    message: 'Too many installations for the official workbook.',
    navTarget: null,
  },
  MAPPING_OR_TEMPLATE_INVALID: {
    message: 'The official workbook template is not available.',
    navTarget: null,
  },
  RECALCULATION_ENGINE_UNAVAILABLE: {
    message: 'The recalculation engine is unavailable.',
    navTarget: null,
  },
};

export function mapBlockingIssue(code: string): OfficialSeeBlockingIssue {
  const known = BLOCKING_MESSAGES[code];
  if (known) {
    return { code, message: known.message, navTarget: known.navTarget };
  }
  return {
    code,
    message: `More information is needed. (${code})`,
    navTarget: null,
  };
}

export function mapOfficialSeeError(error: unknown): string {
  if (error && typeof error === 'object' && 'status' in error) {
    const http = error as {
      status: number;
      error?: { error?: { code?: string; details?: Array<{ code?: string }> } };
    };
    if (http.status === 401 || http.status === 403) {
      return 'You do not have permission to do this.';
    }
    if (http.status === 404) {
      return 'The official Excel file was not found.';
    }
    if (http.status === 0) {
      return 'The network request failed. Try again.';
    }
    const details = http.error?.error?.details ?? [];
    const detailCode = details
      .map((d) => d.code)
      .find((c): c is string => typeof c === 'string' && c.length > 0);
    const code = detailCode ?? http.error?.error?.code;
    if (code) {
      return mapOfficialSeeErrorCode(code);
    }
  }
  return 'The official Excel could not be generated. Try again.';
}

export function mapOfficialSeeErrorCode(code: string): string {
  switch (code) {
    case 'IDEMPOTENCY_KEY_REUSED':
      return 'This export request changed. Try again.';
    case 'RECALCULATION_ENGINE_UNAVAILABLE':
      return 'The recalculation engine is unavailable.';
    case 'FORMULA_PARITY_FAILED':
      return 'Workbook values did not match the EcoTrace result.';
    case 'FORMULA_PRESERVATION_FAILED':
      return 'A workbook formula error blocked the export.';
    case 'EXAMPLE_LEAKAGE_DETECTED':
      return 'Example data was found in the workbook.';
    case 'MAPPING_OR_TEMPLATE_INVALID':
      return 'The official workbook template is not available.';
    case 'ARTIFACT_NOT_FOUND':
      return 'The official Excel file was not found.';
    default: {
      if (code.startsWith('CAPACITY_EXCEEDED_')) {
        return 'Workbook capacity was exceeded.';
      }
      if (BLOCKING_MESSAGES[code]) {
        return BLOCKING_MESSAGES[code].message;
      }
      return `The official Excel could not be generated. (${code})`;
    }
  }
}

export function capacityStatusLabel(
  used: number,
  limit: number,
): { label: string; ok: boolean } {
  const ok = used <= limit;
  return {
    ok,
    label: ok ? `${used} / ${limit}` : `${used} / ${limit} (over limit)`,
  };
}
