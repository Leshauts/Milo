// frontend/src/stores/radioStore.js
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import axios from 'axios';

export const useRadioStore = defineStore('radio', () => {
  // === ÉTAT ===
  const stations = ref([]);
  const favorites = ref([]);
  const currentStation = ref(null);
  // SUPPRIMÉ: isPlaying local - utiliser unifiedAudioStore.metadata.is_playing à la place
  const loading = ref(false);
  const searchQuery = ref('');
  const countryFilter = ref('');
  const genreFilter = ref('');

  // === GETTERS ===
  const filteredStations = computed(() => {
    let result = stations.value;

    if (searchQuery.value) {
      const query = searchQuery.value.toLowerCase();
      result = result.filter(s =>
        s.name.toLowerCase().includes(query) ||
        s.genre.toLowerCase().includes(query)
      );
    }

    if (countryFilter.value) {
      const country = countryFilter.value.toLowerCase();
      result = result.filter(s => s.country.toLowerCase().includes(country));
    }

    if (genreFilter.value) {
      const genre = genreFilter.value.toLowerCase();
      result = result.filter(s => s.genre.toLowerCase().includes(genre));
    }

    return result;
  });

  const favoriteStations = computed(() => {
    return stations.value.filter(s => s.is_favorite);
  });

  // === ACTIONS ===
  async function loadStations(favoritesOnly = false) {
    loading.value = true;
    try {
      const params = {
        limit: 100,
        favorites_only: favoritesOnly
      };

      if (searchQuery.value) params.query = searchQuery.value;
      if (countryFilter.value) params.country = countryFilter.value;
      if (genreFilter.value) params.genre = genreFilter.value;

      const response = await axios.get('/api/radio/stations', { params });
      stations.value = response.data;
      return true;
    } catch (error) {
      console.error('Error loading stations:', error);
      return false;
    } finally {
      loading.value = false;
    }
  }

  async function loadFavorites() {
    try {
      const response = await axios.get('/api/radio/favorites');
      favorites.value = response.data;
      return true;
    } catch (error) {
      console.error('Error loading favorites:', error);
      return false;
    }
  }

  async function playStation(stationId) {
    try {
      // SIMPLIFIÉ: Pas d'optimistic update - faire confiance au backend
      // L'état sera synchronisé via WebSocket
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
    // Chercher d'abord dans la liste des stations
    let station = stations.value.find(s => s.id === stationId);

    // Si pas trouvée, utiliser currentStation si c'est la bonne
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
        // Retirer de la liste
        stations.value = stations.value.filter(s => s.id !== stationId);
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

  function updateFromWebSocket(metadata) {
    // SIMPLIFIÉ: Synchronisation directe depuis le backend (source de vérité)
    // Plus d'optimistic updates à gérer

    // Mise à jour depuis le WebSocket (via unifiedAudioStore)
    if (metadata.station_id) {
      const station = stations.value.find(s => s.id === metadata.station_id);
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
    // Ce store ne maintient plus d'état local pour isPlaying
  }

  function handleFavoriteEvent(stationId, isFavorite) {
    // Synchroniser le statut favori depuis le backend (source de vérité)
    console.log(`🔄 Syncing favorite status: ${stationId} = ${isFavorite}`);

    // Mettre à jour dans la liste des stations
    const station = stations.value.find(s => s.id === stationId);
    if (station) {
      station.is_favorite = isFavorite;
    }

    // Mettre à jour currentStation si c'est celle-ci
    if (currentStation.value?.id === stationId) {
      currentStation.value.is_favorite = isFavorite;
    }

    // Recharger la liste des favoris
    loadFavorites();
  }

  return {
    // État
    stations,
    favorites,
    currentStation,
    // SUPPRIMÉ: isPlaying - utiliser unifiedAudioStore.metadata.is_playing
    loading,
    searchQuery,
    countryFilter,
    genreFilter,

    // Getters
    filteredStations,
    favoriteStations,

    // Actions
    loadStations,
    loadFavorites,
    playStation,
    stopPlayback,
    addFavorite,
    removeFavorite,
    toggleFavorite,
    markBroken,
    resetBrokenStations,
    updateFromWebSocket,
    handleFavoriteEvent
  };
});
