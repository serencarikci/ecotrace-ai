export type FacilityType =
  | 'manufacturing'
  | 'warehouse'
  | 'office'
  | 'laboratory'
  | 'wastewater_treatment'
  | 'energy_generation'
  | 'logistics_center'
  | 'agricultural_site'
  | 'other';

export const FACILITY_TYPES: FacilityType[] = [
  'manufacturing',
  'warehouse',
  'office',
  'laboratory',
  'wastewater_treatment',
  'energy_generation',
  'logistics_center',
  'agricultural_site',
  'other',
];

export interface Facility {
  id: string;
  organizationId: string;
  code: string;
  name: string;
  description: string | null;
  facilityType: string;
  countryCode: string;
  city: string | null;
  district: string | null;
  addressLine: string | null;
  postalCode: string | null;
  latitude: string | number | null;
  longitude: string | number | null;
  timezone: string;
  operationalStartDate: string | null;
  operationalEndDate: string | null;
  isActive: boolean;
  createdAt?: string;
  updatedAt?: string;
}

export interface FacilityCreate {
  code: string;
  name: string;
  description?: string | null;
  facilityType: string;
  countryCode: string;
  city?: string | null;
  district?: string | null;
  addressLine?: string | null;
  postalCode?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  timezone?: string;
  operationalStartDate?: string | null;
  operationalEndDate?: string | null;
  isActive?: boolean;
}

export interface FacilityUpdate {
  name?: string;
  description?: string | null;
  facilityType?: string;
  countryCode?: string;
  city?: string | null;
  district?: string | null;
  addressLine?: string | null;
  postalCode?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  timezone?: string;
  operationalStartDate?: string | null;
  operationalEndDate?: string | null;
  isActive?: boolean;
}

export interface FacilityListParams {
  page?: number;
  pageSize?: number;
  search?: string;
  facilityType?: string;
  countryCode?: string;
  city?: string;
  isActive?: boolean;
}
