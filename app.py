import traceback

from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate

from admin_routes import admin_routes
from models import db, User
from routes import routes
from flask_jwt_extended import JWTManager
# Подключаем Blueprint с аутентификацией
from auth import auth
from flask import request, jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from functools import wraps


app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://quramdb2:9P3RoNtzfA08JVXClmUgTXE1fH3D7Ys8@dpg-cuua60qj1k6c73dojbt0-a.oregon-postgres.render.com/quramdb2'
app.debug = True

app.config['JWT_SECRET_KEY'] = 'your_secret_key'  # Секретный ключ для подписи JWT
jwt = JWTManager(app)

app.register_blueprint(auth, url_prefix='/auth')
app.register_blueprint(admin_routes)

from notification_routes import notification_routes
app.register_blueprint(notification_routes, url_prefix='/notifications')

db.init_app(app)
migrate = Migrate(app, db)

app.register_blueprint(routes)

@app.before_request
def check_auth():
    open_routes = ['/auth/login', '/auth/register']  
    if request.path.startswith(tuple(open_routes)):  
        return  

    try:
        print(f"🔍 Проверка JWT для запроса: {request.path}")
        verify_jwt_in_request()
        print("✅ JWT-токен успешно проверен")
    except Exception as e:
        print("❌ Ошибка при проверке JWT-токена")
        traceback.print_exc()
        return jsonify({"error": "Необходима авторизация"}), 401

def admin_required(fn):
    """Декоратор для ограничения доступа к эндпоинтам только для админов"""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        current_user_id = get_jwt_identity()  # Получаем ID пользователя из JWT
        user = User.query.get(current_user_id)  # Ищем пользователя в базе

        if not user or user.authority != "admin":
            return jsonify({"status": "error", "message": "Доступ запрещен"}), 403

        return fn(*args, **kwargs)  # Выполняем исходную функцию, если админ
    return wrapper



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    print(app.url_map)

    app.run(debug=True)




