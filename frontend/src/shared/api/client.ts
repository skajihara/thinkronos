import createClient from 'openapi-fetch'

import type { paths } from './schema'

/**
 * Typed API client. Types come only from openapi.json (C-28); run `npm run gen-types`
 * after the API changes. Requests go to the page's own origin; the dev server proxies them (C-19).
 */
export const apiClient = createClient<paths>({
  baseUrl: window.location.origin,
  // Look up fetch on each call so tests can stub it.
  fetch: (request) => globalThis.fetch(request),
})
