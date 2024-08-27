from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str
    API_V1_STR: str
    DATABASE_URL: str
    ALGORITHM: str
    SECRET_KEY: str
    SECRET_ID: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_MINUTES: int
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    #
    class Config:
        env_file = ".env"

settings = Settings()

