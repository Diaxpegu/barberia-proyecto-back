from bson import ObjectId

def to_json(doc):
    """Convierte documentos Mongo en JSON serializable"""
    if not doc:
        return None
    doc["_id"] = str(doc["_id"])
    return doc
