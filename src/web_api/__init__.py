"""Web API package / Plugin Pages 后端 API 包"""
from .data_admin import register_data_apis
from .registry import register_web_apis

__all__ = [
    "register_web_apis",
    "register_data_apis",
]
