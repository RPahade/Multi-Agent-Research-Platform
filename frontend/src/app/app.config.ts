import {
  ApplicationConfig,
  inject,
  provideAppInitializer,
  provideBrowserGlobalErrorListeners,
  provideZoneChangeDetection,
} from '@angular/core';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideRouter, withComponentInputBinding } from '@angular/router';

import { routes } from './app.routes';
import { authInterceptor } from './core/interceptors/auth-interceptor';
import { AuthService } from './core/services/auth.service';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideZoneChangeDetection({ eventCoalescing: true }),

    // withComponentInputBinding lets a component receive route params
    // (e.g. :id) as normal @Input()s — used from the detail screens onward.
    provideRouter(routes, withComponentInputBinding()),

    provideHttpClient(withInterceptors([authInterceptor])),

    // Restore the session before the app renders. The access token only lives
    // in memory, so after a reload the stored refresh token has to be exchanged
    // for a new one — otherwise the guards would bounce the user to /login.
    provideAppInitializer(() => inject(AuthService).restoreSession()),
  ],
};
