import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

class Config:
    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///edx_store.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Debug Configuration
    DEBUG = os.getenv('FLASK_ENV') == 'development'
    
    # OpenEdX Configuration
    OPENEDX_URL = os.getenv('OPENEDX_URL', 'https://eskills.eslsca.edu.eg')
    OPENEDX_CLIENT_ID = 'ScUck2iZMf6aoaujlfOzvy0fSRMwnauiifWoyljS'
    OPENEDX_CLIENT_SECRET = 'iHLTF0sG74xq76E1izDefhf9O6qGUhHEnRq0maHhQzw2d9tlkhvN97Xtr8wMfRIM6snUP5aEKYjZXilJP0FAKiNmpaJXK3wjJuDyced7zKLBHL4SFAc2qJK8HnLXDrBM'
    # OPENEDX_CLIENT_ID = os.getenv('OPENEDX_CLIENT_ID')
    # OPENEDX_CLIENT_SECRET = os.getenv('OPENEDX_CLIENT_SECRET')
    
    VERIFY_SSL = os.getenv('VERIFY_SSL', 'False').lower() == 'true'  # Default to False for development
    
    # Stripe Configuration
    STRIPE_PUBLIC_KEY = os.getenv('STRIPE_PUBLIC_KEY')
    STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
    STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')
    STRIPE_CURRENCY = os.getenv('STRIPE_CURRENCY', 'usd')
    
    # Logging Configuration
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'standard'
            }
        },
        'root': {
            'level': 'INFO',
            'handlers': ['console']
        }
    }
    
    # Session Configuration
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # API Rate Limiting
    RATELIMIT_DEFAULT = "100/hour"
    RATELIMIT_STORAGE_URL = "memory://"
    
    # API Endpoints
    OPENEDX_CATALOG_API = f"{OPENEDX_URL}/api/courses/v1/courses/"
    OPENEDX_ENROLLMENT_API = f"{OPENEDX_URL}/api/enrollment/v1/enrollment"
    OPENEDX_USER_API = f"{OPENEDX_URL}/api/user/v1/accounts" 