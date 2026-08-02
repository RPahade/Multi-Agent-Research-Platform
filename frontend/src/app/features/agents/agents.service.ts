import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { Agent, AgentQuery, Page } from '../../core/models';
import { ApiService } from '../../core/services/api.service';

/** Calls for the /agents endpoints. */
@Injectable({ providedIn: 'root' })
export class AgentsService {
  private readonly api = inject(ApiService);

  list(query: AgentQuery = {}): Observable<Page<Agent>> {
    return this.api.getPage<Agent>('/agents', {
      page: query.page,
      size: query.size,
      is_active: query.is_active,
      q: query.q,
    });
  }

  get(id: string): Observable<Agent> {
    return this.api.get<Agent>(`/agents/${id}`);
  }
}
