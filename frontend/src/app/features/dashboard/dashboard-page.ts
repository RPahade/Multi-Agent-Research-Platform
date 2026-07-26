import { Component, OnInit, inject, signal } from '@angular/core';

import { apiErrorMessage } from '../../core/services/api-error';
import { ApiService } from '../../core/services/api.service';
import { DbHealthResponse, HealthResponse } from '../../core/models';

/**
 * Landing page.
 *
 * For this milestone it exists to prove the whole chain works:
 * component -> ApiService -> dev-server proxy -> FastAPI backend.
 * The real dashboard (counts, recent activity) comes later.
 */
@Component({
  selector: 'app-dashboard-page',
  templateUrl: './dashboard-page.html',
  styleUrl: './dashboard-page.scss',
})
export class DashboardPage implements OnInit {
  private readonly api = inject(ApiService);

  readonly health = signal<HealthResponse | null>(null);
  readonly dbHealth = signal<DbHealthResponse | null>(null);
  readonly error = signal<string | null>(null);
  readonly loading = signal(true);

  ngOnInit(): void {
    this.checkBackend();
  }

  checkBackend(): void {
    this.loading.set(true);
    this.error.set(null);

    this.api.get<HealthResponse>('/health').subscribe({
      next: (result) => {
        this.health.set(result);
        this.loading.set(false);
      },
      error: (err) => {
        this.error.set(apiErrorMessage(err));
        this.loading.set(false);
      },
    });

    // Reported separately: the API can be up while the database is not.
    this.api.get<DbHealthResponse>('/health/db').subscribe({
      next: (result) => this.dbHealth.set(result),
      error: () => this.dbHealth.set(null),
    });
  }
}
