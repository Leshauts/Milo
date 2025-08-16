<!-- LibrespotView.vue - Version finale avec protections anti-écrasement -->
<template>
  <div class="librespot-player" :class="animationClasses">
    <div class="now-playing">
      <!-- Partie gauche : Image de couverture -->
      <div class="album-art-section stagger-1">
        <div class="album-art-container">
          <!-- Blur en arrière-plan -->
          <div class="album-art-blur"
            :style="{ backgroundImage: persistentMetadata.album_art_url ? `url(${persistentMetadata.album_art_url})` : 'none' }">
          </div>

          <!-- Art cover principale -->
          <div class="album-art">
            <img v-if="persistentMetadata.album_art_url" :src="persistentMetadata.album_art_url"
              alt="Album Art" />
          </div>
        </div>
      </div>

      <!-- Partie droite : Informations et contrôles -->
      <div class="content-section stagger-2">
        <!-- Bloc 1 : Informations (prend l'espace restant) -->
        <div class="track-info stagger-3">
          <h1 class="track-title heading-1">{{ persistentMetadata.title || 'Titre inconnu' }}</h1>
          <p class="track-artist heading-2">{{ persistentMetadata.artist || 'Artiste inconnu' }}</p>
        </div>

        <!-- Bloc 2 : Contrôles (aligné en bas) -->
        <div class="controls-section">
          <div class="progress-wrapper stagger-4">
            <ProgressBar :currentPosition="currentPosition" :duration="duration"
              :progressPercentage="progressPercentage" @seek="seekTo" />
          </div>
          <div class="controls-wrapper stagger-5">
            <PlaybackControls :isPlaying="persistentMetadata.is_playing" @play-pause="togglePlayPause"
              @previous="previousTrack" @next="nextTrack" />
          </div>
        </div>
      </div>
    </div>

    <div v-if="unifiedStore.error && unifiedStore.currentSource === 'librespot'" class="error-message">
      {{ unifiedStore.error }}
    </div>
  </div>
</template>

<script setup>
import { computed, watch, onMounted, ref } from 'vue';
import { useUnifiedAudioStore } from '@/stores/unifiedAudioStore';
import { useLibrespotControl } from '@/composables/useLibrespotControl';
import { usePlaybackProgress } from '@/composables/usePlaybackProgress';
import axios from 'axios';

import PlaybackControls from '../components/librespot/PlaybackControls.vue';
import ProgressBar from '../components/librespot/ProgressBar.vue';

// Props pour les animations
const props = defineProps({
  moveIn: {
    type: Boolean,
    default: false
  },
  moveOut: {
    type: Boolean,
    default: false
  }
});

const unifiedStore = useUnifiedAudioStore();
const { togglePlayPause, previousTrack, nextTrack } = useLibrespotControl();
const { currentPosition, duration, progressPercentage, seekTo } = usePlaybackProgress();

// === CLASSES D'ANIMATION ===
const animationClasses = computed(() => ({
  'move-in': props.moveIn,
  'move-out': props.moveOut
}));

// === PERSISTANCE DES MÉTADONNÉES ===
const lastValidMetadata = ref({
  title: '',
  artist: '',
  album_art_url: '',
  is_playing: false
});

const persistentMetadata = computed(() => {
  const currentMetadata = unifiedStore.metadata || {};
  
  // Si on a des métadonnées valides actuellement, les utiliser et les sauvegarder
  if (currentMetadata.title && currentMetadata.artist) {
    lastValidMetadata.value = {
      title: currentMetadata.title,
      artist: currentMetadata.artist,
      album_art_url: currentMetadata.album_art_url || '',
      is_playing: currentMetadata.is_playing || false
    };
    return lastValidMetadata.value;
  }
  
  // Sinon, utiliser les dernières métadonnées valides sauvegardées
  return lastValidMetadata.value;
});

// === LIFECYCLE AVEC PROTECTIONS ===
onMounted(async () => {
  // Protection: Ne pas faire d'appel API pendant une transition
  if (unifiedStore.isTransitioning) {
    return;
  }
  
  // Protection: Vérifier que nous sommes bien sur librespot
  if (unifiedStore.currentSource !== 'librespot') {
    return;
  }
  
  try {
    const response = await axios.get('/librespot/status');
    if (response.data.status === 'ok') {
      const metadata = response.data.metadata || {};

      // Protection supplémentaire: Vérifier à nouveau qu'on n'est pas en transition
      if (unifiedStore.isTransitioning) {
        return;
      }

      unifiedStore.updateState({
        data: {
          full_state: {
            active_source: 'librespot',
            plugin_state: response.data.plugin_state,
            transitioning: false,
            metadata: metadata,
            error: null
          }
        }
      });
    }
  } catch (error) {
    console.error('Error fetching librespot status:', error);
  }
});
</script>

<style scoped>
/* === ANIMATIONS === */

/* État initial : éléments cachés */
.librespot-player .stagger-1,
.librespot-player .stagger-2,
.librespot-player .stagger-3,
.librespot-player .stagger-4,
.librespot-player .stagger-5 {
  opacity: 0;
  transform: translateY(32px);
  will-change: transform, opacity;
}

/* Move-in : animer depuis le bas */
.librespot-player.move-in .stagger-1 { 
  animation: moveInStagger var(--transition-spring) forwards 0ms; 
}
.librespot-player.move-in .stagger-2 { 
  animation: moveInStagger var(--transition-spring) forwards 100ms; 
}
.librespot-player.move-in .stagger-3 { 
  animation: moveInStagger var(--transition-spring) forwards 200ms; 
}
.librespot-player.move-in .stagger-4 { 
  animation: moveInStagger var(--transition-spring) forwards 300ms; 
}
.librespot-player.move-in .stagger-5 { 
  animation: moveInStagger var(--transition-spring) forwards 400ms; 
}

/* Move-out : fade + slide vers le haut */
.librespot-player.move-out .stagger-1,
.librespot-player.move-out .stagger-2,
.librespot-player.move-out .stagger-3,
.librespot-player.move-out .stagger-4,
.librespot-player.move-out .stagger-5 {
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

.librespot-player {
  width: 100%;
  height: 100%;
  overflow: hidden;
  position: relative;
}

.now-playing {
  display: flex;
  height: 100%;
  padding: var(--space-05);
  gap: var(--space-06);
  background: var(--color-background-neutral);
}

/* Album Art */
.album-art-section {
  flex-shrink: 0;
  aspect-ratio: 1;
  order: 1;
  z-index: 2;
}

/* Content Section */
.content-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  order: 2;
  z-index: 1;
}

/* Container pour les deux art covers superposées */
.album-art-container {
  position: relative;
  width: 100%;
  height: 100%;
}

/* Art cover en arrière-plan avec blur */
.album-art-blur {
  position: absolute;
  top: -20px;
  left: -20px;
  right: -20px;
  bottom: -20px;
  z-index: 2;
  background-size: cover;
  background-position: center;
  filter: blur(var(--space-07)) saturate(1.5);
  transform: scale(1.1) translateZ(0);
  opacity: .25;
  will-change: transform, filter;
  backface-visibility: hidden;
}

/* Art cover principale avec border radius */
.album-art {
  position: relative;
  z-index: 3;
  width: 100%;
  height: 100%;
  border-radius: var(--radius-06);
  overflow: hidden;
  box-shadow: 0px 0px 96px 0px #0000000d;
  pointer-events: none;
}

.album-art img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.track-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  text-align: center;
  gap: var(--space-03);
  padding: var(--space-06) 0;
}

.controls-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-05);
}

.track-title {
  color: var(--color-text);
}

.track-artist {
  color: var(--color-text-light);
}

.error-message {
  color: #ff4444;
  margin-top: 10px;
  text-align: center;
  padding: 10px;
  background-color: #fff0f0;
  border-radius: 4px;
}

@media (max-aspect-ratio: 4/3) {
  .now-playing {
    padding: var(--space-05) var(--space-05) 0 var(--space-05);
    flex-direction: column;
    gap: 0;
  }

  .controls-section {
    margin-bottom: var(--space-06);
  }

  .album-art-blur {
    transform: scale(1) translateZ(0);
  }

  .track-info {
    padding: var(--space-06) 0 var(--space-03) 0;
  }
}

/* iOS */
.ios-app .now-playing {
  padding: var(--space-08) var(--space-05) 0 var(--space-05);
}

.ios-app .controls-section {
  margin-bottom: var(--space-09);
}

/* Android */
.android-app .controls-section {
  margin-bottom: var(--space-08);
}
</style>