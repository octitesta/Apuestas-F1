import os

ENVIRONMENT = os.environ.get("DJANGO_ENV", "dev")

if ENVIRONMENT == "prod":
    from .prod import *
else:
    from .dev import *