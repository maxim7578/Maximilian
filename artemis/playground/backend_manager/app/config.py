# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings

# Public placeholder; only acceptable outside production (see _secure_production_defaults).
DEFAULT_JWT_SECRET = "artemis-cos-production-super-secret-key-change-in-prod"
DEV_ENVIRONMENTS = {"development", "dev", "test", "local"}


class Settings(BaseSettings):
    # Application & Server Settings
    APP_NAME: str = "Artemis Backend Manager"
    APP_ENV: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    # Security & JWT Token Config
    JWT_SECRET_KEY: str = DEFAULT_JWT_SECRET
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # OTP Authentication Config
    OTP_EXPIRE_SECONDS: int = 300  # 5 minutes
    DEV_MOCK_OTP: str = "123456"  # Bypass code for dev/test environments only

    # Cross-origin access. The bundled UI calls the API from the same origin, so no
    # origin is allowed by default; list trusted origins explicitly if needed.
    CORS_ORIGINS: list[str] = []

    # Docker Socket & Ephemeral Container Settings
    DOCKER_SOCKET_PATH: str = "unix://var/run/docker.sock"
    ARTEMIS_IMAGE: str = "artemis:latest"
    DOCKER_NETWORK: str = "artemis-net"
    ARTEMIS_CONTAINER_PREFIX: str = "artemis-session"
    ARTEMIS_CPU_LIMIT: float = 2.0
    ARTEMIS_MEMORY_LIMIT: str = "2g"

    # Cloud Orchestrator & Cuttlefish Host Settings
    CLOUD_ORCHESTRATOR_URL: str = os.getenv(
        "CLOUD_ORCHESTRATOR_URL", "http://cloud-orchestrator:2081"
    )
    CUTTLEFISH_HOST_GATEWAY: str = os.getenv("CUTTLEFISH_HOST_GATEWAY", "cloud-orchestrator")
    CUTTLEFISH_START_ADB_PORT: int = 6520
    CUTTLEFISH_START_WEBRTC_PORT: int = 8443

    # Google Cloud BigQuery Settings
    GCP_PROJECT_ID: str = os.getenv("GOOGLE_CLOUD_PROJECT", "artemis-cloud-project")
    BQ_DATASET: str = "artemis_orchestration"
    BQ_TABLE: str = "sessions_registry"
    USE_LOCAL_FALLBACK_DB: bool = True  # In-memory fallback if BigQuery credentials are unset

    # Session Lifecycle & Auto-Reaper
    SESSION_TTL_MINUTES: int = 60
    SESSION_HEARTBEAT_TIMEOUT_SECONDS: int = 120
    REAPER_CHECK_INTERVAL_SECONDS: int = 30

    # Paths
    STATIC_DIR: Path = Path(__file__).resolve().parent / "static"

    class Config:
        env_file = ".env"
        extra = "allow"

    @model_validator(mode="after")
    def _secure_production_defaults(self) -> "Settings":
        """Refuse insecure development defaults outside development/test.

        Without this, a production deployment would accept the mock OTP "123456" for
        every account and sign JWTs with a secret published in the source code, so
        anyone could log in and spawn containers via the mounted Docker socket.
        """
        if self.APP_ENV.lower() in DEV_ENVIRONMENTS:
            return self
        if self.JWT_SECRET_KEY == DEFAULT_JWT_SECRET or len(self.JWT_SECRET_KEY) < 32:
            raise ValueError(
                "JWT_SECRET_KEY must be set to a random value of at least 32 characters "
                f"when APP_ENV={self.APP_ENV!r}"
            )
        if "DEV_MOCK_OTP" not in self.model_fields_set:
            self.DEV_MOCK_OTP = ""
        elif self.DEV_MOCK_OTP:
            raise ValueError(f"DEV_MOCK_OTP must be empty when APP_ENV={self.APP_ENV!r}")
        if "DEBUG" not in self.model_fields_set:
            self.DEBUG = False
        return self


settings = Settings()
