from flask import Blueprint, request, jsonify
from models import db, ScanHistory, Product
from utils import admin_required

admin_routes = Blueprint("admin_routes", __name__)

# 📌 1. Получить данные по scan_id для редактирования
@admin_routes.route("/admin/get-scan/<int:scan_id>", methods=["GET"])
@admin_required
def get_scan(scan_id):
    scan = ScanHistory.query.get_or_404(scan_id)

    return jsonify({
        "scan_id": scan.id,
        "product_name": scan.product_name,
        "image": scan.image,
        "ingredients": scan.ingredients,
        "status": scan.status,
        "haram_ingredients": scan.haram_ingredients,
        "is_processed": scan.is_processed
    }), 200


# 📌 2. Сохранить отредактированные данные и добавить в Product
@admin_routes.route("/admin/save-product", methods=["POST"])
@admin_required
def save_product():
    data = request.json

    scan_id = data.get("scan_id")
    product_name = data.get("product_name")
    new_image = data.get("image")
    ingredients = data.get("ingredients")
    status = data.get("status")
    haram_ingredients = data.get("haram_ingredients")
    description_id = data.get("description_id")

    scan = ScanHistory.query.get_or_404(scan_id)

    # Добавляем в Product
    new_product = Product(
        name=product_name,
        image=new_image,
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


# 📌 3. Получить список всех сканированных продуктов
@admin_routes.route("/admin/scan-products", methods=["GET"])
@admin_required
def get_scan_products():
    scans = ScanHistory.query.all()

    scan_list = [{
        "scan_id": scan.id,
        "user_id": scan.user_id,
        "product_name": scan.product_name or "Неизвестно",
        "status": scan.status,
        "is_processed": scan.is_processed
    } for scan in scans]

    return jsonify({"status": "success", "data": scan_list}), 200
