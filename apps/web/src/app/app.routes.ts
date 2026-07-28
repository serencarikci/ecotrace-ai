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
        path: 'profile',
        loadComponent: () =>
          import('./features/profile/profile.component').then((m) => m.ProfileComponent),
      },
    ],
  },
  {
    path: '**',
    loadComponent: () =>
      import('./features/auth/not-found.component').then((m) => m.NotFoundComponent),
  },
];
