import { Component, inject, OnInit, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatTableModule } from '@angular/material/table';
import { ReferenceService } from '../../core/services/reference.service';
import { ActivityType } from '../../core/models/reference.models';
import { extractApiErrorMessage } from '../../core/services/error.util';

@Component({
  selector: 'app-activity-types-list',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatTableModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatCheckboxModule,
  ],
  templateUrl: './activity-types-list.component.html',
})
export class ActivityTypesListComponent implements OnInit {
  private readonly api = inject(ReferenceService);
  private readonly fb = inject(FormBuilder);

  readonly items = signal<ActivityType[]>([]);
  readonly errorMessage = signal<string | null>(null);
  readonly showCreate = signal(false);
  readonly displayedColumns = ['code', 'name', 'category', 'defaultUnitCode', 'status'];

  readonly form = this.fb.nonNullable.group({
    code: ['', Validators.required],
    name: ['', Validators.required],
    description: [''],
    category: ['electricity', Validators.required],
    defaultUnitCode: ['kWh', Validators.required],
    allowedUnitDimension: ['energy', Validators.required],
    expectedValueType: ['decimal'],
    dataFrequency: ['monthly'],
    requiresFacility: [true],
    requiresEquipment: [false],
    isActive: [true],
  });

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.api.listActivityTypes({ pageSize: 200 }).subscribe({
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
    const v = this.form.getRawValue();
    this.api
      .createActivityType({
        ...v,
        description: v.description || null,
      })
      .subscribe({
        next: () => {
          this.showCreate.set(false);
          this.load();
        },
        error: (err: unknown) => this.errorMessage.set(extractApiErrorMessage(err)),
      });
  }
}
