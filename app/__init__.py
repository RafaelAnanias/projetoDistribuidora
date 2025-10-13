from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt

# Inicialização das extensões
db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = 'routes.login' # Rota para onde o usuário não logado é redirecionado
login_manager.login_message_category = 'info'
login_manager.login_message = "Por favor, faça login para acessar esta página."

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Inicializa as extensões com o app
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)

    # Importa e registra os Blueprints (nossas rotas)
    from app.routes import bp as routes_bp
    app.register_blueprint(routes_bp)
    
    from .models import Usuario

    @login_manager.user_loader
    def load_user(user_id):
        return Usuario.query.get(int(user_id))

    return app