"""Provider routing: the configured endpoint is the one that gets used.

Four settings existed in `.env` files (`OPENAI_ENDPOINT`, `OPENAI_MODEL`,
`GEMINI_IMAGE_MODEL`, `GEMINI_LIVE_MODEL`) that **nothing in the application
read**. A deployment could set them, see no error, and get none of the behaviour
they implied.

These tests pin what each one now does, and — for the live model — that the
absence of an implementation is reported rather than implied away.
"""

import tempfile

import pytest

from genesis.config.settings import Settings


@pytest.fixture()
def clean_env(monkeypatch):
    """Remove provider variables and ignore the developer's `.env`.

    Deleting the environment variables is not enough on its own: `Settings`
    declares `env_file=".env"`, so a key set there still resolves. These tests
    read a real developer's `.env` — which is exactly the file that had the four
    unwired settings in it — and would otherwise assert against it.
    """
    for name in (
        "OPENAI_API_KEY",
        "OPENAI_ENDPOINT",
        "OPENAI_MODEL",
        "GEMINI_API_KEY",
        "GEMINI_IMAGE_MODEL",
        "GEMINI_LIVE_MODEL",
        "POLLINATIONS_API_KEY",
        "OPENROUTER_API_KEY",
        "GROQ_API_KEY",
        "ANTHROPIC_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("GENESIS_HOME", tempfile.mkdtemp())
    yield lambda: Settings(_env_file=None)


def test_endpoint_is_recorded_and_reported(clean_env, monkeypatch):
    """A custom endpoint must be visible as the active one."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-not-a-real-key")
    monkeypatch.setenv("OPENAI_ENDPOINT", "https://api.tokenrouter.com/v1")
    monkeypatch.setenv("OPENAI_MODEL", "openai/gpt-6-luna")

    routing = clean_env().media_routing()["text"]

    assert routing["endpoint"] == "https://api.tokenrouter.com/v1"
    assert routing["custom_endpoint"] is True
    assert routing["model"] == "openai/gpt-6-luna"
    assert routing["configured"] is True


def test_default_endpoint_is_named_when_unset(clean_env, monkeypatch):
    """With no override, the report says which endpoint is actually used."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-not-a-real-key")

    routing = clean_env().media_routing()["text"]

    assert routing["custom_endpoint"] is False
    assert "api.openai.com" in routing["endpoint"]


def test_openai_provider_honours_a_custom_base_url(clean_env, monkeypatch):
    """The client must be pointed at the configured endpoint.

    Without this the SDK silently used api.openai.com, so a key from another
    vendor failed with an authentication error naming the wrong cause.
    """
    from genesis.models.openai_provider import OpenAIProvider

    provider = OpenAIProvider(api_key="sk-not-a-real-key", base_url="https://api.tokenrouter.com/v1")

    assert provider.is_available() is True
    assert str(provider.client.base_url).rstrip("/") == "https://api.tokenrouter.com/v1"
    assert provider.base_url == "https://api.tokenrouter.com/v1"


def test_openai_provider_defaults_to_the_vendor_endpoint(clean_env):
    from genesis.models.openai_provider import OpenAIProvider

    provider = OpenAIProvider(api_key="sk-not-a-real-key")

    assert "api.openai.com" in str(provider.client.base_url)


def test_blank_base_url_is_treated_as_absent(clean_env):
    """An empty string must not become a base URL, which would break the client."""
    from genesis.models.openai_provider import OpenAIProvider

    provider = OpenAIProvider(api_key="sk-not-a-real-key", base_url="   ")

    assert provider.base_url is None
    assert "api.openai.com" in str(provider.client.base_url)


def test_image_prefers_gemini_when_configured(clean_env, monkeypatch):
    """A deployment that set an image model must get that model, not a fallback."""
    monkeypatch.setenv("GEMINI_API_KEY", "not-a-real-key")
    monkeypatch.setenv("GEMINI_IMAGE_MODEL", "gemini-3.1-flash-lite-image")

    routing = clean_env().media_routing()["image"]

    assert routing["provider"] == "gemini"
    assert routing["model"] == "gemini-3.1-flash-lite-image"
    assert routing["configured"] is True


def test_image_falls_back_to_pollinations(clean_env):
    """With no Gemini configuration, the free default is named as the source."""
    routing = clean_env().media_routing()["image"]

    assert routing["provider"] == "pollinations"
    assert routing["configured"] is False


def test_image_model_alone_is_not_enough(clean_env, monkeypatch):
    """A model with no key cannot be used, and must not be reported as configured."""
    monkeypatch.setenv("GEMINI_IMAGE_MODEL", "gemini-3.1-flash-lite-image")

    routing = clean_env().media_routing()["image"]

    assert routing["provider"] == "pollinations"
    assert routing["configured"] is False


def test_live_model_is_reported_as_configured_but_unimplemented(clean_env, monkeypatch):
    """The one setting that is recorded rather than honoured says so.

    Reporting `implemented: false` is the point: a configured model name would
    otherwise imply a working realtime voice session.
    """
    monkeypatch.setenv("GEMINI_API_KEY", "not-a-real-key")
    monkeypatch.setenv("GEMINI_LIVE_MODEL", "gemini-3.5-flash-lite")

    routing = clean_env().media_routing()["voice_live"]

    assert routing["model"] == "gemini-3.5-flash-lite"
    assert routing["configured"] is True
    assert routing["implemented"] is False
    assert routing["note"]


def test_every_routing_entry_states_whether_it_is_implemented(clean_env):
    """A caller filtering on `implemented` must never hit a missing key."""
    routing = clean_env().media_routing()

    assert set(routing) == {"text", "image", "voice_live"}
    for purpose, entry in routing.items():
        assert "implemented" in entry, f"{purpose} does not say whether it is implemented"
        assert "provider" in entry, f"{purpose} does not name a provider"
