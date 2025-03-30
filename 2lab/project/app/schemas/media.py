from pydantic import BaseModel

class ImageBinarizationRequest(BaseModel):
    image: str 
    algorithm: str = "niblack"  