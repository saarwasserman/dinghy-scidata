from pydantic_settings import BaseSettings, SettingsConfigDict
from openai import OpenAI


class Settings(BaseSettings):
    openai_api_key: str
    openai_project_id: str
    openai_organization_id: str
    
    model_config = SettingsConfigDict(env_file=".env")
    

settings = Settings()
