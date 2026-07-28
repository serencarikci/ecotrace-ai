import {
  AfterViewInit,
  Component,
  ElementRef,
  Input,
  OnChanges,
  OnDestroy,
  SimpleChanges,
  ViewChild,
} from '@angular/core';
import * as echarts from 'echarts/core';
import { BarChart, LineChart, PieChart } from 'echarts/charts';
import {
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import type { EChartsCoreOption } from 'echarts/core';

echarts.use([
  BarChart,
  LineChart,
  PieChart,
  GridComponent,
  LegendComponent,
  TooltipComponent,
  CanvasRenderer,
]);

@Component({
  selector: 'app-chart',
  standalone: true,
  template: `<div #host class="chart-host" [style.height]="height"></div>`,
  styles: `
    .chart-host {
      width: 100%;
      min-height: 240px;
    }
  `,
})
export class ChartComponent implements AfterViewInit, OnChanges, OnDestroy {
  @ViewChild('host', { static: true }) host!: ElementRef<HTMLDivElement>;
  @Input() option: EChartsCoreOption | null = null;
  @Input() height = '280px';

  private chart: echarts.ECharts | null = null;

  ngAfterViewInit(): void {
    this.chart = echarts.init(this.host.nativeElement);
    if (this.option) {
      this.chart.setOption(this.option);
    }
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['option'] && this.chart && this.option) {
      this.chart.setOption(this.option, true);
    }
  }

  ngOnDestroy(): void {
    this.chart?.dispose();
  }
}
