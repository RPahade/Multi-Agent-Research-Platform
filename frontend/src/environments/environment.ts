/**
 * Development settings (the default).
 *
 * `apiUrl` is a relative path on purpose: the Angular dev server proxies
 * /api -> http://localhost:8000 (see proxy.conf.json), so every request is
 * same-origin and CORS never comes into play while developing.
 */
export const environment = {
  production: false,
  apiUrl: '/api/v1',
};
