import traceback

from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate

from admin_routes import admin_routes
from gcs_setting import gcs_routes
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
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://quramdb:8EseRnDEm703Y9M2y1U6rdrujKkDXuiq@dpg-d08uspidbo4c73ebchf0-a.oregon-postgres.render.com/quramdb'
# app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://postgres:root@localhost:5433/postgres"
app.debug = True

app.config['JWT_SECRET_KEY'] = 'your_secret_key'  # Секретный ключ для подписи JWT
jwt = JWTManager(app)

app.register_blueprint(auth, url_prefix='/auth')
app.register_blueprint(admin_routes)

from notification_routes import notification_routes
app.register_blueprint(notification_routes, url_prefix='/notifications')
app.register_blueprint(gcs_routes)

db.init_app(app)
migrate = Migrate(app, db)

app.register_blueprint(routes)
@app.before_request
def handle_options():
    """Разрешаем OPTIONS-запросы без проверки JWT"""
    if request.method == "OPTIONS":
        return "", 200  # Отдаем пустой 200 OK, чтобы CORS работал нормально

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


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    print(app.url_map)

    app.run(debug=True)




