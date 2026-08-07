import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { AuthService } from '../../core/services/auth.service';
import { CbamApiService, CbamModuleStatus } from './cbam-api.service';

@Component({
  selector: 'app-cbam-shell',
  standalone: true,
  templateUrl: './cbam-shell.component.html',
  styleUrl: './cbam-shell.component.scss',
})
export class CbamShellComponent implements OnInit {
  private readonly auth = inject(AuthService);
  private readonly cbamApi = inject(CbamApiService);

  readonly title = 'SKDM';
  readonly loading = signal(true);
  readonly error = signal<string | null>(null);
  readonly status = signal<CbamModuleStatus | null>(null);

  readonly organizationName = computed(() => {
    const id = this.auth.currentOrganizationId();
    return (
      this.auth.organizations().find((o) => o.organizationId === id)?.organizationName ??
      'Organization'
    );
  });

  ngOnInit(): void {
    this.cbamApi.getModuleStatus().subscribe({
      next: (body) => {
        this.status.set(body);
        this.loading.set(false);
      },
      error: () => {
        this.error.set(
          'SKDM modül durumu alınamadı. Oturum ve organizasyon erişiminizi kontrol edin.',
        );
        this.loading.set(false);
      },
    });
  }
}
