from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import os

from check import check_halal_status
from image_processor import extract_text_from_image
from models import db, Product

routes = Blueprint('routes', __name__)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@routes.route('/process-images', methods=['POST'])
def process_images():
    if 'file' not in request.files:
        return jsonify({
            "status": "error",
            "message": "Файл не найден",
            "code": 400
        }), 400


    file = request.files['file']

    if file.filename == '':
        return jsonify({
            "status": "error",
            "message": "Файл не выбран",
            "code": 400
        }), 400


    if not allowed_file(file.filename):
        return jsonify({
            "status": "error",
            "message": "Неверный формат файла",
            "code": 400
        }), 400


    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    # Запускаем обработку изображения и анализ состава
    extracted_text = extract_text_from_image(filepath)
    status, found_ingredients = check_halal_status(extracted_text)

    return jsonify({
        "status": "success",
        "message": "Файл успешно загружен",
        "data": {
            "file_path": filepath,
            "extracted_text": extracted_text,
            "status": status,
            "found_ingredients": found_ingredients
        }
    }), 200



@routes.route('/test', methods=['GET'])
def test():
    return jsonify({"status": "success", "data": {"test": "test1"}}), 200

@routes.route('/product/<int:product_id>', methods=['GET'])
def get_product(product_id):
    product = Product.query.get(product_id)
    if not product:
        return jsonify({
            "status": "error",
            "message": f"Продукт с ID {product_id} не найден",
            "code": 404
        }), 404


    return jsonify({
        "status": "success",
        "data": {
            "id": product.id,
            "name": product.name,
            "image": product.image,
            "ingredients": product.ingredients
        }
    }), 200


@routes.route('/products', methods=['GET'])
def get_all_products():
    products = Product.query.all()

    product_list = [{
        "id": product.id,
        "name": product.name,
        "image": product.image,
        "ingredients": product.ingredients
    } for product in products]

    return jsonify({
        "status": "success",
        "data": {
            "products": product_list
        }
    }), 200