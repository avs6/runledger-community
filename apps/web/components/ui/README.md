# Shared UI kit

Use these instead of hand-rolled equivalents. Live examples: `/design-system`.

| Component | Use for |
|---|---|
| `DataTable` (`data-table.tsx`) | Any list. Server mode: `fetchPage={(q) => apiFetchPage(\`/things?limit=${q.limit}&offset=${q.offset}\`, apiKey)}`; the total comes from `X-Total-Count`. Client mode: `rows={items}`. Sort, search, column chooser (remembered per table) and CSV export built in; page/sort/search live in the URL (`urlPrefix` keeps two tables apart). |
| `useConfirm()` / `ConfirmDialog` (`confirm-dialog.tsx`) | Replaces `window.confirm` (eslint warns on it): `if (await confirm({ title, destructive: true })) …` and render `{dialog}`. |
| `AsyncCard`, `SectionError` (`async-card.tsx`) | A section that loads on its own: loading, error with retry, empty and ready states. Never swallow errors into an empty state. |
| `EmptyState` (`empty-state.tsx`) | No data: say what it is and offer the next action. |
| `PageHeader` (`page-header.tsx`) | Title, description, breadcrumbs and actions. |
| `TimeRangePicker`, `rangeToWindow` (`time-range-picker.tsx`) | Preset time windows and the `from`/`to` the list endpoints take. |
| `RelatedPanel` (`components/context/RelatedPanel.tsx`) | On-demand related context for an entity (`GET /context`). |

Routes: link with `lib/routes.ts` (`routes.apiKeysKeyId(id)`, `STATIC_ROUTES`), not string literals;
`npm run check:routes` fails on hrefs that match no page. Regenerate after adding a page with
`npm run gen:routes`.

Colours: use the Tailwind tokens backed by CSS variables (`text-status-error`, `bg-severity-high`,
`text-scope-workspace`, `bg-runtime-degraded`). Charts take `CHART_SERIES` / `seriesColor(i)` from
`lib/tokens.ts`, the only place raw hex is allowed (eslint warns elsewhere).
