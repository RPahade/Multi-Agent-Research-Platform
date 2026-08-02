import { Component, OnInit, inject, signal } from '@angular/core';
import { forkJoin, of } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { DbHealthResponse, EventsStatus, HealthResponse } from '../../core/models';
import { SystemService } from '../../core/services/system.service';
import { AgentsService } from '../agents/agents.service';
import { DocumentsService } from '../documents/documents.service';
import { JobsService } from '../jobs/jobs.service';
import { ReportsService } from '../reports/reports.service';
import { ActivityPanel } from './activity-panel';
import { AgentsPanel } from './agents-panel';
import { ReportsPanel } from './reports-panel';

interface Tile {
  label: string;
  value: number | string;
  hint?: string;
}

/**
 * Landing page: headline counts, platform status, the reports table, agent
 * status and recent activity. Read-only, and available to every role — all
 * three can read reports, jobs and agents.
 */
@Component({
  selector: 'app-dashboard-page',
  imports: [ReportsPanel, AgentsPanel, ActivityPanel],
  templateUrl: './dashboard-page.html',
  styleUrl: './dashboard-page.scss',
})
export class DashboardPage implements OnInit {
  private readonly system = inject(SystemService);
  private readonly reports = inject(ReportsService);
  private readonly jobs = inject(JobsService);
  private readonly documents = inject(DocumentsService);
  private readonly agents = inject(AgentsService);

  protected readonly tiles = signal<Tile[]>([]);
  protected readonly tilesLoading = signal(true);

  protected readonly health = signal<HealthResponse | null>(null);
  protected readonly dbHealth = signal<DbHealthResponse | null>(null);
  protected readonly events = signal<EventsStatus | null>(null);

  ngOnInit(): void {
    this.loadTiles();
    this.loadStatus();
  }

  /**
   * Each count comes from the `total` of a one-row page — the cheapest way to
   * ask "how many are there?" with the endpoints available.
   */
  private loadTiles(): void {
    this.tilesLoading.set(true);

    forkJoin({
      reports: this.reports.list({ page: 1, size: 1 }),
      jobs: this.jobs.list({ page: 1, size: 1 }),
      running: this.jobs.list({ page: 1, size: 1, status: 'running' }),
      failed: this.jobs.list({ page: 1, size: 1, status: 'failed' }),
      documents: this.documents.list({ page: 1, size: 1 }),
      agents: this.agents.list({ page: 1, size: 1, is_active: true }),
    })
      .pipe(catchError(() => of(null)))
      .subscribe((result) => {
        if (result) {
          this.tiles.set([
            { label: 'Reports', value: result.reports.total },
            {
              label: 'Jobs',
              value: result.jobs.total,
              hint: `${result.running.total} running · ${result.failed.total} failed`,
            },
            { label: 'Documents', value: result.documents.total },
            { label: 'Active agents', value: result.agents.total },
          ]);
        }
        this.tilesLoading.set(false);
      });
  }

  private loadStatus(): void {
    this.system.health().subscribe({
      next: (value) => this.health.set(value),
      error: () => this.health.set(null),
    });
    this.system.dbHealth().subscribe({
      next: (value) => this.dbHealth.set(value),
      error: () => this.dbHealth.set(null),
    });
    this.system.events().subscribe({
      next: (value) => this.events.set(value),
      error: () => this.events.set(null),
    });
  }
}
