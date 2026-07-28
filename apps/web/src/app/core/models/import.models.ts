export interface ImportJob {
  id: string;
  organizationId: string;
  fileName: string;
  storedFileName: string;
  status: string;
  totalRows: number;
  validRows: number;
  invalidRows: number;
  importedRows: number;
  duplicateRows: number;
  startedAt: string | null;
  completedAt: string | null;
  createdByUserId: string | null;
  executedAt: string | null;
  createdAt?: string;
  updatedAt?: string;
}

export interface ImportJobRow {
  id: string;
  importJobId: string;
  rowNumber: number;
  rawDataJson: Record<string, unknown>;
  normalizedDataJson: Record<string, unknown> | null;
  validationStatus: string;
  validationErrorsJson: Array<{ field?: string; message: string }> | string[] | null;
  activityRecordId: string | null;
  createdAt: string;
}

export interface ImportJobListParams {
  page?: number;
  pageSize?: number;
  status?: string;
}

export interface ImportRowListParams {
  page?: number;
  pageSize?: number;
  validationStatus?: string;
}
