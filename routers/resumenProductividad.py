from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from datetime import datetime, date

from service.cicloService import resumenDeProductiviada

from config import db

RouterProductividad = APIRouter(prefix="/productividad", tags=["Productividad"])
@RouterProductividad.get("resumen")
def read_productividad(
    fecha_inicio: date = Query(..., description="Fecha de inicio (YYYY-MM-DD HH:MM:SS)"),
    fecha_fin: date = Query(..., description="Fecha de fin (YYYY-MM-DD)"), 
    db : Session = Depends(db.get_db)):
    return resumenDeProductiviada(db, fecha_inicio, fecha_fin)