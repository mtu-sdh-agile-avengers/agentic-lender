from pydantic_settings import BaseSettings, SettingsConfigDict

class Config(BaseSettings):
    google_application_credentials : str
    
    model_config = SettingsConfigDict(
        env_file=".env"
    )

config = Config() # pyright: ignore[reportCallIssue]