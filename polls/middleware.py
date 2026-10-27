import secrets

from django.conf import settings

COOKIE_NAME = "voter_token"
COOKIE_MAX_AGE = 60 * 60 * 24 * 365  # 1 year


class VoterTokenMiddleware:
    """Gives every visitor a long-lived anonymous `voter_token` cookie.

    Used to stop guests from voting twice on the same poll. This is not
    bulletproof (the cookie can be deleted), which is fine for a prototype.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = request.COOKIES.get(COOKIE_NAME, "")
        is_new = not token or len(token) > 64
        if is_new:
            token = secrets.token_urlsafe(32)
        request.voter_token = token

        response = self.get_response(request)

        if is_new:
            response.set_cookie(
                COOKIE_NAME,
                token,
                max_age=COOKIE_MAX_AGE,
                httponly=True,
                samesite="Lax",
                secure=settings.SESSION_COOKIE_SECURE,
            )
        return response
