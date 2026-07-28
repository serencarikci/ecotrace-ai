export interface Unit {
  id: string;
  code: string;
  name: string;
  symbol: string;
  dimension: string;
  conversionFactorToBase: string | number;
  baseUnitCode: string;
  decimalPrecision: number;
  isActive: boolean;
  createdAt?: string;
  updatedAt?: string;
}

export interface UnitCreate {
  code: string;
  name: string;
  symbol: string;
  dimension: string;
  conversionFactorToBase: number;
  baseUnitCode: string;
  decimalPrecision?: number;
  isActive?: boolean;
}

export interface UnitUpdate {
  name?: string;
  symbol?: string;
  dimension?: string;
  conversionFactorToBase?: number;
  baseUnitCode?: string;
  decimalPrecision?: number;
  isActive?: boolean;
}

export interface ActivityType {
  id: string;
  code: string;
  name: string;
  description: string | null;
  category: string;
  defaultUnitCode: string;
  allowedUnitDimension: string;
  expectedValueType: string;
  dataFrequency: string;
  requiresFacility: boolean;
  requiresEquipment: boolean;
  isActive: boolean;
  createdAt?: string;
  updatedAt?: string;
}

export interface ActivityTypeCreate {
  code: string;
  name: string;
  description?: string | null;
  category: string;
  defaultUnitCode: string;
  allowedUnitDimension: string;
  expectedValueType?: string;
  dataFrequency?: string;
  requiresFacility?: boolean;
  requiresEquipment?: boolean;
  isActive?: boolean;
}

export interface ActivityTypeUpdate {
  name?: string;
  description?: string | null;
  category?: string;
  defaultUnitCode?: string;
  allowedUnitDimension?: string;
  expectedValueType?: string;
  dataFrequency?: string;
  requiresFacility?: boolean;
  requiresEquipment?: boolean;
  isActive?: boolean;
}

export interface ReferenceListParams {
  page?: number;
  pageSize?: number;
  search?: string;
  activeOnly?: boolean;
  category?: string;
  dimension?: string;
}
