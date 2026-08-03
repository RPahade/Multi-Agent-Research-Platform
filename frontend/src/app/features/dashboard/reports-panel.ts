import { DatePipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { debounceTime, distinctUntilChanged } from 'rxjs';

import { REPORT_STATUSES, Report, ReportStatus } from '../../core/models';
import { apiErrorMessage } from '../../core/services/api-error';
import { EmptyState } from '../../shared/components/empty-state/empty-state';
import { Paginator } from '../../shared/components/paginator/paginator';
import { StatusBadge } from '../../shared/components/status-badge/status-badge';
import { ReportsService } from '../reports/reports.service';

/** Columns the table can be sorted by. */
type SortKey = 'title' | 'status' | 'version' | 'created_at';

@Component({
  selector: 'app-reports-panel',
  imports: [ReactiveFormsModule, RouterLink, DatePipe, StatusBadge, Paginator, EmptyState],
  templateUrl: './reports-panel.html',
  styleUrl: './reports-panel.scss',
})
export class ReportsPanel implements OnInit {
  private readonly reports = inject(ReportsService);

  protected readonly statuses = REPORT_STATUSES;

  /** Filters — sent to the API, which does the filtering server-side. */
  protected readonly qControl = new FormControl('', { nonNullable: true });
  protected readonly statusControl = new FormControl<ReportStatus | ''>('', {
    nonNullable: true,
  });

  protected readonly items = signal<Report[]>([]);
  protected readonly total = signal(0);
  protected readonly page = signal(1);
  protected readonly size = signal(10);
  protected readonly pages = signal(0);
  protected readonly loading = signal(false);
  protected readonly error = signal<string | null>(null);

  /**
   * Sorting is client-side: the API has no sort parameter and always returns
   * newest-first, so this reorders the rows of the current page only.
   */
  protected readonly sortKey = signal<SortKey | null>(null);
  protected readonly sortAscending = signal(true);

  protected readonly sortedItems = computed(() => {
    const key = this.sortKey();
    const rows = this.items();
    if (!key) {
      return rows;
    }

    const direction = this.sortAscending() ? 1 : -1;
    return [...rows].sort((a, b) => compare(a[key], b[key]) * direction);
  });

  constructor() {
    // Wait for a pause in typing before hitting the API.
    this.qControl.valueChanges
      .pipe(debounceTime(300), distinctUntilChanged(), takeUntilDestroyed())
      .subscribe(() => this.reload());

    this.statusControl.valueChanges
      .pipe(takeUntilDestroyed())
      .subscribe(() => this.reload());
  }

  ngOnInit(): void {
    this.load();
  }

  /** Filter changed — go back to the first page before loading. */
  private reload(): void {
    this.page.set(1);
    this.load();
  }

  protected load(): void {
    this.loading.set(true);
    this.error.set(null);

    this.reports
      .list({
        page: this.page(),
        size: this.size(),
        q: this.qControl.value || undefined,
        status: this.statusControl.value || undefined,
      })
      .subscribe({
        next: (result) => {
          this.items.set(result.items);
          this.total.set(result.total);
          this.pages.set(result.pages);
          this.loading.set(false);
        },
        error: (err) => {
          this.error.set(apiErrorMessage(err));
          this.items.set([]);
          this.loading.set(false);
        },
      });
  }

  protected onPage(page: number): void {
    this.page.set(page);
    this.load();
  }

  protected onSize(size: number): void {
    this.size.set(size);
    this.page.set(1);
    this.load();
  }

  /** Click a header: sort by it, or flip the direction if already sorted by it. */
  protected sortBy(key: SortKey): void {
    if (this.sortKey() === key) {
      this.sortAscending.update((ascending) => !ascending);
    } else {
      this.sortKey.set(key);
      this.sortAscending.set(true);
    }
  }

  protected sortIndicator(key: SortKey): string {
    if (this.sortKey() !== key) {
      return '';
    }
    return this.sortAscending() ? ' ▲' : ' ▼';
  }
}

/** Orders strings case-insensitively and numbers numerically; nulls go last. */
function compare(a: unknown, b: unknown): number {
  if (a == null) return 1;
  if (b == null) return -1;
  if (typeof a === 'number' && typeof b === 'number') {
    return a - b;
  }
  return String(a).localeCompare(String(b), undefined, { sensitivity: 'base' });
}
