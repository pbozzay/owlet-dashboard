"""Safe, actionable messages for linking an Owlet account."""

import aiohttp
from pyowletapi.exceptions import (
    OwletAuthenticationError,
    OwletConnectionError,
    OwletCredentialsError,
    OwletDevicesError,
)


def link_error(exc: Exception) -> tuple[int, str]:
    # Never return upstream exception text: it may contain credentials or URLs.
    if isinstance(exc, OwletCredentialsError):
        return 400, "Owlet rejected the login. Check your email, password, and selected region."
    if isinstance(exc, TimeoutError):
        return 504, "The connection to Owlet timed out. Check this computer's network and try again."
    if isinstance(exc, (aiohttp.ClientConnectionError, OwletConnectionError)):
        return 503, (
            "This computer could not connect to Owlet's sign-in service. "
            "Check its internet connection, proxy, or firewall settings."
        )
    if isinstance(exc, OwletDevicesError):
        return 400, "Signed in, but no supported Owlet sock was found. Check the account and region."
    if isinstance(exc, OwletAuthenticationError):
        # pyowletapi has no separate exception type for this specific condition.
        if exc.args == ("Too many incorrect attempts",):
            return 429, "Owlet is limiting sign-in attempts. Wait before trying again."
        return 502, "Owlet's sign-in service could not complete authentication. Please try again later."
    return 502, "Could not finish linking the Owlet account. Please try again later."
