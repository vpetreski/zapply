<template>
  <div class="stats">
    <!-- Profile Warning Banner -->
    <ProfileWarningBanner />

    <h2>Statistics</h2>

    <div class="grid grid-2" style="margin-top: 2rem;">
      <div class="card">
        <h3>Overview</h3>
        <div class="stats-grid">
          <div class="stat-item">
            <span class="label">Total Jobs</span>
            <span class="value">{{ stats.total_jobs }}</span>
          </div>
          <div class="stat-item">
            <span class="label">New</span>
            <span class="value">{{ stats.new_jobs }}</span>
          </div>
          <div class="stat-item">
            <span class="label">Matched</span>
            <span class="value text-success">{{ stats.matched_jobs }}</span>
          </div>
          <div class="stat-item">
            <span class="label">Rejected</span>
            <span class="value text-danger">{{ stats.rejected_jobs }}</span>
          </div>
          <div class="stat-item">
            <span class="label">Applied</span>
            <span class="value text-success">{{ stats.applied_jobs }}</span>
          </div>
          <div class="stat-item">
            <span class="label">Failed</span>
            <span class="value text-danger">{{ stats.failed_jobs }}</span>
          </div>
        </div>
      </div>

      <div class="card">
        <h3>Success Rate</h3>
        <div class="success-rate">
          <div class="rate-value">{{ stats.success_rate }}%</div>
          <p class="text-muted">
            {{ stats.applied_jobs }} successful out of {{ stats.applied_jobs + stats.failed_jobs }} attempts
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import ProfileWarningBanner from '@/components/ProfileWarningBanner.vue'

const stats = ref({
  total_jobs: 0,
  new_jobs: 0,
  matched_jobs: 0,
  rejected_jobs: 0,
  applied_jobs: 0,
  failed_jobs: 0,
  success_rate: 0
})

const fetchStats = async () => {
  try {
    const response = await axios.get('/api/stats')
    stats.value = response.data
  } catch (error) {
    console.error('Failed to fetch stats:', error)
  }
}

onMounted(() => {
  fetchStats()
})
</script>

<style scoped>
.stats h2 {
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.card h3 {
  font-size: 1.25rem;
  margin-bottom: 1.5rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.5rem;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.stat-item .label {
  color: var(--text-muted);
  font-size: 0.875rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.stat-item .value {
  font-size: 2rem;
  font-weight: 700;
}

.success-rate {
  text-align: center;
  padding: 2rem;
}

.rate-value {
  font-size: 4rem;
  font-weight: 700;
  color: var(--success);
  margin-bottom: 1rem;
}
</style>
