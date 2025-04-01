from flask import Blueprint, request, jsonify
from googlestorage import upload_product_image, upload_scan_history_image
from models import db, Product, ScanHistory

# Определяем Blueprints для маршрутов
google_routes = Blueprint('google_routes', __name__)

# Маршрут для загрузки изображения продукта
@google_routes.route('/upload_product_image', methods=['POST'])
def upload_product_image_route_func():
    file = request.files.get('image')  # Получаем файл из запроса
    product_name = request.form.get('product_name')  # Имя продукта

    if file:
        image_url = upload_product_image(file, product_name)  # Загрузка в GCS
        new_product = Product(name=product_name, image=image_url)
        db.session.add(new_product)
        db.session.commit()
        return jsonify({"message": "Изображение продукта загружено успешно", "image_url": image_url}), 200
    else:
        return jsonify({"error": "Файл не найден"}), 400


# Маршрут для загрузки изображения истории сканирования
@google_routes.route('/upload_scan_history_image', methods=['POST'])
def upload_scan_history_image_route_func():
    file = request.files.get('image')  # Получаем файл из запроса
    product_name = request.form.get('product_name')  # Имя продукта

    if file:
        image_url = upload_scan_history_image(file, product_name)  # Загрузка в GCS
        new_scan_history = ScanHistory(product_name=product_name, image=image_url)
        db.session.add(new_scan_history)
        db.session.commit()
        return jsonify({"message": "Изображение истории сканирования загружено успешно", "image_url": image_url}), 200
    else:
        return jsonify({"error": "Файл не найден"}), 400
