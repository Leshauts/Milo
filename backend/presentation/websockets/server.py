# backend/presentation/websockets/server.py
"""
Serveur WebSocket - Version finale avec état initial frais
"""
import json
from fastapi import WebSocket, WebSocketDisconnect
from backend.presentation.websockets.manager import WebSocketManager
from backend.domain.audio_state import AudioSource

class WebSocketServer:
    """Serveur WebSocket simplifié avec état initial correct"""
    
    def __init__(self, ws_manager: WebSocketManager, state_machine):
        self.manager = ws_manager
        self.state_machine = state_machine
    
    async def websocket_endpoint(self, websocket: WebSocket):
        """Point d'entrée WebSocket avec état initial frais"""
        await self.manager.connect(websocket)
        
        try:
            # Récupérer l'état initial de la machine à états
            current_state = await self.state_machine.get_current_state()
            
            # Si un plugin est actif, forcer un refresh des métadonnées
            if current_state['active_source'] != 'none':
                active_source = AudioSource(current_state['active_source'])
                active_plugin = self.state_machine.plugins.get(active_source)
                
                if active_plugin and hasattr(active_plugin, '_refresh_metadata'):
                    # Forcer un refresh pour avoir la position actuelle
                    await active_plugin._refresh_metadata()
                    
                    # Récupérer l'état frais du plugin
                    plugin_status = await active_plugin.get_initial_state()
                    
                    # Mettre à jour l'état courant avec les données fraîches
                    current_state['metadata'] = plugin_status.get('metadata', {})
                    current_state['device_connected'] = plugin_status.get('device_connected', False)
                    current_state['ws_connected'] = plugin_status.get('ws_connected', False)
                    current_state['is_playing'] = plugin_status.get('is_playing', False)
            
            # Envoyer l'état initial
            initial_event = {
                "category": "system",
                "type": "state_changed", 
                "source": "system",
                "data": {"full_state": current_state},
                "timestamp": current_state.get("timestamp", 0)
            }
            
            await websocket.send_text(json.dumps(initial_event))
            
            # Maintenir la connexion ouverte
            while True:
                await websocket.receive_text()
                
        except WebSocketDisconnect:
            self.manager.disconnect(websocket)