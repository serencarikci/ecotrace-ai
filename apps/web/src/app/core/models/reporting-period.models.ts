export type PeriodType = 'monthly' | 'quarterly' | 'annual' | 'custom';
export type PeriodStatus = 'open' | 'under_review' | 'locked' | 'archived';

export const PERIOD_TYPES: PeriodType[] = ['monthly', 'quarterly', 'annual', 'custom'];
export const PERIOD_STATUSES: PeriodStatus[] = ['open', 'under_review', 'locked', 'archived'];

export interface ReportingPeriod {
  id: string;
  organizationId: string;
  code: string;
  name: string;
  periodType: string;
  startDate: string;
  endDate: string;
  status: string;
  lockedAt: string | null;
  lockedByUserId: string | null;
  activityRecordCount?: number;
  createdAt?: string;
  updatedAt?: string;
}

export interface ReportingPeriodCreate {
  code: string;
  name: string;
  periodType: string;
  startDate: string;
  endDate: string;
  status?: string;
}

export interface ReportingPeriodUpdate {
  name?: string;
  periodType?: string;
  startDate?: string;
  endDate?: string;
  status?: string;
}

export interface ReportingPeriodListParams {
  page?: number;
  pageSize?: number;
  search?: string;
  status?: string;
  periodType?: string;
}
