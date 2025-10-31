from bson import ObjectId

def to_json(document):
    """
    Convierte un documento MongoDB a un JSON compatible con FastAPI.
    """
    if not document:
        return None
    if "_id" in document:
        document["_id"] = str(document["_id"])
    return document
