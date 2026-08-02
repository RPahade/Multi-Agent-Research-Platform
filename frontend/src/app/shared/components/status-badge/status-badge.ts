import { Component, computed, input } from '@angular/core';

/**
 * Colour for every status value the API can return, across jobs, job steps,
 * documents, reports and agents. Anything unmapped falls back to the neutral
 * blue `.badge`.
 */
const BADGE_CLASS: Record<string, string> = {
  // jobs + job steps
  succeeded: 'badge-success',
  running: '',
  pending: 'badge-warning',
  failed: 'badge-danger',
  cancelled: 'badge-neutral',
  skipped: 'badge-neutral',
  // documents
  ingested: 'badge-success',
  processing: '',
  uploaded: 'badge-warning',
  // reports
  final: 'badge-success',
  draft: 'badge-warning',
  archived: 'badge-neutral',
  // agents / tools
  active: 'badge-success',
  inactive: 'badge-neutral',
  enabled: 'badge-success',
  disabled: 'badge-neutral',
};

/** Coloured pill for a status value. */
@Component({
  selector: 'app-status-badge',
  template: `<span class="badge" [class]="cssClass()">{{ status() }}</span>`,
})
export class StatusBadge {
  readonly status = input.required<string>();

  protected readonly cssClass = computed(() => BADGE_CLASS[this.status()] ?? '');
}
