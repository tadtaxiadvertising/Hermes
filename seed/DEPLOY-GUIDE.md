# Deploy Guide: Hermes Agent on Easypanel with Full TAD Access

This guide walks you through deploying the Hermes agent on Easypanel with full access to:
- TAD DOOH Platform private repos (via GitHub PAT)
- Memory context (MEMORY.md, USER.md seeded at deploy time)
- Web research (Firecrawl)
- All the same capabilities as the local agent

## Prerequisites

1. **Easypanel VPS** with the Hermes Gateway service already running
2. **GitHub PAT** with `repo` scope for the tadtaxiadvertising org
3. **Firecrawl API key** (optional, for web research)
4. **NVIDIA API key** (already configured)
5. **Telegram bot token** (already configured)

## Step 1: Generate a GitHub PAT

1. Go to https://github.com/settings/tokens/new
2. Name it: `hermes-easypanel-agent`
3. Select scope: **repo** (full access to private repos)
4. Set expiration: 90 days (or custom)
5. Click "Generate token" and copy it

## Step 2: Add Environment Variables in Easypanel

In your Easypanel service's **Environment** tab, add:

| Variable | Value | Secret? |
|---|---|---|
| `GITHUB_PAT` | Your GitHub PAT from Step 1 | ✅ Yes |
| `FIRECRAWL_API_KEY` | Your Firecrawl key (optional) | ✅ Yes |

These are already defined in `schema.json` so Easypanel should show them in the UI.

## Step 3: Rebuild the Docker Image

The Dockerfile now includes memory seeds (MEMORY.md, USER.md) and an enhanced SOUL.md.
You need to rebuild the image for these changes to take effect.

### Option A: Easypanel Auto-Build (Recommended)
1. Push changes to the GitHub repo (tadtaxiadvertising/hermes or your overlay repo)
2. In Easypanel, click **Deploy** → **Rebuild** on the Hermes Gateway service
3. Wait for the build to complete (~3-5 min)

### Option B: Manual Build on VPS
```bash
cd /path/to/hermes-overlay
docker build -t hermes-gateway:slim .
docker compose -f docker-compose.easypanel.yml up -d
```

## Step 4: Verify Memory Seeds

After rebuild, the entrypoint will seed MEMORY.md and USER.md into `/opt/data/memories/`.
These seeds only apply on **first boot** (when files don't already exist on the persistent volume).

### If you already have a running deployment:
You need to either:
1. **Delete the volume** and redeploy (⚠️ loses all session data, cron state, etc.)
2. **Manually copy** the seed files into the volume:
   ```bash
   # Find the container
   docker exec hermes-gateway cat /opt/memories-seed/MEMORY.md
   # Copy to persistent volume
   docker exec hermes-gateway cp /opt/memories-seed/MEMORY.md /opt/data/memories/MEMORY.md
   docker exec hermes-gateway cp /opt/memories-seed/USER.md /opt/data/memories/USER.md
   ```

## Step 5: Verify Git Access

After the container starts with `GITHUB_PAT` set:
```bash
docker exec hermes-gateway git clone https://${GITHUB_PAT}@github.com/tadtaxiadvertising/tad-dooh-platform.git /opt/data/tad-dooh-platform
```

The agent will also be able to clone repos autonomously via its terminal tool.

## Step 6: Test via Telegram

Send a message to @taxiadvertising_bot:
- "Clona el repo de TAD y verifica el último commit"
- "Qué servicios hay en Easypanel?"
- "Busca información sobre [topic] en internet"

The agent should:
- Clone repos via terminal using the GitHub PAT
- Use memory context for TAD-specific knowledge
- Use Firecrawl for web research
- Execute commands and deploy changes autonomously

## Memory Sync Strategy

The VPS agent and local agent maintain **separate** memory files. When you want to sync:

### VPS → Local (pull new memories from agent)
```bash
docker exec hermes-gateway cat /opt/data/memories/MEMORY.md
# Copy the output to your local memories/MEMORY.md
```

### Local → VPS (push updated memories to agent)
```bash
# Read your local MEMORY.md
cat %LOCALAPPDATA%\hermes\memories\MEMORY.md
# Push to VPS volume
docker exec -i hermes-gateway tee /opt/data/memories/MEMORY.md < %LOCALAPPDATA%\hermes\memories\MEMORY.md
```

### Future: Cloud Memory Provider
For automatic sync, consider switching to a cloud memory provider (Honcho, Mem0, etc.)
in config.yaml. Both deployments would share the same memory backend.

## Troubleshooting

| Issue | Solution |
|---|---|
| Agent can't clone repos | Check `GITHUB_PAT` is set in Easypanel env vars |
| Agent has no memory context | Verify seed files exist: `docker exec hermes-gateway ls /opt/data/memories/` |
| 502 on Easypanel service | Check primaryDomain port via Easypanel API |
| Agent doesn't know TAD context | Verify SOUL.md: `docker exec hermes-gateway cat /opt/data/SOUL.md` |
