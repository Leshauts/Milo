<!-- frontend/src/components/equalizer/EqualizerModal.vue - Version OPTIM nettoyée -->
<template>
  <div class="equalizer-modal">
    <div class="screen-main">
      <!-- Header avec toggle -->
      <div class="modal-header">
        <h2 class="heading-2">Égaliseur</h2>
        <div class="controls-wrapper">
          <IconButton v-if="isEqualizerEnabled" icon="reset" variant="dark" :disabled="resetting"
            @click="resetAllBands" />
          <Toggle v-model="isEqualizerEnabled" variant="primary" :disabled="unifiedStore.isTransitioning"
            @change="handleEqualizerToggle" />
        </div>
      </div>

      <!-- Contenu principal -->
      <div class="main-content">
        <div v-if="!isEqualizerEnabled" class="not-active">
          <Icon name="equalizer" :size="148" color="var(--color-background-glass)" />
          <p class="text-mono">Égaliseur désactivé</p>
        </div>

        <div v-else class="equalizer-controls">
          <div v-if="loading" class="loading-state">
            <Icon name="equalizer" :size="148" color="var(--color-background-glass)" />
            <p class="text-mono">Chargement de l'égaliseur</p>
          </div>

          <template v-else>
            <RangeSliderEqualizer v-for="band in bands" :key="band.id" v-model="band.value" :label="band.display_name"
              :orientation="sliderOrientation" :min="0" :max="100" :step="1" unit="%" :disabled="updating"
              @input="handleBandInput(band.id, $event)" @change="handleBandChange(band.id, $event)" />
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useUnifiedAudioStore } from '@/stores/unifiedAudioStore';
import useWebSocket from '@/services/websocket';
import axios from 'axios';
import IconButton from '@/components/ui/IconButton.vue';
import Toggle from '@/components/ui/Toggle.vue';
import RangeSliderEqualizer from './RangeSliderEqualizer.vue';
import Icon from '@/components/ui/Icon.vue';

const unifiedStore = useUnifiedAudioStore();
const { on } = useWebSocket();

// État local
const loading = ref(false);
const updating = ref(false);
const resetting = ref(false);
const bands = ref([]);
const isMobile = ref(false);

// Gestion du throttling pour les bandes
const bandThrottleMap = new Map();
const THROTTLE_DELAY = 100;
const FINAL_DELAY = 300;

// Références pour nettoyage
let unsubscribeFunctions = [];

// Computed
const isEqualizerEnabled = computed(() => unifiedStore.equalizerEnabled);
const sliderOrientation = computed(() => isMobile.value ? 'horizontal' : 'vertical');

// Détection mobile
function updateMobileStatus() {
  const aspectRatio = window.innerWidth / window.innerHeight;
  isMobile.value = aspectRatio <= 4 / 3;
}

// === FETCH INITIAL ===
async function fetchEqualizerState() {
  try {
    const routingResponse = await axios.get('/api/routing/status');
    const routingData = routingResponse.data;
    
    if (routingData.routing?.equalizer_enabled !== undefined) {
      unifiedStore.systemState.equalizer_enabled = routingData.routing.equalizer_enabled;
    }
    
    if (routingData.routing?.equalizer_enabled) {
      await loadEqualizerData();
    }
  } catch (error) {
    console.error('Error fetching equalizer state:', error);
  }
}

async function loadEqualizerData() {
  if (!isEqualizerEnabled.value) return;

  loading.value = true;
  try {
    const [statusResponse, bandsResponse] = await Promise.all([
      axios.get('/api/equalizer/status'),
      axios.get('/api/equalizer/bands')
    ]);

    if (statusResponse.data.available) {
      bands.value = bandsResponse.data.bands || [];
    } else {
      bands.value = [];
    }
  } catch (error) {
    console.error('Error loading equalizer data:', error);
    bands.value = [];
  } finally {
    loading.value = false;
  }
}

// === GESTION DES BANDES ===
function handleBandInput(bandId, value) {
  const band = bands.value.find(b => b.id === bandId);
  if (band) band.value = value;
  handleBandThrottled(bandId, value);
}

function handleBandChange(bandId, value) {
  sendBandRequest(bandId, value);
  clearThrottleForBand(bandId);
}

function handleBandThrottled(bandId, value) {
  const now = Date.now();
  let state = bandThrottleMap.get(bandId) || {};

  if (state.throttleTimeout) clearTimeout(state.throttleTimeout);
  if (state.finalTimeout) clearTimeout(state.finalTimeout);

  if (!state.lastRequestTime || (now - state.lastRequestTime) >= THROTTLE_DELAY) {
    sendBandRequest(bandId, value);
    state.lastRequestTime = now;
  } else {
    state.throttleTimeout = setTimeout(() => {
      sendBandRequest(bandId, value);
      state.lastRequestTime = Date.now();
    }, THROTTLE_DELAY - (now - state.lastRequestTime));
  }

  state.finalTimeout = setTimeout(() => {
    sendBandRequest(bandId, value);
    state.lastRequestTime = Date.now();
  }, FINAL_DELAY);

  bandThrottleMap.set(bandId, state);
}

async function sendBandRequest(bandId, value) {
  try {
    const response = await axios.post(`/api/equalizer/band/${bandId}`, { value });
    if (response.data.status !== 'success') {
      console.error('Failed to update band:', response.data.message);
    }
  } catch (error) {
    console.error('Error updating band:', error);
  }
}

function clearThrottleForBand(bandId) {
  const state = bandThrottleMap.get(bandId);
  if (state) {
    if (state.throttleTimeout) clearTimeout(state.throttleTimeout);
    if (state.finalTimeout) clearTimeout(state.finalTimeout);
    bandThrottleMap.delete(bandId);
  }
}

async function resetAllBands() {
  if (resetting.value) return;

  resetting.value = true;
  try {
    const response = await axios.post('/api/equalizer/reset', { value: 66 });
    if (response.data.status === 'success') {
      bands.value.forEach(band => { band.value = 66; });
    }
  } catch (error) {
    console.error('Error resetting bands:', error);
  } finally {
    resetting.value = false;
  }
}

async function handleEqualizerToggle(enabled) {
  await unifiedStore.setEqualizerEnabled(enabled);
}

// === WEBSOCKET ===
function handleEqualizerUpdate(event) {
  if (event.data.band_changed) {
    const { band_id, value } = event.data;
    const band = bands.value.find(b => b.id === band_id);
    if (band && bandThrottleMap.size === 0) {
      band.value = value;
    }
  } else if (event.data.reset) {
    if (bandThrottleMap.size === 0) {
      bands.value.forEach(band => { band.value = event.data.reset_value; });
    }
  }
}

// Watcher equalizer state
let lastEqualizerState = isEqualizerEnabled.value;
const watcherInterval = setInterval(() => {
  if (lastEqualizerState !== isEqualizerEnabled.value) {
    lastEqualizerState = isEqualizerEnabled.value;
    if (isEqualizerEnabled.value) {
      loadEqualizerData();
    } else {
      bands.value = [];
      bandThrottleMap.forEach(state => {
        if (state.throttleTimeout) clearTimeout(state.throttleTimeout);
        if (state.finalTimeout) clearTimeout(state.finalTimeout);
      });
      bandThrottleMap.clear();
    }
  }
}, 100);

// === LIFECYCLE ===
onMounted(async () => {
  updateMobileStatus();
  window.addEventListener('resize', updateMobileStatus);
  
  await fetchEqualizerState();
  
  unsubscribeFunctions.push(
    on('equalizer', 'band_changed', handleEqualizerUpdate),
    on('equalizer', 'reset', handleEqualizerUpdate)
  );
});

onUnmounted(() => {
  window.removeEventListener('resize', updateMobileStatus);
  unsubscribeFunctions.forEach(unsubscribe => unsubscribe());
  clearInterval(watcherInterval);
  
  bandThrottleMap.forEach(state => {
    if (state.throttleTimeout) clearTimeout(state.throttleTimeout);
    if (state.finalTimeout) clearTimeout(state.finalTimeout);
  });
  bandThrottleMap.clear();
});
</script>

<style scoped>
.equalizer-modal {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.screen-main {
  display: flex;
  flex-direction: column;
  gap: var(--space-03);
  height: 100%;
  min-height: 0;
}

.modal-header {
  background: var(--color-background-contrast);
  border-radius: var(--radius-04);
  padding: var(--space-04) var(--space-04) var(--space-04) var(--space-05);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h2 {
  color: var(--color-text-contrast);
}

.controls-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
}

.main-content {
  flex: 1;
}

.not-active {
  display: flex;
  height: 100%;
  flex-direction: column;
  padding: var(--space-09) var(--space-05);
  border-radius: var(--radius-04);
  background: var(--color-background-neutral);
  gap: var(--space-04);
}

.not-active .text-mono {
  text-align: center;
  color: var(--color-text-secondary);
}

.equalizer-controls {
  background: var(--color-background-neutral);
  border-radius: var(--radius-04);
  height: 100%;
  display: flex;
  justify-content: space-between;
  gap: var(--space-02);
  padding: var(--space-05);
  overflow-x: auto;
}

.loading-state {
  width: 100%;
  text-align: center;
  padding: 20px;
  align-self: center;
}

@media (max-aspect-ratio: 4/3) {
  .main-content {
    flex: none;
  }

  .equalizer-controls {
    flex-direction: column;
  }
}
</style>