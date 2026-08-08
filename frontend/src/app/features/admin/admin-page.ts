import { DatePipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { forkJoin, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';

import {
  DbHealthResponse,
  EventsStatus,
  HealthResponse,
  Job,
  JobStatus,
  JobType,
  McpStatus,
} from '../../core/models';
import { ApiService } from '../../core/services/api.service';
import { apiErrorMessage } from '../../core/services/api-error';
import { SystemService } from '../../core/services/system.service';
import { EmptyState } from '../../shared/components/empty-state/empty-state';
import { StatusBadge } from '../../shared/components/status-badge/status-badge';
import { JobsService } from '../jobs/jobs.service';

const JOB_STATUSES: JobStatus[] = ['pending', 'running', 'succeeded', 'failed', 'cancelled'];
const JOB_TYPES: JobType[] = ['research', 'ingestion', 'export'];

/**
 * Admin monitoring.
 *
 * There is no metrics endpoint, so every number here is a real `total` from a
 * `?size=1` page — the cheapest way to ask "how many?" with the API available.
 * That is roughly a dozen small parallel requests; a `/stats` endpoint would
 * collapse them (BACKEND_CHANGES_REQUIRED_FOR_FE.md §9).
 */
@Component({
  selector: 'app-admin-page',
  imports: [DatePipe, RouterLink, StatusBadge, EmptyState],
  templateUrl: './admin-page.html',
  styleUrl: './admin-page.scss',
})
export class AdminPage implements OnInit {
  private readonly api = inject(ApiService);
  private readonly jobs = inject(JobsService);
  private readonly system = inject(SystemService);

  protected readonly jobStatuses = JOB_STATUSES;
  protected readonly jobTypes = JOB_TYPES;

  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);

  protected readonly byStatus = signal<Record<string, number>>({});
  protected readonly byType = signal<Record<string, number>>({});
  protected readonly totals = signal<Record<string, number>>({});
  protected readonly recentFailures = signal<Job[]>([]);

  protected readonly health = signal<HealthResponse | null>(null);
  protected readonly dbHealth = signal<DbHealthResponse | null>(null);
  protected readonly mcp = signal<McpStatus | null>(null);
  protected readonly events = signal<EventsStatus | null>(null);

  /** Jobs that finished one way or another — the denominator for error rate. */
  protected readonly terminalJobs = computed(() => {
    const counts = this.byStatus();
    return (counts['succeeded'] ?? 0) + (counts['failed'] ?? 0) + (counts['cancelled'] ?? 0);
  });

  protected readonly errorRate = computed(() => {
    const total = this.terminalJobs();
    if (!total) {
      return null;
    }
    return ((this.byStatus()['failed'] ?? 0) / total) * 100;
  });

  /** Anything unhealthy, so the page can lead with problems rather than bury them. */
  protected readonly problems = computed(() => {
    const list: string[] = [];
    const db = this.dbHealth();
    const mcp = this.mcp();

    if (db && db.status !== 'ok') {
      list.push(`Database: ${db.database}`);
    }
    if (mcp?.enabled && !mcp.reachable) {
      list.push('MCP tool server is configured but unreachable — agent tools fall back to local.');
    }
    const rate = this.errorRate();
    if (rate !== null && rate >= 20) {
      list.push(`${rate.toFixed(0)}% of finished jobs failed.`);
    }
    return list;
  });

  ngOnInit(): void {
    this.load();
  }

  protected load(): void {
    this.loading.set(true);
    this.error.set(null);

    // One `?size=1` request per bucket; `total` is the count we want.
    const count = (path: string, params: Record<string, string | number>) =>
      this.api
        .getPage<unknown>(path, { ...params, size: 1 })
        .pipe(
          map((page) => page.total),
          catchError(() => of(0)),
        );

    forkJoin({
      statuses: forkJoin(
        Object.fromEntries(
          JOB_STATUSES.map((status) => [status, count('/jobs', { status })]),
        ) as Record<string, ReturnType<typeof count>>,
      ),
      types: forkJoin(
        Object.fromEntries(
          JOB_TYPES.map((type) => [type, count('/jobs', { type })]),
        ) as Record<string, ReturnType<typeof count>>,
      ),
      totals: forkJoin({
        jobs: count('/jobs', {}),
        reports: count('/reports', {}),
        documents: count('/documents', {}),
        users: count('/users', {}),
        agents: count('/agents', {}),
        tools: count('/tools', {}),
      }),
    }).subscribe({
      next: (result) => {
        this.byStatus.set(result.statuses);
        this.byType.set(result.types);
        this.totals.set(result.totals);
        this.loading.set(false);
      },
      error: (err) => {
        this.error.set(apiErrorMessage(err));
        this.loading.set(false);
      },
    });

    this.jobs.list({ page: 1, size: 5, status: 'failed' }).subscribe({
      next: (page) => this.recentFailures.set(page.items),
      error: () => this.recentFailures.set([]),
    });

    this.system.health().subscribe({ next: (h) => this.health.set(h), error: () => this.health.set(null) });
    this.system.dbHealth().subscribe({ next: (h) => this.dbHealth.set(h), error: () => this.dbHealth.set(null) });
    this.system.mcp().subscribe({ next: (s) => this.mcp.set(s), error: () => this.mcp.set(null) });
    this.system.events().subscribe({ next: (s) => this.events.set(s), error: () => this.events.set(null) });
  }

  protected statusCount(status: string): number {
    return this.byStatus()[status] ?? 0;
  }

  protected typeCount(type: string): number {
    return this.byType()[type] ?? 0;
  }

  protected total(key: string): number {
    return this.totals()[key] ?? 0;
  }

  /** Percentage of all jobs in a given status, for the bar widths. */
  protected share(status: string): number {
    const all = this.total('jobs');
    return all ? (this.statusCount(status) / all) * 100 : 0;
  }
}
