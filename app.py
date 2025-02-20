from flask import Flask
from flask_migrate import Migrate
from models import db
from routes import routes

app = Flask(__name__)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:user@localhost/QuramDatabase'
app.debug = True

db.init_app(app)
migrate = Migrate(app, db)

app.register_blueprint(routes)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
