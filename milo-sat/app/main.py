#!/usr/bin/env python3
"""
Milo Sat - API Service for Satellite Snapclient Management
Version: 1.1 - Hybrid approach (GitHub .deb + APT dependency resolution)
"""

import asyncio
import aiohttp
import aiofiles
import re
import tempfile
import shutil
import logging
import os
import platform
import time
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import uvicorn

# Configuration de base
SNAPCLIENT_VERSION_REGEX = r"v(\d+\.\d+\.\d+)"
GITHUB_REPO = "badaix/snapcast"
API_PORT = 8001
UPDATE_IN_PROGRESS = False

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Milo Sat API",
    description="API pour la gestion des satellites Milo",
    version="1.0.0"
)

class SnapclientManager:
    """Gestionnaire pour les opérations snapclient"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.SnapclientManager")
    
    async def get_installed_version(self) -> Optional[str]:
        """Récupère la version installée de snapclient"""
        try:
            proc = await asyncio.create_subprocess_exec(
                "snapclient", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=5.0)
            output_text = stdout.decode() + stderr.decode()
            
            match = re.search(SNAPCLIENT_VERSION_REGEX, output_text)
            if match:
                return match.group(1)
                
            return None
            
        except (FileNotFoundError, asyncio.TimeoutError, Exception) as e:
            self.logger.error(f"Error getting snapclient version: {e}")
            return None

    async def get_latest_github_version(self) -> Optional[str]:
        """Récupère la dernière version depuis GitHub"""
        try:
            url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        tag_name = data.get("tag_name", "")

                        match = re.search(SNAPCLIENT_VERSION_REGEX, tag_name)
                        if match:
                            return match.group(1)

                        # Fallback: retourner tag_name sans le 'v'
                        return tag_name.lstrip('v')

                    return None

        except Exception as e:
            self.logger.error(f"Error getting latest version from GitHub: {e}")
            return None

    async def is_service_running(self) -> bool:
        """Vérifie si le service snapclient est en cours d'exécution"""
        try:
            proc = await asyncio.create_subprocess_exec(
                "systemctl", "is-active", "milo-sat-snapclient.service",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, _ = await proc.communicate()
            return stdout.decode().strip() == "active"
            
        except Exception as e:
            self.logger.error(f"Error checking service status: {e}")
            return False
    
    async def update_snapclient(self, target_version: str) -> Dict[str, Any]:
        """Met à jour snapclient depuis GitHub avec résolution APT des dépendances"""
        global UPDATE_IN_PROGRESS

        if UPDATE_IN_PROGRESS:
            return {"success": False, "error": "Update already in progress"}

        try:
            UPDATE_IN_PROGRESS = True
            self.logger.info(f"Starting snapclient update to version {target_version}")

            # Récupérer la version actuelle avant mise à jour
            old_version = await self.get_installed_version()

            # 1. Télécharger le .deb depuis GitHub
            download_result = await self._download_snapclient_deb(target_version)
            if not download_result["success"]:
                return download_result

            # 2. Arrêter le service
            stop_result = await self._stop_snapclient_service()
            if not stop_result:
                return {"success": False, "error": "Failed to stop snapclient service"}

            # 3. Installer le .deb avec APT (qui résout les dépendances automatiquement)
            install_result = await self._install_deb_with_apt(download_result["deb_path"])
            if not install_result["success"]:
                return install_result

            # 4. Redémarrer le service
            start_result = await self._start_snapclient_service()
            if not start_result:
                return {"success": False, "error": "Failed to start snapclient service"}

            # 5. Vérifier la mise à jour
            await asyncio.sleep(3)  # Attendre que le service soit stable
            new_version = await self.get_installed_version()

            if new_version == target_version:
                self.logger.info(f"Snapclient successfully updated from {old_version} to {new_version}")
                return {
                    "success": True,
                    "message": f"Snapclient updated successfully",
                    "old_version": old_version,
                    "new_version": new_version
                }
            else:
                return {
                    "success": False,
                    "error": f"Version mismatch after update: expected {target_version}, got {new_version}"
                }

        except Exception as e:
            self.logger.error(f"Update failed: {e}")
            return {"success": False, "error": str(e)}

        finally:
            UPDATE_IN_PROGRESS = False
            # Nettoyer les fichiers temporaires
            if 'download_result' in locals() and download_result.get("temp_dir"):
                shutil.rmtree(download_result["temp_dir"], ignore_errors=True)

    async def _download_snapclient_deb(self, version: str) -> Dict[str, Any]:
        """Télécharge le package .deb snapclient depuis GitHub"""
        try:
            temp_dir = tempfile.mkdtemp()
            package_name = f"snapclient_{version}-1_arm64_bookworm.deb"
            url = f"https://github.com/{GITHUB_REPO}/releases/download/v{version}/{package_name}"

            deb_path = Path(temp_dir) / package_name

            self.logger.info(f"Downloading {package_name} from GitHub...")

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return {
                            "success": False,
                            "error": f"Download failed: HTTP {response.status}"
                        }

                    async with aiofiles.open(deb_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            await f.write(chunk)

            return {
                "success": True,
                "deb_path": str(deb_path),
                "temp_dir": temp_dir
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _install_deb_with_apt(self, deb_path: str) -> Dict[str, Any]:
        """Installe un package .deb en utilisant dpkg + apt-get -f (méthode officielle Snapcast)"""
        try:
            env = {
                "DEBIAN_FRONTEND": "noninteractive",
                "DEBCONF_NONINTERACTIVE_SEEN": "true",
                "APT_LISTCHANGES_FRONTEND": "none"
            }

            # Étape 1 : Mettre à jour la liste des paquets
            self.logger.info("Updating APT package list...")
            proc = await asyncio.create_subprocess_exec(
                "sudo", "-E", "apt", "update",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, **env}
            )
            await proc.communicate()

            # Étape 2 : Installer le .deb avec dpkg (peut échouer sur dépendances manquantes)
            self.logger.info("Installing .deb package with dpkg...")
            proc = await asyncio.create_subprocess_exec(
                "sudo", "-E", "dpkg", "-i",
                "--force-confdef",
                "--force-confnew",
                deb_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, **env}
            )

            stdout, stderr = await proc.communicate()

            # Note: dpkg peut retourner une erreur si des dépendances manquent, c'est normal
            if proc.returncode != 0:
                self.logger.warning(f"dpkg returned error (expected if dependencies missing): {stderr.decode()[:200]}")

            # Étape 3 : Résoudre les dépendances manquantes avec apt-get -f install
            self.logger.info("Fixing dependencies with apt-get -f install...")
            proc = await asyncio.create_subprocess_exec(
                "sudo", "-E", "apt-get", "-f", "install", "-y",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, **env}
            )

            stdout, stderr = await proc.communicate()

            if proc.returncode == 0:
                self.logger.info("Package installed successfully with dependencies resolved")
                return {"success": True}
            else:
                return {
                    "success": False,
                    "error": f"apt-get -f install failed: {stderr.decode()}"
                }

        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _stop_snapclient_service(self) -> bool:
        """Arrête le service snapclient"""
        try:
            proc = await asyncio.create_subprocess_exec(
                "sudo", "systemctl", "stop", "milo-sat-snapclient.service",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE
            )
            
            _, stderr = await proc.communicate()
            return proc.returncode == 0
            
        except Exception as e:
            self.logger.error(f"Failed to stop snapclient service: {e}")
            return False
    
    async def _start_snapclient_service(self) -> bool:
        """Démarre le service snapclient"""
        try:
            proc = await asyncio.create_subprocess_exec(
                "sudo", "systemctl", "start", "milo-sat-snapclient.service",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE
            )
            
            _, stderr = await proc.communicate()
            
            if proc.returncode != 0:
                return False
            
            # Attendre que le service soit vraiment démarré
            await asyncio.sleep(2)
            
            # Vérifier l'état
            is_running = await self.is_service_running()
            return is_running
            
        except Exception as e:
            self.logger.error(f"Failed to start snapclient service: {e}")
            return False

# Instance globale du gestionnaire
snapclient_manager = SnapclientManager()

def get_system_uptime() -> int:
    """Récupère l'uptime du système en secondes"""
    try:
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
            return int(uptime_seconds)
    except Exception:
        return 0

def get_hostname() -> str:
    """Récupère le hostname du système"""
    return platform.node()

# Routes API

@app.get("/health")
async def health_check():
    """Endpoint de santé basique"""
    return {
        "status": "healthy",
        "timestamp": int(time.time()),
        "hostname": get_hostname()
    }

@app.get("/status")
async def get_status():
    """Récupère le statut complet du satellite"""
    try:
        hostname = get_hostname()
        uptime = get_system_uptime()
        snapclient_version = await snapclient_manager.get_installed_version()
        snapclient_running = await snapclient_manager.is_service_running()
        
        return {
            "hostname": hostname,
            "uptime": uptime,
            "snapclient": {
                "version": snapclient_version,
                "running": snapclient_running,
                "status": "running" if snapclient_running else "stopped"
            },
            "update_in_progress": UPDATE_IN_PROGRESS,
            "timestamp": int(time.time())
        }
        
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/version")
async def get_version():
    """Récupère uniquement la version de snapclient"""
    try:
        version = await snapclient_manager.get_installed_version()
        
        if version:
            return {
                "version": version,
                "timestamp": int(time.time())
            }
        else:
            return {
                "version": None,
                "error": "Could not determine snapclient version",
                "timestamp": int(time.time())
            }
            
    except Exception as e:
        logger.error(f"Error getting version: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/update")
async def update_snapclient(background_tasks: BackgroundTasks):
    """Lance la mise à jour de snapclient depuis GitHub"""
    global UPDATE_IN_PROGRESS

    if UPDATE_IN_PROGRESS:
        raise HTTPException(status_code=409, detail="Update already in progress")

    try:
        # Récupérer la dernière version disponible sur GitHub
        latest_version = await snapclient_manager.get_latest_github_version()
        if not latest_version:
            raise HTTPException(status_code=500, detail="Could not determine latest version")

        # Vérifier si une mise à jour est nécessaire
        current_version = await snapclient_manager.get_installed_version()
        if current_version == latest_version:
            return {
                "success": False,
                "message": "Already up to date",
                "current_version": current_version,
                "latest_version": latest_version
            }

        # Lancer la mise à jour en arrière-plan
        async def do_update():
            result = await snapclient_manager.update_snapclient(latest_version)
            logger.info(f"Update completed: {result}")

        background_tasks.add_task(do_update)

        return {
            "success": True,
            "message": f"Update started: {current_version} -> {latest_version}",
            "current_version": current_version,
            "target_version": latest_version
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting update: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/update/status")
async def get_update_status():
    """Récupère le statut de la mise à jour en cours"""
    return {
        "update_in_progress": UPDATE_IN_PROGRESS,
        "timestamp": int(time.time())
    }

# Point d'entrée principal
if __name__ == "__main__":
    logger.info(f"Starting Milo Sat API on port {API_PORT}")
    logger.info(f"Hostname: {get_hostname()}")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=API_PORT,
        log_level="info",
        access_log=True
    )