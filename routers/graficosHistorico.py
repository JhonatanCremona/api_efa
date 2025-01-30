from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from datetime import datetime, date
from fastapi.responses import StreamingResponse

from service.cicloService import obtenerRecetasPorFecha, obtenerListaCiclosXProductos, generarDocumentoXLMSGraficos, graficosHistoricos
from config import db
from desp import user_dependency

RoutersGraficosH = APIRouter(prefix="/graficos-historico", tags=["Graficos Historico"]) 
@RoutersGraficosH.get("/ciclos-productos/")
def red_lista_ciclos_productos(user: user_dependency, 
    fecha_inicio: date = Query(..., description="Fecha de inicio (YYYY-MM-DD HH:MM:SS)"),
    fecha_fin: date = Query(..., description="Fecha de fin (YYYY-MM-DD)"), 
    db : Session = Depends(db.get_db)):

    resupuesta = obtenerRecetasPorFecha(db, fecha_inicio, fecha_fin)
    return resupuesta

@RoutersGraficosH.get("/productos-realizados/")
def red_productos_realizados(user: user_dependency, fecha_inicio: date = Query(..., description="Fecha de inicio (YYYY-MM-DD)"),fecha_fin: date = Query(..., description="Fecha de fin (YYYY-MM-DD)"), db : Session = Depends(db.get_db)):
    resupuesta = obtenerListaCiclosXProductos(db, fecha_inicio, fecha_fin)
    return resupuesta

@RoutersGraficosH.get("/descargar-excel")
def descargar_documento(user: user_dependency, fecha_inicio: date = Query(..., description="Fecha de inicio (YYYY-MM-DD)"),fecha_fin: date = Query(..., description="Fecha de fin (YYYY-MM-DD)"), db : Session = Depends(db.get_db)):
    if not fecha_inicio:
        raise HTTPException(status_code=400 , detail="Debe especificar una fecha de inicio.")
    if not fecha_fin:
        raise HTTPException(status_code=400, detail="Debe especificar una fecha de fin.")
    excel_streem = generarDocumentoXLMSGraficos(db, fecha_inicio, fecha_fin)
    
    fecha_actual = datetime.now().strftime("%Y-%m-%d_%H-%M")
    nombreArchivo = f"productos_ciclos_{fecha_actual}.xlsx"

    return StreamingResponse(
        excel_streem, 
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
        headers={"Content-Disposition": f"attachment; filename={nombreArchivo}"}
    )

@RoutersGraficosH.get("/lista-datos")
def red_lista_datos_graficos(user: user_dependency, fecha_inicio: date = Query(..., description="Fecha de inicio (YYYY-MM-DD)"),fecha_fin: date = Query(..., description="Fecha de fin (YYYY-MM-DD)"), db : Session = Depends(db.get_db)):
    if not fecha_inicio:
        raise HTTPException(status_code=400 , detail="Debe especificar una fecha de inicio.")
    if not fecha_fin:
        raise HTTPException(status_code=400, detail="Debe especificar una fecha de fin.")
    return graficosHistoricos(db, fecha_inicio, fecha_fin)