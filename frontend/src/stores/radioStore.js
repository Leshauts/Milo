// frontend/src/stores/radioStore.js
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import axios from 'axios';

export const useRadioStore = defineStore('radio', () => {
  // === ÉTAT ===
  const currentStation = ref(null);
  const loading = ref(false);

  // Filtres actifs
  const searchQuery = ref('');
  const countryFilter = ref('');
  const genreFilter = ref('');

  // Cache unifié avec clés composites
  // Clé = combinaison des filtres (ex: "query:nova|country:France|genre:pop")
  const stationsCache = ref(new Map());

  // Cache séparé pour les favoris
  const favoritesCache = ref({ stations: [], total: 0, loaded: false, lastSync: null });

  // Stations visibles actuellement (pour rendu progressif)
  const visibleStations = ref([]);

  // === GETTERS ===

  // Génère une clé de cache composite basée sur tous les filtres actifs
  const generateCacheKey = (query, country, genre) => {
    const parts = [];
    if (query) parts.push(`query:${query}`);
    if (country) parts.push(`country:${country}`);
    if (genre) parts.push(`genre:${genre}`);
    return parts.length > 0 ? parts.join('|') : 'top';
  };

  // Clé du cache actuel
  const currentCacheKey = computed(() => {
    return generateCacheKey(searchQuery.value, countryFilter.value, genreFilter.value);
  });

  // Stations actuelles (toutes celles du cache, pas encore slicées)
  const currentStations = computed(() => {
    const cacheEntry = stationsCache.value.get(currentCacheKey.value);
    return cacheEntry?.stations || [];
  });

  // Total de stations disponibles (depuis le backend)
  const totalStations = computed(() => {
    const cacheEntry = stationsCache.value.get(currentCacheKey.value);
    return cacheEntry?.total || 0;
  });

  // Stations affichées (accumulées progressivement)
  const displayedStations = computed(() => {
    return visibleStations.value;
  });

  // Y a-t-il plus de stations à afficher ?
  const hasMoreStations = computed(() => {
    return visibleStations.value.length < currentStations.value.length;
  });

  // Nombre de stations restantes
  const remainingStations = computed(() => {
    return Math.max(0, currentStations.value.length - visibleStations.value.length);
  });

  // Stations favorites (depuis cache dédié)
  const favoriteStations = computed(() => {
    return favoritesCache.value.stations
      .filter(s => s.is_favorite)
      .sort((a, b) => a.name.localeCompare(b.name));
  });

  // === ACTIONS ===

  /**
   * Charge les stations selon les filtres actifs
   * Utilise le cache si déjà chargé
   */
  async function loadStations(favoritesOnly = false, forceRefresh = false) {
    if (favoritesOnly) {
      // Gestion des favoris (cache séparé)
      if (!forceRefresh && favoritesCache.value.loaded) {
        console.log('📻 Using cached favorites');
        return true;
      }

      loading.value = true;
      try {
        const response = await axios.get('/api/radio/stations', {
          params: { limit: 10000, favorites_only: true }
        });

        favoritesCache.value = {
          stations: response.data.stations,
          total: response.data.total,
          loaded: true,
          lastSync: Date.now()
        };

        console.log(`✅ Loaded ${response.data.stations.length} favorites`);
        return true;
      } catch (error) {
        console.error('❌ Error loading favorites:', error);
        return false;
      } finally {
        loading.value = false;
      }
    }

    // Charger stations normales avec cache composite
    const cacheKey = currentCacheKey.value;

    // Vérifier si déjà en cache (sauf si forceRefresh)
    if (!forceRefresh && stationsCache.value.has(cacheKey) && stationsCache.value.get(cacheKey).loaded) {
      console.log(`📻 Using cached stations for: "${cacheKey}"`);
      // Réinitialiser les stations visibles avec les 40 premières
      visibleStations.value = currentStations.value.slice(0, 40);
      return true;
    }

    // Charger depuis l'API
    loading.value = true;
    try {
      const params = {
        limit: 10000,
        favorites_only: false
      };

      if (searchQuery.value) params.query = searchQuery.value;
      if (countryFilter.value) params.country = countryFilter.value;
      if (genreFilter.value) params.genre = genreFilter.value;

      console.log(`📻 Fetching stations from API - Key: "${cacheKey}"`);
      const response = await axios.get('/api/radio/stations', { params });

      // Stocker dans le cache avec la clé composite
      stationsCache.value.set(cacheKey, {
        stations: response.data.stations,
        total: response.data.total,
        loaded: true
      });

      // Initialiser les stations visibles avec les 40 premières
      visibleStations.value = response.data.stations.slice(0, 40);

      console.log(`✅ Loaded ${response.data.stations.length} stations (total: ${response.data.total})`);
      return true;
    } catch (error) {
      console.error('❌ Error loading stations:', error);
      return false;
    } finally {
      loading.value = false;
    }
  }

  /**
   * Charge plus de stations (pagination locale avec accumulation progressive)
   */
  function loadMore() {
    const increment = 40;
    const currentVisible = visibleStations.value.length;
    const maxAvailable = currentStations.value.length;

    // Calculer combien on peut ajouter
    const newLimit = Math.min(currentVisible + increment, maxAvailable);

    // Ajouter les nouvelles stations à la liste visible
    const newStations = currentStations.value.slice(currentVisible, newLimit);
    visibleStations.value = [...visibleStations.value, ...newStations];

    console.log(`📻 Load more: displaying ${visibleStations.value.length} / ${maxAvailable} stations (added ${newStations.length})`);
  }


  async function playStation(stationId) {
    try {
      // SIMPLIFIÉ: Pas d'optimistic update - faire confiance au backend
      // L'état de buffering sera synchronisé via WebSocket (metadata.buffering)
      const response = await axios.post('/api/radio/play', { station_id: stationId });
      return response.data.success;
    } catch (error) {
      console.error('Error playing station:', error);
      return false;
    }
  }

  async function stopPlayback() {
    try {
      // SIMPLIFIÉ: Pas d'optimistic update - faire confiance au backend
      // L'état sera synchronisé via WebSocket
      const response = await axios.post('/api/radio/stop');
      return response.data.success;
    } catch (error) {
      console.error('Error stopping playback:', error);
      return false;
    }
  }

  async function addFavorite(stationId) {
    try {
      // SIMPLIFIÉ: L'état sera synchronisé via WebSocket
      const response = await axios.post('/api/radio/favorites/add', { station_id: stationId });
      return response.data.success;
    } catch (error) {
      console.error('Error adding favorite:', error);
      return false;
    }
  }

  async function removeFavorite(stationId) {
    try {
      // SIMPLIFIÉ: L'état sera synchronisé via WebSocket
      const response = await axios.post('/api/radio/favorites/remove', { station_id: stationId });
      return response.data.success;
    } catch (error) {
      console.error('Error removing favorite:', error);
      return false;
    }
  }

  async function toggleFavorite(stationId) {
    // Chercher d'abord dans les stations actuelles
    let station = currentStations.value.find(s => s.id === stationId);

    // Sinon dans les stations visibles
    if (!station) {
      station = visibleStations.value.find(s => s.id === stationId);
    }

    // Sinon utiliser currentStation si c'est la bonne
    if (!station && currentStation.value?.id === stationId) {
      station = currentStation.value;
    }

    if (!station) {
      console.warn('toggleFavorite: station not found', stationId);
      return false;
    }

    if (station.is_favorite) {
      return await removeFavorite(stationId);
    } else {
      return await addFavorite(stationId);
    }
  }

  async function markBroken(stationId) {
    try {
      const response = await axios.post('/api/radio/broken/mark', { station_id: stationId });

      if (response.data.success) {
        // Retirer de visibleStations
        visibleStations.value = visibleStations.value.filter(s => s.id !== stationId);

        // Retirer de tous les caches
        stationsCache.value.forEach((cacheEntry) => {
          if (cacheEntry.stations) {
            cacheEntry.stations = cacheEntry.stations.filter(s => s.id !== stationId);
          }
        });

        return true;
      }
      return false;
    } catch (error) {
      console.error('Error marking station as broken:', error);
      return false;
    }
  }

  async function resetBrokenStations() {
    try {
      const response = await axios.post('/api/radio/broken/reset');
      if (response.data.success) {
        await loadStations();
        return true;
      }
      return false;
    } catch (error) {
      console.error('Error resetting broken stations:', error);
      return false;
    }
  }

  async function addCustomStation(stationData) {
    /**
     * Ajoute une station personnalisée avec upload d'image
     *
     * @param {Object} stationData - Données de la station
     * @param {string} stationData.name - Nom de la station
     * @param {string} stationData.url - URL du flux audio
     * @param {string} stationData.country - Pays (défaut: "France")
     * @param {string} stationData.genre - Genre (défaut: "Variety")
     * @param {File} stationData.image - Fichier image (optionnel)
     * @param {number} stationData.bitrate - Bitrate (défaut: 128)
     * @param {string} stationData.codec - Codec (défaut: "MP3")
     * @returns {Promise<{success: boolean, station?: Object, error?: string}>}
     */
    try {
      // Créer un FormData pour l'upload multipart/form-data
      const formData = new FormData();
      formData.append('name', stationData.name);
      formData.append('url', stationData.url);
      formData.append('country', stationData.country || 'France');
      formData.append('genre', stationData.genre || 'Variety');
      formData.append('bitrate', stationData.bitrate || 128);
      formData.append('codec', stationData.codec || 'MP3');

      // Ajouter l'image si fournie
      if (stationData.image) {
        formData.append('image', stationData.image);
      }

      const response = await axios.post('/api/radio/custom/add', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });

      if (response.data.success) {
        const newStation = response.data.station;
        console.log('📻 Station personnalisée ajoutée:', newStation);

        // Invalider tous les caches pour forcer un reload
        stationsCache.value.clear();
        favoritesCache.value.loaded = false;

        return { success: true, station: newStation };
      } else {
        return { success: false, error: response.data.error || 'Échec ajout station' };
      }
    } catch (error) {
      console.error('Error adding custom station:', error);
      const errorMessage = error.response?.data?.detail || error.message || 'Erreur inconnue';
      return { success: false, error: errorMessage };
    }
  }

  async function removeCustomStation(stationId) {
    try {
      const response = await axios.post('/api/radio/custom/remove', { station_id: stationId });

      if (response.data.success) {
        console.log('📻 Station personnalisée supprimée:', stationId);

        // Retirer de visibleStations
        visibleStations.value = visibleStations.value.filter(s => s.id !== stationId);

        // Invalider tous les caches pour forcer un reload
        stationsCache.value.clear();
        favoritesCache.value.loaded = false;

        return true;
      }
      return false;
    } catch (error) {
      console.error('Error removing custom station:', error);
      return false;
    }
  }

  async function removeStationImage(stationId) {
    /**
     * Supprime l'image importée d'une station
     *
     * @param {string} stationId - ID de la station
     * @returns {Promise<{success: boolean, station?: Object, error?: string}>}
     */
    try {
      const formData = new FormData();
      formData.append('station_id', stationId);

      const response = await axios.post('/api/radio/custom/remove-image', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });

      if (response.data.success) {
        const updatedStation = response.data.station;
        console.log('🖼️ Image supprimée:', stationId);

        // Mettre à jour dans visibleStations
        const visibleIndex = visibleStations.value.findIndex(s => s.id === stationId);
        if (visibleIndex !== -1) {
          visibleStations.value[visibleIndex] = updatedStation;
        }

        // Mettre à jour dans tous les caches
        stationsCache.value.forEach((cacheEntry) => {
          if (cacheEntry.stations) {
            const index = cacheEntry.stations.findIndex(s => s.id === stationId);
            if (index !== -1) {
              cacheEntry.stations[index] = updatedStation;
            }
          }
        });

        return { success: true, station: updatedStation };
      } else {
        return { success: false, error: response.data.error || 'Échec suppression image' };
      }
    } catch (error) {
      console.error('Error removing station image:', error);
      const errorMessage = error.response?.data?.detail || error.message || 'Erreur inconnue';
      return { success: false, error: errorMessage };
    }
  }

  function updateFromWebSocket(metadata) {
    // SIMPLIFIÉ: Synchronisation directe depuis le backend (source de vérité)

    // Mise à jour depuis le WebSocket (via unifiedAudioStore)
    if (metadata.station_id) {
      // Chercher la station dans tous les caches
      let station = null;

      // Chercher dans le cache actuel
      station = currentStations.value.find(s => s.id === metadata.station_id);

      // Sinon, chercher dans les favoris
      if (!station) {
        station = favoritesCache.value.stations.find(s => s.id === metadata.station_id);
      }

      if (station) {
        currentStation.value = station;
      } else {
        // Station pas encore chargée, créer un objet minimal
        currentStation.value = {
          id: metadata.station_id,
          name: metadata.station_name || 'Station inconnue',
          country: metadata.country || '',
          genre: metadata.genre || '',
          favicon: metadata.favicon || '',
          is_favorite: metadata.is_favorite || false
        };
      }
    } else {
      // Pas de station en cours (plugin en mode READY)
      currentStation.value = null;
    }

    // NOTE: isPlaying est maintenant géré par unifiedAudioStore.metadata.is_playing
    // NOTE: buffering est maintenant géré par unifiedAudioStore.metadata.buffering
  }

  async function handleFavoriteEvent(stationId, isFavorite) {
    // Synchroniser le statut favori depuis le backend (source de vérité)
    console.log(`🔄 Syncing favorite status: ${stationId} = ${isFavorite}`);

    // Mettre à jour dans TOUS les caches
    const updateInCache = (cacheEntry) => {
      if (cacheEntry && Array.isArray(cacheEntry.stations)) {
        const station = cacheEntry.stations.find(s => s.id === stationId);
        if (station) {
          station.is_favorite = isFavorite;
          return true;
        }
      }
      return false;
    };

    // Mettre à jour dans tous les caches de stations
    stationsCache.value.forEach((cacheEntry) => {
      updateInCache(cacheEntry);
    });

    // Mettre à jour dans les favoris
    updateInCache(favoritesCache.value);

    // Mettre à jour dans visibleStations
    const visibleStation = visibleStations.value.find(s => s.id === stationId);
    if (visibleStation) {
      visibleStation.is_favorite = isFavorite;
    }

    // Si ajout aux favoris et pas déjà dans le cache favorites, recharger
    if (isFavorite && !favoritesCache.value.stations.find(s => s.id === stationId)) {
      console.log('📻 New favorite added, reloading favorites cache');
      await loadStations(true, true); // forceRefresh
    }

    // Mettre à jour currentStation si c'est celle-ci
    if (currentStation.value?.id === stationId) {
      currentStation.value.is_favorite = isFavorite;
    }
  }

  return {
    // État
    currentStation,
    loading,
    searchQuery,
    countryFilter,
    genreFilter,

    // Getters (valeurs calculées)
    currentCacheKey,
    currentStations,
    totalStations,
    displayedStations,
    hasMoreStations,
    remainingStations,
    favoriteStations,

    // Actions
    loadStations,
    loadMore,
    playStation,
    stopPlayback,
    addFavorite,
    removeFavorite,
    toggleFavorite,
    markBroken,
    resetBrokenStations,
    addCustomStation,
    removeCustomStation,
    removeStationImage,
    updateFromWebSocket,
    handleFavoriteEvent
  };
});
