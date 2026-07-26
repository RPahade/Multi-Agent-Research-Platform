import { HttpErrorResponse } from '@angular/common/http';

/**
 * Turns any backend error into one readable sentence.
 *
 * The API always answers with `{ "detail": ... }`, but `detail` is a string
 * for normal errors and an array of `{ loc, msg }` for 422 validation errors.
 */
export function apiErrorMessage(error: unknown): string {
  if (!(error instanceof HttpErrorResponse)) {
    return 'Something went wrong.';
  }

  if (error.status === 0) {
    return 'Cannot reach the server. Is the backend running?';
  }

  const detail = error.error?.detail;

  if (typeof detail === 'string') {
    return detail;
  }

  // 422: [{ loc: ['body', 'email'], msg: 'value is not a valid email' }, ...]
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        const field = Array.isArray(item.loc) ? item.loc[item.loc.length - 1] : '';
        return field ? `${field}: ${item.msg}` : item.msg;
      })
      .join(', ');
  }

  return error.message || `Request failed (${error.status}).`;
}
