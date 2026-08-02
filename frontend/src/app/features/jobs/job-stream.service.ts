import { Injectable, NgZone, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { JobEvent, TERMINAL_JOB_STATUSES } from '../../core/models';
import { TokenStorage } from '../../core/services/token-storage';
import { environment } from '../../../environments/environment';

/**
 * Live job progress over Server-Sent Events.
 *
 * The endpoint is Bearer-authenticated but also accepts `?token=`, which is why
 * the browser's native EventSource can be used at all — it cannot set headers.
 * (A token in a URL can end up in server logs; the backend documents this and
 * it is acceptable for a short-lived access token in development.)
 *
 * The stream is fed by the backend reading the job, not by Kafka directly —
 * Kafka carries the same events to server-side consumers. A browser cannot
 * speak the Kafka protocol, so SSE is the transport either way.
 */
@Injectable({ providedIn: 'root' })
export class JobStreamService {
  private readonly tokens = inject(TokenStorage);
  private readonly zone = inject(NgZone);

  /**
   * Emits every event for a job and completes once it reaches a terminal
   * status. Errors if the stream drops — callers should fall back to polling.
   */
  stream(jobId: string): Observable<JobEvent> {
    return new Observable<JobEvent>((subscriber) => {
      const token = this.tokens.accessToken();
      if (!token) {
        subscriber.error(new Error('No access token for the stream.'));
        return;
      }

      const url = `${environment.apiUrl}/jobs/${jobId}/stream?token=${encodeURIComponent(token)}`;
      const source = new EventSource(url);

      // EventSource callbacks can land outside Angular's zone, so re-enter it
      // to be sure the signals written by subscribers trigger a render.
      source.onmessage = (message) =>
        this.zone.run(() => {
          let event: JobEvent;
          try {
            event = JSON.parse(message.data) as JobEvent;
          } catch {
            return; // ignore keep-alive noise or a malformed frame
          }

          subscriber.next(event);

          if (TERMINAL_JOB_STATUSES.includes(event.status)) {
            // Closing here is NOT optional. The backend ends the stream on a
            // terminal status, and EventSource treats a closed stream as an
            // error and reconnects — forever — unless we close it ourselves.
            source.close();
            subscriber.complete();
          }
        });

      source.onerror = () =>
        this.zone.run(() => {
          // Close before erroring for the same reason: no silent retry loop.
          // A 401 lands here too, once the token in the URL has expired.
          source.close();
          subscriber.error(new Error('The progress stream was interrupted.'));
        });

      return () => source.close();
    });
  }
}
