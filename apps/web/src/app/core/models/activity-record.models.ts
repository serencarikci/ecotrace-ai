export type ActivityStatus = 'draft' | 'submitted' | 'approved' | 'rejected' | 'archived';

export const ACTIVITY_STATUSES: ActivityStatus[] = [
  'draft',
  'submitted',
  'approved',
  'rejected',
  'archived',
];

export interface ActivityRecord {
  id: string;
  organizationId: string;
  facilityId: string | null;
  productionLineId: string | null;
  equipmentId: string | null;
  dataSourceId: string | null;
  activityTypeId: string;
  reportingPeriodId: string;
  activityDate: string | null;
  periodStart: string | null;
  periodEnd: string | null;
  quantity: string | number;
  unitCode: string;
  normalizedQuantity: string | number;
  normalizedUnitCode: string;
  status: string;
  sourceReference: string | null;
  description: string | null;
  notes: string | null;
  metadataJson: Record<string, unknown> | null;
  rejectionReason: string | null;
  correctionReason: string | null;
  submittedByUserId: string | null;
  submittedAt: string | null;
  approvedByUserId: string | null;
  approvedAt: string | null;
  createdByUserId: string | null;
  updatedByUserId: string | null;
  rowVersion: number;
  isArchived: boolean;
  createdAt?: string;
  updatedAt?: string;
}

export interface ActivityRecordCreate {
  facilityId?: string | null;
  productionLineId?: string | null;
  equipmentId?: string | null;
  dataSourceId?: string | null;
  activityTypeId: string;
  reportingPeriodId: string;
  activityDate?: string | null;
  periodStart?: string | null;
  periodEnd?: string | null;
  quantity: number | string;
  unitCode: string;
  sourceReference?: string | null;
  description?: string | null;
  notes?: string | null;
  metadataJson?: Record<string, unknown> | null;
}

export interface ActivityRecordUpdate {
  facilityId?: string | null;
  productionLineId?: string | null;
  equipmentId?: string | null;
  dataSourceId?: string | null;
  activityTypeId?: string;
  reportingPeriodId?: string;
  activityDate?: string | null;
  periodStart?: string | null;
  periodEnd?: string | null;
  quantity?: number | string;
  unitCode?: string;
  sourceReference?: string | null;
  description?: string | null;
  notes?: string | null;
  metadataJson?: Record<string, unknown> | null;
  rowVersion: number;
}

export interface ActivityRecordRejectRequest {
  reason: string;
  rowVersion: number;
}

export interface ActivityRecordCorrectRequest {
  reason: string;
  quantity?: number | string;
  unitCode?: string;
  description?: string | null;
  notes?: string | null;
  sourceReference?: string | null;
  rowVersion: number;
}

export interface ActivityRecordRevision {
  id: string;
  activityRecordId: string;
  revisionNumber: number;
  changeType: string;
  changedByUserId: string | null;
  previousDataJson: Record<string, unknown> | null;
  newDataJson: Record<string, unknown> | null;
  changeReason: string | null;
  createdAt: string;
}

export interface ActivityRecordListParams {
  page?: number;
  pageSize?: number;
  search?: string;
  facilityId?: string;
  productionLineId?: string;
  equipmentId?: string;
  dataSourceId?: string;
  activityTypeId?: string;
  reportingPeriodId?: string;
  status?: string;
  dateFrom?: string;
  dateTo?: string;
  sortBy?: string;
  sortDirection?: 'asc' | 'desc';
}
