"""Settings and configuration for Genesis."""

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

#: The placeholder shipped in `.env.example`. Booting with this means every JWT
#: in the deployment is forgeable by anyone who has read the repository.
INSECURE_SECRET_PLACEHOLDER = "your-secret-key-change-this-in-production"

#: Environments where an insecure secret is tolerated, because the app is only
#: reachable from the developer's own machine and requiring a key on every test
#: run is friction that leads to people committing a real one.
_INSECURE_ALLOWED_ENVS = ("test", "development", "dev", "local")

#: Shortest secret accepted as "real". A 32-character secret is the same order as
#: what `secrets.token_hex(32)` produces for the compose file.
MINIMUM_SECRET_LENGTH = 32


class InsecureSecretError(RuntimeError):
    """Raised when the app is configured with a placeholder signing key."""


class Settings(BaseSettings):
    """Genesis configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",
    )

    # Application
    app_name: str = "Genesis AGI Framework"
    version: str = "0.1.5"
    debug: bool = False

    # Paths
    genesis_home: Path = Field(default_factory=lambda: Path.home() / ".genesis")
    data_dir: Path = Field(default_factory=lambda: Path.home() / ".genesis" / "data")
    minds_dir: Path = Field(default_factory=lambda: Path.home() / ".genesis" / "minds")
    logs_dir: Path = Field(default_factory=lambda: Path.home() / ".genesis" / "logs")

    # Database
    database_url: str = "sqlite:///genesis.db"
    vector_db_path: str = "./chroma_db"
    #: "persistent" writes a ChromaDB directory under data_dir and survives
    #: restarts. "ephemeral" keeps vectors in memory only, which is what makes the
    #: test suite hermetic: a shared persistent collection accumulates across
    #: runs, so a test asserting "there is exactly 1 memory" fails against the
    #: hundreds a previous run left behind rather than against the code. Also the
    #: right choice for a read-only or demo deployment that has no business
    #: writing a vector database.
    vector_store_mode: str = "persistent"

    # Model Providers - API Keys
    openrouter_api_key: Optional[str] = None  # Free models available from https://openrouter.ai/
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None  # Free from Google AI Studio
    groq_api_key: Optional[str] = None
    pollinations_api_key: Optional[str] = None  # Free from https://enter.pollinations.ai/

    #: Base URL for the OpenAI-compatible endpoint.
    #:
    #: Any service that speaks the OpenAI Chat Completions API can be used by
    #: pointing this at it — a gateway, a proxy, a self-hosted vLLM, or a
    #: third-party router. Left unset, the official api.openai.com is used.
    #:
    #: This exists because `OPENAI_API_KEY` was wired to the vendor's default
    #: base URL with no way to override it, so a key issued by anything other
    #: than OpenAI itself could be configured and then fail at request time with
    #: an authentication error that named the wrong cause.
    openai_endpoint: Optional[str] = None

    #: Model to use on the OpenAI-compatible endpoint.
    #:
    #: Used when a Mind has not been given its own model. Set this to whatever
    #: your endpoint exposes; the value is passed through as-is, because only the
    #: endpoint knows its own model namespace.
    openai_model: Optional[str] = None

    #: Gemini model used for image generation. Replaces the Pollinations default
    #: when both this and `gemini_api_key` are set.
    gemini_image_model: Optional[str] = None

    # ------------------------------------------------------------------ #
    # Digital presence: the Mind's own communications (docs/v3/DIGITAL_PRESENCE.md)
    #
    # The administrator supplies these; the Mind never holds a credential. It
    # holds an intent to communicate, the channel adapter holds the secret, and
    # the policy holds the veto.
    #
    # Install-level (one Mind per installation) is the documented default. Per-Mind
    # provisioning — each Mind with its own address — is a later phase and will
    # override these rather than replace them, so a single-Mind install keeps
    # working with no configuration change.
    # ------------------------------------------------------------------ #
    #: Name shown in every AI disclosure. Required in practice: an anonymous AI is
    #: worse than an undisclosed one, because there is nobody to hold responsible.
    mind_administrator_name: str = ""

    #: The email address the Mind owns.
    #:
    #: Named `mind_*` rather than `email_*` deliberately. `Settings` has no
    #: `env_prefix`, so a field name *is* the environment variable name, and
    #: `EMAIL_PASSWORD` or `EMAIL_ADDRESS` would collide with whatever the host
    #: already sets — silently taking the Mind's credentials from an unrelated
    #: service. The rest of this file uses specific names for the same reason.
    mind_email_address: Optional[str] = None
    mind_email_display_name: Optional[str] = None
    mind_email_username: Optional[str] = None
    mind_email_password: Optional[str] = None
    mind_email_imap_host: Optional[str] = None
    mind_email_imap_port: int = 993
    mind_email_smtp_host: Optional[str] = None
    mind_email_smtp_port: int = 587
    mind_email_use_tls: bool = True

    #: Telegram bot identity. A token from @BotFather; no business verification.
    mind_telegram_bot_token: Optional[str] = None
    mind_telegram_bot_username: Optional[str] = None

    # --- Hostinger Mail API (recommended email provider) -------------------
    #
    # Hostinger runs a Mail API separate from their hosting API: different base
    # URL, different tokens, different SDK. Their hosting API *manages mailboxes*;
    # this one **reads and sends mail**, which is the part a Mind needs.
    #
    # Create the token under Agentic Mail -> API access in the email domain's
    # sidebar. It is scoped to one order and optionally to specific mailboxes, so
    # the token can only reach what it was granted — which is the same shape as
    # our own capability model and worth preferring over a broader credential.
    #
    # Two provider features are worth knowing about because they overlap with
    # controls we already enforce ourselves:
    #   * an outgoing allow list, which rejects a send addressed to the wrong
    #     person (provider-side, so it holds even if our code is wrong)
    #   * webhooks for new mail, so reacting to inbound does not need polling
    mind_hostinger_mail_api_token: Optional[str] = None
    #: Mailbox resource id, `AC...`. Returned by the account endpoint; every other
    #: operation is scoped to one mailbox.
    mind_hostinger_mailbox_id: Optional[str] = None
    #: The address the mailbox owns. Shown in the disclosure and used as the From.
    mind_hostinger_mail_address: Optional[str] = None
    mind_hostinger_mail_display_name: Optional[str] = None
    #: Overridable so a documented-but-unverified path can be corrected without a
    #: code change. `HostingerMailChannel.verify()` reports which paths work.
    mind_hostinger_mail_base_url: str = "https://api.mail.hostinger.com"
    mind_hostinger_mail_api_version: str = "v1"

    # --- Ringg AI voice ----------------------------------------------------
    #
    # Ringg runs the voice assistant; the Mind starts calls and reads the results.
    # That is a different shape from every other channel: the Mind does not speak,
    # Ringg does, using a prompt configured in Ringg's dashboard. So the adapter
    # cannot put our prepared body on the wire — see `ringg_voice.py`.
    mind_ringg_api_key: Optional[str] = None
    #: Assistant that handles the call. Created in the Ringg dashboard.
    mind_ringg_agent_id: Optional[str] = None
    #: Caller number id from `GET /workspace/numbers`.
    mind_ringg_from_number_id: Optional[str] = None
    #: The E.164 number the Mind calls from, for the disclosure and for receipts.
    mind_ringg_phone_number: Optional[str] = None
    #: Records call windows in Ringg. Ringg enforces `call_config.call_time`, so
    #: this is a hint for the adapter's own quiet-hours default, not the control.
    mind_ringg_call_window: str = "09:00-18:00"
    #: **An assertion, not a check.**
    #:
    #: Ringg's assistant speaks a prompt configured in Ringg's dashboard, and no
    #: API exposes that prompt's text. So we cannot verify that the assistant
    #: discloses it is an AI — and an undisclosed voice channel is the one outcome
    #: this product must not ship. The channel therefore registers **disabled**
    #: unless the operator asserts it, and the assertion is recorded.
    #:
    #: This is the same rule as `supports_disclosure` in the registry: a channel
    #: that cannot demonstrate disclosure is not enabled. The honest difference is
    #: that here it is a human's word rather than a capability flag, and that is
    #: stated rather than hidden.
    mind_ringg_disclosure_confirmed: bool = False

    #: Gemini model used for realtime / live voice sessions.
    #:
    #: Recorded and surfaced so a deployment can declare its intent, but there is
    #: no Live API client in this codebase yet — the bidirectional audio stream is
    #: a feature, not a setting. See `genesis/senses/` for what does exist.
    gemini_live_model: Optional[str] = None

    # Model Defaults  
    default_reasoning_model: str = "openrouter/meta-llama/llama-3.3-70b-instruct:free"  # ✓ Works - Clean JSON output
    default_fast_model: str = "openrouter/meta-llama/llama-3.3-70b-instruct:free"  # ✓ Fast & reliable
    default_local_model: str = "ollama/llama3.1"
    ollama_base_url: str = "http://localhost:11434"

    # Consciousness Settings
    consciousness_tick_interval: int = 60  # seconds (1 minute for active consciousness)
    dream_schedule: str = "02:00"  # 2 AM
    thought_generation_enabled: bool = True

    # Safety
    action_logging_enabled: bool = True
    require_approval_for_external_actions: bool = True
    max_autonomous_actions_per_hour: int = 100

    # Process supervision for Mind daemons (plan item B11).
    #   None      - fall through to the GENESIS_SUPERVISOR environment variable,
    #               then to "none". The default, so the environment variable is
    #               authoritative and this field cannot shadow it.
    #   "none"    - this API will not start or stop daemons; it tells the caller
    #               what the operator should run instead, because the API tier
    #               should not hold process-control authority.
    #   "systemd" - delegate to `systemctl` against genesis-mind@<gmid>.service.
    supervisor: Optional[str] = None

    # Uploads
    max_upload_size_mb: int = 100  # Per-file cap for workspace uploads (SEC-14)

    # API Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = False
    cors_origins: str = "*"  # Comma-separated list of allowed origins or * for all

    # Security & Authentication
    api_secret_key: str = "your-secret-key-change-this-in-production"
    api_authentication_enabled: bool = True
    secret_key: str = "your-secret-key-change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Firebase Authentication (optional)
    firebase_project_id: Optional[str] = None  # Set to enable Firebase auth
    firebase_api_key: Optional[str] = None  # Firebase Web API key for token verification
    
    # Mind Creation Limits
    max_minds_per_user: int = 1  # Maximum minds a user can create (admins exempt)

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins string into list."""
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure directories exist
        self.genesis_home.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.minds_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    # Secret validation (plan item B12)
    # ------------------------------------------------------------------ #

    @staticmethod
    def environment_name() -> str:
        """The configured environment, normalised."""
        return (
            os.environ.get("GENESIS_ENV", "").strip().lower()
            or os.environ.get("ENVIRONMENT", "").strip().lower()
            or "production"
        )

    def insecure_secrets(self) -> list[str]:
        """Names of signing secrets still set to the shipped placeholder.

        Empty means nothing to complain about.
        """
        offenders: list[str] = []
        if self.api_secret_key == INSECURE_SECRET_PLACEHOLDER:
            offenders.append("API_SECRET_KEY")
        if self.secret_key == INSECURE_SECRET_PLACEHOLDER:
            offenders.append("SECRET_KEY")
        return offenders

    def short_secrets(self) -> list[str]:
        """Names of signing secrets that are real but too short to be safe."""
        offenders: list[str] = []
        for name, value in (
            ("API_SECRET_KEY", self.api_secret_key),
            ("SECRET_KEY", self.secret_key),
        ):
            if value and value != INSECURE_SECRET_PLACEHOLDER and len(value) < MINIMUM_SECRET_LENGTH:
                offenders.append(name)
        return offenders

    def assert_secure_secrets(self) -> None:
        """Refuse to run in production with a placeholder or weak signing key.

        `docker-compose.yml` already fails fast on a missing key, but the
        application did not, so any install that bypassed compose (a systemd
        unit, a bare `uvicorn`, a container run by hand) silently shipped with a
        key published in this repository. Every token would be forgeable.

        Raises:
            InsecureSecretError: outside test/development, if a signing secret is
                still the shipped placeholder.
        """
        environment = self.environment_name()
        placeholders = self.insecure_secrets()

        if not placeholders:
            short = self.short_secrets()
            if short and environment not in _INSECURE_ALLOWED_ENVS:
                logger.warning(
                    "Signing secrets %s are shorter than %d characters. Generate one with: "
                    "python -c \"import secrets; print(secrets.token_hex(32))\"",
                    ", ".join(short),
                    MINIMUM_SECRET_LENGTH,
                )
            return

        if environment in _INSECURE_ALLOWED_ENVS:
            logger.warning(
                "Running with the placeholder signing key (%s) because GENESIS_ENV=%s. "
                "This must not be reachable from a network.",
                ", ".join(placeholders),
                environment,
            )
            return

        raise InsecureSecretError(
            "Refusing to start: "
            + ", ".join(placeholders)
            + " is still the placeholder value from .env.example, so every issued token "
            "would be forgeable by anyone who has read this repository. Generate a real "
            "one and set it in the environment:\n"
            '  python -c "import secrets; print(secrets.token_hex(32))"\n'
            "Set GENESIS_ENV=development to bypass this check for local work."
        )

    # ------------------------------------------------------------------ #
    # Which provider serves which purpose
    # ------------------------------------------------------------------ #

    def media_routing(self) -> dict[str, dict[str, object]]:
        """What is configured for each non-text purpose, and what is not.

        Exists because the provider settings were invisible: `OPENAI_ENDPOINT`,
        `OPENAI_MODEL`, `GEMINI_IMAGE_MODEL` and `GEMINI_LIVE_MODEL` could all be
        set in `.env` while nothing in the application read them, and there was no
        way to tell from the outside whether an image was generated by Gemini or
        by the free public fallback. A deployment that has configured a model
        should be able to confirm what is actually being used.

        `implemented` is part of the shape on purpose. `gemini_live_model` is read
        and reported, but there is no Live API client in this codebase — the
        bidirectional audio session is a feature, not a setting — and saying so
        here is better than letting a configured model name imply otherwise.
        """
        text_endpoint = (self.openai_endpoint or "").strip()
        return {
            "text": {
                "provider": "openai" if self.openai_api_key else None,
                "model": self.openai_model,
                "endpoint": text_endpoint or "https://api.openai.com/v1 (default)",
                "custom_endpoint": bool(text_endpoint),
                "configured": bool(self.openai_api_key),
                "implemented": True,
            },
            "image": {
                "provider": "gemini" if (self.gemini_api_key and self.gemini_image_model) else "pollinations",
                "model": self.gemini_image_model,
                "configured": bool(self.gemini_api_key and self.gemini_image_model),
                "implemented": True,
                "fallback": "pollinations (no key required)",
            },
            "voice_live": {
                "provider": "gemini" if self.gemini_live_model else None,
                "model": self.gemini_live_model,
                "configured": bool(self.gemini_live_model),
                # Honest: the setting is honoured by nothing yet.
                "implemented": False,
                "note": (
                    "Recorded but not wired. Realtime bidirectional audio needs a Live API "
                    "client, which does not exist here; see genesis/senses/ for the "
                    "text-to-speech and speech-to-text paths that are implemented."
                ),
            },
        }


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
