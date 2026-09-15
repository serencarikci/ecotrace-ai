/**
 * Production browser environment for Vercel / static hosting.
 *
 * At build time, set `ECOTRACE_API_URL` (HTTPS API origin, no trailing slash).
 * The `apps/web/scripts/write-production-env.mjs` helper rewrites this file
 * before `ng build --configuration=production`.
 *
 * Empty `apiUrl` means same-origin relative calls (only valid behind a reverse proxy).
 * Never ship a loopback API origin in a production bundle.
 */
export const environment = {
  production: true,
  apiUrl: '',
  apiV1Prefix: '/api/v1',
  appVersion: '0.7.1',
};
