<template>
  <div class="jobs">
    <div class="jobs-header">
      <h2>Jobs</h2>
      <div class="filters">
        <select v-model="statusFilter" @change="fetchJobs" class="filter-select">
          <option value="">All Statuses</option>
          <option value="new">New</option>
          <option value="matched">Matched</option>
          <option value="rejected">Rejected</option>
          <option value="applied">Applied</option>
          <option value="failed">Failed</option>
        </select>
      </div>
    </div>

    <div v-if="loading" class="loading">Loading jobs...</div>

    <div v-else-if="jobs.length === 0" class="empty">
      <p>No jobs found. The scraper will fetch jobs hourly.</p>
    </div>

    <div v-else class="jobs-list">
      <div v-for="job in jobs" :key="job.id" class="card job-card">
        <div class="job-header">
          <div>
            <h3>{{ job.title }}</h3>
            <p class="company">{{ job.company }}</p>
          </div>
          <span :class="['badge', `badge-${job.status}`]">{{ job.status }}</span>
        </div>
        <p class="job-description">{{ truncate(job.description, 200) }}</p>
        <div class="job-footer">
          <span v-if="job.location" class="text-muted">📍 {{ job.location }}</span>
          <a :href="job.url" target="_blank" class="btn btn-primary">View Job</a>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const jobs = ref([])
const loading = ref(true)
const statusFilter = ref('')

const fetchJobs = async () => {
  loading.value = true
  try {
    const params = {}
    if (statusFilter.value) {
      params.status = statusFilter.value
    }
    const response = await axios.get('/api/jobs', { params })
    jobs.value = response.data.jobs
  } catch (error) {
    console.error('Failed to fetch jobs:', error)
  } finally {
    loading.value = false
  }
}

const truncate = (text, length) => {
  if (text.length <= length) return text
  return text.substring(0, length) + '...'
}

onMounted(() => {
  fetchJobs()
})
</script>

<style scoped>
.jobs-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.jobs h2 {
  font-size: 2rem;
}

.filter-select {
  padding: 0.5rem 1rem;
  background-color: var(--bg-darker);
  border: 1px solid var(--border);
  border-radius: 0.375rem;
  color: var(--text);
  font-size: 0.875rem;
}

.loading, .empty {
  text-align: center;
  padding: 3rem;
  color: var(--text-muted);
}

.jobs-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.job-card {
  transition: transform 0.2s;
}

.job-card:hover {
  transform: translateY(-2px);
}

.job-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.job-header h3 {
  font-size: 1.25rem;
  margin-bottom: 0.25rem;
}

.company {
  color: var(--text-muted);
  font-size: 0.875rem;
}

.job-description {
  color: var(--text-muted);
  line-height: 1.6;
  margin-bottom: 1rem;
}

.job-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border);
}
</style>
