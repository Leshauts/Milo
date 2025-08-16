<!-- PluginStatus.vue - Avec gestion correcte du contenu gelé et transitions -->
<template>
  <div class="plugin-status-container">
    <div class="plugin-status stagger-1" :class="animationClasses">
      <div class="plugin-status-content">
        <div class="plugin-status-inner">
          <!-- Section info appareil -->
          <div class="device-info">
            <div class="device-info-content">
              <div class="device-info-inner">
                <!-- Icône du plugin -->
                <div class="plugin-icon">
                  <AppIcon :name="displayedIconName" :size="32"
                      :state="displayedPluginState === 'starting' ? 'loading' : 'normal'" />
                </div>

                <!-- Statut textuel -->
                <div class="device-status">
                  <div v-if="displayedStatusLines.length === 1" class="status-single">
                    <h2 class="heading-2">{{ displayedStatusLines[0] }}</h2>
                  </div>
                  <template v-else>
                    <div class="status-line-1" :class="getDisplayedStatusLine1Class()">
                      <h2 class="heading-2">{{ displayedStatusLines[0] }}</h2>
                    </div>
                    <div class="status-line-2" :class="getDisplayedStatusLine2Class()">
                      <h2 class="heading-2">{{ displayedStatusLines[1] }}</h2>
                    </div>
                  </template>
                </div>
              </div>
            </div>
          </div>

          <!-- Bouton déconnecter (conditionnel) -->
          <div v-if="displayedShowDisconnectButton" class="disconnect-button">
            <div class="disconnect-button-content">
              <div class="disconnect-button-inner">
                <button @click="handleDisconnect" :disabled="displayedIsDisconnecting" class="disconnect-text">
                  <p>{{ displayedIsDisconnecting ? 'Déconnexion...' : 'Déconnecter' }}</p>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, watch } from 'vue';
import AppIcon from './AppIcon.vue';

// Props
const props = defineProps({
  moveIn: {
    type: Boolean,
    default: false
  },
  moveOut: {
    type: Boolean,
    default: false
  },
  pluginType: {
    type: String,
    required: true,
    validator: (value) => ['librespot', 'bluetooth', 'roc'].includes(value)
  },
  pluginState: {
    type: String,
    required: true
  },
  deviceName: {
    type: String,
    default: ''
  },
  isDisconnecting: {
    type: Boolean,
    default: false
  },
  frozenContent: {
    type: Object,
    default: null
  },
  isTransitioning: {
    type: Boolean,
    default: false
  }
});

// Émissions
const emit = defineEmits(['disconnect']);

// === CLASSES D'ANIMATION ===
const animationClasses = computed(() => ({
  'move-in': props.moveIn,
  'move-out': props.moveOut
}));

// === FONCTION UTILITAIRE ===
function cleanDeviceName(deviceName) {
  if (!deviceName) return '';
  return deviceName
    .replace('.local', '')
    .replace(/-/g, ' ');
}

// === COMPUTED POUR LE CONTENU AFFICHÉ ===

// ✅ CORRECTION : Utiliser le contenu gelé pendant les transitions de sortie SEULEMENT
const displayedIconName = computed(() => {
  const pluginType = props.isTransitioning && props.frozenContent 
    ? props.frozenContent.pluginType 
    : props.pluginType;
  return pluginType === 'librespot' ? 'spotify' : pluginType;
});

const displayedPluginState = computed(() => {
  return props.isTransitioning && props.frozenContent 
    ? props.frozenContent.pluginState 
    : props.pluginState;
});

const displayedDeviceName = computed(() => {
  return props.isTransitioning && props.frozenContent 
    ? props.frozenContent.deviceName 
    : props.deviceName;
});

const displayedIsDisconnecting = computed(() => {
  return props.isTransitioning && props.frozenContent 
    ? props.frozenContent.isDisconnecting 
    : props.isDisconnecting;
});

const displayedStatusLines = computed(() => {
  const pluginType = props.isTransitioning && props.frozenContent 
    ? props.frozenContent.pluginType 
    : props.pluginType;
  const pluginState = displayedPluginState.value;
  const deviceName = displayedDeviceName.value;

  console.log('🔍 PluginStatus displayedStatusLines:', {
    pluginType,
    pluginState, 
    deviceName,
    isTransitioning: props.isTransitioning,
    hasFrozenContent: !!props.frozenContent
  });

  // État de démarrage - affiché pendant les transitions avec loading icon
  if (pluginState === 'starting') {
    switch (pluginType) {
      case 'bluetooth':
        return ['Démarrage du', 'Bluetooth'];
      case 'roc':
        return ['Démarrage de', 'MacOS'];
      case 'librespot':
        return ['Démarrage de', 'Spotify'];
      default:
        return ['Démarrage...'];
    }
  }

  // État ready : messages d'attente
  if (pluginState === 'ready') {
    switch (pluginType) {
      case 'bluetooth':
        return ['Bluetooth', 'Prêt à diffuser'];
      case 'roc':
        return ['MacOS', 'Prêt à diffuser'];
      case 'librespot':
        return ['Spotify', 'Prêt à diffuser'];
      default:
        return ['En attente de connexion'];
    }
  }

  // État connected : messages avec nom d'appareil
  if (pluginState === 'connected' && deviceName) {
    const cleanedDeviceName = cleanDeviceName(deviceName);
    
    switch (pluginType) {
      case 'bluetooth':
        return ['Connecté à', cleanedDeviceName];
      case 'roc':
        return ['Connecté au', cleanedDeviceName];
      default:
        return ['Connecté à', deviceName];
    }
  }

  return ['En attente...'];
});

const displayedShowDisconnectButton = computed(() => {
  const pluginType = props.isTransitioning && props.frozenContent 
    ? props.frozenContent.pluginType 
    : props.pluginType;
  const pluginState = displayedPluginState.value;
  
  if (pluginState === 'starting') {
    return false;
  }
  return pluginType === 'bluetooth' && pluginState === 'connected';
});

// Classes pour les lignes de statut
function getDisplayedStatusLine1Class() {
  const pluginState = displayedPluginState.value;
  if (pluginState === 'starting') {
    return 'starting-state';
  }
  if (pluginState === 'connected') {
    return 'connected-state';
  }
  return '';
}

function getDisplayedStatusLine2Class() {
  const pluginState = displayedPluginState.value;
  if (pluginState === 'starting') {
    return 'starting-state';
  }
  if (pluginState === 'connected') {
    return 'connected-state';
  }
  return 'secondary-state';
}

// === GESTIONNAIRE D'ÉVÉNEMENTS ===
function handleDisconnect() {
  emit('disconnect');
}

// === GESTION DES ANIMATIONS ===
watch(() => props.moveIn, (newMoveIn) => {
  if (newMoveIn) {
    console.log('🎬 PluginStatus: Move-in triggered, starting animation');
  }
});

watch(() => props.moveOut, (newMoveOut) => {
  if (newMoveOut) {
    console.log('🎬 PluginStatus: Move-out triggered, starting fade-out animation');
  }
});

// === DEBUG CONTENU GELÉ ===
watch(() => props.frozenContent, (newFrozen) => {
  if (newFrozen) {
    console.log('🧊 PluginStatus: Using frozen content during transition:', newFrozen);
  } else {
    console.log('🔄 PluginStatus: Using current content');
  }
}, { immediate: true });
</script>

<style scoped>
/* === ANIMATIONS HARMONISÉES === */

/* Container pour centrage */
.plugin-status-container {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-05);
}

/* État initial : caché */
.plugin-status.stagger-1 {
  opacity: 0;
  transform: translateY(32px);
  will-change: transform, opacity;
}

/* Move-in : stagger depuis le bas avec transition spring */
.plugin-status.stagger-1.move-in {
  animation: moveInStagger var(--transition-spring) forwards 0ms;
}

/* Move-out : fade + slide vers le haut */
.plugin-status.stagger-1.move-out {
  animation: moveOut 200ms ease forwards;
}

/* Keyframes */
@keyframes moveInStagger {
  from {
    opacity: 0;
    transform: translateY(32px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes moveOut {
  from {
    opacity: 1;
    transform: translateY(0);
  }
  to {
    opacity: 0;
    transform: translateY(-32px);
  }
}

/* === STYLES DU COMPOSANT === */
.plugin-status {
  background: var(--color-background-neutral);
  border-radius: var(--radius-06);
  box-shadow: var(--shadow-02);
  width: 364px;
  position: relative;
}

.plugin-status-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
  height: 100%;
}

.plugin-status-inner {
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: var(--space-02);
  align-items: center;
  justify-content: flex-start;
  padding: var(--space-06) var(--space-04) var(--space-04) var(--space-04);
  position: relative;
  width: 100%;
  height: 100%;
}

.device-info {
  position: relative;
  flex-shrink: 0;
  width: 100%;
}

.device-info-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
  width: 100%;
  height: 100%;
}

.device-info-inner {
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: var(--space-03);
  align-items: center;
  justify-content: flex-start;
  padding: 0 var(--space-04) var(--space-04) var(--space-04);
  position: relative;
  width: 100%;
}

/* Icône du plugin */
.plugin-icon {
  position: relative;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Statut textuel */
.device-status {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

/* États par défaut */
.status-single h2,
.status-line-1 h2,
.status-line-2 h2 {
  color: var(--color-text);
}

/* États spéciaux ligne 1 */
.status-line-1.starting-state h2,
.status-line-1.connected-state h2 {
  color: var(--color-text-secondary);
}

/* États spéciaux ligne 2 */
.status-line-2.starting-state h2,
.status-line-2.connected-state h2 {
  color: var(--color-text);
}

.status-line-2.secondary-state h2 {
  color: var(--color-text-secondary);
}

/* Bouton déconnecter */
.disconnect-button {
  background: var(--color-background-strong);
  height: 42px;
  position: relative;
  border-radius: var(--radius-04);
  flex-shrink: 0;
  width: 100%;
}

.disconnect-button-content {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  position: relative;
  width: 100%;
  height: 100%;
}

.disconnect-button-inner {
  box-sizing: border-box;
  display: flex;
  flex-direction: row;
  gap: 40px;
  height: 42px;
  align-items: center;
  justify-content: center;
  padding: var(--space-02) var(--space-05);
  position: relative;
  width: 100%;
}

.disconnect-text {
  background: none;
  border: none;
  cursor: pointer;
  font-family: 'Neue Montreal Medium';
  font-weight: 500;
  line-height: 0;
  font-style: normal;
  position: relative;
  flex-shrink: 0;
  color: var(--color-text-secondary);
  font-size: var(--font-size-body);
  text-align: center;
  white-space: nowrap;
  letter-spacing: var(--letter-spacing-sans-serif);
}

.disconnect-text:hover:not(:disabled) {
  color: var(--color-text);
}

.disconnect-text:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.disconnect-text p {
  display: block;
  line-height: var(--line-height-body);
  white-space: pre;
  margin: 0;
}

/* Responsive */
@media (max-aspect-ratio: 4/3) {
  .plugin-status {
    width: 100%;
    max-width: 348px;
  }
}
</style>