from dotenv import load_dotenv
import os
from flask import Flask

# Load .env file and declare required environment vars
load_dotenv()
required_envs = [
    'TSH_SECRET_KEY'
]

# Verify required environment variables
missing = []
for env in required_envs:
    if os.getenv(env) == None:
        missing.append(env)

# If any are missing raise an error
if missing:
    raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('TSH_SECRET_KEY')

    from app.routes import app as routes
    app.register_blueprint(routes)

    return app

    
