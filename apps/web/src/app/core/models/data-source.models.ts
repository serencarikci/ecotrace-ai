export type DataSourceType =
  | 'manual_entry'
  | 'csv_import'
  | 'excel_import'
  | 'utility_invoice'
  | 'erp'
  | 'scada'
  | 'meter'
  | 'sensor'
  | 'api'
  | 'mqtt'
  | 'other';

export const DATA_SOURCE_TYPES: DataSourceType[] = [
  'manual_entry',
  'csv_import',
  'excel_import',
  'utility_invoice',
  'erp',
  'scada',
  'meter',
  'sensor',
  'api',
  'mqtt',
  'other',
];

export const LIVE_INTEGRATION_SOURCE_TYPES: DataSourceType[] = ['erp', 'scada', 'api', 'mqtt'];

export interface DataSource {
  id: string;
  organizationId: string;
  facilityId: string | null;
  equipmentId: string | null;
  code: string;
  name: string;
  sourceType: string;
  description: string | null;
  externalReference: string | null;
  isActive: boolean;
  createdAt?: string;
  updatedAt?: string;
}

export interface DataSourceCreate {
  facilityId?: string | null;
  equipmentId?: string | null;
  code: string;
  name: string;
  sourceType: string;
  description?: string | null;
  externalReference?: string | null;
  isActive?: boolean;
}

export interface DataSourceUpdate {
  facilityId?: string | null;
  equipmentId?: string | null;
  name?: string;
  sourceType?: string;
  description?: string | null;
  externalReference?: string | null;
  isActive?: boolean;
}

export interface DataSourceListParams {
  page?: number;
  pageSize?: number;
  search?: string;
  facilityId?: string;
  equipmentId?: string;
  sourceType?: string;
  isActive?: boolean;
}
