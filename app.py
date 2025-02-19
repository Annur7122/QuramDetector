import os
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from models import db, Product
from flask_migrate import Migrate

app = Flask(__name__)

# Настройки базы данных
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:user@localhost/QuramDatabase'
app.debug = True

db.init_app(app)
migrate = Migrate(app, db)

# Настройки загрузки файлов
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Создаем папку uploads, если ее нет
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


# Функция проверки расширения файла
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# API для загрузки изображений
@app.route('/process-images', methods=['POST'])
def process_images():
    if 'file' not in request.files:
        return jsonify({"error": "Файл не найден"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "Файл не выбран"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Неверный формат файла"}), 400

    # Сохраняем файл
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    return jsonify({"message": "Файл успешно загружен", "file_path": filepath}), 200


# Тестовый маршрут
@app.route('/test', methods=['GET'])
def test():
    return {'test': 'test1'}

@app.route('/product/<int:product_id>', methods=['GET'])
def get_product(product_id):
    product = Product.query.get(product_id)
    if not product:
        return jsonify({"error": "Продукт не найден"}), 404

    return jsonify({
        "id": product.id,
        "name": product.name,
        "image": product.image,
        "ingredients": product.ingredients
    }), 200


if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Создаём таблицы, если их нет
    app.run(debug=True)
