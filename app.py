from flask import Flask
from models import db
from flask_migrate import Migrate

app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:user@localhost/QuramDatabase'
app.debug = True

db.init_app(app)
migrate = Migrate(app, db)

@app.route('/test', methods=['GET'])
def test():
    return {'test': 'test1'}

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Создаём таблицы, если их нет
    app.run(debug=True)
