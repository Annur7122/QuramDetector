from operator import or_
import ast
from flask import Blueprint, request, jsonify
from sqlalchemy.orm import joinedload
from werkzeug.utils import secure_filename
import os
from check import check_halal_status
from image_processor import extract_text_from_image
from models import db, Product, Description, Review, User, Favourite
from flask_jwt_extended import jwt_required,get_jwt_identity
import base64
#import openai



routes = Blueprint('routes', __name__)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

openai.api_key = os.getenv("OPENAI_API_KEY")

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

        # Step 4: Send Image to GPT-4o for OCR
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Ты OCR-ассистент, твоя задача – извлекать состав продукта из текста на изображении. "
                                "Неважно, на каком языке состав указан. Твоя цель:  \n\n"
                                "1. Извлечь все ингредиенты и добавки (например: \"вода\", \"сок манго\", \"кислота\", \"сукралоза\", \"E102\", \"E110\").  \n"
                                "2. Если видишь элементы вида \"E100\", \"E121\" и любые другие добавки с префиксом E, выделяй их отдельно как индивидуальные элементы.  \n"
                                "3. Всегда возвращай результат в строго формате Python-списка (list), например:    \n"
                                "   [\"вода\", \"сок манго\", \"кислота\", \"сукралоза\", \"пищевые красители\", \"E102\", \"E110\"]  \n"
                                "4. Никакой другой формы ответа, только список. Без лишнего текста, пояснений или форматов."
                            )
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{img_type};base64,{img_b64_str}"}
                        }
                    ]
                }
            ],
            temperature=0
        )

        # Step 5: Parse Response
        extracted_text = response.choices[0].message.content.strip()
        ingredients_list = ast.literal_eval(extracted_text)  # Convert extracted text into Python list
        
        # Step 6: Check Halal Status (Fixing the Issue)
        halal_status_result = check_halal_status(ingredients_list)

        # Step 7: Return Processed Response
        return jsonify({
            "status": "success",
            "message": "Файл успешно загружен",
            "data": {
                "file_path": filepath,
                "extracted_text": ingredients_list,
                "status": halal_status_result["status"],  # 🔥 FIX: This now correctly shows "Харам", "Халал", or "Подозрительно"
                "found_ingredients": halal_status_result["found_ingredients"]  # 🔥 FIX: Correctly lists the found harmful ingredients
            }
        }), 200

    except openai.OpenAIError as api_error:
        return jsonify({"status": "error", "message": f"Ошибка API OpenAI: {str(api_error)}"}), 500

    except Exception as e:
        return jsonify({"status": "error", "message": f"Ошибка обработки изображения: {str(e)}"}), 500


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
