import os
import uuid
from flask import Blueprint, request, jsonify
from google.cloud import storage
from models import db, Product

# Инициализируем Blueprint
gcs_routes = Blueprint("gcs_routes", __name__)

# Путь к твоему service_account.json
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "service_account.json"

# Название твоего GCS bucket
BUCKET_NAME = "quram_product_photo"  # замените на своё

# 📤 Загрузка в Google Cloud Storage
def upload_to_gcs(file):
    client = storage.Client()
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
