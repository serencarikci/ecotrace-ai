import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { of } from 'rxjs';
import { catchError, finalize, switchMap } from 'rxjs/operators';
import { AuthService } from '../../core/services/auth.service';
import { extractApiErrorMessage } from '../../core/services/error.util';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './login.component.html',
  styleUrl: './login.component.scss',
})
export class LoginComponent {
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  readonly loading = signal(false);
  readonly errorMessage = signal<string | null>(null);

  readonly form = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(8)]],
  });

  submit(): void {
    this.errorMessage.set(null);
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.loading.set(true);
    const { email, password } = this.form.getRawValue();
    this.auth
      .login(email, password)
      .pipe(
        switchMap(() => this.auth.loadMyOrganizations().pipe(catchError(() => of([])))),
        finalize(() => this.loading.set(false)),
      )
      .subscribe({
        next: () => {
          void this.goToDashboard();
        },
        error: (err: unknown) => {
          this.errorMessage.set(extractApiErrorMessage(err, 'Invalid email or password.'));
        },
      });
  }

  private async goToDashboard(): Promise<void> {
    try {
      const ok = await this.router.navigateByUrl('/app/dashboard', { replaceUrl: true });
      if (!ok && !this.router.url.startsWith('/app')) {
        window.location.assign('/app/dashboard');
      }
    } catch {
      window.location.assign('/app/dashboard');
    }
  }
}
