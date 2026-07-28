import { Component, inject, OnInit, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatTableModule } from '@angular/material/table';
import { OrganizationService } from '../../core/services/organization.service';
import { AuthService } from '../../core/services/auth.service';
import { Organization } from '../../core/models/api.models';
import { extractApiErrorMessage } from '../../core/services/error.util';
import { OrganizationFormComponent } from './organization-form.component';

@Component({
  selector: 'app-organization-list',
  standalone: true,
  imports: [RouterLink, MatTableModule, MatButtonModule, OrganizationFormComponent],
  templateUrl: './organization-list.component.html',
  styleUrl: './organization-list.component.scss',
})
export class OrganizationListComponent implements OnInit {
  private readonly organizationsApi = inject(OrganizationService);
  private readonly auth = inject(AuthService);

  readonly organizations = signal<Organization[]>([]);
  readonly errorMessage = signal<string | null>(null);
  readonly showCreate = signal(false);
  readonly canCreate = this.auth.hasAnyRole('system_admin');
  readonly displayedColumns = ['name', 'slug', 'countryCode', 'timezone', 'status', 'actions'];

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.organizationsApi.list().subscribe({
      next: (page) => this.organizations.set(page.items),
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }

  onCreated(): void {
    this.showCreate.set(false);
    this.load();
  }
}
