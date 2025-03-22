from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# Пользователь
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password = db.Column(db.String(255), nullable=False)
    phone_number = db.Column(db.String(20), unique=True, nullable=True)
    city = db.Column(db.String(100), nullable=True)
    authority = db.Column(db.String(50), default="user")

    favourites = db.relationship('Favourite', backref='user', lazy=True)
    history = db.relationship('ScanHistory', backref='user', lazy=True)
    reviews = db.relationship('Review', backref='user', lazy=True)
    notifications = db.relationship('Notification', backref='user', lazy=True)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

# Категория продукта (для поиска альтернатив)
class Description(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), unique=True, nullable=False)
    products = db.relationship('Product', backref='description', lazy=True)

# Продукт
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    image = db.Column(db.String(300), nullable=True)
    ingredients = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    description_id = db.Column(db.Integer, db.ForeignKey('description.id'), nullable=True)
    count = db.Column(db.Integer, default=0)
    status = db.Column(db.String(50), nullable=True, default="Неизвестно",server_default='pending')  # "Харам", "Халал" или "Неизвестно"
    haram_ingredients = db.Column(db.Text, nullable=True)  # Харамные ингредиенты через запятую

    reviews = db.relationship('Review', backref='product', lazy=True)
    scan_result = db.relationship('ScanResult', backref='product', uselist=False)

# Результат проверки продукта
class ScanResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), unique=True, nullable=False)
    status = db.Column(db.String(10), nullable=False)  # ✅ / ⚠️ / ❌

# История проверок
class ScanHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Кто сканировал
    product_name = db.Column(db.String(200), nullable=False)  # Название, если продукта еще нет в БД
    image = db.Column(db.String(300), nullable=True)  # Фото упаковки или состава
    ingredients = db.Column(db.Text, nullable=True)  # Извлеченные ингредиенты
    scan_date = db.Column(db.DateTime, default=datetime.utcnow)  # Дата сканирования
    status = db.Column(db.String(50), nullable=False)  # "Халал", "Харам", "Подозрительно"
    haram_ingredients = db.Column(db.Text, nullable=True)  # Найденные харамные ингредиенты
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=True)  # Если продукт уже есть в базе
    is_processed = db.Column(db.Boolean, default=False)
    description_id = db.Column(db.Integer, db.ForeignKey('description.id'), nullable=True)

    reviews = db.relationship('Review', backref='scan_history', lazy=True)
  
# Избранное
class Favourite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    __table_args__ = (db.UniqueConstraint('user_id', 'product_id', name='unique_fav'),)

# Отзывы
class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    scan_history_id = db.Column(db.Integer, db.ForeignKey('scan_history.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=True)
    review_description = db.Column(db.Text, nullable=True)
    stars = db.Column(db.Integer, nullable=False)

# Уведомления / Новости
class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    news_description = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_global = db.Column(db.Boolean, default=False)

class BaseModel(db.Model):
    __abstract__ = True
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Ingredient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'halal' или 'haram'



