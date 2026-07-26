import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

/**
 * Placeholder sign-in screen. The real form (form-encoded login, token
 * storage, refresh handling) is built in the authentication milestone.
 * Rendered outside the shell — no sidebar on the login screen.
 */
@Component({
  selector: 'app-login-page',
  imports: [RouterLink],
  template: `
    <div class="wrap">
      <div class="card box">
        <h1>Sign in</h1>
        <p class="muted">
          The sign-in form is built in the authentication milestone.
        </p>
        <a routerLink="/dashboard">Go to the dashboard</a>
      </div>
    </div>
  `,
  styles: `
    .wrap {
      display: grid;
      place-items: center;
      min-height: 100vh;
      padding: var(--space-4);
    }
    .box {
      width: 100%;
      max-width: 380px;
    }
  `,
})
export class LoginPage {}
