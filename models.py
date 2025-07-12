from pydantic import BaseModel
class ClientRequest(BaseModel):
    companyId: int