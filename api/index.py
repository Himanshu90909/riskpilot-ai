"""Vercel entrypoint for the RiskPilot FastAPI service."""
from urllib.parse import quote

from starlette.middleware.base import BaseHTTPMiddleware

from server.main import app


class StripApiPrefixMiddleware(BaseHTTPMiddleware):
    """Strip the `/api` gateway prefix that Vercel rewrites onto this function.

    The `vercel.json` rewrite `/api/(.*)` routes requests to this function while
    preserving the original request path (e.g. `/api/v1/health`). The FastAPI
    service defines its routes without the prefix (`/v1/...`), so the prefix is
    removed before routing. This middleware only runs on the Vercel deployment —
    the local uvicorn service (`server.main:app`) is mounted without the prefix
    and never imports this module.
    """

    async def dispatch(self, request, call_next):
        path = request.scope.get("path", "")
        if path == "/api":
            request.scope["path"] = "/"
            request.scope["raw_path"] = b"/"
        elif path.startswith("/api/"):
            request.scope["path"] = path[4:] or "/"
            request.scope["raw_path"] = quote(path[4:] or "/").encode("utf-8")
        return await call_next(request)


app.add_middleware(StripApiPrefixMiddleware)

__all__ = ["app"]
