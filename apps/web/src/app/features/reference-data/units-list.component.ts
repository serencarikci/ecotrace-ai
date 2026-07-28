import { Component, inject, OnInit, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatTableModule } from '@angular/material/table';
import { ReferenceService } from '../../core/services/reference.service';
import { Unit } from '../../core/models/reference.models';
import { extractApiErrorMessage } from '../../core/services/error.util';

@Component({
  selector: 'app-units-list',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatTableModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatCheckboxModule,
  ],
  templateUrl: './units-list.component.html',
})
export class UnitsListComponent implements OnInit {
  private readonly api = inject(ReferenceService);
  private readonly fb = inject(FormBuilder);

  readonly items = signal<Unit[]>([]);
  readonly errorMessage = signal<string | null>(null);
  readonly showCreate = signal(false);
  readonly displayedColumns = ['code', 'name', 'symbol', 'dimension', 'factor', 'status'];

  readonly form = this.fb.nonNullable.group({
    code: ['', Validators.required],
    name: ['', Validators.required],
    symbol: ['', Validators.required],
    dimension: ['energy', Validators.required],
    conversionFactorToBase: [1, [Validators.required, Validators.min(0.000000000001)]],
    baseUnitCode: ['', Validators.required],
    decimalPrecision: [4, Validators.required],
    isActive: [true],
  });

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.api.listUnits({ pageSize: 200 }).subscribe({
      next: (page) => this.items.set(page.items),
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }

  create(): void {
    this.errorMessage.set(null);
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.api.createUnit(this.form.getRawValue()).subscribe({
      next: () => {
        this.showCreate.set(false);
        this.form.reset({
          code: '',
          name: '',
          symbol: '',
          dimension: 'energy',
          conversionFactorToBase: 1,
          baseUnitCode: '',
          decimalPrecision: 4,
          isActive: true,
        });
        this.load();
      },
      error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }
}
