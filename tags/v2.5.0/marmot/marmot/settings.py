# -*- coding: utf-8 -*-

"""
Django settings for marmot project.
"""

import os
import sys


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MARMOT_DIR = os.path.dirname(os.path.abspath(__file__))

SECRET_KEY = 'ao&t$rho3=ch7rk3=q!i@5bd(d31d_698wheut_17_krj+ey7g'

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '192.168.162.91']

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'guardian',
    'bootstrap3',
    'accounts',
    'assets',
    'services',
    'task',
    'script',
)

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',  # this is default
    'guardian.backends.ObjectPermissionBackend',
)

GUARDIAN_RENDER_403 = True

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
)

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(MARMOT_DIR, 'templates')],
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

STATIC_URL = '/static/'

STATICFILES_DIRS = (
    os.path.join(MARMOT_DIR, 'static'),
)

# STATIC_ROOT = '/opt/marmot/marmot/marmot/static'

MEDIA_URL = '/media/'

MEDIA_ROOT = os.path.join(MARMOT_DIR, 'media')

WSGI_APPLICATION = 'marmot.wsgi.application'

ROOT_URLCONF = 'marmot.urls'


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'marmot',
        'USER': 'marmot',
        'PASSWORD': '7552735535',
        'HOST': '192.168.162.103',
        'PORT': '3306',
        'OPTIONS': {'init_command': 'SET storage_engine=MyISAM'},
    }
}

SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_AGE = 60 * 60 * 8

FILE_UPLOAD_MAX_MEMORY_SIZE = 2621440 * 2
FILE_UPLOAD_TEMP_DIR = '/tmp'

FILE_UPLOAD_HANDLERS = (
    "django.core.files.uploadhandler.MemoryFileUploadHandler",
    "django.core.files.uploadhandler.TemporaryFileUploadHandler",
)

# Internationalization

LANGUAGE_CODE = 'zh-CN'

TIME_ZONE = 'Asia/Shanghai'

USE_I18N = True

USE_L10N = False

USE_TZ = False


LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'verbose': {
            'format': '%(asctime)s: %(message)s'
        }
    },
    'filters': {
    },
    'handlers': {
        'marmot': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'error.log'),
            'maxBytes': 1024*1024*5,
            'backupCount': 5,
            'formatter': 'verbose',
        }
    },
    'loggers': {
        'marmot': {
            'handlers': ['marmot'],
            'level': 'ERROR',
        }
    }
}


# EMAIL_HOST = '117.121.48.85'
EMAIL_HOST = 'smtp.100credit.com'
EMAIL_PORT = 25
EMAIL_HOST_USER = 'marmot@100credit.com'
EMAIL_HOST_PASSWORD = 'OK7x10XVhE'
EMAIL_SUBJECT_PREFIX = 'Marmot'
EMAIL_USE_TLS = True


REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0

NODE_PORT = 9001

# ICEGRIDADMIN = ['/opt/Ice-3.6.1/bin/icegridadmin', '--server']
ICEGRIDADMIN = ['icegridadmin', '--server']

# MAIN_URL = 'http://192.168.162.91:8100'
MAIN_URL = 'http://172.16.20.48:8100'


# CELERY STUFF
BROKER_URL = 'redis://%s:%s/1' % (REDIS_HOST, REDIS_PORT)
CELERY_RESULT_BACKEND = 'redis://%s:%s/1' % (REDIS_HOST, REDIS_PORT)
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Shanghai'
