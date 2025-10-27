# mcda_project/settings.py
from pathlib import Path
import os
from decouple import config
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)

hostname = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
ALLOWED_HOSTS = ['localhost', '127.0.0.1']
if hostname:
    ALLOWED_HOSTS.append(hostname)

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'analyzer_app',
    'widget_tweaks',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'mcda_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'wsgi.application'

DATABASES = {
    'default': dj_database_url.config(default=config('DATABASE_URL'))
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
UPLOAD_ROOT = os.path.join(MEDIA_ROOT, 'uploads')

AUTH_USER_MODEL = 'analyzer_app.CustomUser'
AUTHENTICATION_BACKENDS = ['analyzer_app.auth_backend.EmailBackend']
LOGIN_REDIRECT_URL = '/'
LOGIN_URL = '/login/'
LOGOUT_REDIRECT_URL = 'login'

# ===============================================
# CONFIGURAÇÃO DE ENVIO DE E-MAIL (SENDGRID)
# ===============================================

# O "Backend" que o Django vai usar. Informa que é o SendGrid.
EMAIL_BACKEND = 'sendgrid_backend.SendgridBackend'

# A sua API Key, lida de forma segura do ambiente do Render (Etapa 2).
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')

# Opcional, mas recomendado: não rastrear aberturas ou cliques nos e-mails.
SENDGRID_TRACK_CLICKS_HTML = False
SENDGRID_TRACK_OPENS = False

# (Opcional) Configuração do SMTP, que o 'sendgrid_backend' usa por baixo dos panos.
EMAIL_HOST = 'smtp.sendgrid.net'
EMAIL_HOST_USER = 'apikey' # (Isso é literal, deixe 'apikey')
EMAIL_HOST_PASSWORD = SENDGRID_API_KEY
EMAIL_PORT = 587
EMAIL_USE_TLS = True

# --- O REMETENTE PADRÃO ---
# Coloque aqui o e-mail exato que você verificou no SendGrid (Etapa 3 anterior).
# Este é o e-mail que aparecerá no campo "De:"
DEFAULT_FROM_EMAIL = 'gianlucca.rissato@fatec.sp.gov.br'