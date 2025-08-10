<!-- AudioSourceView.vue - Version corrigée pour centrage et transitions -->
<template>
  <div class="audio-source-view">
    <!-- Transition UNIQUE - back to basics -->
    <Transition name="audio-content" mode="out-in">
      
      <!-- LibrespotView -->
      <div 
        v-if="shouldShowLibrespot"
        key="librespot"
        class="librespot-container"
      >
        <LibrespotView />
      </div>

      <!-- PluginStatus -->
      <div
        v-else-if="shouldShowPluginStatus"
        :key="pluginStatusKey"
        class="plugin-status-container"
      >
        <PluginStatus
          :plugin-type="currentPluginType"
          :plugin-state="currentPluginState"
          :device-name="currentDeviceName"
          :is-disconnecting="isDisconnecting"
          @disconnect="$emit('disconnect')"
        />
      </div>

    </Transition>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue';
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
  }
});

// Émissions
const emit = defineEmits(['disconnect']);

// État d'attente initial (800ms)
const showInitialDelay = ref(true);

// === LOGIQUE DE DÉCISION SIMPLIFIÉE ===
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
  if (showInitialDelay.value) return false;
  
  return displayedSource.value === 'librespot' && 
         props.pluginState === 'connected' && 
         hasCompleteTrackInfo.value &&
         !props.transitioning;
});

const shouldShowPluginStatus = computed(() => {
  if (showInitialDelay.value) return false;
  
  // Transition en cours
  if (props.transitioning) return true;
  
  // Sources bluetooth/roc
  if (['bluetooth', 'roc'].includes(displayedSource.value)) return true;
  
  // Librespot sans conditions complètes
  if (displayedSource.value === 'librespot') {
    return !hasCompleteTrackInfo.value || props.pluginState !== 'connected';
  }
  
  return false;
});

// === PROPRIÉTÉS POUR PLUGINSTATUS ===
const currentPluginType = computed(() => {
  // Éviter "none" qui n'est pas une valeur valide pour les composants
  const source = displayedSource.value;
  return source === 'none' ? 'librespot' : source;
});

const currentPluginState = computed(() => {
  if (props.transitioning) return 'starting';
  return props.pluginState;
});

const currentDeviceName = computed(() => {
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

// Clé simple pour forcer re-render quand le contenu change
const pluginStatusKey = computed(() => {
  return `${currentPluginType.value}-${currentPluginState.value}-${!!currentDeviceName.value}`;
});

// === LIFECYCLE ===
onMounted(() => {
  console.log('🚀 AudioSourceView mounted - SIMPLIFIED');
  
  // Attente initiale de 800ms
  setTimeout(() => {
    console.log('🚀 Initial delay finished');
    showInitialDelay.value = false;
  }, 800);
});
</script>

<style scoped>
.audio-source-view {
  width: 100%;
  height: 100%;
  position: relative;
}

/* === CONTAINERS POUR LAYOUTS SPÉCIFIQUES === */

/* === CONTAINERS SIMPLIFIÉS === */

/* LibrespotView : plein écran naturel */
.librespot-container {
  width: 100%;
  height: 100%;
}

/* PluginStatus : centré naturel */
.plugin-status-container {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-05);
}

/* === TRANSITIONS FLUIDES ET PERFORMANTES === */

.audio-content-enter-active {
  transition: all var(--transition-spring);
}

.audio-content-leave-active {
  transition: all var(--transition-fast);
}

/* Direction par défaut pour tous */
.audio-content-enter-from {
  opacity: 0;
  transform: translateY(var(--space-06)) scale(0.98);
}

.audio-content-leave-to {
  opacity: 0;
  transform: translateY(calc(-1 * var(--space-06))) scale(0.98);
}

.audio-content-enter-to,
.audio-content-leave-from {
  opacity: 1;
  transform: translateY(0) scale(1);
}

/* Optimisations performance */
.librespot-container,
.plugin-status-container {
  will-change: transform, opacity;
  backface-visibility: hidden;
}

/* === STAGGER CORRECT ET FLUIDE === */

.librespot-container .stagger-1,
.librespot-container .stagger-2,
.librespot-container .stagger-3,
.librespot-container .stagger-4,
.librespot-container .stagger-5 {
  opacity: 0;
  transform: translateY(var(--space-05));
  will-change: transform, opacity;
}

/* Stagger démarre quand LibrespotView est affiché */
.librespot-container .stagger-1 { animation: stagger-appear var(--transition-spring) forwards 0ms; }
.librespot-container .stagger-2 { animation: stagger-appear var(--transition-spring) forwards 0ms; }
.librespot-container .stagger-3 { animation: stagger-appear var(--transition-spring) forwards 100ms; }
.librespot-container .stagger-4 { animation: stagger-appear var(--transition-spring) forwards 200ms; }
.librespot-container .stagger-5 { animation: stagger-appear var(--transition-spring) forwards 300ms; }

@keyframes stagger-appear {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>