import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { AuthService } from './auth.service';

@Injectable({ providedIn: 'root' })
export class OpsApiService {
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);

  private org(suffix: string): string {
    const id = this.auth.requireOrganizationId();
    return `${environment.apiUrl}${environment.apiV1Prefix}/organizations/${id}${suffix}`;
  }

  private root(suffix: string): string {
    return `${environment.apiUrl}${environment.apiV1Prefix}${suffix}`;
  }

  listAgents() {
    return this.http.get<any[]>(this.root('/agents'));
  }
  getAgent(code: string) {
    return this.http.get<any>(this.root(`/agents/${code}`));
  }
  executeAgent(code: string, prompt: string) {
    return this.http.post<any>(this.org(`/agents/${code}/execute`), { prompt });
  }
  listExecutions() {
    return this.http.get<any[]>(this.org('/agent-executions'));
  }
  getExecution(id: string) {
    return this.http.get<any>(this.org(`/agent-executions/${id}`));
  }
  listActionRequests() {
    return this.http.get<any[]>(this.org('/agent-action-requests'));
  }
  approveAction(id: string, comment?: string) {
    return this.http.post<any>(this.org(`/agent-action-requests/${id}/approve`), { comment });
  }
  rejectAction(id: string, comment?: string) {
    return this.http.post<any>(this.org(`/agent-action-requests/${id}/reject`), { comment });
  }
  executeAction(id: string) {
    return this.http.post<any>(this.org(`/agent-action-requests/${id}/execute`), {});
  }

  listAutomationRules() {
    return this.http.get<any[]>(this.org('/automation-rules'));
  }
  automationTemplates() {
    return this.http.get<any[]>(this.org('/automation-rules/templates'));
  }
  createAutomation(body: Record<string, unknown>) {
    return this.http.post<any>(this.org('/automation-rules'), body);
  }
  getAutomation(id: string) {
    return this.http.get<any>(this.org(`/automation-rules/${id}`));
  }
  activateAutomation(id: string) {
    return this.http.post<any>(this.org(`/automation-rules/${id}/activate`), {});
  }
  pauseAutomation(id: string) {
    return this.http.post<any>(this.org(`/automation-rules/${id}/pause`), {});
  }
  runAutomation(id: string) {
    return this.http.post<any>(this.org(`/automation-rules/${id}/run`), {});
  }
  automationExecutions(id: string) {
    return this.http.get<any[]>(this.org(`/automation-rules/${id}/executions`));
  }

  listJobs() {
    return this.http.get<any[]>(this.org('/job-executions'));
  }

  listAnomalies() {
    return this.http.get<any[]>(this.org('/anomalies'));
  }
  getAnomaly(id: string) {
    return this.http.get<any>(this.org(`/anomalies/${id}`));
  }
  acknowledgeAnomaly(id: string) {
    return this.http.post<any>(this.org(`/anomalies/${id}/acknowledge`), {});
  }
  resolveAnomaly(id: string, notes?: string) {
    return this.http.post<any>(this.org(`/anomalies/${id}/resolve`), { notes });
  }
  dismissAnomaly(id: string, reason: string) {
    return this.http.post<any>(this.org(`/anomalies/${id}/dismiss`), { reason });
  }
  listAnomalyRules() {
    return this.http.get<any[]>(this.org('/anomaly-rules'));
  }
  runAnomalyRule(id: string) {
    return this.http.post<any>(this.org(`/anomaly-rules/${id}/run`), {});
  }

  listForecasts() {
    return this.http.get<any[]>(this.org('/forecast-definitions'));
  }
  createForecast(body: Record<string, unknown>) {
    return this.http.post<any>(this.org('/forecast-definitions'), body);
  }
  getForecast(id: string) {
    return this.http.get<any>(this.org(`/forecast-definitions/${id}`));
  }
  runForecast(id: string) {
    return this.http.post<any>(this.org(`/forecast-definitions/${id}/run`), {});
  }
  forecastRuns(id: string) {
    return this.http.get<any[]>(this.org(`/forecast-definitions/${id}/runs`));
  }
  forecastPoints(runId: string) {
    return this.http.get<any[]>(this.org(`/forecast-runs/${runId}/points`));
  }
  targetTrajectory() {
    return this.http.get<any[]>(this.org('/forecasts/target-trajectory'));
  }

  dqIssues() {
    return this.http.get<any[]>(this.org('/data-quality/issues'));
  }
  dqIssue(id: string) {
    return this.http.get<any>(this.org(`/data-quality/issues/${id}`));
  }
  dqScan() {
    return this.http.post<any>(this.org('/data-quality/scan'), {});
  }
  dqResolve(id: string, notes?: string) {
    return this.http.post<any>(this.org(`/data-quality/issues/${id}/resolve`), { notes });
  }

  listAlerts() {
    return this.http.get<any[]>(this.org('/alerts'));
  }
  getAlert(id: string) {
    return this.http.get<any>(this.org(`/alerts/${id}`));
  }
  ackAlert(id: string) {
    return this.http.post<any>(this.org(`/alerts/${id}/acknowledge`), {});
  }
  resolveAlert(id: string, notes?: string) {
    return this.http.post<any>(this.org(`/alerts/${id}/resolve`), { notes });
  }

  notifications() {
    return this.http.get<any[]>(this.root('/notifications'));
  }
  unreadCount() {
    return this.http.get<{ count: number }>(this.root('/notifications/unread-count'));
  }
  markRead(id: string) {
    return this.http.post<any>(this.root(`/notifications/${id}/read`), {});
  }
  markAllRead() {
    return this.http.post<any>(this.root('/notifications/read-all'), {});
  }
  getPrefs() {
    return this.http.get<any>(this.org('/notification-preferences'));
  }
  updatePrefs(body: Record<string, unknown>) {
    return this.http.patch<any>(this.org('/notification-preferences'), body);
  }

  scheduledReports() {
    return this.http.get<any[]>(this.org('/scheduled-reports'));
  }
  createScheduledReport(body: Record<string, unknown>) {
    return this.http.post<any>(this.org('/scheduled-reports'), body);
  }
  getScheduledReport(id: string) {
    return this.http.get<any>(this.org(`/scheduled-reports/${id}`));
  }
  activateScheduled(id: string) {
    return this.http.post<any>(this.org(`/scheduled-reports/${id}/activate`), {});
  }
  pauseScheduled(id: string) {
    return this.http.post<any>(this.org(`/scheduled-reports/${id}/pause`), {});
  }
  runScheduled(id: string) {
    return this.http.post<any>(this.org(`/scheduled-reports/${id}/run`), {});
  }
  generatedReports() {
    return this.http.get<any[]>(this.org('/generated-reports'));
  }
  getGenerated(id: string) {
    return this.http.get<any>(this.org(`/generated-reports/${id}`));
  }
  downloadGenerated(id: string): Observable<Blob> {
    return this.http.get(this.org(`/generated-reports/${id}/download`), {
      responseType: 'blob',
    });
  }

  supplierMonitoring() {
    return this.http.get<any[]>(this.org('/supplier-monitoring'));
  }
  supplierProfile(id: string) {
    return this.http.get<any>(this.org(`/supplier-monitoring/${id}`));
  }
  assessSupplier(id: string) {
    return this.http.post<any>(this.org(`/supplier-monitoring/${id}/assess`), {});
  }
  supplierAssessments(id: string) {
    return this.http.get<any[]>(this.org(`/supplier-monitoring/${id}/assessments`));
  }

  regulatoryDocs() {
    return this.http.get<any[]>(this.root('/regulatory-documents'));
  }
  regulatoryDoc(id: string) {
    return this.http.get<any>(this.root(`/regulatory-documents/${id}`));
  }
  regulatoryAssessments() {
    return this.http.get<any[]>(this.org('/regulatory-assessments'));
  }
  reviewAssessment(id: string, applicabilityStatus: string, notes?: string) {
    return this.http.post<any>(this.org(`/regulatory-assessments/${id}/review`), {
      applicabilityStatus,
      notes,
    });
  }
  scanRegulatory() {
    return this.http.post<any>(this.org('/regulatory-assessments/scan'), {});
  }

  systemHealth() {
    return this.http.get<any>(this.root('/system/health'));
  }
  systemVersion() {
    return this.http.get<any>(this.root('/system/version'));
  }
}
