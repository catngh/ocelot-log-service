from typing import Callable
from fastapi import FastAPI
from app.db.mongodb import connect_to_mongo, close_mongo_connection


def startup_event_handler(app: FastAPI) -> Callable:
    """
    FastAPI startup event handler.
    """
    async def start_app() -> None:
        connect_to_mongo()
        print("Application startup complete")
    
    return start_app


def shutdown_event_handler(app: FastAPI) -> Callable:
    """
    FastAPI shutdown event handler.
    """
    async def stop_app() -> None:
        close_mongo_connection()
        print("Application shutdown complete")
    
    return stop_app 