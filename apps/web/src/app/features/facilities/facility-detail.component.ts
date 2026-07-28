import { Component, inject, OnInit, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { forkJoin } from 'rxjs';
import { FacilityService } from '../../core/services/facility.service';
import { ProductionLineService } from '../../core/services/production-line.service';
import { EquipmentService } from '../../core/services/equipment.service';
import { DataSourceService } from '../../core/services/data-source.service';
import { ActivityRecordService } from '../../core/services/activity-record.service';
import { AuthService } from '../../core/services/auth.service';
import { Facility } from '../../core/models/facility.models';
import { ActivityRecord } from '../../core/models/activity-record.models';
import { extractApiErrorMessage } from '../../core/services/error.util';
import { canManageStructure } from '../../core/services/roles.util';

@Component({
  selector: 'app-facility-detail',
  standalone: true,
  imports: [RouterLink, MatButtonModule],
  templateUrl: './facility-detail.component.html',
  styleUrl: './facility-detail.component.scss',
})
export class FacilityDetailComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly facilities = inject(FacilityService);
  private readonly lines = inject(ProductionLineService);
  private readonly equipment = inject(EquipmentService);
  private readonly dataSources = inject(DataSourceService);
  private readonly activities = inject(ActivityRecordService);
  private readonly auth = inject(AuthService);

  readonly facility = signal<Facility | null>(null);
  readonly lineCount = signal(0);
  readonly equipmentCount = signal(0);
  readonly dataSourceCount = signal(0);
  readonly recentActivities = signal<ActivityRecord[]>([]);
  readonly errorMessage = signal<string | null>(null);
  readonly loading = signal(true);
  readonly canManage = canManageStructure(this.auth.currentRoles());

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (!id) {
      this.errorMessage.set('Facility not found.');
      this.loading.set(false);
      return;
    }
    forkJoin({
      facility: this.facilities.get(id),
      lines: this.lines.listByFacility(id, 1, 1),
      equipment: this.equipment.list({ facilityId: id, page: 1, pageSize: 1 }),
      dataSources: this.dataSources.list({ facilityId: id, page: 1, pageSize: 1 }),
      activities: this.activities.list({ facilityId: id, page: 1, pageSize: 5 }),
    }).subscribe({
      next: (result) => {
        this.facility.set(result.facility);
        this.lineCount.set(result.lines.totalItems);
        this.equipmentCount.set(result.equipment.totalItems);
        this.dataSourceCount.set(result.dataSources.totalItems);
        this.recentActivities.set(result.activities.items);
        this.loading.set(false);
      },
      error: (err: unknown) => {
        this.errorMessage.set(extractApiErrorMessage(err));
        this.loading.set(false);
      },
    });
  }
}
