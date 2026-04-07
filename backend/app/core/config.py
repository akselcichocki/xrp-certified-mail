from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ENVIRONMENT: str = "dev"
    XRP_NETWORK: str = "testnet"  # mainnet | testnet | devnet
    XRP_WALLET_SEED: Optional[str] = None
    LOG_LEVEL: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
