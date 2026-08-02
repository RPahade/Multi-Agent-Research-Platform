import { DatePipe } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule } from '@angular/forms';

import { Job, JobStatus, JobStep, JobType } from '../../core/models';
import { apiErrorMessage } from '../../core/services/api-error';
import { EmptyState } from '../../shared/components/empty-state/empty-state';
import { StatusBadge } from '../../shared/components/status-badge/status-badge';
import { JobsService } from '../jobs/jobs.service';

const JOB_STATUSES: JobStatus[] = [
  'pending',
  'running',
  'succeeded',
  'failed',
  'cancelled',
];
const JOB_TYPES: JobType[] = ['research', 'ingestion', 'export'];

/**
 * Recent activity — the closest thing the platform has to a log.
 *
 * There is no logs endpoint, but every piece of work runs as a job, so the job
 * feed is the real execution record. Expanding a row loads that job's per-tool
 * trace (GET /jobs/{id}/steps), which is what the agent actually did.
 */
@Component({
  selector: 'app-activity-panel',
  imports: [ReactiveFormsModule, DatePipe, StatusBadge, EmptyState],
  templateUrl: './activity-panel.html',
  styleUrl: './activity-panel.scss',
})
export class ActivityPanel implements OnInit {
  private readonly jobs = inject(JobsService);

  protected readonly jobStatuses = JOB_STATUSES;
  protected readonly jobTypes = JOB_TYPES;

  protected readonly statusControl = new FormControl<JobStatus | ''>('', {
    nonNullable: true,
  });
  protected readonly typeControl = new FormControl<JobType | ''>('', {
    nonNullable: true,
  });

  protected readonly items = signal<Job[]>([]);
  protected readonly loading = signal(false);
  protected readonly error = signal<string | null>(null);

  /** Which job's trace is open, and the steps loaded so far (cached by job id). */
  protected readonly expandedId = signal<string | null>(null);
  protected readonly steps = signal<Record<string, JobStep[]>>({});
  protected readonly stepsLoading = signal(false);

  constructor() {
    this.statusControl.valueChanges.pipe(takeUntilDestroyed()).subscribe(() => this.load());
    this.typeControl.valueChanges.pipe(takeUntilDestroyed()).subscribe(() => this.load());
  }

  ngOnInit(): void {
    this.load();
  }

  protected load(): void {
    this.loading.set(true);
    this.error.set(null);
    this.expandedId.set(null);

    this.jobs
      .list({
        page: 1,
        size: 8,
        status: this.statusControl.value || undefined,
        type: this.typeControl.value || undefined,
      })
      .subscribe({
        next: (result) => {
          this.items.set(result.items);
          this.loading.set(false);
        },
        error: (err) => {
          this.error.set(apiErrorMessage(err));
          this.items.set([]);
          this.loading.set(false);
        },
      });
  }

  /** Open a job's trace, fetching the steps the first time it is opened. */
  protected toggle(job: Job): void {
    if (this.expandedId() === job.id) {
      this.expandedId.set(null);
      return;
    }

    this.expandedId.set(job.id);

    if (this.steps()[job.id]) {
      return;
    }

    this.stepsLoading.set(true);
    this.jobs.steps(job.id).subscribe({
      next: (steps) => {
        this.steps.update((cache) => ({ ...cache, [job.id]: steps }));
        this.stepsLoading.set(false);
      },
      error: () => {
        this.steps.update((cache) => ({ ...cache, [job.id]: [] }));
        this.stepsLoading.set(false);
      },
    });
  }

  protected stepsFor(jobId: string): JobStep[] {
    return this.steps()[jobId] ?? [];
  }

  /** Short label for what a job was asked to do. */
  protected jobLabel(job: Job): string {
    const query = job.input?.['query'];
    return typeof query === 'string' && query ? query : job.type;
  }
}
