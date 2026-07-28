export interface UserSummary {
  id: string;
  email: string;
  fullName: string;
  roles: string[];
}

export interface TokenResponse {
  accessToken: string;
  refreshToken: string;
  tokenType: string;
  expiresIn: number;
  user: UserSummary;
}

export interface MeResponse {
  id: string;
  email: string;
  fullName: string;
  isActive: boolean;
  isVerified: boolean;
  roles: string[];
  lastLoginAt: string | null;
}

export interface OrganizationMembership {
  organizationId: string;
  organizationName: string;
  organizationSlug: string;
  roleCode: string;
  isActive: boolean;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  legalName: string | null;
  countryCode: string;
  timezone: string;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface OrganizationCreate {
  name: string;
  slug: string;
  legalName?: string | null;
  countryCode: string;
  timezone: string;
  isActive: boolean;
}

export interface OrganizationUpdate {
  name?: string;
  legalName?: string | null;
  countryCode?: string;
  timezone?: string;
  isActive?: boolean;
}

export interface Page<T> {
  items: T[];
  page: number;
  pageSize: number;
  totalItems: number;
  totalPages: number;
}

export interface MetaResponse {
  name: string;
  version: string;
  environment: string;
  apiVersion: string;
}

export interface ApiErrorDetail {
  field?: string | null;
  message: string;
}

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details: ApiErrorDetail[];
    requestId: string | null;
  };
}
