# Import all model modules to ensure SQLAlchemy sees all tables
from . import auth
from . import voters  
from . import tracking
from . import benefits
from . import meetings
from . import donors
from . import suppliers
from . import budgets

# This ensures all models are registered with SQLAlchemy Base
