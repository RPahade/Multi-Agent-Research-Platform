import {
  ApplicationConfig,
  provideBrowserGlobalErrorListeners,
  provideZoneChangeDetection,
} from '@angular/core';
import { provideHttpClient } from '@angular/common/http';
import { provideRouter, withComponentInputBinding } from '@angular/router';

import { routes } from './app.routes';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideZoneChangeDetection({ eventCoalescing: true }),

    // withComponentInputBinding lets a component receive route params
    // (e.g. :id) as normal @Input()s — used from the detail screens onward.
    provideRouter(routes, withComponentInputBinding()),

    // The auth interceptor is registered here in the next milestone.
    provideHttpClient(),
  ],
};
