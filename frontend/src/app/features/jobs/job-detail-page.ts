import { DatePipe } from '@angular/common';
import { Component, OnDestroy, OnInit, computed, inject, input, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { Subscription, timer } from 'rxjs';
import { switchMap } from 'rxjs/operators';

import {
  Job,
  JobStep,
  JobStepStatus,
  Report,
  TERMINAL_JOB_STATUSES,
} from '../../core/models';
import { apiErrorMessage } from '../../core/services/api-error';
import { AuthService } from '../../core/services/auth.service';
import { StatusBadge } from '../../shared/components/status-badge/status-badge';
import { ReportsService } from '../reports/reports.service';
import { JobStreamService } from './job-stream.service';
import { JobsService } from './jobs.service';

/** The fixed research pipeline, so steps that have not started yet still show. */
const RESEARCH_PIPELINE = [
  { key: 'retrieval', name: 'Retrieving relevant passages' },
  { key: 'research', name: 'Researching sources' },
  { key: 'synthesis', name: 'Synthesizing report' },
  { key: 'citation', name: 'Verifying citations' },
  { key: 'compliance', name: 'Redacting PII' },
];

/** How often the polling fallback re-reads the job. */
const POLL_INTERVAL_MS = 1500;

interface StepRow {
  key: string;
  name: string;
  status: JobStepStatus | 'pending';
  error: string | null;
  required: boolean;
  startedAt: string | null;
  finishedAt: string | null;
}

@Component({
  selector: 'app-job-detail-page',
  imports: [DatePipe, RouterLink, StatusBadge],
  templateUrl: './job-detail-page.html',
  styleUrl: './job-detail-page.scss',
})
export class JobDetailPage implements OnInit, OnDestroy {
  /** Route parameter, bound by withComponentInputBinding(). */
  readonly id = input.required<string>();

  private readonly jobs = inject(JobsService);
  private readonly reports = inject(ReportsService);
  private readonly stream = inject(JobStreamService);
  private readonly auth = inject(AuthService);

  protected readonly job = signal<Job | null>(null);
  protected readonly steps = signal<JobStep[]>([]);
  protected readonly report = signal<Report | null>(null);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly cancelError = signal<string | null>(null);
  protected readonly cancelling = signal(false);

  /** How updates are arriving, shown to the user so the view is not a black box. */
  protected readonly liveMode = signal<'stream' | 'polling' | 'idle'>('idle');

  private streamSubscription?: Subscription;
  private pollSubscription?: Subscription;
  /** Last step name we fetched the trace for, so we refetch only on change. */
  private lastStepFetchedFor: string | null = null;

  protected readonly isTerminal = computed(() => {
    const job = this.job();
    return !!job && TERMINAL_JOB_STATUSES.includes(job.status);
  });

  /** Cancelling is analyst + admin only, and only before the job finishes. */
  protected readonly canCancel = computed(() => {
    const role = this.auth.role();
    return (
      !this.isTerminal() &&
      !!this.job() &&
      (role === 'admin' || role === 'analyst')
    );
  });

  /**
   * The pipeline merged with the steps recorded so far. Step rows only exist
   * once a tool starts, so anything missing is still pending.
   */
  protected readonly stepRows = computed<StepRow[]>(() => {
    const recorded = this.steps();
    const job = this.job();

    // Only research jobs run the fixed pipeline; others just show what ran.
    if (job && job.type !== 'research') {
      return recorded.map(toRow);
    }

    return RESEARCH_PIPELINE.map((tool) => {
      const step = recorded.find((s) => s.tool_key === tool.key);
      return step
        ? toRow(step)
        : {
            key: tool.key,
            name: tool.name,
            status: 'pending' as const,
            error: null,
            required: true,
            startedAt: null,
            finishedAt: null,
          };
    });
  });

  /** Wall-clock duration once the job has finished. */
  protected readonly duration = computed(() => {
    const job = this.job();
    if (!job?.started_at || !job.finished_at) {
      return null;
    }
    const seconds = (Date.parse(job.finished_at) - Date.parse(job.started_at)) / 1000;
    return seconds < 60 ? `${seconds.toFixed(1)}s` : `${(seconds / 60).toFixed(1)} min`;
  });

  ngOnInit(): void {
    this.jobs.get(this.id()).subscribe({
      next: (job) => {
        this.job.set(job);
        this.loading.set(false);
        this.loadSteps();

        if (TERMINAL_JOB_STATUSES.includes(job.status)) {
          this.onFinished();
        } else {
          this.startStreaming();
        }
      },
      error: (err) => {
        this.error.set(apiErrorMessage(err));
        this.loading.set(false);
      },
    });
  }

  /** Live updates over SSE, falling back to polling if the stream drops. */
  private startStreaming(): void {
    this.liveMode.set('stream');

    this.streamSubscription = this.stream.stream(this.id()).subscribe({
      next: (event) => this.applyEvent(event),
      error: () => {
        // Most likely the access token in the stream URL expired. Polling goes
        // through HttpClient, so the auth interceptor refreshes it for us.
        this.startPolling();
      },
      complete: () => this.onFinished(),
    });
  }

  private startPolling(): void {
    this.liveMode.set('polling');

    this.pollSubscription = timer(0, POLL_INTERVAL_MS)
      .pipe(switchMap(() => this.jobs.get(this.id())))
      .subscribe({
        next: (job) => {
          this.job.set(job);
          this.refreshStepsIfChanged(job.current_step);
          if (TERMINAL_JOB_STATUSES.includes(job.status)) {
            this.pollSubscription?.unsubscribe();
            this.onFinished();
          }
        },
        error: (err) => {
          this.error.set(apiErrorMessage(err));
          this.liveMode.set('idle');
        },
      });
  }

  /** SSE carries job-level fields only, so patch them onto the loaded job. */
  private applyEvent(event: { status: Job['status']; progress: number; current_step: string | null; attempts?: number; error?: string | null }): void {
    this.job.update((job) =>
      job
        ? {
            ...job,
            status: event.status,
            progress: event.progress,
            current_step: event.current_step,
            attempts: event.attempts ?? job.attempts,
            error: event.error ?? null,
          }
        : job,
    );

    this.refreshStepsIfChanged(event.current_step);
  }

  /** The trace is not streamed — refetch it whenever the current step moves on. */
  private refreshStepsIfChanged(currentStep: string | null): void {
    if (currentStep !== this.lastStepFetchedFor) {
      this.lastStepFetchedFor = currentStep;
      this.loadSteps();
    }
  }

  private loadSteps(): void {
    this.jobs.steps(this.id()).subscribe({
      next: (steps) => this.steps.set(steps),
      error: () => undefined,
    });
  }

  /** Terminal: settle the view and pull in the report if one was produced. */
  private onFinished(): void {
    this.liveMode.set('idle');
    this.loadSteps();

    this.jobs.get(this.id()).subscribe({
      next: (job) => this.job.set(job),
      error: () => undefined,
    });

    this.reports.list({ job_id: this.id(), page: 1, size: 1 }).subscribe({
      next: (page) => this.report.set(page.items[0] ?? null),
      error: () => this.report.set(null),
    });
  }

  protected cancel(): void {
    if (!confirm('Stop this job? Work already done is kept, but it will not finish.')) {
      return;
    }

    this.cancelling.set(true);
    this.cancelError.set(null);

    this.jobs.cancel(this.id()).subscribe({
      next: (job) => {
        this.job.set(job);
        this.cancelling.set(false);
        this.stopWatching();
        this.onFinished();
      },
      error: (err) => {
        // 409 means it finished while the confirm dialog was open — not an
        // error worth alarming anyone about, just show the real outcome.
        if (err?.status === 409) {
          this.onFinished();
        } else {
          this.cancelError.set(apiErrorMessage(err));
        }
        this.cancelling.set(false);
      },
    });
  }

  private stopWatching(): void {
    this.streamSubscription?.unsubscribe();
    this.pollSubscription?.unsubscribe();
  }

  ngOnDestroy(): void {
    this.stopWatching();
  }
}

function toRow(step: JobStep): StepRow {
  return {
    key: step.tool_key,
    name: step.name,
    status: step.status,
    error: step.error,
    required: step.required,
    startedAt: step.started_at,
    finishedAt: step.finished_at,
  };
}
