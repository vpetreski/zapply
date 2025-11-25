<template>
  <div class="jobs">
    <div class="jobs-header">
      <h2>Jobs ({{ total }} total)</h2>
      <div class="filters">
        <select v-model="statusFilter" @change="resetAndFetch" class="filter-select">
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

    <div v-else>
      <div class="jobs-list">
        <div v-for="job in jobs" :key="job.id" class="card job-card">
          <div class="job-header">
            <div>
              <h3 class="job-title" @click="openJobDetail(job)">{{ job.title }}</h3>
              <p class="company">{{ job.company }}</p>
            </div>
            <span :class="['badge', `badge-${job.status}`]">{{ job.status }}</span>
          </div>
          <p class="job-description">{{ truncate(job.description, 200) }}</p>
          <div class="job-footer">
            <div class="job-footer-left">
              <span v-if="job.location" class="text-muted">📍 {{ job.location }}</span>
              <span class="text-muted timestamp">🕐 {{ formatTimestamp(job.created_at) }}</span>
            </div>
            <a :href="job.url" target="_blank" class="btn btn-primary">View Job</a>
          </div>
        </div>
      </div>

      <!-- Loading more indicator -->
      <div v-if="loadingMore" class="loading-more">
        Loading more jobs...
      </div>

      <!-- End of results -->
      <div v-if="!hasMore && jobs.length > 0" class="end-message">
        No more jobs to load
      </div>
    </div>

    <!-- Job Detail Modal -->
    <div v-if="selectedJob" class="modal-overlay" @click="closeJobDetail">
      <div class="modal" @click.stop>
        <div class="modal-header">
          <div>
            <h2>{{ selectedJob.title }}</h2>
            <p class="company">{{ selectedJob.company }}</p>
          </div>
          <button @click="closeJobDetail" class="btn-close">×</button>
        </div>

        <div class="modal-body">
          <div class="job-meta">
            <span :class="['badge', `badge-${selectedJob.status}`]">{{ selectedJob.status }}</span>
            <span v-if="selectedJob.location" class="text-muted">📍 {{ selectedJob.location }}</span>
            <span v-if="selectedJob.source" class="text-muted">Source: {{ selectedJob.source }}</span>
            <span class="text-muted">🕐 {{ formatTimestamp(selectedJob.created_at) }}</span>
          </div>

          <div class="job-section">
            <h3>Description</h3>
            <p class="job-full-description">{{ selectedJob.description }}</p>
          </div>

          <div v-if="selectedJob.requirements" class="job-section">
            <h3>Requirements</h3>
            <p>{{ selectedJob.requirements }}</p>
          </div>

          <div v-if="selectedJob.tags && selectedJob.tags.length > 0" class="job-section">
            <h3>Tags</h3>
            <div class="tags">
              <span v-for="tag in selectedJob.tags" :key="tag" class="tag">{{ tag }}</span>
            </div>
          </div>

          <div v-if="selectedJob.match_score" class="job-section">
            <h3>Match Score</h3>
            <div class="match-score">{{ selectedJob.match_score }}%</div>
          </div>

          <div v-if="selectedJob.match_reasoning" class="job-section">
            <h3>Match Reasoning</h3>
            <p>{{ selectedJob.match_reasoning }}</p>
          </div>
        </div>

        <div class="modal-footer">
          <button @click="closeJobDetail" class="btn btn-secondary">Close</button>
          <a :href="selectedJob.url" target="_blank" class="btn btn-primary">View Job</a>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import axios from 'axios'

const jobs = ref([])
const loading = ref(true)
const loadingMore = ref(false)
const statusFilter = ref('')
const selectedJob = ref(null)

// Infinite scroll
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

const hasMore = computed(() => jobs.value.length < total.value)

const fetchJobs = async (append = false) => {
  if (append) {
    loadingMore.value = true
  } else {
    loading.value = true
  }

  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value
    }
    if (statusFilter.value) {
      params.status = statusFilter.value
    }
    const response = await axios.get('/api/jobs', { params })

    if (append) {
      jobs.value = [...jobs.value, ...response.data.jobs]
    } else {
      jobs.value = response.data.jobs
    }

    total.value = response.data.total
  } catch (error) {
    console.error('Failed to fetch jobs:', error)
  } finally {
    loading.value = false
    loadingMore.value = false
  }
}

const loadMore = () => {
  if (!loadingMore.value && hasMore.value) {
    currentPage.value++
    fetchJobs(true)
  }
}

const handleScroll = () => {
  const scrollPosition = window.innerHeight + window.scrollY
  const threshold = document.documentElement.scrollHeight - 300

  if (scrollPosition >= threshold && !loadingMore.value && hasMore.value) {
    loadMore()
  }
}

const resetAndFetch = () => {
  currentPage.value = 1
  jobs.value = []
  fetchJobs()
}

const openJobDetail = (job) => {
  selectedJob.value = job
}

const closeJobDetail = () => {
  selectedJob.value = null
}

const truncate = (text, length) => {
  if (!text) return ''
  if (text.length <= length) return text
  return text.substring(0, length) + '...'
}

const formatTimestamp = (timestamp) => {
  if (!timestamp) return ''

  // Parse the timestamp - if it doesn't have 'Z' suffix, add it to force UTC parsing
  const isoString = timestamp.includes('Z') ? timestamp : timestamp + 'Z'
  const utcDate = new Date(isoString)

  // Subtract 5 hours for Colombian time (UTC-5)
  const colombianDate = new Date(utcDate.getTime() - (5 * 60 * 60 * 1000))

  // Format using UTC methods (since we already adjusted the timestamp by -5 hours)
  const year = colombianDate.getUTCFullYear()
  const month = String(colombianDate.getUTCMonth() + 1).padStart(2, '0')
  const day = String(colombianDate.getUTCDate()).padStart(2, '0')
  const hours = String(colombianDate.getUTCHours()).padStart(2, '0')
  const minutes = String(colombianDate.getUTCMinutes()).padStart(2, '0')
  const seconds = String(colombianDate.getUTCSeconds()).padStart(2, '0')

  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
}

onMounted(() => {
  fetchJobs()
  window.addEventListener('scroll', handleScroll)
})

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll)
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
  margin-bottom: 2rem;
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

.job-title {
  cursor: pointer;
  transition: color 0.2s;
}

.job-title:hover {
  color: var(--primary);
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

.job-footer-left {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.timestamp {
  font-size: 0.75rem;
}

/* Infinite Scroll */
.loading-more, .end-message {
  text-align: center;
  padding: 2rem;
  color: var(--text-muted);
  font-size: 0.875rem;
}

.loading-more {
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
  backdrop-filter: blur(4px);
}

.modal {
  background-color: #1a1a1a;
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  max-width: 800px;
  width: 100%;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 10px 10px -5px rgba(0, 0, 0, 0.4);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 1.5rem;
  border-bottom: 1px solid var(--border);
}

.modal-header h2 {
  font-size: 1.5rem;
  margin-bottom: 0.25rem;
}

.btn-close {
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 2rem;
  cursor: pointer;
  padding: 0;
  width: 2rem;
  height: 2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 0.25rem;
  transition: all 0.2s;
}

.btn-close:hover {
  background-color: var(--bg-darker);
  color: var(--text);
}

.modal-body {
  padding: 1.5rem;
  overflow-y: auto;
  flex: 1;
}

.job-meta {
  display: flex;
  gap: 1rem;
  align-items: center;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
}

.job-section {
  margin-bottom: 1.5rem;
}

.job-section h3 {
  font-size: 1.125rem;
  margin-bottom: 0.75rem;
  color: var(--text);
}

.job-full-description {
  white-space: pre-wrap;
  line-height: 1.6;
  color: var(--text-muted);
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.tag {
  padding: 0.25rem 0.75rem;
  background-color: var(--bg-darker);
  border-radius: 0.25rem;
  font-size: 0.875rem;
  color: var(--text-muted);
}

.match-score {
  font-size: 2rem;
  font-weight: bold;
  color: var(--primary);
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding: 1.5rem;
  border-top: 1px solid var(--border);
}
</style>
