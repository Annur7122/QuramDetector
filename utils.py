# utils.py
from flask import jsonify
from flask_jwt_extended import get_jwt_identity
from functools import wraps
from models import User

def admin_required(fn):
    """Декоратор для ограничения доступа только для админов"""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        current_user_id = get_jwt_identity()  # Получаем ID пользователя
        user = User.query.get(current_user_id)  # Ищем пользователя

        if not user or user.authority != "admin":
            return jsonify({"status": "error", "message": "Доступ запрещен"}), 403

        return fn(*args, **kwargs)
    return wrapper
