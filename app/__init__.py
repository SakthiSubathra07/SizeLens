import os
from flask import Flask
from app import config, db

def create_app(test_config=None):
    template_dir = os.path.join(config.BASE_DIR, 'templates')
    static_dir = os.path.join(config.BASE_DIR, 'static')

    app = Flask(
        __name__,
        template_folder=template_dir,
        static_folder=static_dir
    )

    app.config.from_object(config)

    if test_config:
        app.config.update(test_config)
    if not app.config.get('SECRET_KEY'):
        raise RuntimeError(
            'SECRET_KEY must be set in the environment or application config.'
        )
    database_dir = os.path.dirname(os.path.abspath(app.config['DATABASE']))
    os.makedirs(database_dir, exist_ok=True)

    db.init_app(app)

    with app.app_context():
        db.init_db()

    from app.routes import bp
    app.register_blueprint(bp)

    return app
