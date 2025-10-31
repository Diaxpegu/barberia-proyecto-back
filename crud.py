from bson import ObjectId

def to_json(document):
    if not document:
        return {}
    result = {}
    for key, value in document.items():
        if isinstance(value, ObjectId):
            result[key] = str(value)  # convertir ObjectId en string
        else:
            result[key] = value
    return result