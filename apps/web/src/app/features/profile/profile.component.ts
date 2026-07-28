import { Component, inject, OnInit, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { AuthService } from '../../core/services/auth.service';
import { MeResponse } from '../../core/models/api.models';

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [DatePipe],
  template: `
    <section class="page">
      <h1 class="page-title">Profile</h1>
      <p class="page-subtitle">Your EcoTrace identity and assigned platform roles.</p>

      @if (user(); as me) {
        <div class="surface-card profile">
          <div>
            <span class="label">Full name</span>
            <strong>{{ me.fullName }}</strong>
          </div>
          <div>
            <span class="label">Email</span>
            <strong>{{ me.email }}</strong>
          </div>
          <div>
            <span class="label">Roles</span>
            <strong>{{ me.roles.join(', ') }}</strong>
          </div>
          <div>
            <span class="label">Last login</span>
            <strong>{{ me.lastLoginAt ? (me.lastLoginAt | date: 'medium') : '—' }}</strong>
          </div>
        </div>
      }
    </section>
  `,
  styles: `
    .profile {
      display: grid;
      gap: 1rem;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    }
    .label {
      display: block;
      color: var(--et-muted);
      font-size: 0.8rem;
      margin-bottom: 0.25rem;
    }
  `,
})
export class ProfileComponent implements OnInit {
  private readonly auth = inject(AuthService);
  readonly user = signal<MeResponse | null>(this.auth.currentUser());

  ngOnInit(): void {
    this.auth.loadMe().subscribe({
      next: (me) => this.user.set(me),
      error: () => this.user.set(this.auth.currentUser()),
    });
  }
}
