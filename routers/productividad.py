from fastapi import APIRouter, HTTPException, Depends, Query, status
from sqlalchemy.orm import Session
from datetime import datetime, date
from services.desp import user_dependency

from fastapi.responses import StreamingResponse

from services.cicloService import resumenDeProductividad, generarDocumentoXLMSProductividad

from config import db

RouterProductividad = APIRouter(prefix="/productividad", tags=["Productividad"])
@RouterProductividad.get("/resumen")
def read_productividad(
    fecha_inicio: date = Query(..., description="Fecha de inicio (YYYY-MM-DD HH:MM:SS)"),
    fecha_fin: date = Query(..., description="Fecha de fin (YYYY-MM-DD)"), 
    db : Session = Depends(db.get_db)):

    if not fecha_inicio:
        raise HTTPException(status_code=400 , detail="Debe especificar una fecha de inicio.")
    if not fecha_fin:
        raise HTTPException(status_code=400, detail="Debe especificar una fecha de fin.")

    return resumenDeProductividad(db, fecha_inicio, fecha_fin)

@RouterProductividad.get("/descargar-excel")
async def descargar_documento(
    fecha_inicio: date = Query(..., description="Fecha de inicio (YYYY-MM-DD HH:MM:SS)"),
    fecha_fin: date = Query(..., description="Fecha de fin (YYYY-MM-DD)"), 
    db : Session = Depends(db.get_db)):

    if not fecha_inicio:
        raise HTTPException(status_code=400 , detail="Debe especificar una fecha de inicio.")
    if not fecha_fin:
        raise HTTPException(status_code=400, detail="Debe especificar una fecha de fin.")
    
    excel_stream = generarDocumentoXLMSProductividad(db, fecha_inicio, fecha_fin)

    fecha_actual = datetime.now().strftime("%Y-%m-%d_%H-%M")
    nombreArchivo = f"resumen_productividad_{fecha_actual}.xlsx"

    return StreamingResponse(
        excel_stream, 
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
        headers={"Content-Disposition": f"attachment; filename={nombreArchivo}"}
    )
