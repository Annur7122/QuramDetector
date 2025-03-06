from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Notification, User

notification_routes = Blueprint('notification_routes', __name__)

# **1. Отправка уведомления (админский эндпоинт)**
@notification_routes.route('/send', methods=['POST'])
@jwt_required()
def send_notification():
    data = request.get_json()
    user_id = data.get("user_id")  # Если None, то уведомление для всех
    news_description = data.get("news_description")

    if not news_description:
        return jsonify({"status": "error", "message": "Описание уведомления не может быть пустым"}), 400

    is_global = user_id is None  # Если user_id не указан, значит уведомление для всех

    new_notification = Notification(user_id=user_id, news_description=news_description, is_global=is_global)
    db.session.add(new_notification)
    db.session.commit()

    message = "Общее уведомление отправлено всем пользователям" if is_global else f"Уведомление отправлено пользователю ID {user_id}"
    return jsonify({"status": "success", "message": message}), 201


# **2. Получение уведомлений текущего пользователя**
@notification_routes.route('/', methods=['GET'])
@jwt_required()
def get_notifications():
    current_user_id = get_jwt_identity()

    # Получаем как персональные уведомления, так и глобальные
    notifications = Notification.query.filter(
        (Notification.user_id == current_user_id) | (Notification.is_global == True)
    ).order_by(Notification.created_at.desc()).all()

    notification_list = [{
        "id": n.id,
        "news_description": n.news_description,
        "created_at": n.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        "is_global": n.is_global
    } for n in notifications]

    return jsonify({"status": "success", "data": {"notifications": notification_list}}), 200


# **3. Получение всех уведомлений (для админа)**
@notification_routes.route('/all', methods=['GET'])
@jwt_required()
def get_all_notifications():
    notifications = Notification.query.order_by(Notification.created_at.desc()).all()

    notification_list = [{
        "id": n.id,
        "user_id": n.user_id,
        "news_description": n.news_description,
        "created_at": n.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        "is_global": n.is_global
    } for n in notifications]

    return jsonify({"status": "success", "data": {"notifications": notification_list}}), 200
