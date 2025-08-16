<!-- MainView.vue - Avec délai initial de 800ms pour AudioSourceView -->
<template>
  <div class="main-view">
    <!-- AudioSourceView - Le plus bas -->
    <div class="content-container">
      <AudioSourceView
        :active-source="unifiedStore.currentSource"
        :plugin-state="unifiedStore.pluginState"
        :transitioning="unifiedStore.isTransitioning"
        :target-source="unifiedStore.systemState.target_source"
        :metadata="unifiedStore.metadata"
        :is-disconnecting="disconnectingStates[unifiedStore.currentSource]"
        :initial-delay="showInitialDelay"
        @disconnect="handleDisconnect"
      />
    </div>

    <!-- Logo - Au-dessus d'AudioSource -->
    <Logo 
      :position="logoPosition"
      :size="logoSize"
      :visible="logoVisible"
    />
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue';
import { useUnifiedAudioStore } from '@/stores/unifiedAudioStore';
import AudioSourceView from '@/components/audio/AudioSourceView.vue';
import Logo from '@/components/ui/Logo.vue';

const unifiedStore = useUnifiedAudioStore();

// États de déconnexion pour chaque plugin
const disconnectingStates = ref({
  bluetooth: false,
  roc: false,
  librespot: false
});

// Délai initial pour AudioSourceView
const showInitialDelay = ref(true);

// === LOGIQUE DU LOGO SIMPLIFIÉE ===

const logoPosition = computed(() => {
  // Logo centré pendant le délai initial ou si aucune source active
  if (showInitialDelay.value || (unifiedStore.currentSource === 'none' && !unifiedStore.isTransitioning)) {
    return 'center';
  }
  
  // Logo en haut dans tous les autres cas
  return 'top';
});

const logoSize = computed(() => {
  return logoPosition.value === 'center' ? 'large' : 'small';
});

const logoVisible = computed(() => {
  // Pendant le délai initial, toujours afficher le logo
  if (showInitialDelay.value) {
    return true;
  }

  // Cacher le logo quand LibrespotView est affiché (plein écran)
  const hasCompleteTrackInfo = !!(
    unifiedStore.pluginState === 'connected' &&
    unifiedStore.metadata?.title &&
    unifiedStore.metadata?.artist
  );
  
  const isLibrespotFullScreen = unifiedStore.currentSource === 'librespot' && 
                               unifiedStore.pluginState === 'connected' && 
                               hasCompleteTrackInfo &&
                               !unifiedStore.isTransitioning;
  
  return !isLibrespotFullScreen;
});

// === GESTION DES ACTIONS ===

async function handleDisconnect() {
  const currentSource = unifiedStore.currentSource;
  if (!currentSource || currentSource === 'none') return;
  
  disconnectingStates.value[currentSource] = true;
  
  try {
    let response;
    
    switch (currentSource) {
      case 'bluetooth':
        response = await fetch('/api/bluetooth/disconnect', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        });
        break;
      case 'roc':
        console.log('ROC disconnect not implemented');
        return;
      default:
        console.warn(`Disconnect not supported for ${currentSource}`);
        return;
    }
    
    if (response && response.ok) {
      const result = await response.json();
      if (result.status === 'success' || result.success) {
        console.log(`${currentSource} disconnected successfully`);
      } else {
        console.error(`Disconnect error: ${result.message || result.error}`);
      }
    }
  } catch (error) {
    console.error(`Error disconnecting ${currentSource}:`, error);
  } finally {
    setTimeout(() => {
      disconnectingStates.value[currentSource] = false;
    }, 1000);
  }
}

// === LIFECYCLE ===
onMounted(() => {
  console.log('🚀 MainView mounted - Starting initial delay sequence');
  
  // Délai initial : 800ms après le montage (le logo s'affiche pendant 1000ms total)
  setTimeout(() => {
    console.log('🚀 Initial delay finished - AudioSourceView can now show content');
    showInitialDelay.value = false;
  }, 800);
});
</script>

<style scoped>
.main-view {
  background: var(--color-background);
  height: 100%;
  position: relative;
}

.content-container {
  width: 100%;
  height: 100%;
  position: relative;
  z-index: 1; /* Le plus bas */
}

/* VolumeBar sera z-index: 120 (défini dans son composant) */
/* Logo sera z-index: 100 (défini dans son composant) */  
/* BottomNavigation sera z-index: 1000 (défini dans son composant) */
/* AudioSource reste z-index: 1 */
</style>