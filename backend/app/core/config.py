from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # OpenAI
    openai_api_key: str = ""
    embedding_model: str = "text-embedding-3-large"
    chat_model: str = "gpt-4o"

    # Chat model provider toggle — "openai" (always used in production) or
    # "groq" (free/fast, for local testing only, so it doesn't burn paid
    # OpenAI quota). Embeddings always stay on OpenAI regardless. Groq's API
    # is OpenAI-compatible, so this reuses ChatOpenAI with a different
    # base_url — no separate SDK/dependency needed.
    chat_provider: str = "openai"
    groq_api_key: str = ""
    groq_chat_model: str = "llama-3.3-70b-versatile"

    # Qdrant
    qdrant_url: str = "http://qdrant:6333"
    qdrant_collection: str = "digi_knowledge_base"

    # Auth
    jwt_secret: str = "change-me-in-prod"
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 8
    app_username: str = "demo@digitrends.ai"
    # bcrypt hash of the demo password, generated at setup time — never store plaintext
    app_password_hash: str = ""

    # CORS
    allowed_origins: str = "http://localhost:3000"


settings = Settings()
