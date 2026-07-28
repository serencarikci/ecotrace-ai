export type EquipmentType =
  | 'electricity_meter'
  | 'gas_meter'
  | 'water_meter'
  | 'fuel_tank'
  | 'boiler'
  | 'generator'
  | 'vehicle'
  | 'refrigeration_system'
  | 'production_machine'
  | 'wastewater_unit'
  | 'sensor'
  | 'other';

export const EQUIPMENT_TYPES: EquipmentType[] = [
  'electricity_meter',
  'gas_meter',
  'water_meter',
  'fuel_tank',
  'boiler',
  'generator',
  'vehicle',
  'refrigeration_system',
  'production_machine',
  'wastewater_unit',
  'sensor',
  'other',
];

export interface Equipment {
  id: string;
  organizationId: string;
  facilityId: string;
  productionLineId: string | null;
  code: string;
  name: string;
  description: string | null;
  equipmentType: string;
  manufacturer: string | null;
  model: string | null;
  serialNumber: string | null;
  commissioningDate: string | null;
  decommissioningDate: string | null;
  isActive: boolean;
  metadataJson: Record<string, unknown> | null;
  createdAt?: string;
  updatedAt?: string;
}

export interface EquipmentCreate {
  facilityId: string;
  productionLineId?: string | null;
  code: string;
  name: string;
  description?: string | null;
  equipmentType: string;
  manufacturer?: string | null;
  model?: string | null;
  serialNumber?: string | null;
  commissioningDate?: string | null;
  decommissioningDate?: string | null;
  isActive?: boolean;
  metadataJson?: Record<string, unknown> | null;
}

export interface EquipmentUpdate {
  facilityId?: string;
  productionLineId?: string | null;
  name?: string;
  description?: string | null;
  equipmentType?: string;
  manufacturer?: string | null;
  model?: string | null;
  serialNumber?: string | null;
  commissioningDate?: string | null;
  decommissioningDate?: string | null;
  isActive?: boolean;
  metadataJson?: Record<string, unknown> | null;
}

export interface EquipmentListParams {
  page?: number;
  pageSize?: number;
  search?: string;
  facilityId?: string;
  productionLineId?: string;
  equipmentType?: string;
  isActive?: boolean;
}
