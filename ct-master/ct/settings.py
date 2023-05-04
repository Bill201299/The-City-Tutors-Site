"""
Django settings for ct project.

Generated by 'django-admin startproject' using Django 3.2.5.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.2/ref/settings/
"""
import os
from pathlib import Path

from django.contrib import messages
import twilio.rest

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'nECmUkP8I3cYAewNlN7Ec3k38VHjCNk7'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DJANGO_DEBUG', '') != 'False'
ALLOWED_HOSTS = ["127.0.0.1", "app.thecitytutors.org", "appdev.thecitytutors.org", "54.159.239.55", "52.54.137.50", "3.236.193.58", "3.220.12.27", "3.236.132.55"]
if os.getenv("LOCAL_ADDRESS"):
    ALLOWED_HOSTS.append(os.getenv("LOCAL_ADDRESS"))

# Application definition

INSTALLED_APPS = [
    'tutor',
    'django.forms',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    #'debug_toolbar',
    'crispy_forms',
    'phonenumber_field',
    'django_crontab',
    'django_static_jquery3',
    'django_yearmonth_widget'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    #'debug_toolbar.middleware.DebugToolbarMiddleware',
]


AUTHENTICATION_BACKENDS = ['django.contrib.auth.backends.AllowAllUsersModelBackend']

if DEBUG is False:
    del MIDDLEWARE[0]

ROOT_URLCONF = 'ct.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, "templates")],
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

WSGI_APPLICATION = 'ct.wsgi.application'


# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'America/New_York'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/

STATIC_ROOT = "/home/ubuntu/ct/ct/static/"
STATIC_URL = '/static/'

# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGOUT_REDIRECT_URL = '/register'

LOGIN_REDIRECT_URL = '/request'

LOGIN_URL = '/login'

if os.getenv("LOGGING"):
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {
            'file': {
                'level': 'INFO',
                'class': 'logging.FileHandler',
                'filename': '/var/log/django/info.log',
                'formatter': 'timestamp'
            },
        },
        'loggers': {
            'django': {
                'handlers': ['file'],
                'level': 'INFO',
                'propagate': True,
            },
        },
        'formatters': {
            'timestamp': {
                'format': '{asctime} {message}',
                'style': '{',
            },
        },
    }
else:
    LOGGING = None

CRISPY_TEMPLATE_PACK = 'bootstrap4'

MESSAGE_TAGS = {
    messages.DEBUG: 'alert-secondary',
    messages.INFO: 'alert-info',
    messages.SUCCESS: 'alert-success',
    messages.WARNING: 'alert-warning',
    messages.ERROR: 'alert-danger',
}

FORM_RENDERER = 'django.forms.renderers.TemplatesSetting'

INTERNAL_IPS = [
    '127.0.0.1',
]

DRY_RUN = os.getenv('DRY_RUN') == "True"
SKIP_NOTIFY_EMAIL = os.getenv('SKIP_NOTIFY_EMAIL') == "True"
SKIP_NOTIFY_SMS = os.getenv('SKIP_NOTIFY_SMS') == "True"
COPY_DB = os.getenv('COPY_DB') == "True"

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST')
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
RECIPIENT_ADDRESS = os.getenv('RECIPIENT_ADDRESS')
REPLYTO_ADDRESS = os.getenv('REPLYTO_ADDRESS')
SEND_TO_USERS = os.getenv('SEND_TO_USERS') == "True"

TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_NUMBER = os.getenv('TWILIO_NUMBER')
TWILIO_CLIENT = None
if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
    TWILIO_CLIENT = twilio.rest.Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

DEVELOPMENT_NUMBER = os.getenv('DEVELOPMENT_NUMBER')
PHONENUMBER_DEFAULT_FORMAT="NATIONAL"
PHONENUMBER_DEFAULT_REGION="US"

TRAINING_CODE = os.getenv('TRAINING_CODE')
LIVE_SESSION_CODE = os.getenv('LIVE_SESSION_CODE')

CRONTAB_COMMAND_PREFIX=(
    f"SEND_TO_USERS={SEND_TO_USERS} "
    f"TWILIO_ACCOUNT_SID={TWILIO_ACCOUNT_SID} "
    f"TWILIO_AUTH_TOKEN={TWILIO_AUTH_TOKEN} "
    f"DEVELOPMENT_NUMBER={DEVELOPMENT_NUMBER} "
    f"TWILIO_NUMBER={TWILIO_NUMBER} "
    f"EMAIL_HOST={EMAIL_HOST} "
    f"EMAIL_HOST_USER={EMAIL_HOST_USER} "
    f"EMAIL_HOST_PASSWORD={EMAIL_HOST_PASSWORD} "
    f"RECIPIENT_ADDRESS={RECIPIENT_ADDRESS} "
    f"REPLYTO_ADDRESS={REPLYTO_ADDRESS} "
    f"DRY_RUN={DRY_RUN} "
    f"SKIP_NOTIFY_EMAIL={SKIP_NOTIFY_EMAIL} "
    f"SKIP_NOTIFY_SMS={SKIP_NOTIFY_SMS} "
    f"COPY_DB={COPY_DB} "
)
CRONTAB_COMMAND_SUFFIX = "2>&1"
CRONJOBS = [
    ('0 0 * * *', 'tutor.cron.print_env', '>> ' + os.path.join(BASE_DIR,'log/cron.log')),
    ('0 0 1 1 *', 'tutor.cron.test_logging', '>> ' + os.path.join(BASE_DIR,'log/cron.log')),
    # ('0 18 * * *', 'tutor.cron.notify_inactive_tutors'),
    ('*/15 * * * *', 'tutor.cron.notify_session_start', '>> ' + os.path.join(BASE_DIR,'log/cron.log')),
    ('*/15 * * * *', 'tutor.cron.notify_late_session', '>> ' + os.path.join(BASE_DIR,'log/cron.log')),
    ('0 18 * * *', 'tutor.match.fulfill_requests', '>> ' + os.path.join(BASE_DIR,'log/match.log')),
    ('0 * * * *', 'tutor.cron.cancel_unconfirmed_students', '>> ' + os.path.join(BASE_DIR,'log/cron.log')),
    ('0 * * * *', 'tutor.cron.cancel_unconfirmed_tutors', '>> ' + os.path.join(BASE_DIR,'log/cron.log')),
    ('0 1 * * *', 'export.export'),
    # ('14-59/15 * * * *', 'tutor.cron.copy_database', '>> ' + os.path.join(BASE_DIR,'log/cron.log')),
]

"""    ('0 * * * *', 'tutor.cron.automatic_clockout', '>>' + os.path.join(BASE_DIR,'log/debug7.log' + ' 2>&1 ')), """

