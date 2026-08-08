import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { Page, Tool, ToolCreate, ToolQuery, ToolUpdate } from '../../core/models';
import { ApiService } from '../../core/services/api.service';

/**
 * Calls for the /tools endpoints. Reads are open to every role; writes are
 * admin-only and the backend answers 403 for anyone else.
 *
 * ⚠️ These rows are a **catalogue**, not a control plane. The agent pipeline is
 * hard-coded in the backend (`build_pipeline()` takes no arguments) and never
 * reads this table, so `enabled` and `config` here do not change what a job
 * runs. See BACKEND_CHANGES_REQUIRED_FOR_FE.md §2.
 */
@Injectable({ providedIn: 'root' })
export class ToolsService {
  private readonly api = inject(ApiService);

  list(query: ToolQuery = {}): Observable<Page<Tool>> {
    return this.api.getPage<Tool>('/tools', {
      page: query.page,
      size: query.size,
      category: query.category,
      enabled: query.enabled,
      q: query.q,
    });
  }

  get(id: string): Observable<Tool> {
    return this.api.get<Tool>(`/tools/${id}`);
  }

  create(payload: ToolCreate): Observable<Tool> {
    return this.api.post<Tool>('/tools', payload);
  }

  /** `key` is immutable once created, so it is not part of ToolUpdate. */
  update(id: string, payload: ToolUpdate): Observable<Tool> {
    return this.api.patch<Tool>(`/tools/${id}`, payload);
  }

  /** Soft delete on the backend. */
  remove(id: string): Observable<void> {
    return this.api.delete<void>(`/tools/${id}`);
  }
}
