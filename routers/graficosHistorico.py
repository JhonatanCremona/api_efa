from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from datetime import datetime, date

from service.cicloService import obtenerRecetasPorFecha, obtenerListaCiclosXProductos
from config import db

RoutersGraficosH = APIRouter(prefix="/graficos-hsitorico", tags=["Graficos Historico"]) 
#Ejemplo: http://localhost:8000/graficos-hsitorico/ciclos-productos/?fecha_inicio=2024-01-02&fecha_fin=2024-01-08
#Lineas de productos en un grafico
@RoutersGraficosH.get("/ciclos-productos/")
def red_lista_ciclos_productos(
    fecha_inicio: date = Query(..., description="Fecha de inicio (YYYY-MM-DD HH:MM:SS)"),
    fecha_fin: date = Query(..., description="Fecha de fin (YYYY-MM-DD)"), 
    db : Session = Depends(db.get_db)):

    resupuesta = obtenerRecetasPorFecha(db, fecha_inicio, fecha_fin)
    return resupuesta

#Ejemplo : 
#Lineas de productos y ciclos realizados proyectado en un grafico
@RoutersGraficosH.get("/productos-realizados/")
def red_productos_realizados(fecha_inicio: date = Query(..., description="Fecha de inicio (YYYY-MM-DD)"),fecha_fin: date = Query(..., description="Fecha de fin (YYYY-MM-DD)"), db : Session = Depends(db.get_db)):
    resupuesta = obtenerListaCiclosXProductos(db, fecha_inicio, fecha_fin)
    return resupuesta
