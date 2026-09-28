from dotenv import load_dotenv
import os

load_dotenv()


class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    SESSION_SECRET_KEY: str = os.getenv("SESSION_SECRET_KEY", "")
    SESSION_MAX_AGE_SECONDS: int = int(os.getenv("SESSION_MAX_AGE_SECONDS", "3600"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    def validate(self):
        if not self.DATABASE_URL:
            raise RuntimeError("DATABASE_URL is not set in .env")
        if not self.SESSION_SECRET_KEY:
            raise RuntimeError("SESSION_SECRET_KEY is not set in .env")


settings = Settings()
