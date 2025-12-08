<template>
  <div class="jobs">
    <!-- Profile Warning Banner -->
    <ProfileWarningBanner />

    <div class="jobs-header">
      <h2>Jobs ({{ total }} total)</h2>
      <div class="filters">
        <div class="filter-group">
          <label for="status-filter">Status:</label>
          <select id="status-filter" v-model="statusFilter" @change="resetAndFetch" class="filter-select">
            <option value="matched">Matched</option>
            <option value="rejected">Rejected</option>
            <option value="applied">Applied</option>
            <option value="">All</option>
          </select>
        </div>

        <div class="filter-group">
          <label for="matching-source-filter">Matching:</label>
          <select id="matching-source-filter" v-model="matchingSourceFilter" @change="resetAndFetch" class="filter-select">
            <option value="">Both</option>
            <option value="auto">Auto</option>
            <option value="manual">Manual</option>
          </select>
        </div>

        <div class="filter-group">
          <label for="days-filter">Scraped:</label>
          <select id="days-filter" v-model="daysFilter" @change="resetAndFetch" class="filter-select">
            <option value="0">Today</option>
            <option value="7">Last 7 Days</option>
            <option value="15">Last 15 Days</option>
            <option value="30">Last 30 Days</option>
            <option value="">All</option>
          </select>
        </div>
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
            <div class="job-header-left">
              <h3 class="job-title" @click="openJobDetail(job)">{{ job.title }}</h3>
              <p class="company">{{ job.company }}</p>
            </div>
            <div class="job-header-right">
              <span
                v-if="job.match_score !== null && job.match_score !== undefined"
                :class="['match-badge', getMatchScoreClass(job.match_score)]"
              >
                {{ job.match_score }}%
              </span>
              <span :class="['badge', `badge-${job.status}`]">{{ job.status }}</span>
              <span :class="['badge', `badge-${job.matching_source}`]">{{ job.matching_source }}</span>
              <span v-if="job.applied_at" class="badge badge-applied">applied</span>
            </div>
          </div>
          <p class="job-description">{{ truncate(job.description, 200) }}</p>
          <div class="job-footer">
            <div class="job-footer-left">
              <span v-if="job.location" class="text-muted">📍 {{ job.location }}</span>
              <span class="text-muted timestamp">🕐 {{ formatTimestamp(job.created_at) }}</span>
            </div>
            <div class="job-footer-right">
              <button
                v-if="job.status === 'rejected'"
                @click.stop="markAsMatched(job)"
                class="btn btn-success btn-sm"
                :disabled="updatingJobId === job.id"
              >
                {{ updatingJobId === job.id ? '...' : 'Mark Matched' }}
              </button>
              <button
                v-if="job.status === 'matched' && !job.applied_at"
                @click.stop="markAsRejected(job)"
                class="btn btn-danger btn-sm"
                :disabled="updatingJobId === job.id"
              >
                {{ updatingJobId === job.id ? '...' : 'Mark Rejected' }}
              </button>
              <button
                v-if="!job.applied_at"
                @click.stop="markAsApplied(job)"
                class="btn btn-purple btn-sm"
                :disabled="updatingJobId === job.id"
              >
                {{ updatingJobId === job.id ? '...' : 'Mark Applied' }}
              </button>
              <a :href="job.url" target="_blank" class="btn btn-primary btn-sm">View Job</a>
            </div>
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
            <span :class="['badge', `badge-${selectedJob.matching_source}`]">{{ selectedJob.matching_source }}</span>
            <span v-if="selectedJob.applied_at" class="badge badge-applied">applied</span>
            <span
              v-if="selectedJob.match_score !== null && selectedJob.match_score !== undefined"
              :class="['match-badge', 'match-badge-large', getMatchScoreClass(selectedJob.match_score)]"
            >
              {{ selectedJob.match_score }}% Match
            </span>
            <span v-if="selectedJob.location" class="text-muted">📍 {{ selectedJob.location }}</span>
            <span v-if="selectedJob.source" class="text-muted">Source: {{ selectedJob.source }}</span>
            <span class="text-muted">🕐 {{ formatTimestamp(selectedJob.created_at) }}</span>
          </div>

          <div v-if="selectedJob.match_reasoning" class="job-section match-reasoning-section">
            <h3>Match Reasoning</h3>
            <div class="match-reasoning">{{ selectedJob.match_reasoning }}</div>
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
        </div>

        <div class="modal-footer">
          <button @click="closeJobDetail" class="btn btn-secondary">Close</button>
          <button
            v-if="selectedJob.status === 'rejected'"
            @click="markAsMatched(selectedJob)"
            class="btn btn-success"
            :disabled="updatingJobId === selectedJob.id"
          >
            {{ updatingJobId === selectedJob.id ? 'Updating...' : 'Mark as Matched' }}
          </button>
          <button
            v-if="selectedJob.status === 'matched' && !selectedJob.applied_at"
            @click="markAsRejected(selectedJob)"
            class="btn btn-danger"
            :disabled="updatingJobId === selectedJob.id"
          >
            {{ updatingJobId === selectedJob.id ? 'Updating...' : 'Mark as Rejected' }}
          </button>
          <button
            v-if="!selectedJob.applied_at"
            @click="markAsApplied(selectedJob)"
            class="btn btn-purple"
            :disabled="updatingJobId === selectedJob.id"
          >
            {{ updatingJobId === selectedJob.id ? 'Updating...' : 'Mark as Applied' }}
          </button>
          <a :href="selectedJob.url" target="_blank" class="btn btn-primary">View Job</a>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
import ProfileWarningBanner from '@/components/ProfileWarningBanner.vue'

const jobs = ref([])
const loading = ref(true)
const loadingMore = ref(false)
const statusFilter = ref('matched')
const matchingSourceFilter = ref('')
const daysFilter = ref('0')
const selectedJob = ref(null)
const updatingJobId = ref(null)

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

    // Handle status filter with proper API parameters
    if (statusFilter.value === 'matched') {
      params.status = 'matched'
      params.applied = false  // Matched but not applied
    } else if (statusFilter.value === 'rejected') {
      params.status = 'rejected'
    } else if (statusFilter.value === 'applied') {
      params.applied = true  // Any job that has been applied
    }
    // statusFilter.value === '' means "All" - no filter

    if (matchingSourceFilter.value) {
      params.matching_source = matchingSourceFilter.value
    }

    if (daysFilter.value) {
      params.days = parseInt(daysFilter.value)
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

const markAsMatched = async (job) => {
  updatingJobId.value = job.id
  try {
    const response = await axios.patch(`/api/jobs/${job.id}/status`, {
      status: 'matched',
      matching_source: 'manual'
    })
    // Update selected job if it's the same
    if (selectedJob.value && selectedJob.value.id === job.id) {
      selectedJob.value = response.data
    }
    // Remove from list if filter would hide this job, otherwise update in place
    const index = jobs.value.findIndex(j => j.id === job.id)
    if (index !== -1) {
      if (statusFilter.value === 'rejected') {
        jobs.value.splice(index, 1)
        total.value--
      } else {
        jobs.value[index] = response.data
      }
    }
  } catch (error) {
    console.error('Failed to mark as matched:', error)
  } finally {
    updatingJobId.value = null
  }
}

const markAsRejected = async (job) => {
  updatingJobId.value = job.id
  try {
    const response = await axios.patch(`/api/jobs/${job.id}/status`, {
      status: 'rejected',
      matching_source: 'manual'
    })
    // Update selected job if it's the same
    if (selectedJob.value && selectedJob.value.id === job.id) {
      selectedJob.value = response.data
    }
    // Remove from list if filter would hide this job, otherwise update in place
    const index = jobs.value.findIndex(j => j.id === job.id)
    if (index !== -1) {
      if (statusFilter.value === 'matched') {
        jobs.value.splice(index, 1)
        total.value--
      } else {
        jobs.value[index] = response.data
      }
    }
  } catch (error) {
    console.error('Failed to mark as rejected:', error)
  } finally {
    updatingJobId.value = null
  }
}

const markAsApplied = async (job) => {
  updatingJobId.value = job.id
  try {
    const now = new Date().toISOString()
    // Don't change matching_source when marking as applied - keep auto/manual as is
    const response = await axios.patch(`/api/jobs/${job.id}/status`, {
      status: 'matched',
      application_data: { manually_marked: true, marked_at: now }
    })
    // Update selected job if it's the same
    if (selectedJob.value && selectedJob.value.id === job.id) {
      selectedJob.value = response.data
    }
    // Remove from list if filter would hide this job, otherwise update in place
    const index = jobs.value.findIndex(j => j.id === job.id)
    if (index !== -1) {
      if (statusFilter.value === 'matched') {
        // Matched filter excludes applied jobs
        jobs.value.splice(index, 1)
        total.value--
      } else {
        jobs.value[index] = response.data
      }
    }
  } catch (error) {
    console.error('Failed to mark as applied:', error)
  } finally {
    updatingJobId.value = null
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

const getMatchScoreClass = (score) => {
  if (score >= 90) return 'match-excellent'
  if (score >= 75) return 'match-good'
  if (score >= 60) return 'match-fair'
  return 'match-poor'
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
  flex-wrap: wrap;
  gap: 1rem;
}

.jobs h2 {
  font-size: 2rem;
}

.filters {
  display: flex;
  gap: 1.5rem;
  align-items: center;
  flex-wrap: wrap;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.filter-group label {
  font-size: 0.75rem;
  color: var(--text-muted);
  font-weight: 500;
}

.filter-select {
  padding: 0.5rem 1rem;
  background-color: var(--bg-darker);
  border: 1px solid var(--border);
  border-radius: 0.375rem;
  color: var(--text);
  font-size: 0.875rem;
  cursor: pointer;
  transition: border-color 0.2s;
}

.filter-select:hover {
  border-color: var(--primary);
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
  gap: 1rem;
}

.job-header-left {
  flex: 1;
}

.job-header-right {
  display: flex;
  gap: 0.5rem;
  align-items: flex-start;
  flex-shrink: 0;
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

/* Match Score Badges */
.match-badge {
  padding: 0.375rem 0.75rem;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  font-weight: 700;
  text-align: center;
  min-width: 55px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
}

.match-badge-large {
  font-size: 1rem;
  padding: 0.5rem 1rem;
  min-width: 80px;
}

.match-excellent {
  background-color: #10b981;
  color: #ffffff;
}

.match-good {
  background-color: #3b82f6;
  color: #ffffff;
}

.match-fair {
  background-color: #f59e0b;
  color: #ffffff;
}

.match-poor {
  background-color: #ef4444;
  color: #ffffff;
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

.job-footer-right {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  flex-wrap: wrap;
}

/* Action Buttons */
.btn-sm {
  padding: 0.375rem 0.75rem;
  font-size: 0.75rem;
}

.btn-success {
  background-color: #10b981;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 0.375rem;
  cursor: pointer;
  font-weight: 500;
  transition: background-color 0.2s;
}

.btn-success:hover:not(:disabled) {
  background-color: #059669;
}

.btn-success:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-danger {
  background-color: #ef4444;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 0.375rem;
  cursor: pointer;
  font-weight: 500;
  transition: background-color 0.2s;
}

.btn-danger:hover:not(:disabled) {
  background-color: #dc2626;
}

.btn-danger:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-purple {
  background-color: #8b5cf6;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 0.375rem;
  cursor: pointer;
  font-weight: 500;
  transition: background-color 0.2s;
}

.btn-purple:hover:not(:disabled) {
  background-color: #7c3aed;
}

.btn-purple:disabled {
  opacity: 0.6;
  cursor: not-allowed;
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

.match-reasoning-section {
  background-color: rgba(59, 130, 246, 0.1);
  border-left: 4px solid #3b82f6;
  padding: 1rem;
  border-radius: 0.375rem;
}

.match-reasoning {
  line-height: 1.6;
  color: var(--text-muted);
  white-space: pre-wrap;
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

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding: 1.5rem;
  border-top: 1px solid var(--border);
}

/* Application Data Section */
.application-section {
  background-color: rgba(139, 92, 246, 0.1);
  border-left: 4px solid #8b5cf6;
  padding: 1rem;
  border-radius: 0.375rem;
}

.application-section h4 {
  font-size: 0.95rem;
  margin: 1rem 0 0.5rem 0;
  color: var(--text);
}

.application-error {
  background-color: rgba(239, 68, 68, 0.2);
  border: 1px solid #ef4444;
  padding: 0.75rem;
  border-radius: 0.25rem;
  margin-bottom: 1rem;
  color: #fca5a5;
}

.application-steps {
  margin-top: 0.5rem;
}

.step-item {
  background-color: var(--bg-darker);
  border-radius: 0.375rem;
  padding: 0.75rem;
  margin-bottom: 0.5rem;
}

.step-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.step-number {
  background-color: var(--primary);
  color: white;
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: bold;
}

.step-action {
  font-weight: 600;
  text-transform: capitalize;
}

.step-status {
  margin-left: auto;
  font-weight: bold;
}

.step-status.success {
  color: #10b981;
}

.step-status.failed {
  color: #ef4444;
}

.step-detail {
  font-size: 0.85rem;
  color: var(--text-muted);
  margin: 0.25rem 0;
  padding-left: 2rem;
}

.step-detail a {
  color: var(--primary);
  text-decoration: none;
}

.step-detail a:hover {
  text-decoration: underline;
}

.step-error {
  color: #fca5a5;
}

.step-evidence {
  color: #86efac;
}

.step-notes {
  color: var(--text-muted);
  font-style: italic;
}

.step-status.neutral {
  color: #fbbf24;
}

/* Fields Filled Summary */
.fields-filled-summary {
  margin-bottom: 1rem;
}

.fields-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 0.5rem;
}

.fields-grid .field-item {
  background-color: var(--bg-darker);
  padding: 0.5rem 0.75rem;
  border-radius: 0.25rem;
  display: flex;
  gap: 0.5rem;
  font-size: 0.85rem;
}

.fields-grid .field-name {
  color: var(--text-muted);
  flex-shrink: 0;
}

.fields-grid .field-value {
  color: var(--text);
  word-break: break-word;
}

.fields-filled, .questions-answered {
  margin-top: 0.75rem;
  padding-left: 2rem;
  font-size: 0.85rem;
}

.field-item {
  display: flex;
  gap: 0.5rem;
  padding: 0.25rem 0;
  border-bottom: 1px dashed var(--border);
}

.field-name {
  color: var(--text-muted);
  font-weight: 500;
  min-width: 150px;
}

.field-value {
  color: var(--text);
  word-break: break-word;
}

.question-item {
  background-color: rgba(0, 0, 0, 0.2);
  padding: 0.5rem;
  border-radius: 0.25rem;
  margin: 0.5rem 0;
}

.question-text {
  color: var(--text-muted);
  font-style: italic;
  margin-bottom: 0.25rem;
}

.answer-text {
  color: var(--text);
}

.application-screenshot {
  margin-top: 1rem;
}

.application-screenshot img {
  max-width: 100%;
  border-radius: 0.375rem;
  border: 1px solid var(--border);
}

@media (max-width: 768px) {
  .jobs-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .filters {
    width: 100%;
    flex-direction: column;
    align-items: stretch;
  }

  .filter-group {
    width: 100%;
  }

  .job-header {
    flex-direction: column;
  }

  .job-header-right {
    width: 100%;
    justify-content: flex-start;
  }

  .job-footer {
    flex-direction: column;
    gap: 1rem;
    align-items: flex-start;
  }

  .job-footer-right {
    width: 100%;
    justify-content: flex-start;
  }

  .field-item {
    flex-direction: column;
    gap: 0.25rem;
  }

  .field-name {
    min-width: auto;
  }

  .modal-footer {
    flex-wrap: wrap;
  }
}
</style>
