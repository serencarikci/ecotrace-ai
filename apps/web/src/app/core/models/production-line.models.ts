export interface ProductionLine {
  id: string;
  organizationId: string;
  facilityId: string;
  code: string;
  name: string;
  description: string | null;
  productionCategory: string | null;
  capacityValue: string | number | null;
  capacityUnitCode: string | null;
  isActive: boolean;
  createdAt?: string;
  updatedAt?: string;
}

export interface ProductionLineCreate {
  code: string;
  name: string;
  description?: string | null;
  productionCategory?: string | null;
  capacityValue?: number | null;
  capacityUnitCode?: string | null;
  isActive?: boolean;
}

export interface ProductionLineUpdate {
  name?: string;
  description?: string | null;
  productionCategory?: string | null;
  capacityValue?: number | null;
  capacityUnitCode?: string | null;
  isActive?: boolean;
}
