from app.core.config import settings  

broker_url = settings.REDIS_URL  # URL брокера задач (Redis)
result_backend = settings.REDIS_URL  # URL хранилища результатов (Redis)
task_serializer = "json"  
result_serializer = "json"  
accept_content = ["json"]  
timezone = "UTC" 
enable_utc = True  
