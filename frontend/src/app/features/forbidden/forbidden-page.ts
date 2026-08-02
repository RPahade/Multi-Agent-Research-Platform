import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { AuthService } from '../../core/services/auth.service';

/** Shown when a signed-in user opens a route their role cannot access. */
@Component({
  selector: 'app-forbidden-page',
  imports: [RouterLink],
  template: `
    <div class="card">
      <h1>Not allowed</h1>
      <p class="muted">
        Your role ({{ auth.role() ?? 'unknown' }}) does not have access to that
        page. Ask an administrator if you need it.
      </p>
      <a routerLink="/dashboard">Back to the dashboard</a>
    </div>
  `,
})
export class ForbiddenPage {
  protected readonly auth = inject(AuthService);
}
