/**
 * Production settings.
 *
 * Swapped in for environment.ts by the "production" build configuration
 * (see the fileReplacements block in angular.json). There is no dev-server
 * proxy in a production build, so the API URL must be absolute.
 */
export const environment = {
  production: true,
  apiUrl: 'http://localhost:8000/api/v1',
};
