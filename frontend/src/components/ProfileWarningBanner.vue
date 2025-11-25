<template>
  <div v-if="!hasProfile && !loading" class="warning-banner">
    <div class="banner-content">
      <div class="banner-icon">⚠️</div>
      <div class="banner-text">
        <strong>Profile Required</strong>
        <p>
          You must create a user profile before you can run the pipeline.
          The profile is used for AI-powered job matching and application.
        </p>
      </div>
      <router-link to="/profile" class="banner-button">
        Create Profile →
      </router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from 'axios'

const hasProfile = ref(true)
const loading = ref(true)

async function checkProfile() {
  try {
    const response = await axios.get('/api/profile/exists')
    hasProfile.value = response.data.exists
  } catch (error) {
    console.error('Failed to check profile:', error)
    // Assume profile exists on error to avoid false warnings
    hasProfile.value = true
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  checkProfile()
})

// Expose method to allow parent components to refresh
defineExpose({
  refresh: checkProfile
})
</script>

<style scoped>
.warning-banner {
  background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%);
  border: 2px solid #fca5a5;
  border-radius: 8px;
  padding: 1.25rem;
  margin-bottom: 1.5rem;
  box-shadow: 0 4px 12px rgba(220, 38, 38, 0.3);
  animation: slideDown 0.3s ease-out;
}

@keyframes slideDown {
  from {
    transform: translateY(-20px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.banner-content {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.banner-icon {
  font-size: 2rem;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3));
  flex-shrink: 0;
}

.banner-text {
  flex: 1;
  color: white;
}

.banner-text strong {
  font-size: 1.1rem;
  display: block;
  margin-bottom: 0.25rem;
  font-weight: 600;
}

.banner-text p {
  margin: 0;
  font-size: 0.9rem;
  opacity: 0.95;
  line-height: 1.4;
}

.banner-button {
  background: white;
  color: #dc2626;
  padding: 0.75rem 1.5rem;
  border-radius: 6px;
  text-decoration: none;
  font-weight: 600;
  font-size: 0.95rem;
  transition: all 0.2s;
  white-space: nowrap;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.banner-button:hover {
  background: #fef2f2;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

/* Responsive */
@media (max-width: 768px) {
  .banner-content {
    flex-direction: column;
    text-align: center;
  }

  .banner-button {
    width: 100%;
  }
}
</style>
