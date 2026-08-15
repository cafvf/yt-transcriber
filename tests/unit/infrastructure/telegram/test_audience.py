"""Security contract for the single-operator private Telegram audience."""

from __future__ import annotations

from yt_transcriber_bot.infrastructure.telegram.audience import TelegramAudiencePolicy


def test_configured_operator_private_chat_is_allowed() -> None:
    policy = TelegramAudiencePolicy(allowed_user_id=42)

    assert policy.allows(user_id=42, chat_id=42, chat_type="private") is True


def test_different_user_is_denied_even_in_private_chat() -> None:
    policy = TelegramAudiencePolicy(allowed_user_id=42)

    assert policy.allows(user_id=99, chat_id=99, chat_type="private") is False


def test_configured_operator_is_denied_in_group_or_supergroup() -> None:
    policy = TelegramAudiencePolicy(allowed_user_id=42)

    assert policy.allows(user_id=42, chat_id=-100123, chat_type="group") is False
    assert policy.allows(user_id=42, chat_id=-100456, chat_type="supergroup") is False


def test_private_chat_id_must_match_configured_operator() -> None:
    policy = TelegramAudiencePolicy(allowed_user_id=42)

    assert policy.allows(user_id=42, chat_id=77, chat_type="private") is False


def test_unconfigured_operator_is_always_denied() -> None:
    policy = TelegramAudiencePolicy(allowed_user_id=0)

    assert policy.allows(user_id=0, chat_id=0, chat_type="private") is False


def test_denied_filter_matches_group_before_product_handlers() -> None:
    from types import SimpleNamespace

    from yt_transcriber_bot.infrastructure.telegram.audience import DeniedAudienceFilter

    policy = TelegramAudiencePolicy(allowed_user_id=42)
    denied = DeniedAudienceFilter(policy)
    group_message = SimpleNamespace(
        from_user=SimpleNamespace(id=42),
        chat=SimpleNamespace(id=-100123, type="group"),
    )
    private_message = SimpleNamespace(
        from_user=SimpleNamespace(id=42),
        chat=SimpleNamespace(id=42, type="private"),
    )

    assert denied.filter(group_message) is True  # type: ignore[arg-type]
    assert denied.filter(private_message) is False  # type: ignore[arg-type]
