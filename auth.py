from flask import Blueprint, request, jsonify
from flask_bcrypt import Bcrypt
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from datetime import timedelta
from models import db, User
from werkzeug.security import generate_password_hash, check_password_hash


auth = Blueprint('auth', __name__)
bcrypt = Bcrypt()


# Регистрация пользователя
@auth.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email') or None
    phone_number = data.get('phone_number') or None
    password = data.get('password')
    city = data.get('city')

    # Проверяем, что хотя бы email или телефон указан
    if not name or not password or (not email and not phone_number):
        return jsonify({"error": "Заполните все обязательные поля"}), 400

    # Проверяем, существует ли уже пользователь с таким email или телефоном
    if email and User.query.filter_by(email=email).first():
        return jsonify({"error": "Пользователь с таким email уже существует"}), 400

    if phone_number and User.query.filter_by(phone_number=phone_number).first():
        return jsonify({"error": "Пользователь с таким номером телефона уже существует"}), 400

    # Хешируем пароль
    hashed_password = generate_password_hash(password)

    # Создаём пользователя
    new_user = User(
        name=name,
        email=email,
        phone_number=phone_number,
        password=hashed_password,
        city=city,
        authority="user"  # По умолчанию "user"
    )

    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "Регистрация успешна"}), 201


# Вход пользователя (по email или телефону)
@auth.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    identifier = data.get('identifier')  # Может быть email или phone_number
    password = data.get('password')

    if not identifier or not password:
        return jsonify({"error": "Введите email/телефон и пароль"}), 400

    # Ищем пользователя по email или телефону
    user = User.query.filter((User.email == identifier) | (User.phone_number == identifier)).first()

    if not user or not check_password_hash(user.password, password):
        return jsonify({"error": "Неверные учетные данные"}), 401

    # Создаем JWT токен (действителен 24 часа)
    access_token = create_access_token(identity=str(user.id), expires_delta=timedelta(hours=24))


    return jsonify({
        "access_token": access_token,
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "phone_number": user.phone_number,
            "authority": user.authority
        }
    }), 200


# Пример защищённого маршрута
@auth.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    return jsonify({
        "message": f"Вы авторизованы как {user.name} (ID: {user.id})",
        "authority": user.authority
    }), 200
