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

def get_alternative_products(product):
    """Получение альтернативных продуктов с сортировкой по схожести"""
    if not product.description:
        return []

    # Разбиваем ключевые слова текущего продукта
    keywords = set(product.description.name.lower().split(", "))

    # Поиск продуктов, у которых description.name содержит хотя бы одно слово из keywords
    alternatives = Product.query.join(Description).filter(
        Product.id != product.id,  # Исключаем сам продукт
        or_(*[Description.name.ilike(f"%{word}%") for word in keywords])
    ).all()

    # **Добавляем сортировку по количеству совпадений**
    def count_matches(alt):
        alt_keywords = set(alt.description.name.lower().split(", "))
        return len(keywords & alt_keywords)  # Количество пересечений

    # Сортируем альтернативы по количеству совпадений (от большего к меньшему)
    sorted_alternatives = sorted(alternatives, key=count_matches, reverse=True)

    return [{"id": alt.id, "name": alt.name, "image": alt.image} for alt in sorted_alternatives]