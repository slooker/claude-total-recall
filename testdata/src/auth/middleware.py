"""
src/auth/middleware.py

FastAPI middleware for JWT authentication.
Injects the authenticated user_id into request state for downstream handlers.
"""

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from auth.jwt import decode_token, TokenExpiredError, TokenInvalidError

# Routes that don't require authentication
PUBLIC_ROUTES = {
    "/health",
    "/auth/login",
    "/auth/register",
    "/auth/refresh",
    "/webhooks/stripe",   # Stripe webhooks use HMAC, not JWT
    "/docs",
    "/openapi.json",
}


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """
    Validates the Authorization: Bearer <token> header on protected routes.
    Sets request.state.user_id on success.
    """

    async def dispatch(self, request: Request, call_next):
        if request.url.path in PUBLIC_ROUTES:
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid Authorization header"}
            )

        token = auth_header.removeprefix("Bearer ").strip()

        try:
            payload = decode_token(token, expected_type="access")
            request.state.user_id = payload["sub"]
        except TokenExpiredError:
            return JSONResponse(
                status_code=401,
                content={"detail": "Token expired — please refresh"}
            )
        except TokenInvalidError as e:
            return JSONResponse(
                status_code=401,
                content={"detail": f"Invalid token: {e}"}
            )

        return await call_next(request)


def get_current_user(request: Request) -> str:
    """
    FastAPI dependency. Extracts user_id from request state.
    Use this in route handlers instead of reading state directly.
    """
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user_id
