import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { Job, JobCreate, JobQuery, JobStep, Page } from '../../core/models';
import { ApiService } from '../../core/services/api.service';

/** Calls for the /jobs endpoints. Always returns newest-first; no sorting. */
@Injectable({ providedIn: 'root' })
export class JobsService {
  private readonly api = inject(ApiService);

  /**
   * Start a job. Analyst + admin only.
   *
   * The Idempotency-Key makes a repeated submit return the job that was already
   * created instead of starting a second one — so a double-click is harmless.
   */
  create(payload: JobCreate, idempotencyKey: string): Observable<Job> {
    return this.api.post<Job>('/jobs', payload, {
      'Idempotency-Key': idempotencyKey,
    });
  }

  list(query: JobQuery = {}): Observable<Page<Job>> {
    return this.api.getPage<Job>('/jobs', {
      page: query.page,
      size: query.size,
      status: query.status,
      type: query.type,
    });
  }

  get(id: string): Observable<Job> {
    return this.api.get<Job>(`/jobs/${id}`);
  }

  /** The per-tool trace of what the agent actually did. */
  steps(id: string): Observable<JobStep[]> {
    return this.api.get<JobStep[]>(`/jobs/${id}/steps`);
  }
}
