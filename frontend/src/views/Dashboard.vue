<template>
  <div class="dashboard">
    <h2>Dashboard</h2>
    <div class="grid grid-3" style="margin-top: 2rem;">
      <div class="card stat-card">
        <h3>Total Jobs</h3>
        <p class="stat-value">{{ stats.total_jobs }}</p>
      </div>
      <div class="card stat-card">
        <h3>Matched</h3>
        <p class="stat-value text-success">{{ stats.matched_jobs }}</p>
      </div>
      <div class="card stat-card">
        <h3>Applied</h3>
        <p class="stat-value text-success">{{ stats.applied_jobs }}</p>
      </div>
    </div>

    <div class="card" style="margin-top: 2rem;">
      <h3>Recent Activity</h3>
      <p class="text-muted" style="margin-top: 1rem;">
        System is running. Check the Jobs page to see scraped positions.
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

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
.dashboard h2 {
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.stat-card h3 {
  color: var(--text-muted);
  font-size: 0.875rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.stat-value {
  font-size: 2.5rem;
  font-weight: 700;
  margin-top: 0.5rem;
}
</style>
