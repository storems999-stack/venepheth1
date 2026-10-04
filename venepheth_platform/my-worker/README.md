# Cloudflare Worker

The Worker proxies requests to the Django app. It has no baked-in backend URL:
set `DJANGO_BACKEND_ORIGIN` to the origin of the Django service before using it.

## Local development

Copy `.dev.vars.example` to `.dev.vars` and change `DJANGO_BACKEND_ORIGIN` if
Django is not listening at `http://127.0.0.1:8000`. Then run:

```sh
npm --prefix my-worker install
npm --prefix my-worker run dev
```

The Worker allows plain HTTP only for loopback addresses during local
development. All other backends must use HTTPS.

## Production

Set the permanent HTTPS origin as a Worker secret, replacing the example URL
with the real Django origin:

```sh
npm --prefix my-worker exec -- wrangler secret put DJANGO_BACKEND_ORIGIN --config my-worker/wrangler.jsonc
npm --prefix my-worker run deploy
```

These commands work from the repository root. Alternatively, change directory
to `my-worker` first and use `npx wrangler secret put DJANGO_BACKEND_ORIGIN`
and `npm run deploy`; Wrangler then finds `wrangler.jsonc` automatically.

Do not use a temporary tunnel URL for production. The Worker returns `503` when
the setting is missing or invalid rather than silently proxying to a stale
backend. The distinct binding name avoids conflicts with an older plain-text
`BACKEND_URL` variable on an existing Worker.
