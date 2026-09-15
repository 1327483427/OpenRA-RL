# OpenRA AI Control Platform

This checkout extends OpenRA-RL with configurable games, an installed-map
catalog, and live monitoring for Claude Code, CC-Switch, and other MCP clients.

## Start the platform

```bash
colima start
scripts/build-platform.sh   # first run, or after source changes
scripts/start-platform.sh
```

On Windows, run these commands inside WSL2 Ubuntu. Keep the repository in the
WSL filesystem (for example `~/Workspace/OpenRA-RL`) instead of `/mnt/c` or
`/mnt/d`; Docker builds involving the OpenRA source tree are substantially
faster there. `Dockerfile.platform` supports both x86_64 and ARM64 builders.

Open the control center at <http://127.0.0.1:8000/control>. The page shows
engine readiness, installed mods, map metadata, and a live stream of MCP tool
calls and results. Replays persist under `.platform-data/replays/`.

Stop it with:

```bash
scripts/stop-platform.sh
```

## MCP configuration

```json
{
  "mcpServers": {
    "openra-rl": {
      "type": "stdio",
      "command": "/Users/liqiuping/Workspace/GitWorkspace/Hackathon2025/OpenRA-RL/.venv/bin/openra-rl",
      "args": [
        "mcp-server",
        "--server-url",
        "http://127.0.0.1:8000"
      ],
      "env": {
        "OPENRA_AGENT_NAME": "cc-switch"
      }
    }
  }
}
```

## Configurable games

Agents should call `list_maps` before `start_game`. A typical game starts with:

```text
list_maps(mod="ra", include_campaigns=false)
start_game(map_name="tournament-island.oramap", difficulty="easy", seed=42)
```

`start_game` accepts the following difficulty values: `beginner`, `easy`,
`medium`, `hard`, `brutal`, `rush`, `normal`, `turtle`, and `naval`.

The platform discovers `ra`, `cnc`, `d2k`, and `ts` installations. The current
external-agent bridge is fully verified for `ra`; other mods are listed for
catalog and future compatibility work rather than advertised as verified.

## HTTP endpoints

- `/control` — external-agent control center
- `/platform/status` — Web and gRPC readiness
- `/platform/maps` — installed map catalog
- `/platform/events` — recent MCP activity
- `/platform/events/stream` — live Server-Sent Event feed
- `/docs` — generated REST API documentation
