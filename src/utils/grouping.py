from collections import defaultdict

def agrupar_por_rut_proveedor(registros):
    """
    Agrupa los registros por `rut_proveedor`.

    Retorna un diccionario con:
    - Clave: RUT del proveedor
    - Valor: Lista de registros asociados a ese RUT
    """
    agrupados = defaultdict(list)

    for registro in registros:
        agrupados[registro.area].append(registro)

    return agrupados


from collections import defaultdict

def agrupar_por_area(registros):
    """
    Agrupa los registros por el campo 'area'.

    Args:
        registros (list): Lista de instancias de la clase Registro.

    Returns:
        dict: Diccionario con las áreas como clave y una lista de registros como valor.
    """
    agrupados = defaultdict(list)
    
    for registro in registros:
        agrupados[registro.area.upper()].append(registro)
    
    return agrupados
