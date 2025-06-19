# backend/presentation/api/routes/equalizer.py
"""
Routes API pour l'equalizer - Version OPTIM
"""
from fastapi import APIRouter
from typing import Dict, Any

def create_equalizer_router(equalizer_service, state_machine):
    """Crée le router equalizer"""
    router = APIRouter(prefix="/api/equalizer", tags=["equalizer"])
    
    @router.get("/status")
    async def get_equalizer_status():
        """Récupère l'état complet de l'equalizer"""
        try:
            status = await equalizer_service.get_equalizer_status()
            return status
        except Exception as e:
            return {
                "available": False,
                "bands": [],
                "error": str(e)
            }
    
    @router.get("/bands")
    async def get_all_bands():
        """Récupère toutes les bandes avec leurs valeurs actuelles"""
        try:
            bands = await equalizer_service.get_all_bands()
            return {"bands": bands}
        except Exception as e:
            return {"bands": [], "error": str(e)}
    
    @router.post("/band/{band_id}")
    async def set_band_value(band_id: str, payload: Dict[str, Any]):
        """Modifie la valeur d'une bande"""
        try:
            value = payload.get("value")
            
            if not isinstance(value, int) or not (0 <= value <= 100):
                return {
                    "status": "error", 
                    "message": "Invalid value (0-100 required)"
                }
            
            success = await equalizer_service.set_band_value(band_id, value)
            
            if success:
                # Notifier via WebSocket
                await state_machine.broadcast_event("equalizer", "band_changed", {
                    "band_id": band_id,
                    "value": value,
                    "source": "equalizer"
                })
                
                return {"status": "success", "band_id": band_id, "value": value}
            else:
                return {"status": "error", "message": "Failed to set band value"}
                
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    @router.post("/reset")
    async def reset_all_bands(payload: Dict[str, Any] = None):
        """Remet toutes les bandes à une valeur donnée (50% par défaut)"""
        try:
            reset_value = 50
            if payload and "value" in payload:
                reset_value = payload["value"]
                if not isinstance(reset_value, int) or not (0 <= reset_value <= 100):
                    return {
                        "status": "error",
                        "message": "Invalid reset value (0-100 required)"
                    }
            
            success = await equalizer_service.reset_all_bands(reset_value)
            
            if success:
                # Notifier via WebSocket
                await state_machine.broadcast_event("equalizer", "reset", {
                    "reset_value": reset_value,
                    "source": "equalizer"
                })
                
                return {
                    "status": "success", 
                    "message": f"All bands reset to {reset_value}%",
                    "reset_value": reset_value
                }
            else:
                return {"status": "error", "message": "Failed to reset bands"}
                
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    @router.get("/available")
    async def check_equalizer_available():
        """Vérifie si l'equalizer est disponible"""
        try:
            available = await equalizer_service.is_available()
            return {"available": available}
        except Exception as e:
            return {"available": False, "error": str(e)}
    
    return router