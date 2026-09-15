import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatListModule } from '@angular/material/list';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { AuthService } from '../core/services/auth.service';
import { OpsApiService } from '../core/services/ops-api.service';
import { canManageReferenceData, canViewCbam } from '../core/services/roles.util';
import { APP_VERSION } from '../core/version';

@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    MatToolbarModule,
    MatSidenavModule,
    MatListModule,
    MatButtonModule,
    MatIconModule,
    MatMenuModule,
  ],
  templateUrl: './shell.component.html',
  styleUrl: './shell.component.scss',
})
export class ShellComponent {
  private readonly auth = inject(AuthService);
  private readonly opsApi = inject(OpsApiService);
  private readonly breakpoints = inject(BreakpointObserver);

  readonly appVersion = APP_VERSION;
  readonly user = this.auth.currentUser;
  readonly organizations = this.auth.organizations;
  readonly currentOrganizationId = this.auth.currentOrganizationId;
  readonly sidenavOpen = signal(true);
  readonly unreadCount = signal(0);
  readonly showSystemAdmin = computed(() => canManageReferenceData(this.auth.currentRoles()));
  readonly showCbam = computed(() => canViewCbam(this.auth.currentRoles()));

  readonly selectedOrganizationName = computed(() => {
    const id = this.currentOrganizationId();
    return (
      this.organizations().find((o) => o.organizationId === id)?.organizationName ?? 'Organization'
    );
  });

  constructor() {
    this.breakpoints.observe([Breakpoints.Handset]).subscribe((state) => {
      this.sidenavOpen.set(!state.matches);
    });
    if (this.auth.isAuthenticated() && this.organizations().length === 0) {
      this.auth.loadMyOrganizations().subscribe({ error: () => undefined });
    }
    if (this.auth.isAuthenticated()) {
      this.opsApi.unreadCount().subscribe({
        next: (r: { count?: number }) => this.unreadCount.set(r.count ?? 0),
        error: () => undefined,
      });
    }
  }

  toggleSidenav(): void {
    this.sidenavOpen.update((open) => !open);
  }

  selectOrganization(organizationId: string): void {
    this.auth.selectOrganization(organizationId);
  }

  logout(): void {
    this.auth.logout().subscribe();
  }
}
