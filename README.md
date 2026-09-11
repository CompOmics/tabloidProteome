# MoDPA — Modification-Dependent Protein Associations

Web application for exploring functional associations between post-translational modification (PTM) sites derived from large-scale, public mass spectrometry proteomics data. Built on the [Tabloid Proteome](https://tabloidproteome.ugent.be) concept and developed at the [CompOmics group](https://compomics.com), Ghent University / VIB.

## Overview

MoDPA extends Tabloid Proteome from protein-level co-occurrence to PTM-site-level associations. Nodes represent PTM sites (modification type + protein residue); edges represent co-occurrence and dependency patterns across PRIDE projects, weighted by signed distance correlation computed in a VAE-derived latent space.

The interface provides interactive graph exploration through multiple visualization backends (Sigma, D3, Cytoscape, Cosmograph).

## Stack

| Layer           | Technology                                     |
| --------------- | ---------------------------------------------- |
| Backend         | Python 3.12, FastAPI, SQLAlchemy 2, PostgreSQL |
| Frontend        | Vue 3, Vite, Vuetify 3, Pinia                  |
| Graph libraries | cosmos.gl with Cosmograph                      |
| Container       | Docker (multi-stage), Docker Compose           |
| Analytics       | Umami (self-hosted, cookieless)                |

## Project structure

```
.
├── backend/
│   ├── main.py              # FastAPI app entry point, serves SPA
│   ├── api/v1/routes.py     # REST endpoints: /get-edges, /get-nodes, /get-unimod
│   ├── models.py            # SQLAlchemy models (Node, Edge, Unimod)
│   ├── schemas.py           # Pydantic schemas
│   ├── crud.py              # Database queries
│   ├── config.py            # Environment / DB config
│   ├── utils/               # WebSocket connection manager
│   ├── data/                # Source CSV files
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── views/           # Page-level components
│   │   ├── components/      # Graph visualization components
│   │   ├── stores/          # Pinia state
│   │   └── router/
│   └── package.json
├── Dockerfile               # Multi-stage build (Node → Python)
├── docker-compose.yml       # Production
├── docker-compose-local.yml # Local development
└── docker-compose-db.yml    # PostgreSQL only
```

## Local development

### Prerequisites

- Docker and Docker Compose
- Node.js 20 or 22 (frontend only)
- Python 3.12 (backend only)

### 1. Start the database

```bash
docker compose -f docker-compose-db.yml up -d
```

PostgreSQL will be available on port `54327`.

### 2. Configure environment

Copy `.env.local` and adjust database credentials if needed:

```bash
cp .env.local .env.local.override
```

Credentials are read from the env file at runtime. Do not commit secrets to version control.

### 3. Run with Docker (recommended)

```bash
docker compose -f docker-compose-local.yml up --build
```

The app is served at [http://localhost:5600](http://localhost:5600).

### 4. Run without Docker

**Backend:**

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 5600
```

**Frontend (development server with hot reload):**

```bash
cd frontend
npm install
npm run dev
```

## Production deployment

```bash
docker compose up --build -d
```

The production compose file builds from the `Dockerfile`, which compiles the frontend and bundles it with the backend into a single image served on port `5600`.

### Maintenance mode

While the database is being updated (e.g. re-running `crud.py`), every request can be served a static maintenance page (HTTP 503) instead of hitting the app. Toggle it by creating/removing a flag file inside the running container — no restart needed:

```bash
# activate
docker exec tabloid_proteome_modpa touch /backend/maintenance.flag

# deactivate
docker exec tabloid_proteome_modpa rm /backend/maintenance.flag
```

The page content is `backend/maintenance.html`.

## API

| Method | Path                 | Description                          |
| ------ | -------------------- | ------------------------------------ |
| `GET`  | `/api/v1/get-nodes`  | Retrieve PTM site nodes              |
| `GET`  | `/api/v1/get-edges`  | Retrieve association edges           |
| `GET`  | `/api/v1/get-unimod` | Retrieve Unimod modification entries |

Interactive API docs are available at `/docs` when running locally.

## Citation

MoDPA is an ongoing extension of Tabloid Proteome. Citation details will be provided when the corresponding manuscript is available.

## Contact

- [Lennart.Martens@UGent.be](mailto:Lennart.Martens@UGent.be)
- [Natalia.Tichshenko@UGent.be](mailto:Natalia.Tichshenko@UGent.be)
- [Enrico.Massignani@UGent.be](mailto:Enrico.Massignani@UGent.be)

## License

To be determined.
