from fastapi.templating import Jinja2Templates
import os

# Point to ui/static for all HTML templates
templates_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "ui", "static")
templates = Jinja2Templates(directory=templates_dir)
