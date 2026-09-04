#API'nin döndüreceği response modelini tanımladığımız dosya
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ConversionResponse(BaseModel):

    model_config = ConfigDict(
        populate_by_name=True
    )
    
    amount: Decimal #Döviz para hesabında gereksiz float problemlerini önlemek için Decimal tipini seçtim.
    from_: str =Field(alias="from") #from bir python keywordü olduğu için alias ile değiştirdim.
    to: str
    rate: Decimal
    result: Decimal
    rate_date: str
    asked_date: str
    source: str