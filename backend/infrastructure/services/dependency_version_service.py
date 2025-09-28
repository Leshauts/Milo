# backend/infrastructure/services/dependency_version_service.py
"""
Service de gestion des versions des dépendances - Version OPTIM
"""
import asyncio
import aiohttp
import logging
import re
from typing import Dict, Any, Optional, List
from pathlib import Path

class DependencyVersionService:
    """Service simplifié pour gérer les versions des dépendances Milo"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Configuration des dépendances (snapserver et snapclient séparés)
        self.dependencies = {
            "go-librespot": {
                "name": "go-librespot",
                "description": "Spotify Connect",
                "commands": {
                    "main": ["sh", "-c", "strings /usr/local/bin/go-librespot | grep 'Bv[0-9]' | sed 's/^.*Bv//' | head -1"]
                },
                "repo": "devgianlu/go-librespot",
                "version_regex": r"(\d+\.\d+\.\d+)"
            },
            "snapserver": {
                "name": "Snapserver",
                "description": "Serveur multiroom",
                "commands": {
                    "main": ["snapserver", "--version"]
                },
                "repo": "badaix/snapcast",
                "version_regex": r"v(\d+\.\d+\.\d+)"
            },
            "snapclient": {
                "name": "Snapclient", 
                "description": "Client multiroom",
                "commands": {
                    "main": ["snapclient", "--version"]
                },
                "repo": "badaix/snapcast",
                "version_regex": r"v(\d+\.\d+\.\d+)"
            },
            "bluez-alsa": {
                "name": "BlueZ ALSA",
                "description": "Bluetooth audio",
                "commands": {
                    "main": ["bluealsa", "--version"]
                },
                "repo": "arkq/bluez-alsa",
                "version_regex": r"v(\d+\.\d+\.\d+)"
            },
            "roc-toolkit": {
                "name": "ROC Streaming",
                "description": "Streaming audio depuis macOS",
                "commands": {
                    "recv": ["roc-recv", "--version"]
                },
                "repo": "roc-streaming/roc-toolkit",
                "version_regex": r"roc-recv (\d+\.\d+\.\d+)"
            }
        }
        
        # Cache pour éviter les appels répétés à GitHub
        self._github_cache = {}
        self._cache_timeout = 3600  # 1 heure
        self._last_github_fetch = {}
    
    async def get_installed_version(self, dependency_key: str) -> Dict[str, Any]:
        """Récupère la version installée d'une dépendance"""
        if dependency_key not in self.dependencies:
            return {"status": "error", "message": "Unknown dependency"}
        
        dep_config = self.dependencies[dependency_key]
        result = {
            "name": dep_config["name"],
            "description": dep_config["description"],
            "status": "unknown",
            "versions": {},
            "errors": []
        }
        
        # Tenter de récupérer les versions pour chaque commande
        for cmd_name, cmd_args in dep_config["commands"].items():
            try:
                version = await self._execute_version_command(cmd_args, dep_config["version_regex"])
                if version:
                    result["versions"][cmd_name] = version
                    result["status"] = "installed"
                else:
                    result["errors"].append(f"{cmd_name}: Version non détectée")
            except Exception as e:
                result["errors"].append(f"{cmd_name}: {str(e)}")
        
        # Si aucune version détectée, marquer comme non installé
        if not result["versions"]:
            result["status"] = "not_installed"
        
        return result
    
    async def _execute_version_command(self, cmd_args: List[str], version_regex: str) -> Optional[str]:
        """Exécute une commande de version et extrait le numéro"""
        try:
            # Timeout court pour éviter les blocages
            proc = await asyncio.create_subprocess_exec(
                *cmd_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=5.0)
                
                # Chercher la version dans stdout puis stderr
                output_text = stdout.decode() + stderr.decode()
                match = re.search(version_regex, output_text)
                
                if match:
                    return match.group(1)
                
                # Fallback : chercher des patterns de version communs
                fallback_patterns = [
                    r"(\d+\.\d+\.\d+)",
                    r"version (\d+\.\d+\.\d+)",
                    r"Version: (\d+\.\d+\.\d+)"
                ]
                
                for pattern in fallback_patterns:
                    match = re.search(pattern, output_text, re.IGNORECASE)
                    if match:
                        return match.group(1)
                
                return None
                
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                raise Exception("Command timeout")
                
        except FileNotFoundError:
            raise Exception("Command not found")
        except Exception as e:
            raise Exception(f"Execution error: {str(e)}")
    
    async def get_latest_github_version(self, dependency_key: str) -> Dict[str, Any]:
        """Récupère la dernière version depuis GitHub avec cache"""
        if dependency_key not in self.dependencies:
            return {"status": "error", "message": "Unknown dependency"}
        
        repo = self.dependencies[dependency_key]["repo"]
        
        # Vérifier le cache
        import time
        current_time = time.time()
        cache_key = f"github_{dependency_key}"
        
        if (cache_key in self._github_cache and 
            cache_key in self._last_github_fetch and
            current_time - self._last_github_fetch[cache_key] < self._cache_timeout):
            return self._github_cache[cache_key]
        
        try:
            # Appel à l'API GitHub
            url = f"https://api.github.com/repos/{repo}/releases/latest"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        tag_name = data.get("tag_name", "")
                        
                        # Extraire le numéro de version
                        version_regex = self.dependencies[dependency_key]["version_regex"]
                        match = re.search(version_regex, tag_name)
                        
                        if match:
                            result = {
                                "status": "success",
                                "version": match.group(1),
                                "tag_name": tag_name,
                                "published_at": data.get("published_at"),
                                "html_url": data.get("html_url")
                            }
                        else:
                            result = {
                                "status": "success",
                                "version": tag_name,
                                "tag_name": tag_name,
                                "published_at": data.get("published_at"),
                                "html_url": data.get("html_url")
                            }
                        
                        # Mettre en cache
                        self._github_cache[cache_key] = result
                        self._last_github_fetch[cache_key] = current_time
                        
                        return result
                    
                    elif response.status == 403:
                        return {"status": "error", "message": "GitHub API rate limit exceeded"}
                    else:
                        return {"status": "error", "message": f"GitHub API error: {response.status}"}
        
        except asyncio.TimeoutError:
            return {"status": "error", "message": "GitHub API timeout"}
        except Exception as e:
            return {"status": "error", "message": f"GitHub API error: {str(e)}"}
    
    async def get_all_dependency_status(self) -> Dict[str, Any]:
        """Récupère le statut de toutes les dépendances"""
        results = {}
        
        # Récupérer les versions installées en parallèle
        tasks = []
        for dep_key in self.dependencies.keys():
            tasks.append(self._get_dependency_full_status(dep_key))
        
        dependency_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, dep_key in enumerate(self.dependencies.keys()):
            if isinstance(dependency_results[i], Exception):
                results[dep_key] = {
                    "status": "error",
                    "message": str(dependency_results[i])
                }
            else:
                results[dep_key] = dependency_results[i]
        
        return results
    
    async def _get_dependency_full_status(self, dependency_key: str) -> Dict[str, Any]:
        """Récupère le statut complet (installé + GitHub) pour une dépendance"""
        try:
            # Lancer les deux requêtes en parallèle
            installed_task = self.get_installed_version(dependency_key)
            github_task = self.get_latest_github_version(dependency_key)
            
            installed_result, github_result = await asyncio.gather(
                installed_task, github_task, return_exceptions=True
            )
            
            # Gérer les exceptions
            if isinstance(installed_result, Exception):
                installed_result = {"status": "error", "message": str(installed_result)}
            
            if isinstance(github_result, Exception):
                github_result = {"status": "error", "message": str(github_result)}
            
            # Combiner les résultats
            result = {
                "name": self.dependencies[dependency_key]["name"],
                "description": self.dependencies[dependency_key]["description"],
                "installed": installed_result,
                "latest": github_result,
                "update_available": False
            }
            
            # Déterminer s'il y a une mise à jour disponible
            if (installed_result.get("status") == "installed" and 
                github_result.get("status") == "success"):
                
                # Prendre la première version installée pour comparaison
                installed_versions = installed_result.get("versions", {})
                if installed_versions:
                    installed_version = list(installed_versions.values())[0]
                    latest_version = github_result.get("version")
                    
                    if installed_version and latest_version:
                        result["update_available"] = self._compare_versions(installed_version, latest_version)
            
            return result
            
        except Exception as e:
            return {
                "name": self.dependencies[dependency_key]["name"],
                "description": self.dependencies[dependency_key]["description"],
                "status": "error",
                "message": str(e)
            }
    
    def _compare_versions(self, installed: str, latest: str) -> bool:
        """Compare deux versions semver (retourne True si mise à jour disponible)"""
        try:
            def parse_version(version_str):
                # Nettoyer et parser la version
                clean_version = re.sub(r'[^\d.]', '', version_str)
                parts = clean_version.split('.')
                # S'assurer qu'on a au moins 3 parties
                while len(parts) < 3:
                    parts.append('0')
                return [int(p) for p in parts[:3]]
            
            installed_parts = parse_version(installed)
            latest_parts = parse_version(latest)
            
            # Comparaison semver
            for i in range(3):
                if latest_parts[i] > installed_parts[i]:
                    return True
                elif latest_parts[i] < installed_parts[i]:
                    return False
            
            return False  # Versions identiques
            
        except Exception:
            # En cas d'erreur de parsing, on considère qu'il n'y a pas de mise à jour
            return False
    
    def get_dependency_list(self) -> List[Dict[str, Any]]:
        """Récupère la liste des dépendances configurées"""
        return [
            {
                "key": key,
                "name": config["name"],
                "description": config["description"]
            }
            for key, config in self.dependencies.items()
        ]