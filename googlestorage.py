from google.cloud import storage
from flask import request
from models import Product, ScanHistory, db

def upload_product_image(file, product_name):
    try:
        # Получаем клиент Google Cloud Storage
        client = storage.Client.from_service_account_json('service_account.json')

        # Указываем имя бакета и путь для файла
        bucket_name = 'quram_product_photo'
        bucket = client.get_bucket(bucket_name)
        blob = bucket.blob(f'products/{product_name}/{file.filename}')

        # Загружаем файл в GCS
        blob.upload_from_file(file)

        # Генерируем URL изображения
        image_url = f"https://storage.googleapis.com/{bucket_name}/products/{product_name}/{file.filename}"

        # Обновляем URL в базе данных для соответствующего продукта
        product = Product.query.filter_by(name=product_name).first()
        if product:
            product.set_image_url(image_url)
        else:
            # В случае, если продукт не найден, можно обработать это по-своему
            print(f"Продукт с именем {product_name} не найден.")

        return image_url

    except Exception as e:
        print(f"Ошибка при загрузке изображения: {e}")
        return None


def upload_scan_history_image(file, product_name):
    try:
        # Получаем клиент Google Cloud Storage
        client = storage.Client.from_service_account_json('service_account.json')

        # Указываем имя бакета и путь для файла
        bucket_name = 'quram_product_photo'
        bucket = client.get_bucket(bucket_name)
        blob = bucket.blob(f'scan_history/{product_name}/{file.filename}')

        # Загружаем файл в GCS
        blob.upload_from_file(file)

        # Генерируем URL изображения
        image_url = f"https://storage.googleapis.com/{bucket_name}/scan_history/{product_name}/{file.filename}"

        # Обновляем URL в базе данных для соответствующей истории сканирования
        scan_history = ScanHistory.query.filter_by(product_name=product_name).first()
        if scan_history:
            scan_history.set_image_url(image_url)
        else:
            # В случае, если история сканирования не найдена
            print(f"История сканирования для продукта {product_name} не найдена.")

        return image_url

    except Exception as e:
        print(f"Ошибка при загрузке изображения: {e}")
        return None
