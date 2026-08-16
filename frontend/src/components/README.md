# Components

Component folders are grouped by responsibility:

- `ui/`: shadcn/ui primitives. Keep these generic.
- `layout/`: application shell, sidebar, topbar, route guards, providers.
- `common/`: reusable product components such as tables, metric cards, states, dialogs, markdown.
- `charts/`: chart containers and Recharts wrappers.
- `domain/`: finance-specific display helpers such as P&L, severity, and regime badges.
- `motion/`: optional animation helpers.

Prefer adding new product components to `common`, `charts`, `domain`, or `layout` before touching `ui`.
