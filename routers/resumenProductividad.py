from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from datetime import datetime, date

from fastapi.responses import StreamingResponse
from io import BytesIO

from service.cicloService import resumenDeProductiviada, descargarDocumentoExcel

from config import db

RouterProductividad = APIRouter(prefix="/productividad", tags=["Productividad"])
@RouterProductividad.get("resumen")
def read_productividad(
    fecha_inicio: date = Query(..., description="Fecha de inicio (YYYY-MM-DD HH:MM:SS)"),
    fecha_fin: date = Query(..., description="Fecha de fin (YYYY-MM-DD)"), 
    db : Session = Depends(db.get_db)):
    return resumenDeProductiviada(db, fecha_inicio, fecha_fin)

@RouterProductividad.get("/descargar-excel")
async def download_excel(
    fecha_inicio: date = Query(..., description="Fecha de inicio (YYYY-MM-DD HH:MM:SS)"),
    fecha_fin: date = Query(..., description="Fecha de fin (YYYY-MM-DD)"), 
    db : Session = Depends(db.get_db)):
    
    excel_stream = descargarDocumentoExcel(db, fecha_inicio, fecha_fin)

    # Esta es la respuesta de streaming para descargar el archivo
    return StreamingResponse(
        excel_stream, 
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
        headers={"Content-Disposition": "attachment; filename=productos_ciclos.xlsx"}
    )