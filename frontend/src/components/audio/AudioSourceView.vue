<!-- AudioSourceView.vue - Version finale avec gestion optimisée des transitions -->
<template>
  <div class="audio-source-view">
    <!-- LibrespotView avec animations intégrées -->
    <LibrespotView 
      v-if="showLibrespot"
      :key="librespotContentKey"
      :move-in="librespotMoveIn"
      :move-out="librespotMoveOut"
    />

    <!-- PluginStatus avec animations intégrées -->
    <PluginStatus
      v-if="showPluginStatus"
      :key="pluginStatusContentKey"
      :move-in="pluginStatusMoveIn"
      :move-out="pluginStatusMoveOut"
      :plugin-type="displayedPluginType"
      :plugin-state="displayedPluginState"
      :device-name="displayedDeviceName"
      :is-disconnecting="isDisconnecting"
      :frozen-content="frozenPluginContent"
      :is-transitioning="!!frozenPluginContent"
      @disconnect="$emit('disconnect')"
    />
  </div>
</template>

<script setup>
import { computed, ref, watch, nextTick } from 'vue';
import LibrespotView from '@/views/LibrespotView.vue';
import PluginStatus from '@/components/ui/PluginStatus.vue';

// Props
const props = defineProps({
  activeSource: {
    type: String,
    required: true
  },
  pluginState: {
    type: String,
    required: true
  },
  transitioning: {
    type: Boolean,
    default: false
  },
  targetSource: {
    type: String,
    default: null
  },
  metadata: {
    type: Object,
    default: () => ({})
  },
  isDisconnecting: {
    type: Boolean,
    default: false
  },
  initialDelay: {
    type: Boolean,
    default: true
  }
});

// Émissions
const emit = defineEmits(['disconnect']);

// États pour les composants
const showLibrespot = ref(false);
const showPluginStatus = ref(false);

// États pour les animations
const librespotMoveIn = ref(false);
const librespotMoveOut = ref(false);
const pluginStatusMoveIn = ref(false);
const pluginStatusMoveOut = ref(false);

// Contenu gelé pour préserver l'affichage pendant les transitions
const frozenPluginContent = ref(null);

let transitionTimeout = null;

// === LOGIQUE DE DÉCISION ===
const displayedSource = computed(() => {
  if (props.transitioning && props.targetSource) {
    return props.targetSource;
  }
  return props.activeSource;
});

const hasCompleteTrackInfo = computed(() => {
  return !!(
    props.pluginState === 'connected' &&
    props.metadata?.title &&
    props.metadata?.artist
  );
});

const shouldShowLibrespot = computed(() => {
  if (props.initialDelay) return false;
  
  return displayedSource.value === 'librespot' && 
         props.pluginState === 'connected' && 
         hasCompleteTrackInfo.value &&
         !props.transitioning;
});

const shouldShowPluginStatus = computed(() => {
  if (props.initialDelay) return false;
  
  // Transition en cours - toujours PluginStatus
  if (props.transitioning) return true;
  
  // Sources bluetooth/roc - toujours PluginStatus
  if (['bluetooth', 'roc'].includes(displayedSource.value)) return true;
  
  // Librespot sans conditions complètes - PluginStatus
  if (displayedSource.value === 'librespot') {
    return !hasCompleteTrackInfo.value || props.pluginState !== 'connected';
  }
  
  return false;
});

// === PROPRIÉTÉS AFFICHÉES POUR PLUGINSTATUS ===

const displayedPluginType = computed(() => {
  if (props.targetSource && props.targetSource !== 'none') {
    return props.targetSource;
  }
  
  const source = displayedSource.value;
  return source === 'none' ? 'librespot' : source;
});

const displayedPluginState = computed(() => {
  if (props.targetSource && props.targetSource !== 'none') {
    return 'starting';
  }
  return props.pluginState;
});

const displayedDeviceName = computed(() => {
  // Si targetSource existe, pas de device name (on montre le loading)
  if (props.targetSource && props.targetSource !== 'none') {
    return '';
  }
  
  const metadata = props.metadata || {};
  
  switch (displayedSource.value) {
    case 'bluetooth':
      return metadata.device_name || '';
    case 'roc':
      return metadata.client_name || '';
    default:
      return '';
  }
});

// === CONTENT KEYS ===
const librespotContentKey = computed(() => {
  if (!shouldShowLibrespot.value) return null;
  return `librespot-${props.activeSource}-${props.pluginState}-${props.transitioning}`;
});

const pluginStatusContentKey = computed(() => {
  if (!shouldShowPluginStatus.value) return null;
  return `pluginstatus-${displayedPluginType.value}-${displayedPluginState.value}-${props.transitioning}-${displayedDeviceName.value}-${props.targetSource || 'notarget'}`;
});

// === FONCTIONS ===
async function performTransition(fromComponent, toComponent) {
  if (transitionTimeout) {
    clearTimeout(transitionTimeout);
  }

  // Phase 1: Move-out
  if (fromComponent === 'librespot') {
    librespotMoveOut.value = true;
    librespotMoveIn.value = false;
  } else if (fromComponent === 'pluginStatus') {
    pluginStatusMoveOut.value = true;
    pluginStatusMoveIn.value = false;
  }

  // Phase 2: Switch components
  transitionTimeout = setTimeout(async () => {
    // Reset move-out
    if (fromComponent === 'librespot') {
      librespotMoveOut.value = false;
    } else if (fromComponent === 'pluginStatus') {
      pluginStatusMoveOut.value = false;
    }

    // Change components
    if (fromComponent !== toComponent) {
      if (fromComponent === 'librespot') {
        showLibrespot.value = false;
      } else if (fromComponent === 'pluginStatus') {
        showPluginStatus.value = false;
      }

      if (toComponent === 'librespot') {
        showLibrespot.value = true;
      } else if (toComponent === 'pluginStatus') {
        showPluginStatus.value = true;
      }
    }

    // Phase 3: Move-in
    await nextTick();
    if (toComponent === 'librespot') {
      librespotMoveIn.value = true;
    } else if (toComponent === 'pluginStatus') {
      pluginStatusMoveIn.value = true;
    }
  }, 200);
}

// === WATCHERS ===

// Watcher synchrone pour capturer l'ancien contenu AVANT que les computed changent
watch([
  () => props.activeSource,
  () => props.pluginState, 
  () => props.transitioning,
  () => props.targetSource,
  () => props.metadata
], (newValues, oldValues) => {
  const [newActiveSource, newPluginState, newTransitioning, newTargetSource] = newValues;
  const [oldActiveSource, oldPluginState, oldTransitioning, oldTargetSource] = oldValues || [];

  // Détecter transition DEPUIS LibrespotView vers PluginStatus
  const wasShowingLibrespot = showLibrespot.value;
  
  // Si on vient de LibrespotView et qu'on va vers PluginStatus à cause d'une transition
  if (wasShowingLibrespot && newTransitioning && newTargetSource && newTargetSource !== 'none' && oldValues[0] !== undefined) {
    // Créer un contenu gelé spécifique pour les transitions depuis LibrespotView
    frozenPluginContent.value = {
      pluginType: newTargetSource,
      pluginState: 'starting',
      deviceName: '',
      isDisconnecting: false
    };
    
    // Déclencher l'animation de sortie
    pluginStatusMoveOut.value = true;
    pluginStatusMoveIn.value = false;
    
    setTimeout(async () => {
      pluginStatusMoveOut.value = false;
      frozenPluginContent.value = null;
      await nextTick();
      pluginStatusMoveIn.value = true;
    }, 200);
    
    return; // Sortir tôt pour éviter la logique normale
  }

  // Logique normale: Capturer l'ancien contenu si PluginStatus était déjà affiché
  if (showPluginStatus.value && oldValues[0] !== undefined) {
    const oldContent = {
      pluginType: oldTargetSource && oldTargetSource !== 'none' ? oldTargetSource : (oldActiveSource === 'none' ? 'librespot' : oldActiveSource),
      pluginState: oldTargetSource && oldTargetSource !== 'none' ? 'starting' : oldPluginState,
      deviceName: oldTargetSource && oldTargetSource !== 'none' ? '' : (props.metadata?.device_name || props.metadata?.client_name || ''),
      isDisconnecting: props.isDisconnecting
    };
    
    // Si le contenu va vraiment changer, geler l'ancien
    const newContent = {
      pluginType: displayedPluginType.value,
      pluginState: displayedPluginState.value,
      deviceName: displayedDeviceName.value,
      isDisconnecting: props.isDisconnecting
    };
    
    const contentChanged = JSON.stringify(oldContent) !== JSON.stringify(newContent);
    
    if (contentChanged) {
      frozenPluginContent.value = oldContent;
      
      // Déclencher move-out avec l'ancien contenu gelé
      pluginStatusMoveOut.value = true;
      pluginStatusMoveIn.value = false;
      
      setTimeout(async () => {
        pluginStatusMoveOut.value = false;
        frozenPluginContent.value = null;
        await nextTick();
        pluginStatusMoveIn.value = true;
      }, 200);
    }
  }
}, { flush: 'sync' });

// Watcher principal pour les changements de composant
watch([shouldShowLibrespot, shouldShowPluginStatus], ([newLibrespot, newPluginStatus]) => {
  const currentlyShowingLibrespot = showLibrespot.value;
  const currentlyShowingPluginStatus = showPluginStatus.value;

  let targetComponent = null;
  if (newLibrespot) targetComponent = 'librespot';
  else if (newPluginStatus) targetComponent = 'pluginStatus';

  let currentComponent = null;
  if (currentlyShowingLibrespot) currentComponent = 'librespot';
  else if (currentlyShowingPluginStatus) currentComponent = 'pluginStatus';

  // Cas 1: Première apparition
  if (!currentComponent && targetComponent) {
    if (targetComponent === 'librespot') {
      showLibrespot.value = true;
      nextTick(() => { librespotMoveIn.value = true; });
    } else if (targetComponent === 'pluginStatus') {
      showPluginStatus.value = true;
      nextTick(() => { pluginStatusMoveIn.value = true; });
    }
  }
  // Cas 2: Transition entre composants différents
  else if (currentComponent && targetComponent && currentComponent !== targetComponent) {
    performTransition(currentComponent, targetComponent);
  }
  // Cas 3: Disparition
  else if (currentComponent && !targetComponent) {
    if (currentComponent === 'librespot') {
      librespotMoveOut.value = true;
      setTimeout(() => {
        showLibrespot.value = false;
        librespotMoveOut.value = false;
      }, 200);
    } else if (currentComponent === 'pluginStatus') {
      pluginStatusMoveOut.value = true;
      setTimeout(() => {
        showPluginStatus.value = false;
        pluginStatusMoveOut.value = false;
      }, 200);
    }
  }
}, { immediate: true });
</script>

<style scoped>
.audio-source-view {
  width: 100%;
  height: 100%;
  position: relative;
}
</style>