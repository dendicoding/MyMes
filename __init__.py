from flask import Flask
from routes.auth import auth_bp
from routes.machines import machine_bp
from routes.orders import order_bp
from routes.tasks import task_bp
from routes.operators import operators_bp
from routes.cycles import cycles_bp
from routes.resources import resources_bp
from routes.lots import lots_bp
from routes.storage_movements import storage_movements_bp
from routes.counterparts import counterparts_bp
from routes.misc import misc_bp
from routes.chatbot import chatbot_bp
from routes.notes import notes_bp
from routes.operations import operations_bp
from routes.maintenance import maintenance_bp
from config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Register blueprints
    app.register_blueprint(misc_bp)  # Must be registered last to catch all other routes!
    app.register_blueprint(auth_bp)
    app.register_blueprint(machine_bp)
    app.register_blueprint(order_bp)
    app.register_blueprint(task_bp)
    app.register_blueprint(operators_bp)
    app.register_blueprint(cycles_bp)
    app.register_blueprint(resources_bp)
    app.register_blueprint(lots_bp)
    app.register_blueprint(storage_movements_bp)
    app.register_blueprint(counterparts_bp)
    app.register_blueprint(chatbot_bp)
    app.register_blueprint(notes_bp)
    app.register_blueprint(operations_bp)
    app.register_blueprint(maintenance_bp)

    return app
