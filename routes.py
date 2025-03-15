from operator import or_
import ast
import re
from flask import Blueprint, request, jsonify
from sqlalchemy.orm import joinedload
from werkzeug.utils import secure_filename
import os
import json
from check import check_halal_status
from image_processor import extract_text_from_image
from models import db, Product, Description, Review, User, Favourite, ScanHistory
from flask_jwt_extended import jwt_required,get_jwt_identity
import base64
import google.generativeai as genai
from dotenv import load_dotenv

from utils import get_alternative_products

load_dotenv()

routes = Blueprint('routes', __name__)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash') #using gemini-pro-vision to send images.

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# Ensure upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    """Check if uploaded file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@routes.route("/process-images", methods=["POST"])
def process_images():
    """Extracts text from an image using Gemini API and checks ingredients for Halal compliance."""

    # Step 1: Validate file
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "Файл не найден", "code": 400}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"status": "error", "message": "Файл не выбран", "code": 400}), 400

    if not allowed_file(file.filename):
        return jsonify({"status": "error", "message": "Неверный формат файла", "code": 400}), 400

    # Step 2: Save file securely
    try:
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
    except Exception as e:
        return jsonify({"status": "error", "message": f"Ошибка сохранения файла: {str(e)}", "code": 500}), 500

    try:
        # Step 3: Convert image to Base64 for Gemini
        with open(filepath, "rb") as image_file:
            img_b64_str = base64.b64encode(image_file.read()).decode("utf-8")
        img_type = file.content_type

        # Step 4: Send image to Gemini for OCR and ingredient extraction
        response = model.generate_content([
            "Ты OCR-ассистент, твоя задача – извлекать состав продукта из текста на изображении. "
            "Неважно, на каком языке состав указан. Твоя цель:  \n\n"
            "1. Извлечь все ингредиенты и добавки (например: \"вода\", \"сок манго\", \"кислота\", \"сукралоза\", \"E102\", \"E110\").  \n"
            "2. Если видишь элементы вида \"E100\", \"E121\" и любые другие добавки с префиксом E, выделяй их отдельно как индивидуальные элементы.  \n"
            "3. Всегда возвращай результат в строго формате JSON-массива (list), например:    \n"
            "   [\"вода\", \"сок манго\", \"кислота\", \"сукралоза\", \"пищевые красители\", \"E102\", \"E110\"]  \n"
            "4. Никакой другой формы ответа, только JSON-массив.",
            {
                "mime_type": file.content_type,
                "data": img_b64_str
            }
        ])

        # Step 4: Parsing the response from Gemini
        extracted_text = response.text.strip()

        # Extract JSON using regex
        match = re.search(r'\[.*\]', extracted_text, re.DOTALL)
        if match:
            json_str = match.group(0)
        else:
            return jsonify({
                "status": "error",
                "message": f"Ошибка извлечения JSON: {extracted_text}",
                "code": 500
            }), 500

        # Safe JSON parsing
        try:
            ingredients_list = json.loads(json_str)
        except json.JSONDecodeError as e:
            return jsonify({
                "status": "error",
                "message": f"Ошибка обработки JSON: {extracted_text}, Ошибка: {e}",
                "code": 500
            }), 500

        # Step 6: Check Halal status
        halal_status_result = check_halal_status(ingredients_list)

        # Step 7: Return processed response
        return jsonify({
            "status": "success",
            "message": "Файл успешно загружен",
            "data": {
                "file_path": filepath,
                "extracted_text": ingredients_list,
                "status": halal_status_result["status"],
                "found_ingredients": halal_status_result["found_ingredients"]
            }
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Ошибка обработки изображения: {str(e)}",
            "code": 500
        }), 500



# testprocess-images for frontend
@routes.route("/process-images1", methods=["POST"])
def process_images1():
    """Extract text from an image using GPT-4o OCR and check if ingredients are Halal/Haram."""

    # Step 1: Validate File
    if "file" not in request.files:
        return jsonify({"status": "error", "message": "Файл не найден", "code": 400}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"status": "error", "message": "Файл не выбран", "code": 400}), 400

    if not allowed_file(file.filename):
        return jsonify({"status": "error", "message": "Неверный формат файла", "code": 400}), 400

    # Step 2: Save File Securely
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    try:
        # Step 3: Convert Image to Base64 for OpenAI
        file.seek(0)  # Reset file pointer to beginning
        img_b64_str = base64.b64encode(file.read()).decode("utf-8")
        img_type = file.content_type  # Get content type (e.g., "image/png")

        # Step 5: Parse Response

        ingredients_list = ["вода", "сахар", "диоксид углерода", "карамельный краситель E150d", "ортофосфорная кислота", "натриевый бензоат", "натуральные ароматизаторы", "кофеин"]

        # Проверяем статус
        halal_status = check_halal_status(ingredients_list)
        current_user_id = get_jwt_identity()

        # Сохранение сканирования
        scan_entry = ScanHistory(
            user_id=current_user_id,
            product_name="Неизвестно",  # Название может добавить админ
            image=filepath,
            ingredients=", ".join(ingredients_list),
            status=halal_status["status"],
            haram_ingredients=", ".join(halal_status["found_ingredients"])
        )
        db.session.add(scan_entry)
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "Сканирование завершено",
            "data": {
                "scan_id": scan_entry.id,
                "status": halal_status["status"],
                "found_ingredients": halal_status["found_ingredients"]
            }
        }), 200



    except Exception as e:
        return jsonify({"status": "error", "message": f"Ошибка обработки изображения: {str(e)}"}), 500


@routes.route("/scan-history", methods=["GET"])
def get_scan_history():
    scans = ScanHistory.query.filter_by(user_id=get_jwt_identity()).order_by(ScanHistory.scan_date.desc()).all()

    scan_data = [{
        "id": scan.id,
        "product_name": scan.product_name,
        "status": scan.status,
        "haram_ingredients": scan.haram_ingredients,
        "scan_date": scan.scan_date.strftime('%Y-%m-%d %H:%M:%S')
    } for scan in scans]

    return jsonify({"status": "success", "history": scan_data}), 200

@routes.route('/test', methods=['GET'])
@jwt_required()
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

    product.count += 1  # Увеличиваем счётчик
    db.session.commit()

    reviews = Review.query.filter_by(product_id=product.id).all()

    review_list = [{
        "id": r.id,
        "user_id": r.user_id,
        "review_description": r.review_description,
        "stars": r.stars
    } for r in reviews]

    return jsonify({
        "status": "success",
        "data": {
            "id": product.id,
            "name": product.name,
            "image": product.image,
            "ingredients": product.ingredients,
            "reviews": review_list
        }
    }), 200


@routes.route("/product/<int:product_id>/alternatives", methods=["GET"])
@jwt_required()
def get_alternative_products_endpoint(product_id):
    """Эндпоинт для получения альтернативных продуктов"""
    product = Product.query.get(product_id)

    if not product:
        return jsonify({"status": "error", "message": "Продукт не найден"}), 404

    alternatives = get_alternative_products(product)
    return jsonify({"status": "success", "data": alternatives}), 200


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

@routes.route('/top-products', methods=['GET'])
def get_top_products():
    top_products = Product.query.order_by(Product.count.desc()).limit(3).all()

    product_list = [{
        "id": p.id,
        "name": p.name,
        "image": p.image,
        "ingredients": p.ingredients,
        "count": p.count
    } for p in top_products]

    return jsonify({
        "status": "success",
        "data": {
            "products": product_list
        }
    }), 200



@routes.route('/search', methods=['GET'])
def search_products():
    query = request.args.get('q', '').strip()

    if not query:
        return jsonify({"status": "error", "message": "Введите поисковый запрос"}), 400




    try:
        products = db.session.query(Product).join(Description).filter(
            or_(
                Product.name.ilike(f"%{query}%"),
                Description.name.ilike(f"%{query}%")
            )
        ).options(joinedload(Product.description)).all()

        if not products:
            return jsonify({"status": "error", "message": "Продукт не найден"}), 404

        product_list = [{
            "id": p.id,
            "name": p.name,
            "image": p.image,
            "ingredients": p.ingredients,
            "description": p.description.name if p.description else None
        } for p in products]

        return jsonify({"status": "success", "data": {"products": product_list}}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": f"Ошибка запроса: {str(e)}"}), 500


@routes.route('/reviews', methods=['POST'])
@jwt_required()
def add_review():
    current_user_id = get_jwt_identity()  # Получаем ID залогиненного пользователя
    user = User.query.get(current_user_id)

    if not user:
        return jsonify({"status": "error", "message": "Пользователь не найден"}), 401

    data = request.get_json()
    product_id = data.get("product_id")
    review_description = data.get("review_description", "")
    stars = data.get("stars")

    if not all([product_id, stars]):
        return jsonify({"status": "error", "message": "product_id и stars обязательны"}), 400

    product = Product.query.get(product_id)
    if not product:
        return jsonify({"status": "error", "message": "Продукт не найден"}), 404

    new_review = Review(
        user_id=user.id,  # Берем user_id из JWT токена
        product_id=product_id,
        review_description=review_description,
        stars=stars
    )
    db.session.add(new_review)
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Отзыв добавлен",
        "data": {
            "user_id": user.id,
            "user_name": user.name,
            "review_description": review_description,
            "stars": stars
        }
    }), 201

@routes.route('/favourites/toggle', methods=['POST'])
@jwt_required()
def toggle_favourite():
    """Добавить или удалить продукт из избранного"""
    user_id = get_jwt_identity()  # Получаем ID текущего пользователя
    data = request.get_json()
    product_id = data.get("product_id")

    if not product_id:
        return jsonify({"status": "error", "message": "product_id обязателен"}), 400

    product = Product.query.get(product_id)
    if not product:
        return jsonify({"status": "error", "message": "Продукт не найден"}), 404

    # Проверяем, есть ли уже продукт в избранном
    favourite = Favourite.query.filter_by(user_id=user_id, product_id=product_id).first()

    if favourite:
        # Если продукт уже в избранном, удаляем его
        db.session.delete(favourite)
        db.session.commit()
        return jsonify({"status": "success", "message": "Продукт удалён из избранного"}), 200
    else:
        # Если продукта нет в избранном, добавляем его
        new_fav = Favourite(user_id=user_id, product_id=product_id)
        db.session.add(new_fav)
        db.session.commit()
        return jsonify({"status": "success", "message": "Продукт добавлен в избранное"}), 201

@routes.route('/favourites', methods=['GET'])
@jwt_required()
def get_favourites():
    """Получить список избранных продуктов пользователя"""
    user_id = get_jwt_identity()

    favourites = (
        db.session.query(Product)
        .join(Favourite, Product.id == Favourite.product_id)
        .filter(Favourite.user_id == user_id)
        .all()
    )

    products_list = [
        {"id": p.id, "name": p.name, "image": p.image, "ingredients": p.ingredients}
        for p in favourites
    ]

    return jsonify({"status": "success", "data": {"favourites": products_list}}), 200
