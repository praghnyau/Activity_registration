# Activity Registration and Group Formation System

A web application for colleges that run group-based activities such as workshops, coding challenges, and design sprints. Students find activities, register, and see the group they are assigned to. Administrators create activities, manage registrations, and form groups.

---

## What it does

- Students browse open activities, register, track their registration status, and view their assigned group.
- Administrators create and publish activities, monitor registrations, run group formation, and resolve incomplete groups.
- The system keeps a history of past groupings and uses it to prefer new pairings in future activities.

## Documentation

| Document | Contents |
|---|---|
| [docs/project-overview.md](docs/project-overview.md) | Full project scope, users, roles, status definitions, workflows, and requirements |
| [docs/frontend.md](docs/frontend.md) | All pages, visual design, colour palette, layout, components, and responsive behaviour |
| [docs/data-model.md](docs/data-model.md) | All database tables, fields, constraints, and relationships |
| [docs/template-contract.md](docs/template-contract.md) | Every Jinja template variable passed by the backend to each page |
| [docs/design-decisions.md](docs/design-decisions.md) | Resolved decisions on withdrawal, edit limits, sessions, dark mode, capacity, and more |
| [docs/stack.md](docs/stack.md) | Technology stack, libraries, and local development setup |
| [docs/implementation-plan.md](docs/implementation-plan.md) | Phased build order for both frontend and backend |

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI |
| Templates | Jinja2 (server-rendered) |
| Database | PostgreSQL |
| ORM | SQLAlchemy (async) |
| Migrations | Alembic |
| Auth | Session cookies, Passlib + bcrypt |
| Frontend | HTML, CSS, JavaScript (no framework) |

## Roles

- **Student** — registers for activities, views groups, tracks status
- **Administrator** — manages activities, runs group formation, resolves edge cases

## Project status

Under development. No code yet. Documentation complete.
