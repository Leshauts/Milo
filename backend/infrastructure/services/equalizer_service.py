# backend/infrastructure/services/equalizer_service.py
"""
Service Equalizer OPTIM pour Milo - Gestion alsaequal via amixer
"""
import asyncio
import logging
import re
from typing import Dict, List, Any, Optional

class EqualizerService:
    """Service de gestion de l'equalizer alsaequal - Version OPTIM"""
    
    # Configuration des bandes d'equalizer
    BANDS = [
        {"id": "00", "freq": "31 Hz"},
        {"id": "01", "freq": "63 Hz"}, 
        {"id": "02", "freq": "125 Hz"},
        {"id": "03", "freq": "250 Hz"},
        {"id": "04", "freq": "500 Hz"},
        {"id": "05", "freq": "1 kHz"},
        {"id": "06", "freq": "2 kHz"},
        {"id": "07", "freq": "4 kHz"},
        {"id": "08", "freq": "8 kHz"},
        {"id": "09", "freq": "16 kHz"}
    ]
    
    def __init__(self, settings_service=None):
        self.logger = logging.getLogger(__name__)
        self.settings_service = settings_service
    
    def _format_frequency_display(self, freq: str) -> str:
        """Formate les fréquences pour un affichage simplifié"""
        freq = freq.strip()
        
        if "kHz" in freq:
            # Extraire le nombre avant "kHz"
            number = freq.replace("kHz", "").strip()
            return f"{number}K"
        elif "Hz" in freq:
            # Extraire le nombre avant "Hz"
            number = freq.replace("Hz", "").strip()
            return number
        
        # Fallback : retourner tel quel
        return freq
    
    async def get_all_bands(self) -> List[Dict[str, Any]]:
        """Récupère les valeurs de toutes les bandes"""
        try:
            proc = await asyncio.create_subprocess_exec(
                "amixer", "-D", "equal", "scontents",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode != 0:
                self.logger.error(f"amixer error: {stderr.decode()}")
                return []
            
            return self._parse_amixer_output(stdout.decode())
            
        except Exception as e:
            self.logger.error(f"Error getting equalizer bands: {e}")
            return []
    
    def _parse_amixer_output(self, output: str) -> List[Dict[str, Any]]:
        """Parse la sortie d'amixer pour extraire les valeurs"""
        bands = []
        lines = output.split('\n')
        current_band = None
        
        for line in lines:
            line = line.strip()
            
            # Détecter le début d'une bande
            if line.startswith("Simple mixer control"):
                match = re.search(r"'(\d+)\.\s+([\d\w\s]+)',", line)
                if match:
                    band_id = match.group(1)
                    freq = match.group(2).strip()
                    current_band = {
                        "id": band_id,
                        "freq": freq,
                        "display_name": self._format_frequency_display(freq),
                        "value": 66 
                    }
            
            # Extraire la valeur (prendre Left comme référence)
            elif line.startswith("Front Left:") and current_band:
                match = re.search(r"Playback (\d+) \[(\d+)%\]", line)
                if match:
                    current_band["value"] = int(match.group(2))
                    bands.append(current_band)
                    current_band = None
        
        return bands
    
    async def set_band_value(self, band_id: str, value: int) -> bool:
        """Modifie la valeur d'une bande spécifique"""
        try:
            # Validation
            if not (0 <= value <= 100):
                self.logger.error(f"Invalid value {value}, must be 0-100")
                return False
            
            # Trouver la bande
            band_info = next((b for b in self.BANDS if b["id"] == band_id), None)
            if not band_info:
                self.logger.error(f"Unknown band ID: {band_id}")
                return False
            
            # Construire le nom du contrôle
            control_name = f"{band_id}. {band_info['freq']}"
            
            # Commande amixer
            proc = await asyncio.create_subprocess_exec(
                "amixer", "-D", "equal", "sset", control_name, f"{value}%",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await proc.communicate()
            
            if proc.returncode != 0:
                error_msg = stderr.decode().strip()
                self.logger.error(f"amixer set error: {error_msg}")
                return False
            
            self.logger.debug(f"Set band {control_name} to {value}%")
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting band {band_id}: {e}")
            return False
    
    async def reset_all_bands(self, value: int = 66) -> bool:
        """Remet toutes les bandes à une valeur donnée (66% par défaut)"""
        try:
            success_count = 0
            
            for band in self.BANDS:
                if await self.set_band_value(band["id"], value):
                    success_count += 1
            
            self.logger.info(f"Reset {success_count}/{len(self.BANDS)} bands to {value}%")
            return success_count == len(self.BANDS)
            
        except Exception as e:
            self.logger.error(f"Error resetting bands: {e}")
            return False
    
    async def is_available(self) -> bool:
        """Vérifie si l'equalizer est disponible"""
        try:
            proc = await asyncio.create_subprocess_exec(
                "amixer", "-D", "equal", "scontents",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await proc.communicate()
            return proc.returncode == 0
        except:
            return False

    async def save_current_bands(self) -> bool:
        """Sauvegarde les valeurs actuelles de l'equalizer dans settings"""
        try:
            if not self.settings_service:
                self.logger.error("SettingsService not available, cannot save bands")
                return False

            # Récupérer les valeurs actuelles
            current_bands = await self.get_all_bands()
            if not current_bands:
                self.logger.warning("No bands to save")
                return False

            # Formater pour la sauvegarde (seulement id et value)
            bands_to_save = [{"id": band["id"], "value": band["value"]} for band in current_bands]

            # Sauvegarder dans settings
            await self.settings_service.set_setting('equalizer.saved_bands', bands_to_save)
            self.logger.info(f"Saved {len(bands_to_save)} equalizer bands to settings")
            return True

        except Exception as e:
            self.logger.error(f"Error saving bands: {e}")
            return False

    async def restore_saved_bands(self) -> bool:
        """Restaure les valeurs de l'equalizer depuis settings"""
        try:
            if not self.settings_service:
                self.logger.error("SettingsService not available, cannot restore bands")
                return False

            # Récupérer les valeurs sauvegardées
            saved_bands = await self.settings_service.get_setting('equalizer.saved_bands')
            if not saved_bands:
                self.logger.info("No saved bands found, skipping restore")
                return True  # Pas une erreur, juste rien à restaurer

            # Restaurer chaque bande
            success_count = 0
            for band_data in saved_bands:
                band_id = band_data.get("id")
                value = band_data.get("value")

                if band_id is not None and value is not None:
                    if await self.set_band_value(band_id, value):
                        success_count += 1

            self.logger.info(f"Restored {success_count}/{len(saved_bands)} equalizer bands from settings")
            return success_count == len(saved_bands)

        except Exception as e:
            self.logger.error(f"Error restoring bands: {e}")
            return False
    
    async def get_equalizer_status(self) -> Dict[str, Any]:
        """Récupère l'état complet de l'equalizer"""
        try:
            available = await self.is_available()
            if not available:
                return {
                    "available": False,
                    "bands": [],
                    "message": "Equalizer not available"
                }
            
            bands = await self.get_all_bands()
            return {
                "available": True,
                "bands": bands,
                "band_count": len(bands)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting equalizer status: {e}")
            return {
                "available": False,
                "bands": [],
                "error": str(e)
            }