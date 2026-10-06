# Security notes

Jarvis is a personal, single-user project meant to run on your own machine.
It has not had an external security review. This file lists the protections that
exist in the code so you can judge whether they fit your setup.

## What the code does

- **Secrets stay in the environment.** API keys are read from `.env` / environment
  variables. `config.py` warns if a key-like value is written to `config.json`, and
  writes that file with mode 600. `.env`, `config.json` and `credentials/` are
  git-ignored.
- **Tool server authentication.** Every tool endpoint except `GET /health` requires
  `Authorization: Bearer $MCP_API_KEY`. If `MCP_API_KEY` is unset the server
  refuses requests (HTTP 500) instead of running open.
- **Local binding.** The tool server binds `127.0.0.1` by default
  (`MCP_HOST` to change it). CORS is limited to `ALLOWED_ORIGINS`.
- **Rate limiting.** In-memory sliding window per client IP
  (`RATE_LIMIT_PER_MINUTE`, default 60; 30/min for Gmail and Calendar).
- **Input validation.** Query parameters for search, weather, crypto and news are
  length-limited and rejected if they contain shell metacharacters or script/URL
  schemes.
- **Filesystem sandbox.** The filesystem tool resolves paths and refuses anything
  outside the user's home directory (component-wise check, covered by tests).
- **System commands.** Disabled unless `SYSTEM_COMMANDS_ENABLED=true`, and even then
  only whitelisted argument lists run (`shell=False`). The default whitelist is a
  single `echo` test command.
- **Security headers** (`X-Frame-Options`, `X-Content-Type-Options`, CSP, HSTS) on
  tool server responses.

## Known limits

- The rate limiter trusts `X-Forwarded-For`, so it is only meaningful when the
  server is not exposed directly to untrusted clients.
- There is no TLS in the app; put it behind a reverse proxy if it ever leaves
  localhost.
- The filesystem tool can read and write anything in your home directory once a
  caller has the API key.
- Conversation history and learned personal facts are stored unencrypted in
  `memory/` and `jarvis_state.json`.
- Gmail and Calendar OAuth tokens are pickled in `credentials/`; protect that
  directory like a password.

## Reporting

Open a GitHub issue for non-sensitive problems, or contact the repository owner
through GitHub for anything that should not be public.
