import { DatePipe } from '@angular/common';
import { Component, OnInit, computed, inject, input, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Report, ReportContent, ReportVersion } from '../../core/models';
import { apiErrorMessage } from '../../core/services/api-error';
import { StatusBadge } from '../../shared/components/status-badge/status-badge';
import { ReportChat } from './report-chat';
import { ReportsService } from './reports.service';

@Component({
  selector: 'app-report-detail-page',
  imports: [DatePipe, RouterLink, StatusBadge, ReportChat],
  templateUrl: './report-detail-page.html',
  styleUrl: './report-detail-page.scss',
})
export class ReportDetailPage implements OnInit {
  /** Route parameter, bound by withComponentInputBinding(). */
  readonly id = input.required<string>();

  private readonly reports = inject(ReportsService);

  protected readonly report = signal<Report | null>(null);
  protected readonly versions = signal<ReportVersion[]>([]);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);

  /** When set, the page is showing an older snapshot instead of the current one. */
  protected readonly viewingVersion = signal<ReportVersion | null>(null);

  /** Content of whichever version is on screen. */
  protected readonly content = computed<ReportContent>(() => {
    const older = this.viewingVersion();
    return (older ? older.content : this.report()?.content) ?? {};
  });

  protected readonly shownTitle = computed(
    () => this.viewingVersion()?.title ?? this.report()?.title ?? '',
  );

  protected readonly shownSummary = computed(
    () => this.viewingVersion()?.summary ?? this.report()?.summary ?? null,
  );

  protected readonly sections = computed(() => this.content().sections ?? []);
  protected readonly citations = computed(() => this.content().citations ?? []);
  protected readonly warnings = computed(() => this.content().warnings ?? []);

  /**
   * `generated_by` is free-form JSON, so read it defensively — every field here
   * is genuinely optional and must stay typed as nullable.
   */
  protected readonly provenance = computed(() => {
    const raw = this.content().generated_by as Record<string, unknown> | undefined;
    if (!raw) {
      return null;
    }
    const usage = raw['usage'] as Record<string, unknown> | undefined;
    return {
      provider: asString(raw['provider']),
      model: asString(raw['model']),
      totalTokens: asNumber(usage?.['totalTokenCount']),
    };
  });

  /** The compliance tool records whether it ran and what it removed. */
  protected readonly compliance = computed(
    () => this.content()['compliance'] as { scanned?: boolean; pii_redacted?: number } | undefined,
  );

  ngOnInit(): void {
    this.reports.get(this.id()).subscribe({
      next: (report) => {
        this.report.set(report);
        this.loading.set(false);
      },
      error: (err) => {
        this.error.set(apiErrorMessage(err));
        this.loading.set(false);
      },
    });

    // Unpaginated by design — the endpoint returns the full history.
    this.reports.versions(this.id()).subscribe({
      next: (versions) => this.versions.set([...versions].sort((a, b) => b.version - a.version)),
      error: () => this.versions.set([]),
    });
  }

  protected showVersion(version: ReportVersion): void {
    this.viewingVersion.set(version);
  }

  protected showCurrent(): void {
    this.viewingVersion.set(null);
  }
}

function asString(value: unknown): string | null {
  return typeof value === 'string' && value ? value : null;
}

function asNumber(value: unknown): number | null {
  return typeof value === 'number' ? value : null;
}
