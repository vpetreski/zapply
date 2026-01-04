<template>
  <div class="interviews">
    <div class="interviews-header">
      <h2>Interviews ({{ total }} total)</h2>
      <div class="header-actions">
        <div class="filter-group">
          <label for="status-filter">Status:</label>
          <select id="status-filter" v-model="statusFilter" @change="resetAndFetch" class="filter-select">
            <option value="active">Active</option>
            <option value="closed">Closed</option>
            <option value="">All</option>
          </select>
        </div>
        <button @click="openCreateModal" class="btn btn-primary">
          + New Interview
        </button>
      </div>
    </div>

    <div v-if="loading" class="loading">Loading interviews...</div>

    <div v-else-if="interviews.length === 0" class="empty">
      <p>No interviews found.</p>
      <p class="empty-hint">Click "New Interview" to add your first interview.</p>
    </div>

    <div v-else>
      <div class="interviews-list">
        <div
          v-for="interview in interviews"
          :key="interview.id"
          class="card interview-card"
          @click="openEditModal(interview)"
        >
          <div class="interview-header">
            <h3 class="interview-title">{{ interview.title }}</h3>
            <span :class="['badge', `badge-${interview.status}`]">{{ interview.status }}</span>
          </div>
          <p
            v-if="interview.description"
            class="interview-description"
          >{{ stripHtmlAndTruncate(interview.description, 200) }}</p>
          <div class="interview-footer">
            <span class="text-muted timestamp">Updated: {{ formatTimestamp(interview.updated_at) }}</span>
            <div class="cv-indicator">
              <a
                v-if="interview.has_cv"
                @click.stop="downloadCv(interview.id)"
                class="cv-link"
                title="Download CV"
              >
                <svg class="pdf-icon" viewBox="0 0 32 32" width="20" height="20"><path fill="#e74c3c" d="M26 30H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h14l8 8v18a2 2 0 0 1-2 2z"/><path fill="#c0392b" d="M20 2l8 8h-6a2 2 0 0 1-2-2V2z"/><path fill="#fff" d="M10.5 17.5h1.8c.8 0 1.4.6 1.4 1.3s-.6 1.3-1.4 1.3h-.8v1.4h-1v-4zm1 1v1.2h.7c.3 0 .5-.2.5-.6s-.2-.6-.5-.6h-.7zm3.5-1h1.6c1.3 0 2.2.9 2.2 2s-.9 2-2.2 2H15v-4zm1 1v2h.5c.7 0 1.2-.4 1.2-1s-.5-1-1.2-1H16zm4-1h2.5v.9H21v.8h1.3v.9H21v1.4h-1v-4z"/></svg> Download CV
              </a>
              <span v-else class="text-muted">No custom CV</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Loading more indicator -->
      <div v-if="loadingMore" class="loading-more">
        Loading more interviews...
      </div>

      <!-- End of results -->
      <div v-if="!hasMore && interviews.length > 0" class="end-message">
        No more interviews to load
      </div>
    </div>

    <!-- Create/Edit Modal -->
    <div v-if="showModal" class="modal-overlay" @click="closeModal">
      <div class="modal interview-modal" @click.stop>
        <div class="modal-header">
          <h2>{{ isEditing ? 'Edit Interview' : 'New Interview' }}</h2>
          <button @click="closeModal" class="btn-close">×</button>
        </div>

        <div class="modal-body">
          <div class="form-group">
            <label for="interview-title">Title</label>
            <input
              id="interview-title"
              v-model="formData.title"
              type="text"
              class="form-input"
              placeholder="Company - Position"
            />
          </div>

          <div class="form-group">
            <label>Description</label>
            <RichTextEditor v-model="formData.description" />
          </div>

          <div v-if="isEditing" class="form-group">
            <label for="interview-status">Status</label>
            <select id="interview-status" v-model="formData.status" class="form-input">
              <option value="active">Active</option>
              <option value="closed">Closed</option>
            </select>
          </div>

          <div class="form-group">
            <label>Custom CV (PDF)</label>
            <div class="cv-upload">
              <input
                type="file"
                ref="cvInput"
                accept=".pdf,application/pdf"
                @change="handleCvSelect"
                class="file-input"
              />
              <div v-if="currentInterview?.has_cv && !selectedCvFile && !cvRemoved" class="cv-info">
                <span class="cv-filename"><svg class="pdf-icon" viewBox="0 0 32 32" width="18" height="18"><path fill="#e74c3c" d="M26 30H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h14l8 8v18a2 2 0 0 1-2 2z"/><path fill="#c0392b" d="M20 2l8 8h-6a2 2 0 0 1-2-2V2z"/><path fill="#fff" d="M10.5 17.5h1.8c.8 0 1.4.6 1.4 1.3s-.6 1.3-1.4 1.3h-.8v1.4h-1v-4zm1 1v1.2h.7c.3 0 .5-.2.5-.6s-.2-.6-.5-.6h-.7zm3.5-1h1.6c1.3 0 2.2.9 2.2 2s-.9 2-2.2 2H15v-4zm1 1v2h.5c.7 0 1.2-.4 1.2-1s-.5-1-1.2-1H16zm4-1h2.5v.9H21v.8h1.3v.9H21v1.4h-1v-4z"/></svg> {{ currentInterview.cv_filename || 'CV attached' }}</span>
                <button type="button" @click="markCvForRemoval" class="btn btn-sm btn-danger">Remove</button>
              </div>
              <div v-else-if="selectedCvFile" class="cv-info">
                <span class="cv-filename"><svg class="pdf-icon" viewBox="0 0 32 32" width="18" height="18"><path fill="#e74c3c" d="M26 30H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h14l8 8v18a2 2 0 0 1-2 2z"/><path fill="#c0392b" d="M20 2l8 8h-6a2 2 0 0 1-2-2V2z"/><path fill="#fff" d="M10.5 17.5h1.8c.8 0 1.4.6 1.4 1.3s-.6 1.3-1.4 1.3h-.8v1.4h-1v-4zm1 1v1.2h.7c.3 0 .5-.2.5-.6s-.2-.6-.5-.6h-.7zm3.5-1h1.6c1.3 0 2.2.9 2.2 2s-.9 2-2.2 2H15v-4zm1 1v2h.5c.7 0 1.2-.4 1.2-1s-.5-1-1.2-1H16zm4-1h2.5v.9H21v.8h1.3v.9H21v1.4h-1v-4z"/></svg> {{ selectedCvFile.name }}</span>
                <button type="button" @click="clearSelectedCv" class="btn btn-sm btn-secondary">Clear</button>
              </div>
              <div v-else-if="cvRemoved" class="cv-info cv-removed">
                <span class="text-muted">CV will be removed on save</span>
                <button type="button" @click="undoCvRemoval" class="btn btn-sm btn-secondary">Undo</button>
              </div>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button v-if="isEditing" @click="confirmDelete" class="btn btn-danger" :disabled="saving">
            Delete
          </button>
          <div class="modal-footer-right">
            <button @click="closeModal" class="btn btn-secondary" :disabled="saving">Cancel</button>
            <button type="button" @click="saveInterview" class="btn btn-primary" :disabled="saving || !formData.title?.trim()">
              {{ saving ? 'Saving...' : (isEditing ? 'Update' : 'Create') }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Delete Confirmation Dialog -->
    <ConfirmDialog
      v-model:isOpen="showDeleteConfirm"
      title="Delete Interview"
      :message="`Are you sure you want to delete '${currentInterview?.title}'? This action cannot be undone.`"
      confirmText="Delete"
      variant="danger"
      @confirm="deleteInterview"
      @cancel="showDeleteConfirm = false"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
import RichTextEditor from '@/components/RichTextEditor.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'

const interviews = ref([])
const loading = ref(true)
const loadingMore = ref(false)
const saving = ref(false)
const statusFilter = ref('active')
const showModal = ref(false)
const showDeleteConfirm = ref(false)
const isEditing = ref(false)
const currentInterview = ref(null)

// Infinite scroll
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// Form data
const formData = ref({
  title: '',
  description: '',
  status: 'active'
})

// CV handling
const cvInput = ref(null)
const selectedCvFile = ref(null)
const cvRemoved = ref(false)

const hasMore = computed(() => interviews.value.length < total.value)

const fetchInterviews = async (append = false) => {
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

    const response = await axios.get('/api/interviews', { params })

    if (append) {
      interviews.value = [...interviews.value, ...response.data.interviews]
    } else {
      interviews.value = response.data.interviews
    }

    total.value = response.data.total
  } catch (error) {
    console.error('Failed to fetch interviews:', error)
  } finally {
    loading.value = false
    loadingMore.value = false
  }
}

const loadMore = () => {
  if (!loadingMore.value && hasMore.value) {
    currentPage.value++
    fetchInterviews(true)
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
  interviews.value = []
  fetchInterviews()
}

const openCreateModal = () => {
  isEditing.value = false
  currentInterview.value = null
  formData.value = {
    title: '',
    description: '',
    status: 'active'
  }
  selectedCvFile.value = null
  cvRemoved.value = false
  showModal.value = true
}

const openEditModal = (interview) => {
  isEditing.value = true
  currentInterview.value = interview
  formData.value = {
    title: interview.title,
    description: interview.description || '',
    status: interview.status
  }
  selectedCvFile.value = null
  cvRemoved.value = false
  showModal.value = true
}

const closeModal = () => {
  if (saving.value) return
  showModal.value = false
  currentInterview.value = null
  selectedCvFile.value = null
  cvRemoved.value = false
  if (cvInput.value) {
    cvInput.value.value = ''
  }
}

const handleCvSelect = (event) => {
  const file = event.target.files[0]
  if (file) {
    if (file.type !== 'application/pdf') {
      alert('Please select a PDF file')
      event.target.value = ''
      return
    }
    if (file.size > 10 * 1024 * 1024) {
      alert('File size must be less than 10MB')
      event.target.value = ''
      return
    }
    selectedCvFile.value = file
    cvRemoved.value = false
  }
}

const clearSelectedCv = () => {
  selectedCvFile.value = null
  if (cvInput.value) {
    cvInput.value.value = ''
  }
}

const markCvForRemoval = () => {
  cvRemoved.value = true
  selectedCvFile.value = null
  if (cvInput.value) {
    cvInput.value.value = ''
  }
}

const undoCvRemoval = () => {
  cvRemoved.value = false
}

const saveInterview = async () => {
  if (!formData.value.title.trim()) return

  saving.value = true

  try {
    let interview

    if (isEditing.value) {
      // Update existing interview
      const response = await axios.put(`/api/interviews/${currentInterview.value.id}`, {
        title: formData.value.title,
        description: formData.value.description,
        status: formData.value.status
      })
      interview = response.data
    } else {
      // Create new interview
      const response = await axios.post('/api/interviews', {
        title: formData.value.title,
        description: formData.value.description
      })
      interview = response.data
    }

    // Handle CV upload/removal
    if (selectedCvFile.value) {
      const cvFormData = new FormData()
      cvFormData.append('file', selectedCvFile.value)
      await axios.post(`/api/interviews/${interview.id}/cv`, cvFormData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
    } else if (cvRemoved.value && currentInterview.value?.has_cv) {
      await axios.delete(`/api/interviews/${interview.id}/cv`)
    }

    // Success - reset saving state and close modal
    saving.value = false
    resetAndFetch()
    closeModal()
  } catch (error) {
    console.error('Failed to save interview:', error)
    const message = error.response?.data?.detail || error.message || 'Unknown error'
    alert(`Failed to save interview: ${message}`)
    saving.value = false
  }
}

const confirmDelete = () => {
  showDeleteConfirm.value = true
}

const deleteInterview = async () => {
  if (!currentInterview.value) return

  saving.value = true

  try {
    await axios.delete(`/api/interviews/${currentInterview.value.id}`)
    // Success - reset saving state before closing modal
    saving.value = false
    showDeleteConfirm.value = false
    closeModal()
    resetAndFetch()
  } catch (error) {
    console.error('Failed to delete interview:', error)
    alert('Failed to delete interview. Please try again.')
    saving.value = false
  }
}

const downloadCv = async (interviewId) => {
  let url = null
  try {
    const response = await axios.get(`/api/interviews/${interviewId}/cv`, {
      responseType: 'blob'
    })

    // Create download link
    url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', 'Resume-Vanja-Petreski.pdf')
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  } catch (error) {
    console.error('Failed to download CV:', error)
    alert('Failed to download CV. Please try again.')
  } finally {
    // Always revoke blob URL to prevent memory leak
    if (url) {
      window.URL.revokeObjectURL(url)
    }
  }
}

const stripHtmlAndTruncate = (html, maxLength) => {
  if (!html) return ''

  // Create a temporary element to parse HTML and extract plain text
  const temp = document.createElement('div')
  temp.innerHTML = html

  // Get text content (safe - no HTML returned)
  const text = temp.textContent || temp.innerText || ''

  if (text.length <= maxLength) {
    return text
  }

  // Truncate and add ellipsis
  return text.substring(0, maxLength) + '...'
}

const formatTimestamp = (timestamp) => {
  if (!timestamp) return ''

  const isoString = timestamp.includes('Z') ? timestamp : timestamp + 'Z'
  const date = new Date(isoString)

  // Use browser's local timezone with Intl.DateTimeFormat
  return new Intl.DateTimeFormat('en-CA', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  }).format(date).replace(',', '')
}

onMounted(() => {
  fetchInterviews()
  window.addEventListener('scroll', handleScroll)
})

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll)
})
</script>

<style scoped>
.interviews-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.interviews h2 {
  font-size: 2rem;
}

.header-actions {
  display: flex;
  gap: 1.5rem;
  align-items: flex-end;
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

.empty-hint {
  margin-top: 0.5rem;
  font-size: 0.875rem;
}

.interviews-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-bottom: 2rem;
}

.interview-card {
  cursor: pointer;
  transition: transform 0.2s, border-color 0.2s;
}

.interview-card:hover {
  transform: translateY(-2px);
  border-color: var(--primary);
}

.interview-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 0.75rem;
  gap: 1rem;
}

.interview-title {
  font-size: 1.25rem;
  margin: 0;
  color: var(--text);
}

.interview-description {
  color: var(--text-muted);
  line-height: 1.6;
  margin-bottom: 1rem;
  font-size: 0.9rem;
}

.interview-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.timestamp {
  font-size: 0.8rem;
}

.cv-indicator {
  font-size: 0.875rem;
}

.cv-link {
  color: var(--primary);
  cursor: pointer;
  text-decoration: none;
  transition: color 0.2s;
}

.cv-link:hover {
  color: #60a5fa;
  text-decoration: underline;
}

/* Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}

.interview-modal {
  background: var(--bg-darker);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
  max-width: 800px;
  width: 100%;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid var(--border);
}

.modal-header h2 {
  margin: 0;
  font-size: 1.5rem;
}

.btn-close {
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 2rem;
  cursor: pointer;
  padding: 0;
  line-height: 1;
  transition: color 0.2s;
}

.btn-close:hover {
  color: var(--text);
}

.modal-body {
  padding: 1.5rem;
  overflow-y: auto;
  flex: 1;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: var(--text);
}

.form-input {
  width: 100%;
  padding: 0.75rem 1rem;
  background-color: #1a1a1a;
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text);
  font-size: 1rem;
  transition: border-color 0.2s;
}

.form-input:focus {
  outline: none;
  border-color: var(--primary);
}

.form-input::placeholder {
  color: #666;
}

/* CV Upload */
.cv-upload {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.file-input {
  padding: 0.5rem;
  background-color: #1a1a1a;
  border: 1px dashed var(--border);
  border-radius: 8px;
  color: var(--text);
  cursor: pointer;
}

.file-input::file-selector-button {
  padding: 0.5rem 1rem;
  margin-right: 1rem;
  background: var(--primary);
  border: none;
  border-radius: 4px;
  color: white;
  cursor: pointer;
}

.cv-info {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem;
  background: #252525;
  border-radius: 6px;
}

.cv-filename {
  flex: 1;
  font-size: 0.9rem;
}

.cv-removed {
  border: 1px dashed var(--danger);
}

.modal-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  border-top: 1px solid var(--border);
  gap: 1rem;
}

.modal-footer-right {
  display: flex;
  gap: 0.75rem;
}

/* Buttons */
.btn {
  padding: 0.625rem 1.25rem;
  border: none;
  border-radius: 6px;
  font-size: 0.95rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary {
  background: var(--primary);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #2563eb;
}

.btn-secondary {
  background: #333;
  color: var(--text);
  border: 1px solid var(--border);
}

.btn-secondary:hover:not(:disabled) {
  background: #444;
}

.btn-danger {
  background: var(--danger);
  color: white;
}

.btn-danger:hover:not(:disabled) {
  background: #dc2626;
}

.btn-sm {
  padding: 0.375rem 0.75rem;
  font-size: 0.8rem;
}

/* Badges */
.badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}

.badge-active {
  background: rgba(16, 185, 129, 0.2);
  color: #10b981;
}

.badge-closed {
  background: rgba(107, 114, 128, 0.2);
  color: #9ca3af;
}

/* Loading states */
.loading-more {
  text-align: center;
  padding: 1.5rem;
  color: var(--text-muted);
}

.end-message {
  text-align: center;
  padding: 1.5rem;
  color: var(--text-muted);
  font-size: 0.875rem;
}

/* Responsive */
@media (max-width: 640px) {
  .interviews-header {
    flex-direction: column;
    align-items: stretch;
  }

  .header-actions {
    flex-direction: column;
    gap: 1rem;
  }

  .interview-modal {
    max-width: 100%;
    margin: 0.5rem;
  }

  .modal-footer {
    flex-direction: column;
  }

  .modal-footer-right {
    width: 100%;
    flex-direction: column-reverse;
  }

  .modal-footer-right .btn {
    width: 100%;
  }
}

.pdf-icon {
  vertical-align: -4px;
  margin-right: 6px;
  flex-shrink: 0;
}
</style>
