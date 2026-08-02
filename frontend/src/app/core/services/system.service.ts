import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import {
  DbHealthResponse,
  EventsStatus,
  HealthResponse,
  McpStatus,
} from '../models';
import { ApiService } from './api.service';

/** The platform's own status endpoints, shown on the dashboard. */
@Injectable({ providedIn: 'root' })
export class SystemService {
  private readonly api = inject(ApiService);

  health(): Observable<HealthResponse> {
    return this.api.get<HealthResponse>('/health');
  }

  dbHealth(): Observable<DbHealthResponse> {
    return this.api.get<DbHealthResponse>('/health/db');
  }

  /** Which agent tools the MCP server is serving, and whether it is reachable. */
  mcp(): Observable<McpStatus> {
    return this.api.get<McpStatus>('/mcp/status');
  }

  /** Kafka event pipeline configuration. */
  events(): Observable<EventsStatus> {
    return this.api.get<EventsStatus>('/events/status');
  }
}
