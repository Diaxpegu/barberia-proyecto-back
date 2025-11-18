from bson import ObjectId, errors

def to_json(document):
    """
    Convierte un documento de MongoDB a diccionario serializable a JSON.
    Convierte ObjectId en string.
    """
    if not document:
        return {}
    result = {}
    for key, value in document.items():
        if isinstance(value, ObjectId):
            result[key] = str(value)
        else:
            result[key] = value
    return result


def get_by_id(collection, id):
    """
    Obtiene un documento por su ObjectId.
    Retorna None si el ID no es válido o no se encuentra.
    """
    try:
        oid = ObjectId(id)
    except errors.InvalidId:
        return None
    return collection.find_one({"_id": oid})


def insert_document(collection, data):
    """
    Inserta un documento en la colección y retorna el ID insertado como string.
    """
    result = collection.insert_one(data)
    return str(result.inserted_id)


def update_document(collection, id, update_data):
    """
    Actualiza un documento por su ObjectId.
    Retorna el número de documentos modificados (0 o 1).
    """
    try:
        oid = ObjectId(id)
    except errors.InvalidId:
        return 0
    result = collection.update_one({"_id": oid}, {"$set": update_data})
    return result.modified_count


def delete_document(collection, id):
    """
    Elimina un documento por su ObjectId.
    Retorna el número de documentos eliminados (0 o 1).
    """
    try:
        oid = ObjectId(id)
    except errors.InvalidId:
        return 0
    result = collection.delete_one({"_id": oid})
    return result.deleted_count
