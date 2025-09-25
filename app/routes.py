from flask import Blueprint

app = Blueprint('main', __name__)

@app.route('/')
def home():
    return 'hi'
