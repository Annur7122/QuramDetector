# utils.py
from flask import jsonify
from flask_jwt_extended import get_jwt_identity
from functools import wraps
from models import User, Product, Description
from sqlalchemy import or_, func


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

def get_alternative_products_endpoint(description_id):
    # Ищем все продукты с переданным description_id
    alternatives = Product.query.filter_by(description_id=description_id).all()

    # Если альтернатив нет, возвращаем пустой список
    if not alternatives:
        return jsonify({"status": "error", "message": "Альтернативные продукты не найдены"}), 404

    # Формируем список альтернативных продуктов
    alternative_products = [
        {
            "id": alt.id,
            "name": alt.name,
            "image": alt.image,
        }
        for alt in alternatives
    ]

    return alternative_products