/**
 * Production browser environment.
 *
 * - Empty `apiUrl` = same-origin relative calls (nginx/Caddy reverse-proxy).
 * - For Vercel SPA + separate API host, replace this file at build time or set
 *   `apiUrl` to the HTTPS API origin (example: `https://api.example.com`).
 * - Never ship `http://localhost` in a production bundle.
 */
export const environment = {
  production: true,
  apiUrl: '',
  apiV1Prefix: '/api/v1',
  appVersion: '0.7.1',
};
