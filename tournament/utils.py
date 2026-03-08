import secrets
from django.utils import timezone

def generate_invitation_token():
    """Генерирует уникальный токен для приглашения"""
    return secrets.token_urlsafe(32)