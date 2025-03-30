from datetime import datetime
from operator import or_
import ast
import re
from flask import Blueprint, request, jsonify
import requests
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
import psycopg2

from utils import get_alternative_products_endpoint

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
DB_URL = "postgresql://quramdb3:cUaVicWuj17LnZDz5a0wCzd6UVzvxZKa@dpg-cvighqqdbo4c73cklfr0-a.oregon-postgres.render.com/quramdb3"

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
    """Extracts text from an image, determines product category, checks ingredients for Halal compliance."""

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
        # Step 3: Convert image to Base64 for Gemini OCR
        with open(filepath, "rb") as image_file:
            img_b64_str = base64.b64encode(image_file.read()).decode("utf-8")

        # Step 4: Extract ingredients from image using Gemini
        response = model.generate_content([
            "Ты OCR-ассистент, твоя задача – извлекать состав продукта из текста на изображении.\n\n"
            "Инструкция:\n"
            "1. Извлеки **только состав продукта, написанный на русском или казахском языках**. "
            "Игнорируй текст на всех других языках.\n"
            "2. Выдели все ингредиенты и добавки отдельно (например: \"вода\", \"сок манго\", \"қышқыл\", \"сукралоза\", \"лимонная кислота\", \"E102\", \"E110\").\n"
            "3. Если встречаются добавки вида \"E100\", \"E121\" и другие с префиксом E, выделяй их отдельно как индивидуальные элементы.\n"
            "4. Верни результат строго в формате JSON-массива, без дополнительных комментариев или пояснений.",
        {
            "mime_type": file.content_type,
            "data": img_b64_str
         }
        ])

        # Step 5: Parsing the response from Gemini
        extracted_text = response.text.strip()

        # Extract JSON using regex
        match = re.search(r'\[.*\]', extracted_text, re.DOTALL)
        if match:
            json_str = match.group(0)
        else:
            return jsonify({"status": "error", "message": f"Ошибка извлечения JSON: {extracted_text}", "code": 500}), 500

        # Parse JSON safely
        try:
            ingredients_list = json.loads(json_str)
        except json.JSONDecodeError as e:
            return jsonify({"status": "error", "message": f"Ошибка обработки JSON: {extracted_text}, Ошибка: {e}", "code": 500}), 500

        # Step 6: Generate category using AI
        ai_category = generate_category_ai(ingredients_list)

        # Step 7: Check if category exists in DB
        category_db_name, description_id = find_existing_category(ai_category)

        if not description_id:
            # Category doesn't exist, insert new category
            description_id = insert_category(ai_category)
            final_category = ai_category
        else:
            final_category = category_db_name

        # Step 8: Check halal status
        halal_result = check_halal_status(ingredients_list)
        halal_status = halal_result["status"]
        found_ingredients = halal_result["found_ingredients"]

        # Debugging Logs
        print(f"Final category: {final_category}")
        print(f"Description ID: {description_id} (type: {type(description_id)})")
        print(f"Found Haram Ingredients: {found_ingredients}")

        # Step 9: Insert product to DB
        insert_product(ingredients_list, filepath, halal_status, description_id, found_ingredients)

        new_scan = ScanHistory(
            user_id=get_jwt_identity(),
            product_name=final_category,
            image=filepath,
            ingredients=", ".join(ingredients_list),  # Список ингредиентов как текст
            scan_date=datetime.utcnow(),
            status=halal_status,
            haram_ingredients=", ".join(found_ingredients) if found_ingredients else None,
            description_id=description_id
            # Харамные ингредиенты, если есть
        )

        db.session.add(new_scan)
        db.session.commit()

        alternatives_data = get_alternative_products_endpoint(description_id)

        # Step 10: Return response
        return jsonify({
            "status": "success",
            "message": "Файл успешно загружен",
            "data": {
                "file_path": filepath,
                "extracted_text": ingredients_list,
                "category": final_category,
                "description_id": description_id,
                "halal_status": halal_status,
                "found_ingredients": found_ingredients,
                "alternatives_data": alternatives_data
            }
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": f"Ошибка обработки изображения: {str(e)}", "code": 500}), 500
    
def find_existing_category(category_name):
    """Check if the given category exists in the description table."""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    category_name = category_name.lower().strip()

    # Check if category exists using a case-insensitive search
    cur.execute("SELECT id, name FROM description WHERE LOWER(name) LIKE %s", (f"%{category_name}%",))
    result = cur.fetchone()

    conn.close()

    if result:
        return result[1], result[0]  # Return category name and ID
    return None, None  # If not found, return None


def generate_category_ai(ingredients):
    """Generates a precise food category based on ingredients, choosing from existing categories when possible."""
    
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("SELECT name FROM description")
    existing_categories = [row[0].lower() for row in cur.fetchall()]
    conn.close()

    prompt = (
        "Ты эксперт по классификации продуктов. Определи категорию продукта по его составу.\n\n"
        "Существующие категории: " + ", ".join(existing_categories) + ".\n\n"
        f"Ингредиенты продукта: {', '.join(ingredients)}.\n\n"
        "Инструкция:\n"
        "- Если продукт подходит под одну из существующих категорий, выбери её и напиши ТОЛЬКО её название.\n"
        "- Если ни одна из категорий не подходит, предложи новую краткую категорию (1-2 слова).\n\n"
        "Ответь строго **ТОЛЬКО названием категории** без пояснений и дополнительных комментариев.\n"
        "Примеры ответов: сок, газировка, молочный напиток, йогурт."
    )

    response = model.generate_content(prompt)
    raw_category = response.text.strip().lower()

    # **Sanitize the output**
    clean_category = sanitize_category(raw_category)

    return clean_category



def sanitize_category(category_text):
    """Ensures AI-generated category is concise, formatted correctly, and meaningful."""
    category_text = category_text.strip()

    # Extract only the first phrase before punctuation or explanations
    category_text = re.split(r'[.,;:\-—]', category_text)[0]

    # Remove unnecessary words and special characters
    category_text = re.sub(r"[^а-яА-ЯёЁa-zA-Z0-9 ]", "", category_text).strip()

    # If AI response is invalid, set it as 'неизвестно'
    if category_text in ["ингредиенты продукта", "не могу определить", "без категории", "не знаю"]:
        return "неизвестно"

    # Ensure category is at most 2 words
    category_words = category_text.split()
    category_text = " ".join(category_words[:2])

    return category_text.lower()


def insert_category(category_name):
    """Inserts a new category into the database."""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    cur.execute("INSERT INTO description (name) VALUES (%s) RETURNING id", (category_name,))
    category_id = cur.fetchone()[0]
    conn.commit()
    conn.close()

    return category_id


def insert_product(ingredients, image_path, halal_status, description_id, found_ingredients):
    """Inserts the product details into the database."""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    ingredients_str = ", ".join(ingredients)
    haram_ingredients_str = ", ".join(found_ingredients) if found_ingredients else None

    # Ensure description_id is valid
    if description_id is None:
        raise ValueError("description_id is None, cannot insert into database.")

    cur.execute(
        """
        INSERT INTO product (name, image, ingredients, status, description_id, haram_ingredients)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        ("Scanned Product", image_path, ingredients_str, halal_status, description_id, haram_ingredients_str)
    )

    conn.commit()
    conn.close()

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

    if product.count is None:
        product.count = 0

    product.count += 1


    db.session.commit()

    reviews = db.session.query(Review, User.name).join(User, Review.user_id == User.id).filter(
        Review.product_id == product.id).all()

    review_list = [{
        "id": r.Review.id,
        "user_id": r.Review.user_id,
        "user_name": r.name,  # Добавили имя пользователя
        "review_description": r.Review.review_description,
        "stars": r.Review.stars
    } for r in reviews]

    return jsonify({
        "status1": "success",
        "data": {
            "id": product.id,
            "name": product.name,
            "image": product.image,
            "ingredients": product.ingredients,
            "status": product.status,
            "reviews": review_list
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


@routes.route('/scans/latest/reviews', methods=['POST'])
def add_review_latest():
    data = request.get_json()
    user_id = get_jwt_identity()
    review_description = data.get("review_description")
    stars = data.get("stars")

    print(user_id, review_description, stars)

    # Получаем последний scan_id
    latest_scan = ScanHistory.query.order_by(ScanHistory.id.desc()).first()

    if not latest_scan:
        return jsonify({"error": "No scans found"}), 404

    if not user_id or not review_description or not stars:
        return jsonify({"error": "Missing fields"}), 400

    new_review = Review(
        scan_history_id=latest_scan.id,  # Привязываем к последнему скану
        user_id=user_id,
        review_description=review_description,
        stars=stars
    )
    db.session.add(new_review)
    db.session.commit()

    return jsonify({"message": "Review added successfully", "scan_id": latest_scan.id}), 201


@routes.route('/scans/<int:scan_id>/reviews', methods=['GET'])
def get_reviews(scan_id):
    scan = ScanHistory.query.get(scan_id)
    if not scan:
        return jsonify({"error": "Scan not found"}), 404

    reviews = Review.query.filter_by(scan_history_id=scan_id).all()
    return jsonify([
        {
            "id": review.id,
            "user_id": review.user_id,
            "review_description": review.review_description,
            "stars": review.stars
        }
        for review in reviews
    ])

@routes.route('/scans', methods=['GET'])
def get_scans():
    scans = ScanHistory.query.all()
    return jsonify([
        {
            "id": scan.id,
            "user_id": scan.user_id,
            "product_name": scan.product_name,
            "scan_date": scan.scan_date,
            "status": scan.status,
            "reviews": len(scan.reviews)
        }
        for scan in scans
    ])


