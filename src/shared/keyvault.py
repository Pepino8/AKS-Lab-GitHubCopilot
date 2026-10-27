"""Azure Key Vault secret hydration helper."""

from __future__ import annotations

import os

import structlog
from azure.identity.aio import DefaultAzureCredential
from azure.keyvault.secrets.aio import SecretClient

log = structlog.get_logger(__name__).bind(service="keyvault-hydration")

_SECRET_MAP: dict[str, str] = {
    "GITHUB-TOKEN": "GITHUB_TOKEN",
    "INVENTORY-MCP-URL": "ZAVA_INVENTORY_MCP_URL",
    "SUPPLIER-MCP-URL": "ZAVA_SUPPLIER_MCP_URL",
    "SHIPPING-MCP-URL": "ZAVA_SHIPPING_MCP_URL",
    "PRICING-MCP-URL": "ZAVA_PRICING_MCP_URL",
}


async def hydrate_from_keyvault(vault_url: str | None = None) -> None:
    """Hydrate environment variables from Azure Key Vault if configured.

    Does not overwrite environment variables that are already set.
    Uses async SecretClient and closes credentials cleanly in a finally block.
    """
    url = vault_url or os.getenv("ZAVA_KV_URL")
    if not url:
        return

    log.info("keyvault.hydrate.start", vault_url=url)
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=url, credential=credential)
    try:
        for secret_name, env_name in _SECRET_MAP.items():
            if os.getenv(env_name):
                continue
            try:
                secret = await client.get_secret(secret_name)
                if secret.value:
                    os.environ[env_name] = secret.value
                    log.info("keyvault.hydrate.set", secret_name=secret_name, env_var=env_name)
            except Exception as e:
                log.warning("keyvault.hydrate.skipped", secret_name=secret_name, error=str(e))
    finally:
        await client.close()
        await credential.close()
        log.info("keyvault.hydrate.complete")
