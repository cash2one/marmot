# -*- coding: utf-8 -*-

"""
Django settings for marmot project.
"""

import os
import sys
from datetime import timedelta


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MARMOT_DIR = os.path.dirname(os.path.abspath(__file__))

SECRET_KEY = 'ao&t$rho3=ch7rk3=q!i@5bd(d31d_698wheut_17_krj+ey7g'

DEBUG = False

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '192.168.23.115', 'marmot.100credit.cn']

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'guardian',
    'bootstrap3',
    'workflow',
    'celerymail',
    'accounts',
    'logview',
    'assets',
    'services',
    'nodeapp',
    'task',
    'script',
    'monitor',
)


CAS_AUTH_URL = 'http://cas.100credit.cn/validate/'
CAS_MAIN_URL = 'http://cas.100credit.cn'

AUTHENTICATION_BACKENDS = (
    # 'django.contrib.auth.backends.ModelBackend',  # this is default
    'accounts.backend.MarmotAuthBackend',
    'guardian.backends.ObjectPermissionBackend',
)

GUARDIAN_RENDER_403 = True

MIDDLEWARE_CLASSES = (
    'utils.middlewares.LoggingMiddleware',
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
        'DIRS': [
            os.path.join(MARMOT_DIR, 'templates')
        ],
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

# STATICFILES_DIRS = (
#     os.path.join(MARMOT_DIR, 'static'),
# )

STATIC_ROOT = '/opt/marmot/marmot/marmot/static'

MEDIA_URL = '/media/'

MEDIA_ROOT = os.path.join(MARMOT_DIR, 'media')

WSGI_APPLICATION = 'marmot.wsgi.application'

ROOT_URLCONF = 'marmot.urls'


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'marmot',
        'USER': 'marmot',
        'PASSWORD': 'MarmoT@Br_2016.06.01',
        'HOST': 'localhost',
        'PORT': '3306',
        'OPTIONS': {'init_command': 'SET storage_engine=MyISAM'},
    }
}


CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://192.168.23.115:6379/3",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_AGE = 60 * 60 * 3

FILE_UPLOAD_MAX_MEMORY_SIZE = 2621440 * 2
FILE_UPLOAD_TEMP_DIR = '/tmp'

FILE_UPLOAD_HANDLERS = (
    "django.core.files.uploadhandler.MemoryFileUploadHandler",
    "django.core.files.uploadhandler.TemporaryFileUploadHandler",
)

# Internationalization

DATETIME_FORMAT = 'Y-m-d H:i:s'

LANGUAGE_CODE = 'zh-CN'

TIME_ZONE = 'Asia/Shanghai'

USE_I18N = True

USE_L10N = False

USE_TZ = False

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[%(asctime)s] %(levelname)s %(name)s %(module)s %(lineno)d : %(message)s'
        },
        'simple': {
            # 'format': '[%(asctime)s] %(levelname)s %(name)s : %(message)s'
            'format': '%(asctime)s [%(name)s] [%(threadName)s] %(levelname)s [no--line:%(lineno)d] %(message)s'
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
        'console': {
            'level': 'DEBUG',
            'filters': ['require_debug_true'],
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'error': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'error.log'),
            'formatter': 'verbose',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'marmot.log'),
            'maxBytes': 1024*1024*10,
            'backupCount': 8,
            'formatter': 'simple',
        }
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'propagate': True,
        },
        'django.request': {
            'handlers': ['error'],
            'level': 'ERROR',
            'propagate': True,
        },
        'django.security': {
            'handlers': ['error'],
            'level': 'ERROR',
            'propagate': True,
        },
        'py.warnings': {
            'handlers': ['console'],
        },
        'marmot': {
            'handlers': ['file'],
            'level': 'INFO',
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


REDIS_HOST = '192.168.23.115'
REDIS_PORT = 6379
REDIS_DB = 0

NODE_PORT = 9001

ICEGRIDADMIN = ['/opt/Ice-3.6.1/bin/icegridadmin', '--server']

MAIN_URL = 'http://localhost:8100'
MAIN_DOMAIN = 'http://marmot.100credit.cn'


# CELERY STUFF
BROKER_URL = 'redis://%s:%s/1' % (REDIS_HOST, REDIS_PORT)
CELERY_RESULT_BACKEND = 'redis://%s:%s/1' % (REDIS_HOST, REDIS_PORT)
CELERY_TASK_RESULT_EXPIRES = 3600
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Shanghai'

# Periodic Tasks
CELERYBEAT_SCHEDULE = {
    'redis-cluster-monitor-every-120': {
        'task': 'task.redis_cluster_monitor',
        'schedule': timedelta(seconds=120),
    },

    'es-monitor-every-90s': {
        'task': 'task.es_monitor',
        'schedule': timedelta(seconds=90),
    },

    'hbase-monitor-every-150s': {
        'task': 'task.hbase_monitor',
        'schedule': timedelta(seconds=150),
    },

    'neo4j-monitor-every-120s': {
        'task': 'task.neo4j_monitor',
        'schedule': timedelta(seconds=120),
    },

    'icegrid-monitor-every-150s': {
        'task': 'task.icegrid_monitor',
        'schedule': timedelta(seconds=150),
    },

    'activemq-monitor-every-300s': {
        'task': 'task.activemq_monitor',
        'schedule': timedelta(seconds=300),
    },

    'springcloud-monitor-every-300s': {
        'task': 'task.springcloud_monitor',
        'schedule': timedelta(seconds=300),
    },
}
