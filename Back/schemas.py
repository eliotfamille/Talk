from dataclasses import dataclass  # remplace BaseModel
from config import Provider  # fournisseurs


@dataclass
class Request:  # requete chat
    message: str
    provider: Provider | None = None
    model: str | None = None
    conversation_id: str | None = None
