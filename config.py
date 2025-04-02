import os

db_config = {
    'host': 'your-db-hostname',
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASS'),
    'database': 'grocery_shop',
}
