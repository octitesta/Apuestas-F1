from .base import *
import os
import dj_database_url

DEBUG = False

ALLOWED_HOSTS = ["apuestas-f1.onrender.com"]

DATABASES = {
    'default': dj_database_url.parse(
        os.environ.get("DATABASE_URL"),
        conn_max_age=600,
        ssl_require=True
    )
}


print("DATABASE_URL:", os.environ.get("DATABASE_URL"))
print("DEBUG ACTIVO:", DEBUG)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')