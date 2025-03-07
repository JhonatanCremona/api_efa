from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import date, datetime
from models.recetaxciclo import RecetaXCiclo
from models.ciclo import Ciclo
from models.recetaxciclo import Recetario
from models.torre import Torre
from models.torreconfiguraciones import TorreConfiguraciones

from collections import defaultdict
from datetime import datetime

from openpyxl import Workbook
from openpyxl.drawing.image import Image
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.worksheet.table import Table, TableStyleInfo

from io import BytesIO

import logging

logger = logging.getLogger("uvicorn")
def listarRecetas(db):
    recetas = db.query(Recetario.id, Recetario.codigoProducto).order_by(Recetario.id.asc()).all()
    
    respuestaListadoRecetas = {"ListadoRecetas": [{"id": receta.id, "codigoProducto": receta.codigoProducto} for receta in recetas]}
    
    return respuestaListadoRecetas

def listarTorres(db, id_receta: int):
    torres = (
        db.query(Torre.id)
        .filter(Torre.id_recetario == id_receta)
        .order_by(Torre.id.asc())
        .all()
    )
    
    respuestaListadoTorres = {"ListadoTorres": [{"id": torre.id} for torre in torres]}
    
    return respuestaListadoTorres

def obtenerTorre(db, id_torre: int):
    datostorre = (
        db.query(
            Torre.hBastidor,
            Torre.hAjuste,
            Torre.hAjusteN1,
            Torre.DisteNivel,
            Torre.ActualizarTAG,
            Torre.cantidadNiveles
        )
        .filter(Torre.id == id_torre)
        .first()
    )
    
    datosnivelesHN = (
        db.query(
            TorreConfiguraciones.nivel, 
            TorreConfiguraciones.valor,
            TorreConfiguraciones.tipo
        )
        .join(Torre, Torre.id == TorreConfiguraciones.id_torre)
        .filter(
            and_(
                TorreConfiguraciones.id_torre == id_torre,  
            )
        )
        .all()
    )

    datosnivelesChB = (
        db.query(
            TorreConfiguraciones.nivel, 
            TorreConfiguraciones.valor,
            TorreConfiguraciones.tipo
        )
        .join(Torre, Torre.id == TorreConfiguraciones.id_torre)
        .filter(
            and_(
                TorreConfiguraciones.id_torre == id_torre,  
            )
        )
        .all()
    )

    datosnivelesChG = (
        db.query( 
            TorreConfiguraciones.nivel, 
            TorreConfiguraciones.valor,
            TorreConfiguraciones.tipo
        )
        .join(Torre, Torre.id == TorreConfiguraciones.id_torre)
        .filter(
            and_(
                TorreConfiguraciones.id_torre == id_torre,  
            )
        )
        .all()
    )

    datosnivelesFallas = (
        db.query(
            TorreConfiguraciones.nivel, 
            TorreConfiguraciones.valor,
            TorreConfiguraciones.tipo
        )
        .join(Torre, Torre.id == TorreConfiguraciones.id_torre)
        .filter(
            and_(
                TorreConfiguraciones.id_torre == id_torre,  
            )
        )
        .all()
    )

    datosnivelesuHN = (
        db.query(
            TorreConfiguraciones.nivel, 
            TorreConfiguraciones.valor,
            TorreConfiguraciones.tipo
        )
        .join(Torre, Torre.id == TorreConfiguraciones.id_torre)
        .filter(
            and_(
                TorreConfiguraciones.id_torre == id_torre,  
            )
        )
        .all()
    )
    
    respuestaNivelesTorre = {
        "DatosTorre": {
            "hBastidor": datostorre.hBastidor,
            "hAjuste": datostorre.hAjuste,
            "hAjusteN1": datostorre.hAjusteN1,
            "DisteNivel": datostorre.DisteNivel,
            "ActualizarTAG": datostorre.ActualizarTAG,
            "cantidadNiveles": datostorre.cantidadNiveles,
        } if datostorre else None,  # Verifica que datostorre no sea None

        "DatosNivelesHN": [],  # Inicializa una lista con 12 elementos en 0
        "DatosNivelesChG": [],  # Inicializa una lista con 12 elementos en 0
        "DatosNivelesChB": [],  # Inicializa una lista con 12 elementos en 0
        "DatosNivelesFallas": [],  # Inicializa una lista con 12 elementos en 0
        "DatosNivelesuHN": []  # Inicializa una lista con 12 elementos en 0
    }

    if datosnivelesHN:
        for dato in datosnivelesHN:
            if dato.tipo == "HN":
                respuestaNivelesTorre["DatosNivelesHN"].append(dato.valor)

    if datosnivelesChG:
        for dato in datosnivelesChG:
            if dato.tipo == "ChG":
                respuestaNivelesTorre["DatosNivelesChG"].append(dato.valor)

    if datosnivelesChB:
        for dato in datosnivelesChB:
            if dato.tipo == "ChB":
                respuestaNivelesTorre["DatosNivelesChB"].append(dato.valor)

    if datosnivelesFallas:
        for dato in datosnivelesFallas:
            if dato.tipo == "Fallas":
                respuestaNivelesTorre["DatosNivelesFallas"].append(dato.valor)
    
    if datosnivelesuHN:
        for dato in datosnivelesuHN:
            if dato.tipo == "uHN":
                respuestaNivelesTorre["DatosNivelesuHN"].append(dato.valor)

    return respuestaNivelesTorre

    datosnivelesHN = (
        db.query(
            TorreConfiguraciones.nivel, 
            TorreConfiguraciones.valor,
            TorreConfiguraciones.tipo
        )
        .join(Torre, Torre.id == TorreConfiguraciones.id_torre)
        .filter(
            and_(
                TorreConfiguraciones.id_torre == id_torre,  
            )
        )
        .all()
    )

def datosRecetasConfiguraciones (db, id_receta: int):
    recetas = (
        db.query(
            Recetario.id, 
            Recetario.codigoProducto, 
            Recetario.nroGripper, 
            Recetario.tipoMolde, 
            Recetario.anchoProducto, 
            Recetario.altoProducto, 
            Recetario.largoProducto,
            Recetario.pesoProducto,
            Recetario.moldesNivel,
            Recetario.altoMolde,
            Recetario.largoMolde,
            Recetario.ajusteAltura,
            Recetario.cantidadNiveles,
            Recetario.deltaNiveles,
            Recetario.n1Altura,
            Recetario.bastidorAltura,
            Recetario.ajusteN1Altura,
        ).filter(Recetario.id == id_receta)  # Filtra según id_receta ingresado
        .order_by(Recetario.id.asc())
        .all()
    )
    
    respuestaDatosRecetas = {
        "DatosRecetas": [{
            "id": receta.id,
            "codigoProducto": receta.codigoProducto,
            "nroGripper": receta.nroGripper,
            "tipoMolde": receta.tipoMolde,
            "anchoProducto": receta.anchoProducto,
            "altoProducto": receta.altoProducto,
            "largoProducto": receta.largoProducto,
            "pesoProducto": receta.pesoProducto,
            "moldesNivel": receta.moldesNivel,
            "altoMolde": receta.altoMolde,
            "largoMolde": receta.largoMolde,
            "ajusteAltura": receta.ajusteAltura,
            "cantidadNiveles": receta.cantidadNiveles,
            "deltaNiveles": receta.deltaNiveles,
            "n1Altura": receta.n1Altura,
            "bastidorAltura": receta.bastidorAltura,
            "ajusteN1Altura": receta.ajusteN1Altura,
        } for receta in recetas]}
    
    return respuestaDatosRecetas
