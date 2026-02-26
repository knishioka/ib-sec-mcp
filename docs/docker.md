# Docker Usage

IB Analytics can be run in a Docker container for isolated, reproducible environments.

## Quick Start

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

## Docker Compose

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

## Security Features

- **Non-root user**: Runs as `mcpuser` (UID 1000)
- **Read-only filesystem**: Root filesystem is read-only
- **Resource limits**: CPU (2 cores) and memory (2GB) limits
- **No new privileges**: Prevents privilege escalation
- **Data persistence**: Data stored in mounted volume

## Environment Variables

| Variable   | Required | Description                                |
| ---------- | -------- | ------------------------------------------ |
| `QUERY_ID` | Yes      | IB Flex Query ID                           |
| `TOKEN`    | Yes      | IB Flex Query token                        |
| `IB_DEBUG` | No       | Enable debug mode (`1` = on, default: `0`) |

## Data Persistence

Mount the `data/` directory to persist fetched data between container restarts:

```bash
docker run -it --rm \
  -e QUERY_ID=your_query_id \
  -e TOKEN=your_token \
  -v $(pwd)/data:/app/data \
  ib-sec-mcp ib-sec-fetch --start-date 2025-01-01
```

## Troubleshooting

**Container fails to start**: Check that `QUERY_ID` and `TOKEN` are set correctly.

**Permission errors**: Ensure the mounted `data/` directory is writable by UID 1000.

**Network issues**: The container needs outbound internet access to reach the IB Flex Query API.
