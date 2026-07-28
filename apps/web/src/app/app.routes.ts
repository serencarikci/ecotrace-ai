import { Routes } from '@angular/router';
import { authGuard, guestGuard, roleGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    redirectTo: 'app/dashboard',
  },
  {
    path: 'login',
    canActivate: [guestGuard],
    loadComponent: () =>
      import('./features/auth/login.component').then((m) => m.LoginComponent),
  },
  {
    path: 'unauthorized',
    loadComponent: () =>
      import('./features/auth/unauthorized.component').then((m) => m.UnauthorizedComponent),
  },
  {
    path: 'app',
    canActivate: [authGuard],
    loadComponent: () => import('./layout/shell.component').then((m) => m.ShellComponent),
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'dashboard' },
      {
        path: 'dashboard',
        loadComponent: () =>
          import('./features/dashboard/dashboard.component').then((m) => m.DashboardComponent),
      },
      {
        path: 'organizations',
        loadComponent: () =>
          import('./features/organizations/organization-list.component').then(
            (m) => m.OrganizationListComponent,
          ),
      },
      {
        path: 'organizations/:id',
        loadComponent: () =>
          import('./features/organizations/organization-detail.component').then(
            (m) => m.OrganizationDetailComponent,
          ),
      },
      {
        path: 'facilities',
        loadComponent: () =>
          import('./features/facilities/facility-list.component').then(
            (m) => m.FacilityListComponent,
          ),
      },
      {
        path: 'facilities/new',
        loadComponent: () =>
          import('./features/facilities/facility-form.component').then(
            (m) => m.FacilityFormComponent,
          ),
      },
      {
        path: 'facilities/:id',
        loadComponent: () =>
          import('./features/facilities/facility-detail.component').then(
            (m) => m.FacilityDetailComponent,
          ),
      },
      {
        path: 'facilities/:id/edit',
        loadComponent: () =>
          import('./features/facilities/facility-form.component').then(
            (m) => m.FacilityFormComponent,
          ),
      },
      {
        path: 'production-lines',
        loadComponent: () =>
          import('./features/production-lines/production-line-list.component').then(
            (m) => m.ProductionLineListComponent,
          ),
      },
      {
        path: 'production-lines/new',
        loadComponent: () =>
          import('./features/production-lines/production-line-form.component').then(
            (m) => m.ProductionLineFormComponent,
          ),
      },
      {
        path: 'production-lines/:id',
        loadComponent: () =>
          import('./features/production-lines/production-line-detail.component').then(
            (m) => m.ProductionLineDetailComponent,
          ),
      },
      {
        path: 'production-lines/:id/edit',
        loadComponent: () =>
          import('./features/production-lines/production-line-form.component').then(
            (m) => m.ProductionLineFormComponent,
          ),
      },
      {
        path: 'equipment',
        loadComponent: () =>
          import('./features/equipment/equipment-list.component').then(
            (m) => m.EquipmentListComponent,
          ),
      },
      {
        path: 'equipment/new',
        loadComponent: () =>
          import('./features/equipment/equipment-form.component').then(
            (m) => m.EquipmentFormComponent,
          ),
      },
      {
        path: 'equipment/:id',
        loadComponent: () =>
          import('./features/equipment/equipment-detail.component').then(
            (m) => m.EquipmentDetailComponent,
          ),
      },
      {
        path: 'equipment/:id/edit',
        loadComponent: () =>
          import('./features/equipment/equipment-form.component').then(
            (m) => m.EquipmentFormComponent,
          ),
      },
      {
        path: 'data-sources',
        loadComponent: () =>
          import('./features/data-sources/data-source-list.component').then(
            (m) => m.DataSourceListComponent,
          ),
      },
      {
        path: 'data-sources/new',
        loadComponent: () =>
          import('./features/data-sources/data-source-form.component').then(
            (m) => m.DataSourceFormComponent,
          ),
      },
      {
        path: 'data-sources/:id',
        loadComponent: () =>
          import('./features/data-sources/data-source-detail.component').then(
            (m) => m.DataSourceDetailComponent,
          ),
      },
      {
        path: 'data-sources/:id/edit',
        loadComponent: () =>
          import('./features/data-sources/data-source-form.component').then(
            (m) => m.DataSourceFormComponent,
          ),
      },
      {
        path: 'reporting-periods',
        loadComponent: () =>
          import('./features/reporting-periods/reporting-period-list.component').then(
            (m) => m.ReportingPeriodListComponent,
          ),
      },
      {
        path: 'reporting-periods/new',
        loadComponent: () =>
          import('./features/reporting-periods/reporting-period-form.component').then(
            (m) => m.ReportingPeriodFormComponent,
          ),
      },
      {
        path: 'reporting-periods/:id',
        loadComponent: () =>
          import('./features/reporting-periods/reporting-period-detail.component').then(
            (m) => m.ReportingPeriodDetailComponent,
          ),
      },
      {
        path: 'activity-data',
        loadComponent: () =>
          import('./features/activity-data/activity-list.component').then(
            (m) => m.ActivityListComponent,
          ),
      },
      {
        path: 'activity-data/new',
        loadComponent: () =>
          import('./features/activity-data/activity-form.component').then(
            (m) => m.ActivityFormComponent,
          ),
      },
      {
        path: 'activity-data/:id',
        loadComponent: () =>
          import('./features/activity-data/activity-detail.component').then(
            (m) => m.ActivityDetailComponent,
          ),
      },
      {
        path: 'activity-data/:id/edit',
        loadComponent: () =>
          import('./features/activity-data/activity-form.component').then(
            (m) => m.ActivityFormComponent,
          ),
      },
      {
        path: 'data-imports',
        loadComponent: () =>
          import('./features/data-imports/import-list.component').then(
            (m) => m.ImportListComponent,
          ),
      },
      {
        path: 'data-imports/new',
        loadComponent: () =>
          import('./features/data-imports/import-wizard.component').then(
            (m) => m.ImportWizardComponent,
          ),
      },
      {
        path: 'data-imports/:id',
        loadComponent: () =>
          import('./features/data-imports/import-detail.component').then(
            (m) => m.ImportDetailComponent,
          ),
      },
      {
        path: 'reference-data/units',
        canActivate: [roleGuard('system_admin')],
        loadComponent: () =>
          import('./features/reference-data/units-list.component').then(
            (m) => m.UnitsListComponent,
          ),
      },
      {
        path: 'reference-data/activity-types',
        canActivate: [roleGuard('system_admin')],
        loadComponent: () =>
          import('./features/reference-data/activity-types-list.component').then(
            (m) => m.ActivityTypesListComponent,
          ),
      },
      {
        path: 'emission-factor-sources',
        loadComponent: () =>
          import('./features/emission-factor-sources/factor-source-list.component').then(
            (m) => m.FactorSourceListComponent,
          ),
      },
      {
        path: 'emission-factor-sources/new',
        canActivate: [roleGuard('system_admin')],
        loadComponent: () =>
          import('./features/emission-factor-sources/factor-source-detail.component').then(
            (m) => m.FactorSourceDetailComponent,
          ),
      },
      {
        path: 'emission-factor-sources/:id',
        loadComponent: () =>
          import('./features/emission-factor-sources/factor-source-detail.component').then(
            (m) => m.FactorSourceDetailComponent,
          ),
      },
      {
        path: 'emission-factors',
        loadComponent: () =>
          import('./features/emission-factors/emission-factor-list.component').then(
            (m) => m.EmissionFactorListComponent,
          ),
      },
      {
        path: 'emission-factors/new',
        canActivate: [roleGuard('system_admin')],
        loadComponent: () =>
          import('./features/emission-factors/emission-factor-detail.component').then(
            (m) => m.EmissionFactorDetailComponent,
          ),
      },
      {
        path: 'emission-factors/:id/edit',
        canActivate: [roleGuard('system_admin')],
        loadComponent: () =>
          import('./features/emission-factors/emission-factor-detail.component').then(
            (m) => m.EmissionFactorDetailComponent,
          ),
      },
      {
        path: 'emission-factors/:id',
        loadComponent: () =>
          import('./features/emission-factors/emission-factor-detail.component').then(
            (m) => m.EmissionFactorDetailComponent,
          ),
      },
      {
        path: 'emission-factor-preferences',
        loadComponent: () =>
          import('./features/emission-factor-preferences/factor-preferences.component').then(
            (m) => m.FactorPreferencesComponent,
          ),
      },
      {
        path: 'carbon-inventories',
        loadComponent: () =>
          import('./features/carbon-inventories/carbon-inventory-pages.component').then(
            (m) => m.CarbonInventoryListComponent,
          ),
      },
      {
        path: 'carbon-inventories/new',
        loadComponent: () =>
          import('./features/carbon-inventories/carbon-inventory-pages.component').then(
            (m) => m.CarbonInventoryDetailComponent,
          ),
      },
      {
        path: 'carbon-inventories/:id',
        loadComponent: () =>
          import('./features/carbon-inventories/carbon-inventory-pages.component').then(
            (m) => m.CarbonInventoryDetailComponent,
          ),
      },
      {
        path: 'carbon-inventories/:id/validation',
        loadComponent: () =>
          import('./features/carbon-inventories/carbon-inventory-pages.component').then(
            (m) => m.CarbonInventoryValidationComponent,
          ),
      },
      {
        path: 'carbon-inventories/:id/results',
        loadComponent: () =>
          import('./features/carbon-inventories/carbon-inventory-pages.component').then(
            (m) => m.CarbonInventoryResultsComponent,
          ),
      },
      {
        path: 'carbon-inventories/:id/runs/:runId',
        loadComponent: () =>
          import('./features/carbon-inventories/carbon-inventory-pages.component').then(
            (m) => m.CarbonInventoryResultsComponent,
          ),
      },
      {
        path: 'carbon-calculation-items/:itemId',
        loadComponent: () =>
          import('./features/carbon-inventories/carbon-inventory-pages.component').then(
            (m) => m.CalculationItemDetailComponent,
          ),
      },
      {
        path: 'analytics',
        loadComponent: () =>
          import('./features/analytics/analytics-pages.component').then(
            (m) => m.AnalyticsDashboardComponent,
          ),
      },
      {
        path: 'analytics/trends',
        loadComponent: () =>
          import('./features/analytics/analytics-pages.component').then(
            (m) => m.AnalyticsTrendsComponent,
          ),
      },
      {
        path: 'analytics/categories',
        data: { dimension: 'categories' },
        loadComponent: () =>
          import('./features/analytics/analytics-pages.component').then(
            (m) => m.AnalyticsBreakdownComponent,
          ),
      },
      {
        path: 'analytics/facilities',
        data: { dimension: 'facilities' },
        loadComponent: () =>
          import('./features/analytics/analytics-pages.component').then(
            (m) => m.AnalyticsBreakdownComponent,
          ),
      },
      {
        path: 'analytics/intensity',
        loadComponent: () =>
          import('./features/analytics/analytics-pages.component').then(
            (m) => m.AnalyticsIntensityKpisComponent,
          ),
      },
      {
        path: 'analytics/decision-support',
        loadComponent: () =>
          import('./features/analytics/analytics-pages.component').then(
            (m) => m.DecisionSupportComponent,
          ),
      },
      {
        path: 'planning/baselines',
        loadComponent: () =>
          import('./features/analytics/analytics-pages.component').then(
            (m) => m.PlanningBaselinesComponent,
          ),
      },
      {
        path: 'planning/targets',
        loadComponent: () =>
          import('./features/analytics/analytics-pages.component').then(
            (m) => m.PlanningTargetsComponent,
          ),
      },
      {
        path: 'planning/initiatives',
        loadComponent: () =>
          import('./features/analytics/analytics-pages.component').then(
            (m) => m.PlanningInitiativesComponent,
          ),
      },
      {
        path: 'planning/scenarios',
        loadComponent: () =>
          import('./features/analytics/analytics-pages.component').then(
            (m) => m.PlanningScenariosComponent,
          ),
      },
      {
        path: 'reports',
        loadComponent: () =>
          import('./features/analytics/analytics-pages.component').then(
            (m) => m.ReportCenterComponent,
          ),
      },
      {
        path: 'profile',
        loadComponent: () =>
          import('./features/profile/profile.component').then((m) => m.ProfileComponent),
      },
      {
        path: 'products',
        loadComponent: () =>
          import('./features/product-sustainability/product-pages.component').then(
            (m) => m.ProductListComponent,
          ),
      },
      {
        path: 'products/new',
        loadComponent: () =>
          import('./features/product-sustainability/product-pages.component').then(
            (m) => m.ProductFormComponent,
          ),
      },
      {
        path: 'products/:id',
        loadComponent: () =>
          import('./features/product-sustainability/product-pages.component').then(
            (m) => m.ProductDetailComponent,
          ),
      },
      {
        path: 'products/:id/edit',
        loadComponent: () =>
          import('./features/product-sustainability/product-pages.component').then(
            (m) => m.ProductFormComponent,
          ),
      },
      {
        path: 'products/:id/variants',
        loadComponent: () =>
          import('./features/product-sustainability/product-pages.component').then(
            (m) => m.ProductPlaceholderComponent,
          ),
        data: { title: 'Product variants', subtitle: 'Manage variants via product API workflows.' },
      },
      {
        path: 'products/:id/boms',
        loadComponent: () =>
          import('./features/product-sustainability/product-pages.component').then(
            (m) => m.ProductBomListComponent,
          ),
      },
      {
        path: 'product-batches',
        loadComponent: () =>
          import('./features/product-sustainability/product-pages.component').then(
            (m) => m.SimpleEntityListComponent,
          ),
        data: { kind: 'batches' },
      },
      {
        path: 'product-batches/new',
        loadComponent: () =>
          import('./features/product-sustainability/product-pages.component').then(
            (m) => m.ProductPlaceholderComponent,
          ),
        data: { title: 'New batch', subtitle: 'Create batches through the product-batches API.' },
      },
      {
        path: 'product-batches/:id',
        loadComponent: () =>
          import('./features/product-sustainability/product-pages.component').then(
            (m) => m.ProductPlaceholderComponent,
          ),
        data: { title: 'Batch detail', subtitle: 'Batch detail and transition controls.' },
      },
      {
        path: 'suppliers',
        loadComponent: () =>
          import('./features/product-sustainability/product-pages.component').then(
            (m) => m.SimpleEntityListComponent,
          ),
        data: { kind: 'suppliers' },
      },
      {
        path: 'suppliers/new',
        loadComponent: () =>
          import('./features/product-sustainability/product-pages.component').then(
            (m) => m.ProductPlaceholderComponent,
          ),
        data: { title: 'New supplier', subtitle: 'Create suppliers through the suppliers API.' },
      },
      {
        path: 'suppliers/:id',
        loadComponent: () =>
          import('./features/product-sustainability/product-pages.component').then(
            (m) => m.ProductPlaceholderComponent,
          ),
        data: { title: 'Supplier detail' },
      },
      {
        path: 'suppliers/:id/edit',
        loadComponent: () =>
          import('./features/product-sustainability/product-pages.component').then(
            (m) => m.ProductPlaceholderComponent,
          ),
        data: { title: 'Edit supplier' },
      },
      {
        path: 'materials',
        loadComponent: () =>
          import('./features/product-sustainability/product-pages.component').then(
            (m) => m.SimpleEntityListComponent,
          ),
        data: { kind: 'materials' },
      },
      {
        path: 'materials/new',
        loadComponent: () =>
          import('./features/product-sustainability/product-pages.component').then(
            (m) => m.ProductPlaceholderComponent,
          ),
        data: { title: 'New material' },
      },
      {
        path: 'materials/:id',
        loadComponent: () =>
          import('./features/product-sustainability/product-pages.component').then(
            (m) => m.ProductPlaceholderComponent,
          ),
        data: { title: 'Material detail' },
      },
      {
        path: 'materials/:id/edit',
        loadComponent: () =>
          import('./features/product-sustainability/product-pages.component').then(
            (m) => m.ProductPlaceholderComponent,
          ),
        data: { title: 'Edit material' },
      },
      {
        path: 'lca-studies',
        loadComponent: () =>
          import('./features/product-sustainability/product-pages.component').then(
            (m) => m.SimpleEntityListComponent,
          ),
        data: { kind: 'studies' },
      },
      {
        path: 'lca-studies/new',
        loadComponent: () =>
          import('./features/product-sustainability/product-pages.component').then(
            (m) => m.ProductPlaceholderComponent,
          ),
        data: { title: 'New LCA study', subtitle: 'Create studies through the LCA API workspace.' },
      },
      {
        path: 'lca-studies/:id',
        loadComponent: () =>
          import('./features/product-sustainability/product-pages.component').then(
            (m) => m.LcaStudyDetailComponent,
          ),
      },
      {
        path: 'lca-studies/:id/inventory',
        loadComponent: () =>
          import('./features/product-sustainability/product-pages.component').then(
            (m) => m.ProductPlaceholderComponent,
          ),
        data: { title: 'LCA inventory', subtitle: 'Inventory inputs grid.' },
      },
      {
        path: 'lca-studies/:id/calculation',
        loadComponent: () =>
          import('./features/product-sustainability/product-pages.component').then(
            (m) => m.LcaStudyDetailComponent,
          ),
      },
      {
        path: 'lca-studies/:id/results',
        loadComponent: () =>
          import('./features/product-sustainability/product-pages.component').then(
            (m) => m.LcaStudyDetailComponent,
          ),
      },
      {
        path: 'lca-studies/:id/data-quality',
        loadComponent: () =>
          import('./features/product-sustainability/product-pages.component').then(
            (m) => m.ProductPlaceholderComponent,
          ),
        data: { title: 'Data quality', subtitle: 'Internal 1–5 data quality indicators.' },
      },
      {
        path: 'product-carbon-footprints',
        loadComponent: () =>
          import('./features/product-sustainability/product-pages.component').then(
            (m) => m.SimpleEntityListComponent,
          ),
        data: { kind: 'footprints' },
      },
      {
        path: 'product-carbon-footprints/:id',
        loadComponent: () =>
          import('./features/product-sustainability/product-pages.component').then(
            (m) => m.ProductPlaceholderComponent,
          ),
        data: { title: 'Footprint detail' },
      },
      {
        path: 'digital-product-passports',
        loadComponent: () =>
          import('./features/product-sustainability/product-pages.component').then(
            (m) => m.SimpleEntityListComponent,
          ),
        data: { kind: 'passports' },
      },
      {
        path: 'digital-product-passports/new',
        loadComponent: () =>
          import('./features/product-sustainability/product-pages.component').then(
            (m) => m.ProductPlaceholderComponent,
          ),
        data: { title: 'New passport' },
      },
      {
        path: 'digital-product-passports/:id',
        loadComponent: () =>
          import('./features/product-sustainability/product-pages.component').then(
            (m) => m.PassportDetailComponent,
          ),
      },
      {
        path: 'digital-product-passports/:id/edit',
        loadComponent: () =>
          import('./features/product-sustainability/product-pages.component').then(
            (m) => m.PassportDetailComponent,
          ),
      },
      {
        path: 'digital-product-passports/:id/preview',
        loadComponent: () =>
          import('./features/product-sustainability/product-pages.component').then(
            (m) => m.PassportDetailComponent,
          ),
      },
      {
        path: 'digital-product-passports/:id/versions',
        loadComponent: () =>
          import('./features/product-sustainability/product-pages.component').then(
            (m) => m.PassportDetailComponent,
          ),
      },
      {
        path: 'ai',
        loadComponent: () =>
          import('./features/ai-copilot/ai-pages.component').then((m) => m.AiChatComponent),
      },
      {
        path: 'ai/documents',
        loadComponent: () =>
          import('./features/ai-copilot/ai-pages.component').then((m) => m.AiDocumentsComponent),
      },
      {
        path: 'ai/search',
        loadComponent: () =>
          import('./features/ai-copilot/ai-pages.component').then((m) => m.AiSearchComponent),
      },
      {
        path: 'ai/admin',
        loadComponent: () =>
          import('./features/ai-copilot/ai-pages.component').then((m) => m.AiAdminComponent),
      },
      {
        path: 'automation',
        loadComponent: () =>
          import('./features/phase7/phase7-pages.component').then((m) => m.AutomationListComponent),
      },
      {
        path: 'automation/new',
        loadComponent: () =>
          import('./features/phase7/phase7-pages.component').then((m) => m.AutomationFormComponent),
      },
      {
        path: 'automation/:id',
        loadComponent: () =>
          import('./features/phase7/phase7-pages.component').then((m) => m.AutomationFormComponent),
      },
      {
        path: 'automation/:id/executions',
        loadComponent: () =>
          import('./features/phase7/phase7-pages.component').then(
            (m) => m.AutomationExecutionsComponent,
          ),
      },
      {
        path: 'agents',
        loadComponent: () =>
          import('./features/phase7/phase7-pages.component').then((m) => m.AgentsListComponent),
      },
      {
        path: 'agents/:code',
        loadComponent: () =>
          import('./features/phase7/phase7-pages.component').then((m) => m.AgentDetailComponent),
      },
      {
        path: 'agent-executions',
        loadComponent: () =>
          import('./features/phase7/phase7-pages.component').then(
            (m) => m.AgentExecutionsComponent,
          ),
      },
      {
        path: 'agent-executions/:id',
        loadComponent: () =>
          import('./features/phase7/phase7-pages.component').then(
            (m) => m.AgentExecutionDetailComponent,
          ),
      },
      {
        path: 'agent-approvals',
        loadComponent: () =>
          import('./features/phase7/phase7-pages.component').then((m) => m.AgentApprovalsComponent),
      },
      {
        path: 'anomalies',
        loadComponent: () =>
          import('./features/phase7/phase7-pages.component').then((m) => m.AnomaliesComponent),
      },
      {
        path: 'anomalies/:id',
        loadComponent: () =>
          import('./features/phase7/phase7-pages.component').then((m) => m.AnomalyDetailComponent),
      },
      {
        path: 'anomaly-rules',
        loadComponent: () =>
          import('./features/phase7/phase7-pages.component').then((m) => m.AnomalyRulesComponent),
      },
      {
        path: 'forecasts',
        loadComponent: () =>
          import('./features/phase7/phase7-pages.component').then((m) => m.ForecastsComponent),
      },
      {
        path: 'forecasts/new',
        loadComponent: () =>
          import('./features/phase7/phase7-pages.component').then((m) => m.ForecastFormComponent),
      },
      {
        path: 'forecasts/:id',
        loadComponent: () =>
          import('./features/phase7/phase7-pages.component').then((m) => m.ForecastFormComponent),
      },
      {
        path: 'forecasts/:id/results',
        loadComponent: () =>
          import('./features/phase7/phase7-pages.component').then(
            (m) => m.ForecastResultsComponent,
          ),
      },
      {
        path: 'data-quality',
        loadComponent: () =>
          import('./features/phase7/phase7-pages.component').then((m) => m.DataQualityComponent),
      },
      {
        path: 'data-quality/:id',
        loadComponent: () =>
          import('./features/phase7/phase7-pages.component').then(
            (m) => m.DataQualityDetailComponent,
          ),
      },
      {
        path: 'alerts',
        loadComponent: () =>
          import('./features/phase7/phase7-pages.component').then((m) => m.AlertsComponent),
      },
      {
        path: 'alerts/:id',
        loadComponent: () =>
          import('./features/phase7/phase7-pages.component').then((m) => m.AlertDetailComponent),
      },
      {
        path: 'notifications',
        loadComponent: () =>
          import('./features/phase7/phase7-pages.component').then((m) => m.NotificationsComponent),
      },
      {
        path: 'notification-settings',
        loadComponent: () =>
          import('./features/phase7/phase7-pages.component').then(
            (m) => m.NotificationSettingsComponent,
          ),
      },
      {
        path: 'scheduled-reports',
        loadComponent: () =>
          import('./features/phase7/phase7-pages.component').then(
            (m) => m.ScheduledReportsComponent,
          ),
      },
      {
        path: 'scheduled-reports/new',
        loadComponent: () =>
          import('./features/phase7/phase7-pages.component').then(
            (m) => m.ScheduledReportFormComponent,
          ),
      },
      {
        path: 'scheduled-reports/:id',
        loadComponent: () =>
          import('./features/phase7/phase7-pages.component').then(
            (m) => m.ScheduledReportFormComponent,
          ),
      },
      {
        path: 'generated-reports',
        loadComponent: () =>
          import('./features/phase7/phase7-pages.component').then(
            (m) => m.GeneratedReportsComponent,
          ),
      },
      {
        path: 'generated-reports/:id',
        loadComponent: () =>
          import('./features/phase7/phase7-pages.component').then(
            (m) => m.GeneratedReportDetailComponent,
          ),
      },
      {
        path: 'supplier-monitoring',
        loadComponent: () =>
          import('./features/phase7/phase7-pages.component').then(
            (m) => m.SupplierMonitoringComponent,
          ),
      },
      {
        path: 'supplier-monitoring/:supplierId',
        loadComponent: () =>
          import('./features/phase7/phase7-pages.component').then(
            (m) => m.SupplierMonitoringDetailComponent,
          ),
      },
      {
        path: 'regulatory-intelligence',
        loadComponent: () =>
          import('./features/phase7/phase7-pages.component').then((m) => m.RegulatoryListComponent),
      },
      {
        path: 'regulatory-intelligence/:id',
        loadComponent: () =>
          import('./features/phase7/phase7-pages.component').then(
            (m) => m.RegulatoryDetailComponent,
          ),
      },
      {
        path: 'regulatory-assessments',
        loadComponent: () =>
          import('./features/phase7/phase7-pages.component').then(
            (m) => m.RegulatoryAssessmentsComponent,
          ),
      },
      {
        path: 'system/job-monitoring',
        canActivate: [roleGuard],
        data: { roles: ['system_admin', 'organization_admin'] },
        loadComponent: () =>
          import('./features/phase7/phase7-pages.component').then((m) => m.JobMonitoringComponent),
      },
      {
        path: 'system/operations',
        canActivate: [roleGuard],
        data: { roles: ['system_admin'] },
        loadComponent: () =>
          import('./features/phase7/phase7-pages.component').then(
            (m) => m.SystemOperationsComponent,
          ),
      },
      {
        path: 'system/health',
        canActivate: [roleGuard],
        data: { roles: ['system_admin'] },
        loadComponent: () =>
          import('./features/phase7/phase7-pages.component').then((m) => m.SystemHealthComponent),
      },
    ],
  },
  {
    path: 'passport/:publicSlug',
    loadComponent: () =>
      import('./features/product-sustainability/public-passport.component').then(
        (m) => m.PublicPassportComponent,
      ),
  },
  {
    path: 'passport/:publicSlug/documents',
    loadComponent: () =>
      import('./features/product-sustainability/public-passport.component').then(
        (m) => m.PublicPassportComponent,
      ),
  },
  {
    path: 'passport/:publicSlug/qr',
    loadComponent: () =>
      import('./features/product-sustainability/public-passport.component').then(
        (m) => m.PublicPassportComponent,
      ),
  },
  {
    path: '**',
    loadComponent: () =>
      import('./features/auth/not-found.component').then((m) => m.NotFoundComponent),
  },
];
