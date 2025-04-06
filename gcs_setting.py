import base64
import os
import uuid
from io import BytesIO
from tkinter import Image

from flask import Blueprint, request, jsonify
from google.cloud import storage
from models import db, Product, ScanHistory
from utils import admin_required

# Инициализируем Blueprint
gcs_routes = Blueprint("gcs_routes", __name__)

# Путь к твоему service_account.json
import json
from google.oauth2 import service_account

def get_gcs_client():
    if "GOOGLE_CREDENTIALS" in os.environ:
        credentials_info = json.loads(os.environ["GOOGLE_CREDENTIALS"])
        credentials = service_account.Credentials.from_service_account_info(credentials_info)
        return storage.Client(credentials=credentials)
    else:
        return storage.Client.from_service_account_json("service_account.json")

# Название твоего GCS bucket
BUCKET_NAME = "quram_product_photo"  # замените на своё

# 📤 Загрузка в Google Cloud Storage
def upload_to_gcs(file):
    client = get_gcs_client()
    bucket = client.bucket(BUCKET_NAME)
    blob_name = f"{uuid.uuid4().hex}_{file.filename}"
    blob = bucket.blob(blob_name)
    blob.upload_from_file(file, content_type=file.content_type)
    blob.make_public()
    return blob.public_url

# 📌 Эндпоинт загрузки изображения к Product
@gcs_routes.route('/upload_product_image', methods=['POST'])
def upload_product_image():
    product_id = request.form.get('product_id')
    file = request.files.get('file')

    if not product_id or not file:
        return jsonify({"error": "product_id and file are required"}), 400

    product = Product.query.get(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), 404

    try:
        image_url = upload_to_gcs(file)
        product.image = image_url
        db.session.commit()
        return jsonify({
            "message": "Image uploaded successfully",
            "image_url": image_url
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@gcs_routes.route('/update_product', methods=['POST'])
def upload_product_image1():
    scan_id = request.form.get("scan_id")
    product_name= request.form.get('product_name')
    ingredients = request.form.get("ingredients")
    status = request.form.get("status")
    haram_ingredients = request.form.get("haram_ingredients")
    description_id = request.form.get("description_id")
    file = request.files.get('file')

    scan = ScanHistory.query.get_or_404(scan_id)

    try:
        image_url = upload_to_gcs(file)
        new_product = Product(
            name=product_name,
            image=image_url,  # Сохраняем URL изображения из GCS
            ingredients=ingredients,
            status=status,
            haram_ingredients=haram_ingredients,
            count=1,
            description_id=description_id
        )
        db.session.add(new_product)
        db.session.commit()

        scan.product_id = new_product.id
        scan.is_processed = True  # Продукт обработан

        db.session.commit()
        return jsonify({
            "message": "Image uploaded successfully",
            "image_url": image_url
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500



@gcs_routes.route("/save-product1", methods=["POST"])
def save_product1():
    data = request.json

    scan_id = data.get("scan_id")
    product_name = data.get("product_name")
    new_image = data.get("image")  # Передаем в base64
    ingredients = data.get("ingredients")
    status = data.get("status")
    haram_ingredients = data.get("haram_ingredients")
    description_id = data.get("description_id")

    scan = ScanHistory.query.get_or_400(scan_id)

    # Загрузка изображения в GCS
    image_url = None
    if new_image:
        try:
            # Если изображение передается как base64, конвертируем его в файл
            image_data = base64.b64decode(new_image.split(",")[1])
            image = Image.open(BytesIO(image_data))
            image_filename = f"{scan_id}_image.png"

            # Временное сохранение изображения перед загрузкой
            temp_image = BytesIO()
            image.save(temp_image, format="PNG")
            temp_image.seek(0)

            # Загрузка изображения в GCS
            image_url = upload_to_gcs(temp_image)

        except Exception as e:
            return jsonify({"error": f"Image upload failed: {str(e)}"}), 500

    # Добавляем новый продукт
    new_product = Product(
        name=product_name,
        image=image_url,  # Сохраняем URL изображения из GCS
        ingredients=ingredients,
        status=status,
        haram_ingredients=haram_ingredients,
        count=1,
        description_id=description_id
    )

    db.session.add(new_product)
    db.session.commit()

    # Обновляем ScanHistory
    scan.product_id = new_product.id
    scan.is_processed = True  # Продукт обработан

    db.session.commit()

    return jsonify({"status": "success", "message": "Продукт добавлен"}), 201


