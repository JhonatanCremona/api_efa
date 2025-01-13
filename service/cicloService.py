from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import date, datetime
from models.recetaxciclo import RecetaXCiclo
from models.ciclo import Ciclo
from models.recetaxciclo import Recetario

from collections import defaultdict
from datetime import datetime

def obtenerRecetasPorFecha(db, fecha_inicio: date, fecha_fin: date):
    #convertir la fecha a timestamp
    fecha_inicio = datetime.combine(fecha_inicio, datetime.min.time())
    fecha_fin = datetime.combine(fecha_fin, datetime.max.time())
    

    data = (
        db.query(RecetaXCiclo)
        .join(Ciclo, RecetaXCiclo.id_ciclo == Ciclo.id)
        .filter(Ciclo.fecha_fin.between(fecha_inicio, fecha_fin))
        .all()
        )
    listaCiclo= []
    listaReceta = []

    for item in data:
        listaCiclo.append(
            db.query(Ciclo).filter(Ciclo.id == item.id_ciclo).first()
        )
        listaReceta.append(
            db.query(Recetario).filter(Recetario.id == item.id_recetario).first()
        )

    listaReceta_dic = {receta.id: receta for receta in listaReceta}
    listaCiclo_dic = {ciclo.id: ciclo for ciclo in listaCiclo}



    resultado = {}

    def buscarNombreReceta(id_recetario):
        return listaReceta_dic.get(id_recetario).nombre
            
    def buscarCiclos(id_recetario):
        return [
            {
                "id_ciclo": ciclo.id,
                "pesoTotal": listaReceta_dic.get(id_recetario).pesoProductoXFila * ciclo.cantidadNivelesCorrectos,
                "fecha_fin": listaCiclo_dic.get(ciclo.id).fecha_fin.timestamp()
            }
            for ciclo in data if ciclo.id_recetario == id_recetario
        ]
    

    for item in data:
        idReceta = item.id_recetario
        if item.id_recetario not in resultado:
            resultado[idReceta] = {
                "nombre": buscarNombreReceta(idReceta),
                "ciclo": buscarCiclos(idReceta)
            }
    
    #return listaCiclo_dic
    return list(resultado.values())

def save_datosCiclo(opc_client):
    #Nodo torreActual: id Torre
    #Nodo tipoFin (Nuevo) --> Nodo estado
    #Nodo nivelesDesmolde (Fin)
    #Nodo nivelActual  --> cantidadNivelesFin -> 
    #Nodo Nivel_x_estado -->int 
    #BDD -> ETAPA (DESMOLDEO - ENCAJONADO - PALLET)
    #Validacion 
    

    data = 0
    return data

def save_recetaXCiclo():
    data = 0
    return data

def obtenerListaCiclosXProductos(db, fecha_inicio: date, fecha_fin: date):
    fecha_inicio = datetime.combine(fecha_inicio, datetime.min.time())
    fecha_fin = datetime.combine(fecha_fin, datetime.max.time())

    tablaCiclo = (
        db.query(Ciclo)
        .join(RecetaXCiclo, Ciclo.id == RecetaXCiclo.id_ciclo)
        .filter(Ciclo.fecha_fin.between(fecha_inicio, fecha_fin))
        .all()
    )

    listaRecetaXCiclo = []
    for item in tablaCiclo:
        listaRecetaXCiclo.append(
            db.query(RecetaXCiclo).filter(RecetaXCiclo.id_ciclo == item.id).first()
        )

    listaRecetas = []
    for item in listaRecetaXCiclo:
        listaRecetas.append(
            db.query(Recetario).filter(Recetario.id == item.id_recetario).first()
        )

    listaReceta_dic = {receta.id: receta for receta in listaRecetas}
    listaCiclos_dic = {ciclo.id: ciclo for ciclo in tablaCiclo}

    listaPeso = []

    for item in listaRecetaXCiclo:
        registro = {}
        idReceta = item.id_recetario
        if item.id_recetario not in registro:
            registro["fecha_fin"] = listaCiclos_dic.get(item.id_ciclo).fecha_fin.strftime("%Y-%m-%d")
            registro["PesoTotal"] = listaReceta_dic.get(item.id_recetario).pesoProductoXFila * item.cantidadNivelesCorrectos
            listaPeso.append(registro)

    
    


    grouped_by_month = defaultdict(list)
    for item in tablaCiclo:
        print(f"Valor de item.fecha_inicio: {item.fecha_inicio}, Tipo: {type(item.fecha_inicio)}")
        fechaInicio = item.fecha_fin
        
        mes = fechaInicio.strftime("%Y-%m")  # Formato "Año-Mes", por ejemplo "2025-01"
        grouped_by_month[mes].append(item)

    grouped_by_month = dict(grouped_by_month)

    """
    def getWeek(fecha_str):
    # Si fecha_str ya es un objeto datetime, no hacemos nada
        if isinstance(fecha_str, datetime):
            fecha = fecha_str
        else:
            # Si fecha_str es una cadena, la convertimos a datetime
            fecha = datetime.strptime(fecha_str, "%Y-%m-%dT%H:%M:%S")
    
        return fecha.isocalendar()[1] 
    
    semanas = defaultdict(list)
    for itemData in tablaCiclo:
        fechaFin = itemData.fecha_fin
        semana = getWeek(fechaFin)
        semanas[semana].append(itemData)
    """

    

    def agruparPorDia(datos):
        grouped_by_day = defaultdict(list)
        
        for item in datos:
            fechaFin = item.fecha_fin
            dia = fechaFin.strftime("%Y-%m-%d")
            grouped_by_day[dia].append(item)
        return dict(grouped_by_day)

    listaXDia = agruparPorDia(tablaCiclo)

    grupo=[]

    for clave, valor in listaXDia.items():
        elemento = {}
        elemento["fecha_fin"]= clave
        elemento["CantidadCIclos"]= len(valor)
        grupo.append(elemento)

    completo = {}

    completo["ciclos"] = grupo
    completo["pesoProducto"] = listaPeso 


    return completo

def resumenDeProductiviada(db, fecha_inicio: date, fecha_fin:date):
    fecha_inicio = datetime.combine(fecha_inicio, datetime.min.time())
    fecha_fin = datetime.combine(fecha_fin, datetime.max.time())
    listaCompleta = {}

    resumen= {}

    tablaCiclo = (
         db.query(Ciclo)
        .join(RecetaXCiclo, Ciclo.id == RecetaXCiclo.id_ciclo)
        .filter(Ciclo.fecha_fin.between(fecha_inicio, fecha_fin))
        .all()
    )

    listaRecetaXCiclo = []
    for item in tablaCiclo:
        listaRecetaXCiclo.append(
            db.query(RecetaXCiclo).filter(RecetaXCiclo.id_ciclo == item.id).first()
        )

    listaRecetas = []
    for item in listaRecetaXCiclo:
        listaRecetas.append(
            db.query(Recetario).filter(Recetario.id == item.id_recetario).first()
        )

    listaReceta_dic = {receta.id: receta for receta in listaRecetas}
    listaCiclos_dic = {ciclo.id: ciclo for ciclo in tablaCiclo}

    productosRealizados = []
    
    resultado = {}
    resumen["cantidadCiclosCorrectos"] = len(tablaCiclo)

    def buscarCiclos(idReceta):
        return [
            {
                "id_ciclo": ciclo.id,
                "pesoTotal": listaReceta_dic.get(idReceta).pesoProductoXFila * ciclo.cantidadNivelesCorrectos,
            }
            for ciclo in listaRecetaXCiclo if ciclo.id_recetario == idReceta
        ]

    totalPeso = 0
    for item in listaRecetaXCiclo:
        totalPeso += item.cantidadNivelesCorrectos * listaReceta_dic.get(item.id_recetario).pesoProductoXFila
        if item.id_recetario not in resultado:
            productosRealizados.append(
                {
                    "NombreProducto": listaReceta_dic.get(item.id_recetario).nombre,
                    "lote": listaCiclos_dic.get(item.id_ciclo).lote,
                    "peso": buscarCiclos(item.id_recetario), #iterar la suam de productos
                    "cantidadCiclos": len(buscarCiclos(item.id_recetario))
                }
            )

    resultado = list(resultado.values())

    resumen["PesoTotal"] = totalPeso / 1000 

    


    

    return resumen