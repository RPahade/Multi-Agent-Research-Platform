import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { Page, Report, ReportQuery, ReportUpdate, ReportVersion } from '../../core/models';
import { ApiService } from '../../core/services/api.service';

/**
 * Calls for the /reports endpoints.
 *
 * Note there is no sorting: the API accepts only the filters listed below and
 * always returns newest-first. Unknown query params are silently ignored, so
 * sending `sort_by` would look like it worked while changing nothing.
 */
@Injectable({ providedIn: 'root' })
export class ReportsService {
  private readonly api = inject(ApiService);

  list(query: ReportQuery = {}): Observable<Page<Report>> {
    return this.api.getPage<Report>('/reports', {
      page: query.page,
      size: query.size,
      status: query.status,
      job_id: query.job_id,
      q: query.q,
    });
  }

  get(id: string): Observable<Report> {
    return this.api.get<Report>(`/reports/${id}`);
  }

  /**
   * Edit a report. Analyst + admin only (leadership gets 403).
   *
   * Every PATCH snapshots a new version server-side — even a status-only
   * change — so callers should refresh the version list after saving.
   */
  update(id: string, payload: ReportUpdate): Observable<Report> {
    return this.api.patch<Report>(`/reports/${id}`, payload);
  }

  versions(id: string): Observable<ReportVersion[]> {
    return this.api.get<ReportVersion[]>(`/reports/${id}/versions`);
  }
}
