import base64
import hashlib
import hmac
import os
from collections.abc import Mapping
from uuid import UUID

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from src.core.config.settings import settings
from src.infra.privacy.core_redis_client import get_core_redis

_STORE_PREFIX = "core:pii-map:v1"
_OWNER_PREFIX = "core:chat-result-owner:v1"
_MAX_TTL_SCRIPT = """
local hard_key = KEYS[2]
local data_key = KEYS[1]
if #ARGV > 2 then
  redis.call('SET', hard_key, '1', 'NX', 'EX', ARGV[1])
elseif redis.call('EXISTS', data_key) == 0 then
  return 0
end
local hard_ttl = redis.call('TTL', hard_key)
if hard_ttl <= 0 then
  redis.call('DEL', data_key)
  return 0
end
local requested = tonumber(ARGV[2])
if hard_ttl < requested then requested = hard_ttl end
if #ARGV > 2 then
  for i = 3, #ARGV, 2 do
    redis.call('HSET', data_key, ARGV[i], ARGV[i + 1])
  end
end
if redis.call('EXISTS', data_key) == 1 then
  redis.call('EXPIRE', data_key, requested)
end
return hard_ttl
"""


def _encryption_key() -> bytes:
    encoded = settings.PII_ENCRYPTION_KEY
    if not encoded:
        raise RuntimeError("PII_ENCRYPTION_KEY não configurada.")
    try:
        key = base64.urlsafe_b64decode(encoded.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as error:
        raise RuntimeError("PII_ENCRYPTION_KEY deve ser Base64 URL-safe.") from error
    if len(key) != 32:
        raise RuntimeError("PII_ENCRYPTION_KEY deve representar exatamente 32 bytes.")
    return key


def validate_pii_encryption_key() -> None:
    _encryption_key()


def _encrypt(value: str, associated_data: str) -> str:
    nonce = os.urandom(12)
    ciphertext = AESGCM(_encryption_key()).encrypt(
        nonce, value.encode("utf-8"), associated_data.encode("utf-8")
    )
    return base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")


def _decrypt(value: str, associated_data: str) -> str:
    raw = base64.urlsafe_b64decode(value.encode("ascii"))
    try:
        return AESGCM(_encryption_key()).decrypt(
            raw[:12], raw[12:], associated_data.encode("utf-8")
        ).decode("utf-8")
    except (InvalidTag, UnicodeDecodeError) as error:
        raise RuntimeError("Não foi possível abrir o mapa PII temporário.") from error


def _conversation_keys(conversation_id: str) -> tuple[str, str]:
    digest = hashlib.sha256(conversation_id.encode("utf-8")).hexdigest()
    key = f"{_STORE_PREFIX}:{digest}"
    return key, f"{key}:max"


async def retain_pii_mappings(
    conversation_id: str, owner_scope: str, mappings: Mapping[str, str]
) -> None:
    redis = get_core_redis()
    scoped_conversation_id = f"{owner_scope}:{conversation_id}"
    data_key, max_key = _conversation_keys(scoped_conversation_id)
    arguments: list[str] = [
        str(settings.PII_MAP_MAX_TTL_SECONDS),
        str(settings.PII_MAP_IDLE_TTL_SECONDS),
    ]
    for token, value in mappings.items():
        arguments.extend((token, _encrypt(value, token)))
    await redis.eval(_MAX_TTL_SCRIPT, 2, data_key, max_key, *arguments)


async def get_pii_mappings(
    conversation_id: str, owner_scope: str
) -> dict[str, str]:
    redis = get_core_redis()
    scoped_conversation_id = f"{owner_scope}:{conversation_id}"
    data_key, max_key = _conversation_keys(scoped_conversation_id)
    hard_ttl = await redis.ttl(max_key)
    if hard_ttl <= 0:
        return {}
    mapping = await redis.hgetall(data_key)
    if not mapping:
        return {}
    idle_ttl = min(settings.PII_MAP_IDLE_TTL_SECONDS, hard_ttl)
    await redis.expire(data_key, idle_ttl)
    return {
        token: _decrypt(encrypted, token) for token, encrypted in mapping.items()
    }


async def delete_pii_mappings(conversation_id: str, owner_scope: str) -> None:
    redis = get_core_redis()
    scoped_conversation_id = f"{owner_scope}:{conversation_id}"
    data_key, max_key = _conversation_keys(scoped_conversation_id)
    await redis.delete(data_key, max_key)


def owner_token_digest(token: str) -> str:
    return hmac.new(_encryption_key(), token.encode("utf-8"), hashlib.sha256).hexdigest()


async def save_result_owner(event_id: UUID | str, token: str) -> None:
    redis = get_core_redis()
    key = f"{_OWNER_PREFIX}:{event_id}"
    await redis.set(
        key,
        owner_token_digest(token),
        ex=settings.AGENT_RESULT_TTL_SECONDS + 60,
    )


async def touch_result_owner(event_id: UUID | str) -> None:
    redis = get_core_redis()
    await redis.expire(
        f"{_OWNER_PREFIX}:{event_id}", settings.AGENT_RESULT_TTL_SECONDS + 60
    )


async def is_result_owner(event_id: UUID | str, token: str) -> bool:
    redis = get_core_redis()
    saved_digest = await redis.get(f"{_OWNER_PREFIX}:{event_id}")
    if not saved_digest:
        return False
    return hmac.compare_digest(saved_digest, owner_token_digest(token))
