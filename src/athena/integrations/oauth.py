"""OAuth flow handler for external service authentication."""

from __future__ import annotations

import json
import secrets
import time
import urllib.parse
from dataclasses import dataclass, field
from typing import Any, Optional

from athena.db.database import Database
from athena.utils.logger import get_logger

logger = get_logger("integrations.oauth")


@dataclass
class OAuthToken:
    """OAuth token data."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600
    refresh_token: str = ""
    scope: str = ""
    created_at: float = field(default_factory=time.time)

    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        return time.time() > (self.created_at + self.expires_in - 60)  # 60s buffer


@dataclass
class OAuthProvider:
    """OAuth provider configuration."""

    name: str
    client_id: str
    client_secret: str
    authorize_url: str
    token_url: str
    redirect_uri: str
    scopes: list[str] = field(default_factory=list)


@dataclass
class OAuthState:
    """OAuth state for CSRF protection."""

    state: str
    provider: str
    created_at: float = field(default_factory=time.time)
    code_verifier: str = ""


class OAuthManager:
    """Manages OAuth flows for external service authentication."""

    SUPPORTED_PROVIDERS: dict[str, dict[str, Any]] = {
        "google": {
            "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "scopes": ["openid", "email", "profile"],
        },
        "github": {
            "authorize_url": "https://github.com/login/oauth/authorize",
            "token_url": "https://github.com/login/oauth/access_token",
            "scopes": ["user", "repo"],
        },
        "microsoft": {
            "authorize_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
            "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
            "scopes": ["openid", "email", "profile"],
        },
    }

    def __init__(self, database: Optional[Database] = None) -> None:
        self._db = database
        self._providers: dict[str, OAuthProvider] = {}
        self._tokens: dict[str, OAuthToken] = {}  # provider -> token
        self._states: dict[str, OAuthState] = {}  # state -> OAuthState

    def register_provider(
        self,
        name: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scopes: Optional[list[str]] = None,
    ) -> OAuthProvider:
        """
        Register an OAuth provider.
        
        Args:
            name: Provider name (google/github/microsoft/custom).
            client_id: OAuth client ID.
            client_secret: OAuth client secret.
            redirect_uri: Redirect URI.
            scopes: Optional scopes.
            
        Returns:
            OAuthProvider configuration.
            
        Raises:
            ValueError: If provider name is unsupported.
        """
        provider_key = name.lower()
        if provider_key in self.SUPPORTED_PROVIDERS:
            preset = self.SUPPORTED_PROVIDERS[provider_key]
            provider = OAuthProvider(
                name=provider_key,
                client_id=client_id,
                client_secret=client_secret,
                authorize_url=preset["authorize_url"],
                token_url=preset["token_url"],
                redirect_uri=redirect_uri,
                scopes=scopes or preset["scopes"],
            )
        else:
            raise ValueError(
                f"Unsupported provider: {name}. Supported: {list(self.SUPPORTED_PROVIDERS.keys())}"
            )

        self._providers[provider_key] = provider
        logger.info(f"OAuth provider registered: {provider_key}")
        return provider

    def get_authorization_url(self, provider_name: str) -> tuple[str, str]:
        """
        Generate the authorization URL for the OAuth flow.
        
        Args:
            provider_name: Registered provider name.
            
        Returns:
            Tuple of (authorization_url, state) — state must be stored for verification.
        """
        provider = self._providers.get(provider_name.lower())
        if not provider:
            raise ValueError(f"Provider not registered: {provider_name}")

        state = secrets.token_urlsafe(32)
        code_verifier = secrets.token_urlsafe(64)

        # Store state for later verification
        self._states[state] = OAuthState(
            state=state,
            provider=provider_name.lower(),
            code_verifier=code_verifier,
        )

        params = {
            "client_id": provider.client_id,
            "redirect_uri": provider.redirect_uri,
            "response_type": "code",
            "scope": " ".join(provider.scopes),
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }

        auth_url = f"{provider.authorize_url}?{urllib.parse.urlencode(params)}"
        return auth_url, state

    def verify_state(self, state: str) -> Optional[OAuthState]:
        """Verify an OAuth state parameter and return the associated state data."""
        oauth_state = self._states.get(state)
        if oauth_state:
            # Check expiry (10 minute window)
            if time.time() - oauth_state.created_at < 600:
                return oauth_state
            else:
                del self._states[state]
        return None

    async def exchange_code(
        self,
        provider_name: str,
        code: str,
        state: str,
    ) -> OAuthToken:
        """
        Exchange an authorization code for tokens.
        
        Args:
            provider_name: Provider name.
            code: Authorization code.
            state: State parameter for verification.
            
        Returns:
            OAuthToken with access token.
            
        Raises:
            ValueError: If state verification fails.
            RuntimeError: If token exchange fails.
        """
        provider = self._providers.get(provider_name.lower())
        if not provider:
            raise ValueError(f"Provider not registered: {provider_name}")

        # Verify state
        oauth_state = self.verify_state(state)
        if not oauth_state:
            raise ValueError("Invalid or expired state parameter")

        # Exchange code for token
        import httpx

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                provider.token_url,
                data={
                    "grant_type": "authorization_code",
                    "client_id": provider.client_id,
                    "client_secret": provider.client_secret,
                    "code": code,
                    "redirect_uri": provider.redirect_uri,
                },
                headers={"Accept": "application/json"},
            )

            if response.status_code != 200:
                raise RuntimeError(
                    f"Token exchange failed: {response.status_code} {response.text}"
                )

            data = response.json()

        token = OAuthToken(
            access_token=data["access_token"],
            token_type=data.get("token_type", "Bearer"),
            expires_in=data.get("expires_in", 3600),
            refresh_token=data.get("refresh_token", ""),
            scope=data.get("scope", ""),
        )

        # Store token
        self._tokens[provider_name.lower()] = token

        # Clean up state
        del self._states[state]

        # Persist to database
        if self._db and self._db.is_connected:
            try:
                await self._db.execute(
                    """
                    INSERT INTO oauth_tokens (provider, access_token, refresh_token,
                                            expires_in, scope, created_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (
                        provider_name.lower(),
                        token.access_token,
                        token.refresh_token,
                        token.expires_in,
                        token.scope,
                    ),
                )
                await self._db.commit()
            except Exception as e:
                logger.warning(f"Failed to persist OAuth token: {e}")

        logger.info(f"OAuth token obtained for {provider_name}")
        return token

    def get_token(self, provider_name: str) -> Optional[OAuthToken]:
        """Get the current token for a provider."""
        return self._tokens.get(provider_name.lower())

    def revoke_token(self, provider_name: str) -> bool:
        """Revoke and remove a stored token."""
        if provider_name.lower() in self._tokens:
            del self._tokens[provider_name.lower()]
            logger.info(f"OAuth token revoked for {provider_name}")
            return True
        return False

    def list_providers(self) -> list[str]:
        """List registered provider names."""
        return list(self._providers.keys())


# Global instance
oauth_manager = OAuthManager()
