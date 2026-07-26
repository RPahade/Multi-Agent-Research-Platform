import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-not-found-page',
  imports: [RouterLink],
  template: `
    <div class="card">
      <h1>Page not found</h1>
      <p class="muted">That page does not exist.</p>
      <a routerLink="/dashboard">Back to the dashboard</a>
    </div>
  `,
})
export class NotFoundPage {}
