import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { ja } from '@/shared/messages/ja'

import { App } from './App'

function renderApp() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <App />
    </QueryClientProvider>,
  )
}

function stubHealth(status: number, body: unknown) {
  const fetchMock = vi.fn(() =>
    Promise.resolve(
      new Response(JSON.stringify(body), {
        status,
        headers: { 'Content-Type': 'application/json' },
      }),
    ),
  )
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

describe('App', () => {
  it('shows that the API and the database are reachable', async () => {
    const fetchMock = stubHealth(200, { status: 'ok', database: 'ok' })
    renderApp()
    expect(await screen.findByText(ja.health.ok)).toBeInTheDocument()
    const request = fetchMock.mock.calls[0] as unknown as [Request]
    expect(new URL(request[0].url).pathname).toBe('/healthz')
  })

  it('shows a degraded state when the API answers 503', async () => {
    stubHealth(503, { status: 'unavailable', database: 'unreachable' })
    renderApp()
    expect(await screen.findByText(ja.health.degraded)).toBeInTheDocument()
  })

  it('shows an error when the API cannot be reached', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.reject(new TypeError('network'))),
    )
    renderApp()
    expect(await screen.findByText(ja.health.unreachable)).toBeInTheDocument()
  })

  it('switches to the dark theme', async () => {
    stubHealth(200, { status: 'ok', database: 'ok' })
    renderApp()
    await userEvent.click(screen.getByRole('button', { name: ja.theme.dark }))
    expect(document.documentElement).toHaveClass('dark')
    expect(screen.getByRole('button', { name: ja.theme.dark })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
  })
})
