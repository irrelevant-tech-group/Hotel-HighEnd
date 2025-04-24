from app import app
from routes import *

if __name__ == '__main__':
    # This block will only run if the script is executed directly
    # In production, we use Gunicorn instead
    print("Please use Gunicorn to run this application in production")
