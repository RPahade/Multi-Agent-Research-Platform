import { Component, input } from '@angular/core';

/** Shown in place of a table or list when there is nothing to display. */
@Component({
  selector: 'app-empty-state',
  template: `
    <p class="empty muted">{{ message() }}</p>
  `,
  styles: `
    .empty {
      margin: 0;
      padding: var(--space-5) var(--space-3);
      text-align: center;
      font-size: 14px;
    }
  `,
})
export class EmptyState {
  readonly message = input('Nothing to show yet.');
}
