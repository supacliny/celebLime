CELERY_RESULT_BACKEND = "mongodb"
CELERY_MONGODB_BACKEND_SETTINGS = {
    "host": "127.0.0.1",
    "port": 27017,
    "database": "celery",
    "taskmeta_collection": "messages",
}
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_IMPORTS = ('celebLime',)