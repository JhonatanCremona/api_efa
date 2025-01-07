from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import date
from models.recetaxciclo import RecetaXCiclo
from models.ciclo import Ciclo



def obtenerRecetasPorFecha(db, fecha_inicio: date, fecha_fin: date):
    data = (
        db.query(RecetaXCiclo)
        .join(Ciclo, RecetaXCiclo.id_ciclo == Ciclo.id)
        .filter(Ciclo.fecha_fin.between(fecha_inicio, fecha_fin))
        .all()
        )

    tablaCiclo = (
        db.query(Ciclo)
        .filter(Ciclo.fecha_fin.between(fecha_inicio, fecha_fin))
        .all()
    )

    value = []   

    for item in data:
        recetario_existente = next((v for v in value if v["id_recetario"] == item.id_recetario), None)

        if recetario_existente:
            recetario_existente["ciclos"].append({
                "id_ciclo": item.ciclo.id,
                "pesoProductoXFila": item.pesoProductoXFila
            })
        else:
            value.append({
                "id_recetario": item.id_recetario,
                "ciclos": [
                    {
                        "id_ciclo": item.ciclo.id,
                        "pesoProductoXFila": item.pesoProductoXFila
                    }
                ]
            })
    mapaFechas = {item.id: item.fecha_fin for item in tablaCiclo}

    resultado = []

    for row in value:
        ciclos_agrupados = {}
        for ciclo in row["ciclos"]:
            id_ciclo = ciclo["id_ciclo"]
            peso = ciclo["pesoProductoXFila"]
            if id_ciclo in ciclos_agrupados:
                ciclos_agrupados[id_ciclo] += peso
            else:
                ciclos_agrupados[id_ciclo] = peso
        ciclos_agrupados_lista = [{"id_ciclo": id_ciclo, "pesoTotal": peso_total, "fecha_fin": mapaFechas.get(id_ciclo, None)} for id_ciclo, peso_total in ciclos_agrupados.items()]
        resultado.append({
            "id_recetario": row["id_recetario"],
            "ciclos": ciclos_agrupados_lista
        })

    return resultado

def save_datosCiclo():
    data = 0
    return data

def save_recetaXCiclo():
    data = 0
    return data

def obtenerListaCiclosXProductos(db, fecha_inicio: date, fecha_fin: date):
    data = (
        db.query(RecetaXCiclo)
        .join(Ciclo, RecetaXCiclo.id_ciclo == Ciclo.id)
        .filter(Ciclo.fecha_fin.between(fecha_inicio, fecha_fin))
        .all()
        )
    tablaCiclo = (
        db.query(Ciclo)
        .join(RecetaXCiclo, Ciclo.id == RecetaXCiclo.id_ciclo)
        .filter(Ciclo.fecha_fin.between(fecha_inicio, fecha_fin))
        .all()
    )
    value = [    ]
    for row in tablaCiclo:
        id_fecha = row["fecha_fin"]
        if id_fecha not in value:
            value.append(





















































                
            )

    return tablaCiclo
