from fastapi import APIRouter, HTTPException, Depends, Query, status
from sqlalchemy.orm import Session
from services.desp import user_dependency
from fastapi.responses import StreamingResponse
from services.configService import listarRecetas, listarTorres, obtenerTorre, datosRecetasConfiguraciones
from config import db
from models.torre import Torre
from models.torreconfiguraciones import TorreConfiguraciones
from models.cicloDesmoldeo import CicloDesmoldeo
from pydantic import BaseModel
from typing import Optional

RouterConfiguraciones = APIRouter(prefix="/configuraciones", tags=["Configuraciones"])

class POSTDatosTorre(BaseModel):
    id: str
    hBastidor: Optional[int] = None
    hAjuste: Optional[int] = None
    hAjusteN1: Optional[int] = None
    DisteNivel: Optional[int] = None
    ActualizarTAG: str
    id_recetario: int  # Hacerlo obligatorio, sin valor por defecto

class POSTDatosNiveles(BaseModel):
    id: str
    tipo: str
    Correccion1: Optional[int] = None
    Correccion2: Optional[int] = None
    Correccion3: Optional[int] = None
    Correccion4: Optional[int] = None
    Correccion5: Optional[int] = None
    Correccion6: Optional[int] = None
    Correccion7: Optional[int] = None
    Correccion8: Optional[int] = None
    Correccion9: Optional[int] = None
    Correccion10: Optional[int] = None
    Correccion11: Optional[int] = None

@RouterConfiguraciones.get("/lista-recetas")
def read_lista_recetas(db: Session = Depends(db.get_db)):
    return listarRecetas(db)

@RouterConfiguraciones.get("/lista-torres")
def read_lista_torres(
    id_receta: int = Query(0, description="ID de la receta para filtrar torres"),
    db: Session = Depends(db.get_db)
):
    return listarTorres(db, id_receta)

@RouterConfiguraciones.get("/niveles-torre")
def read_lista_niveles(
    id_torre: str = Query("", description="ID de la torre para filtrar niveles de la misma"),
    db: Session = Depends(db.get_db)
):
    return obtenerTorre(db, id_torre)

@RouterConfiguraciones.get("/datos-recetas")
def read_datos_recetas(
    id_receta: int = Query(0, description="ID de la receta para filtrar datos"),
    db: Session = Depends(db.get_db)
):
    return datosRecetasConfiguraciones(db, id_receta)

@RouterConfiguraciones.post("/tomar-datos-torre", response_model=POSTDatosTorre)
async def tomar_datos_torre(POST_datos_torre: POSTDatosTorre, db: Session = Depends(db.get_db)):
    try:
        torre_existente = db.query(Torre).filter(Torre.id == POST_datos_torre.id).first()

        if torre_existente:
            old_id = torre_existente.id
            old_ntorre = torre_existente.NTorre  # Obtener NTorre antes de cambios

            # Solo actualiza si el valor recibido no es None ni ""
            if POST_datos_torre.ActualizarTAG not in [None, ""]:
                torre_existente.id = POST_datos_torre.ActualizarTAG

                # Actualizar id_torre en TorreConfiguraciones y Ciclo
                db.query(TorreConfiguraciones).filter(TorreConfiguraciones.id_torre == old_id).update(
                    {"id_torre": torre_existente.id, "id_torreNum": old_ntorre}
                )
                db.query(Ciclo).filter(Ciclo.id_torre == old_id).update({"id_torre": torre_existente.id})

            if POST_datos_torre.hBastidor not in [None, ""]:
                torre_existente.hBastidor = POST_datos_torre.hBastidor

            if POST_datos_torre.hAjuste not in [None, ""]:
                torre_existente.hAjuste = POST_datos_torre.hAjuste

            if POST_datos_torre.hAjusteN1 not in [None, ""]:
                torre_existente.hAjusteN1 = POST_datos_torre.hAjusteN1

            if POST_datos_torre.DisteNivel not in [None, ""]:
                torre_existente.DisteNivel = POST_datos_torre.DisteNivel

            if POST_datos_torre.ActualizarTAG not in [None, "", 0]:
                torre_existente.ActualizarTAG = POST_datos_torre.ActualizarTAG

            db.commit()
            db.refresh(torre_existente)
            return torre_existente
        else:
            raise HTTPException(status_code=404, detail="Torre no encontrada")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@RouterConfiguraciones.post("/tomar-datos-niveles", response_model=POSTDatosNiveles)
async def tomar_datos_niveles(POST_datos_niveles: POSTDatosNiveles, db: Session = Depends(db.get_db)):
    try:
        # Consultamos los ids correspondientes según los parámetros id_torre y tipo
        configuraciones = db.query(TorreConfiguraciones).filter(
            TorreConfiguraciones.id_torre == POST_datos_niveles.id,
            TorreConfiguraciones.tipo == POST_datos_niveles.tipo
        ).all()

        if configuraciones:
            result_ids = [config.id for config in configuraciones]

            nivel_existente = db.query(Torre).filter(Torre.id == POST_datos_niveles.id).first()

            if nivel_existente:
                # Creamos un diccionario con las correcciones
                correcciones = {
                    "Correccion1": POST_datos_niveles.Correccion1,
                    "Correccion2": POST_datos_niveles.Correccion2,
                    "Correccion3": POST_datos_niveles.Correccion3,
                    "Correccion4": POST_datos_niveles.Correccion4,
                    "Correccion5": POST_datos_niveles.Correccion5,
                    "Correccion6": POST_datos_niveles.Correccion6,
                    "Correccion7": POST_datos_niveles.Correccion7,
                    "Correccion8": POST_datos_niveles.Correccion8,
                    "Correccion9": POST_datos_niveles.Correccion9,
                    "Correccion10": POST_datos_niveles.Correccion10,
                    "Correccion11": POST_datos_niveles.Correccion11
                }

                # Filtramos las correcciones, pero conservamos todas las claves, incluso las que son None o ""
                procesadas = {key: value for key, value in correcciones.items() if value not in [None, ""]}

                # Creamos un diccionario para hacer el mapeo entre el ID y la corrección
                correccion_map = {key: correcciones[key] if correcciones[key] not in [None, ""] else None for key in correcciones}

                # Si no hay correcciones válidas, retornamos un mensaje
                if not procesadas:
                    return {"message": "No se procesaron correcciones válidas"}

                # Actualizamos la tabla TorreConfiguraciones solo si la corrección no es None o ""
                for i, config in enumerate(configuraciones):
                    correccion_key = f"Correccion{i+1}"  # Generamos la clave de la corrección a aplicar
                    if correccion_map.get(correccion_key) not in [None, ""]:
                        config.valor = correccion_map[correccion_key]  # Asignamos el valor solo si no es None ni ""
                        db.commit()  # Realizamos el commit después de cada cambio

                return {
                    "id": POST_datos_niveles.id,
                    "tipo": POST_datos_niveles.tipo,
                    "ids": result_ids,
                    **procesadas  # Devolvemos solo las correcciones procesadas (sin None ni "")
                }

            else:
                raise HTTPException(status_code=404, detail="Datos de niveles no encontrados")
        else:
            raise HTTPException(status_code=404, detail="No se encontraron configuraciones con esos datos")

    except Exception as e:
        db.rollback()  # En caso de error, revertimos cualquier cambio
        raise HTTPException(status_code=500, detail=str(e))

@RouterConfiguraciones.post("/reset-datos-niveles", response_model=POSTDatosNiveles)
async def reset_datos_niveles(POST_datos_niveles: POSTDatosNiveles, db: Session = Depends(db.get_db)):
    try:
        # Consultamos los ids correspondientes según los parámetros id_torre y tipo
        configuraciones = db.query(TorreConfiguraciones).filter(
            TorreConfiguraciones.id_torre == POST_datos_niveles.id,
            TorreConfiguraciones.tipo == POST_datos_niveles.tipo
        ).all()

        if configuraciones:
            result_ids = [config.id for config in configuraciones]

            nivel_existente = db.query(Torre).filter(Torre.id == POST_datos_niveles.id).first()

            if nivel_existente:
                # Creamos un diccionario con las correcciones, ignorando las que sean None
                correcciones = {
                    "Correccion1": POST_datos_niveles.Correccion1,
                    "Correccion2": POST_datos_niveles.Correccion2,
                    "Correccion3": POST_datos_niveles.Correccion3,
                    "Correccion4": POST_datos_niveles.Correccion4,
                    "Correccion5": POST_datos_niveles.Correccion5,
                    "Correccion6": POST_datos_niveles.Correccion6,
                    "Correccion7": POST_datos_niveles.Correccion7,
                    "Correccion8": POST_datos_niveles.Correccion8,
                    "Correccion9": POST_datos_niveles.Correccion9,
                    "Correccion10": POST_datos_niveles.Correccion10,
                    "Correccion11": POST_datos_niveles.Correccion11
                }

                # Filtramos SOLO la corrección con el valor 0 y que no sea None
                correccion_reset = {key: value for key, value in correcciones.items() if value == 0}

                # Si no hay ninguna corrección con 0, no hacemos nada
                if not correccion_reset:
                    return {"message": "No se recibió ninguna corrección para resetear"}

                # Aplicamos solo la corrección con 0 en la base de datos
                for i, config in enumerate(configuraciones):
                    correccion_key = f"Correccion{i+1}"
                    if correccion_key in correccion_reset:
                        config.valor = 0
                        db.commit()

                return {
                    "id": POST_datos_niveles.id,
                    "tipo": POST_datos_niveles.tipo,
                    "ids": result_ids,
                    **correccion_reset  # Solo devolvemos las correcciones con 0 aplicadas
                }

            else:
                raise HTTPException(status_code=404, detail="Datos de niveles no encontrados")
        else:
            raise HTTPException(status_code=404, detail="No se encontraron configuraciones con esos datos")

    except Exception as e:
        db.rollback()  # En caso de error, revertimos cualquier cambio
        raise HTTPException(status_code=500, detail=str(e))
