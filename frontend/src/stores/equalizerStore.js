// frontend/src/stores/equalizerStore.js
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import axios from 'axios';

// Constantes des bandes d'égaliseur
const STATIC_BANDS = [
  { id: "00", freq: "31 Hz", display_name: "31" },
  { id: "01", freq: "63 Hz", display_name: "63" },
  { id: "02", freq: "125 Hz", display_name: "125" },
  { id: "03", freq: "250 Hz", display_name: "250" },
  { id: "04", freq: "500 Hz", display_name: "500" },
  { id: "05", freq: "1 kHz", display_name: "1K" },
  { id: "06", freq: "2 kHz", display_name: "2K" },
  { id: "07", freq: "4 kHz", display_name: "4K" },
  { id: "08", freq: "8 kHz", display_name: "8K" },
  { id: "09", freq: "16 kHz", display_name: "16K" }
];

const DEFAULT_VALUE = 66;
const THROTTLE_DELAY = 100;
const FINAL_DELAY = 300;

export const useEqualizerStore = defineStore('equalizer', () => {
  // === ÉTAT ===
  const bands = ref([]);
  const isLoading = ref(false);
  const isUpdating = ref(false);
  const isResetting = ref(false);
  const bandsLoaded = ref(false);

  // Gestion du throttling
  const bandThrottleMap = new Map();

  // === COMPUTED ===
  const isAvailable = computed(() => bands.value.length > 0);

  // === INITIALIZATION ===
  function initializeBands() {
    // Initialiser avec les valeurs par défaut (seront remplacées par l'API)
    bands.value = STATIC_BANDS.map(band => ({
      ...band,
      value: DEFAULT_VALUE
    }));
  }

  // === API CALLS ===
  async function fetchStatus() {
    try {
      const response = await axios.get('/api/equalizer/status');
      return response.data;
    } catch (error) {
      console.error('Error fetching equalizer status:', error);
      return null;
    }
  }

  async function fetchBands() {
    try {
      const response = await axios.get('/api/equalizer/bands');
      return response.data.bands || [];
    } catch (error) {
      console.error('Error fetching equalizer bands:', error);
      return [];
    }
  }

  async function sendBandUpdate(bandId, value) {
    try {
      const response = await axios.post(`/api/equalizer/band/${bandId}`, { value });
      return response.data.status === 'success';
    } catch (error) {
      console.error('Error updating band:', error);
      return false;
    }
  }

  async function sendResetBands(value = 66) {
    try {
      const response = await axios.post('/api/equalizer/reset', { value });
      return response.data.status === 'success';
    } catch (error) {
      console.error('Error resetting bands:', error);
      return false;
    }
  }

  // === ACTIONS ===
  async function loadBands() {
    isLoading.value = true;
    bandsLoaded.value = false;

    try {
      const [statusData, bandsData] = await Promise.all([
        fetchStatus(),
        fetchBands()
      ]);

      if (statusData?.available && bandsData.length > 0) {
        // Mettre à jour vers les vraies valeurs depuis l'API
        bands.value = bands.value.map(band => {
          const apiBand = bandsData.find(b => b.id === band.id);
          return {
            ...band,
            value: apiBand ? apiBand.value : band.value
          };
        });
      }

      bandsLoaded.value = true;
    } catch (error) {
      console.error('Error loading equalizer data:', error);
    } finally {
      isLoading.value = false;
    }
  }

  function updateBandValue(bandId, value) {
    const band = bands.value.find(b => b.id === bandId);
    if (band) {
      band.value = value;
    }
  }

  function handleBandThrottled(bandId, value) {
    const now = Date.now();
    let state = bandThrottleMap.get(bandId) || {};

    if (state.throttleTimeout) clearTimeout(state.throttleTimeout);
    if (state.finalTimeout) clearTimeout(state.finalTimeout);

    if (!state.lastRequestTime || (now - state.lastRequestTime) >= THROTTLE_DELAY) {
      sendBandUpdate(bandId, value);
      state.lastRequestTime = now;
    } else {
      state.throttleTimeout = setTimeout(() => {
        sendBandUpdate(bandId, value);
        state.lastRequestTime = Date.now();
      }, THROTTLE_DELAY - (now - state.lastRequestTime));
    }

    state.finalTimeout = setTimeout(() => {
      sendBandUpdate(bandId, value);
      state.lastRequestTime = Date.now();
    }, FINAL_DELAY);

    bandThrottleMap.set(bandId, state);
  }

  function clearThrottleForBand(bandId) {
    const state = bandThrottleMap.get(bandId);
    if (state) {
      if (state.throttleTimeout) clearTimeout(state.throttleTimeout);
      if (state.finalTimeout) clearTimeout(state.finalTimeout);
      bandThrottleMap.delete(bandId);
    }
  }

  function clearAllThrottles() {
    bandThrottleMap.forEach(state => {
      if (state.throttleTimeout) clearTimeout(state.throttleTimeout);
      if (state.finalTimeout) clearTimeout(state.finalTimeout);
    });
    bandThrottleMap.clear();
  }

  async function updateBand(bandId, value) {
    updateBandValue(bandId, value);
    handleBandThrottled(bandId, value);
  }

  async function finalizeBandUpdate(bandId, value) {
    await sendBandUpdate(bandId, value);
    clearThrottleForBand(bandId);
  }

  async function resetAllBands() {
    if (isResetting.value) return false;

    isResetting.value = true;
    try {
      const success = await sendResetBands(66);
      if (success) {
        bands.value.forEach(band => {
          band.value = 66;
        });
      }
      return success;
    } catch (error) {
      console.error('Error resetting bands:', error);
      return false;
    } finally {
      isResetting.value = false;
    }
  }

  // === WEBSOCKET HANDLERS ===
  function handleBandChanged(event) {
    if (event.data.band_changed) {
      const { band_id, value } = event.data;
      const band = bands.value.find(b => b.id === band_id);
      // Ne pas mettre à jour si on est en train de throttler (évite les conflits)
      if (band && bandThrottleMap.size === 0) {
        band.value = value;
      }
    }
  }

  function handleReset(event) {
    if (event.data.reset) {
      // Ne pas mettre à jour si on est en train de throttler
      if (bandThrottleMap.size === 0) {
        bands.value.forEach(band => {
          band.value = event.data.reset_value;
        });
      }
    }
  }

  // === CLEANUP ===
  function cleanup() {
    clearAllThrottles();
    bandsLoaded.value = false;
  }

  return {
    // État
    bands,
    isLoading,
    isUpdating,
    isResetting,
    bandsLoaded,

    // Computed
    isAvailable,

    // Actions
    initializeBands,
    loadBands,
    updateBand,
    finalizeBandUpdate,
    resetAllBands,
    cleanup,

    // WebSocket Handlers
    handleBandChanged,
    handleReset
  };
});
