from fastapi import HTTPException


class ApiError(HTTPException):
    """base exception class for all modules"""
