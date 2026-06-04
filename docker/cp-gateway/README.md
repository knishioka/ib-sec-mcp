# IBKR Client Portal Gateway (Docker)

A self-contained Docker setup that runs the **Interactive Brokers Client Portal
Gateway** (CP Gateway) — the local proxy that the IBKR Client Portal Web API
(`/v1/api/...`) requires for authentication and request signing.

> **Not the same as the MCP server Docker setup.** This directory packages the
> _IBKR-provided_ Java gateway only. The IB Analytics MCP server has its own
> Docker setup in the repository root (`Dockerfile`, `docker-compose.yml`).
> See [`docs/docker.md`](../../docs/docker.md) for how the two relate.

---

## What this provides

| File                 | Purpose                                                            |
| -------------------- | ------------------------------------------------------------------ |
| `Dockerfile`         | Builds on `eclipse-temurin:21`, downloads the official CP Gateway  |
| `docker-compose.yml` | Runs the gateway, maps host `5001` → container `5000`, healthcheck |
| `conf.yaml`          | Gateway configuration (mounted into `root/conf.yaml`)              |
| `run.sh`             | Container entrypoint that launches the gateway                     |

The image downloads `clientportal.gw.zip` directly from
`download2.interactivebrokers.com` at build time, so an outbound internet
connection is required when building.

---

## Prerequisites

- Docker and Docker Compose
- A funded or paper **IBKR account** with Client Portal Web API access enabled
- Outbound network access to `download2.interactivebrokers.com` (build) and
  `api.ibkr.com` (runtime)

---

## Quick start

```bash
cd docker/cp-gateway

# Build and start the gateway in the background
docker compose up -d --build

# Follow logs
docker compose logs -f

# Stop
docker compose down
```

Once running, the gateway is reachable on the **host** at:

```
https://localhost:5001/
```

(The gateway listens on `5000` inside the container; compose maps it to `5001`
on the host so it does not collide with other local services.)

---

## Authentication

The CP Gateway does **not** accept credentials on the command line. You log in
through the browser, and the gateway holds the authenticated session:

1. Start the gateway (`docker compose up -d --build`).
2. Open <https://localhost:5001/> in a browser.
3. Accept the self-signed certificate warning (the gateway ships with a
   self-signed keystore — see _Security notes_ below).
4. Log in with your IBKR username and password (and 2FA if enabled).
5. After "Client login succeeds", the session is active. Verify with:

   ```bash
   curl -sk https://localhost:5001/v1/api/tickle
   ```

Sessions expire after a period of inactivity; re-authenticate via the browser
when `tickle` reports the session as disconnected. The healthcheck in
`docker-compose.yml` calls `tickle` to track liveness.

---

## Ports

| Context   | Port   | Notes                                           |
| --------- | ------ | ----------------------------------------------- |
| Container | `5000` | `listenPort` in `conf.yaml`, HTTPS              |
| Host      | `5001` | Published by `docker-compose.yml` (`5001:5000`) |

To change the host port, edit the `ports` mapping in `docker-compose.yml`.

---

## Configuration (`conf.yaml`)

`docker-compose.yml` bind-mounts `conf.yaml` over the image's baked-in copy, so
you can edit it and apply changes with `docker compose restart` — no rebuild
required.

Key settings:

- `proxyRemoteHost: "https://api.ibkr.com"` — upstream IBKR API.
- `listenPort: 5000` / `listenSsl: true` — the gateway serves HTTPS internally.
- `ips.allow` / `ips.deny` — client IP allow/deny list. The defaults permit
  common private ranges (`10.*`, `172.*`, `192.*`) and loopback; tighten these
  for production deployments.
- `cors.origin.allowed: "*"` — permissive CORS suited to local development;
  restrict it if you expose the gateway beyond localhost.

---

## Security notes

- **Self-signed TLS / `sslPwd`**: The gateway ships with a bundled `vertx.jks`
  keystore whose password (`mywebapi`) is the **publicly documented IBKR
  default**, not a secret. It only protects the self-signed cert used for the
  local HTTPS listener. For anything beyond localhost, replace the keystore and
  password with your own.
- **No account secrets are stored here.** `conf.yaml` and `run.sh` contain no
  API keys, tokens, or account numbers — authentication happens interactively
  through the browser.
- **Bind to localhost.** The compose file publishes the port on all interfaces
  by default via Docker; if the host is reachable from untrusted networks,
  restrict the published port (e.g. `127.0.0.1:5001:5000`) and tighten
  `ips.allow`.

---

## Troubleshooting

| Symptom                               | Likely cause / fix                                         |
| ------------------------------------- | ---------------------------------------------------------- |
| Build fails downloading the gateway   | No outbound access to `download2.interactivebrokers.com`   |
| Browser cannot reach `localhost:5001` | Container not healthy yet — check `docker compose logs -f` |
| `tickle` returns `not authenticated`  | Log in again via the browser; session expired              |
| Certificate warning in browser        | Expected — the gateway uses a self-signed cert by default  |
