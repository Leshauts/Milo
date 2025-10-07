"""
Routes API pour la gestion du volume - Version volume affiché (0-100%) avec validation
"""
from fastapi import APIRouter, HTTPException
from backend.presentation.api.models import VolumeSetRequest, VolumeAdjustRequest

def create_volume_router(volume_service):
    """Crée le router volume avec injection de dépendances"""
    router = APIRouter(prefix="/api/volume", tags=["volume"])

    @router.get("/status")
    async def get_volume_status():
        """Récupère l'état actuel du volume (en volume affiché)"""
        try:
            status = await volume_service.get_status()
            return {"status": "success", "data": status}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @router.get("/")
    async def get_current_volume():
        """Récupère le volume affiché actuel (0-100%)"""
        try:
            volume = await volume_service.get_display_volume()
            return {"status": "success", "volume": volume}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/set")
    async def set_volume(request: VolumeSetRequest):
        """Définit le volume affiché (0-100%) avec validation"""
        try:
            success = await volume_service.set_display_volume(request.volume, show_bar=request.show_bar)

            if success:
                return {"status": "success", "volume": request.volume}
            else:
                raise HTTPException(status_code=500, detail="Failed to set volume")

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.post("/adjust")
    async def adjust_volume(request: VolumeAdjustRequest):
        """Ajuste le volume affiché par delta avec validation"""
        try:
            success = await volume_service.adjust_display_volume(request.delta, show_bar=request.show_bar)

            if success:
                current_volume = await volume_service.get_display_volume()
                return {"status": "success", "volume": current_volume, "delta": request.delta}
            else:
                raise HTTPException(status_code=500, detail="Failed to adjust volume")

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.post("/increase")
    async def increase_volume():
        """Augmente le volume affiché de 5%"""
        try:
            success = await volume_service.increase_display_volume(5)
            if success:
                current_volume = await volume_service.get_display_volume()
                return {"status": "success", "volume": current_volume}
            else:
                raise HTTPException(status_code=500, detail="Failed to increase volume")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.post("/decrease")
    async def decrease_volume():
        """Diminue le volume affiché de 5%"""
        try:
            success = await volume_service.decrease_display_volume(5)
            if success:
                current_volume = await volume_service.get_display_volume()
                return {"status": "success", "volume": current_volume}
            else:
                raise HTTPException(status_code=500, detail="Failed to decrease volume")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    return router