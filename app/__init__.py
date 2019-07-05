from flask import Flask
from flask_bootstrap import Bootstrap
from flask_flatpages import FlatPages
from flask_cors import CORS

FLATPAGES_AUTO_RELOAD = True
FLATPAGES_EXTENSION = '.md'
FLATPAGES_ROOT = 'content'

app = Flask(__name__)
CORS(app)
bootstrap = Bootstrap(app)
flatpages = FlatPages(app)

app.config.from_object(__name__)

from app import routes