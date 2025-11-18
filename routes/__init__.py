# Routes Package
# Flask Blueprint routes for the LeAIrn system

from .auth_routes import auth_bp
from .booking_routes import booking_bp
from .admin_routes import admin_bp
from .api_routes import api_bp

__all__ = ['auth_bp', 'booking_bp', 'admin_bp', 'api_bp']
