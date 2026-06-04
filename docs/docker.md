# Docker Usage

This repository contains **two independent Docker setups**. They serve different
purposes and are run separately — do not confuse them:

| Setup          | Location             | What it runs                                                          |
| -------------- | -------------------- | --------------------------------------------------------------------- |
| **MCP Server** | repository root      | The IB Analytics MCP server (Python) for Flex Query analytics         |
| **CP Gateway** | `docker/cp-gateway/` | The IBKR Client Portal Gateway (Java) proxy for the Client Portal API |

- Use the **MCP Server** setup if you want to run IB Analytics itself in a
  container (the default for most users).
- Use the **CP Gateway** setup only if you need the IBKR Client Portal Web API
  (`/v1/api/...`), which requires IBKR's local gateway proxy for authentication.

The two are unrelated build contexts: the root `Dockerfile`/`docker-compose.yml`
build the MCP server, while `docker/cp-gateway/` builds IBKR's gateway. A
`.dockerignore` at the repository root keeps the MCP build context small and
prevents local secrets (`.env`) and data from being sent to the Docker daemon.

---

## Part 1 — MCP Server (repository root)

IB Analytics can be run in a Docker container for isolated, reproducible
environments. The relevant files are `Dockerfile` and `docker-compose.yml` in
the repository root.

### Quick Start

```bash
# Build image
docker build -t ib-sec-mcp .

# Run with environment variables
docker run -it --rm \
  -e QUERY_ID=your_query_id \
  -e TOKEN=your_token \
  -v $(pwd)/data:/app/data \
  ib-sec-mcp

# Or use docker-compose
docker-compose up
```

### Docker Compose

Create `.env` file:

```env
QUERY_ID=your_query_id
TOKEN=your_token
IB_DEBUG=0
```

Run:

```bash
# Start server
docker-compose up -d

# View logs
docker-compose logs -f

# Stop server
docker-compose down

# Run tests
docker-compose --profile test run test
```

### Security Features

- **Non-root user**: Runs as `mcpuser` (UID 1000)
- **Read-only filesystem**: Root filesystem is read-only
- **Resource limits**: CPU (2 cores) and memory (2GB) limits
- **No new privileges**: Prevents privilege escalation
- **Data persistence**: Data stored in mounted volume

### Environment Variables

| Variable   | Required | Description                                |
| ---------- | -------- | ------------------------------------------ |
| `QUERY_ID` | Yes      | IB Flex Query ID                           |
| `TOKEN`    | Yes      | IB Flex Query token                        |
| `IB_DEBUG` | No       | Enable debug mode (`1` = on, default: `0`) |

### Data Persistence

Mount the `data/` directory to persist fetched data between container restarts:

```bash
docker run -it --rm \
  -e QUERY_ID=your_query_id \
  -e TOKEN=your_token \
  -v $(pwd)/data:/app/data \
  ib-sec-mcp ib-sec-fetch --start-date 2025-01-01
```

### Troubleshooting

**Container fails to start**: Check that `QUERY_ID` and `TOKEN` are set correctly.

**Permission errors**: Ensure the mounted `data/` directory is writable by UID 1000.

**Network issues**: The container needs outbound internet access to reach the IB Flex Query API.

---

## Part 2 — CP Gateway (`docker/cp-gateway/`)

The `docker/cp-gateway/` directory packages the **IBKR Client Portal Gateway**,
a Java proxy provided by Interactive Brokers that the Client Portal Web API
requires for authentication and request signing. This is **not** the MCP server
— it is IBKR's gateway, downloaded at build time from Interactive Brokers.

### Quick Start

```bash
cd docker/cp-gateway

# Build and start the gateway
docker compose up -d --build

# Then authenticate in the browser
open https://localhost:5001/
```

### Key differences from the MCP Server setup

| Aspect         | MCP Server (root)             | CP Gateway (`docker/cp-gateway/`)      |
| -------------- | ----------------------------- | -------------------------------------- |
| Base image     | `python:3.12-slim`            | `eclipse-temurin:21`                   |
| Authentication | `QUERY_ID` / `TOKEN` env vars | Interactive browser login              |
| Exposed port   | n/a (stdio MCP)               | host `5001` → container `5000` (HTTPS) |
| Purpose        | Flex Query analytics          | Client Portal Web API proxy            |

For full setup, authentication flow, ports, configuration, and security notes,
see [`docker/cp-gateway/README.md`](../docker/cp-gateway/README.md).
