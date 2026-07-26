import { Component, input } from '@angular/core';

/**
 * Stand-in for a screen that a later milestone will build.
 * Keeps the routing walkable end to end today.
 */
@Component({
  selector: 'app-placeholder',
  template: `
    <div class="card">
      <h1>{{ title() }}</h1>
      <p class="muted">{{ note() }}</p>
      <p class="muted"><small>This screen is built in a later milestone.</small></p>
    </div>
  `,
})
export class Placeholder {
  readonly title = input.required<string>();
  readonly note = input('');
}
