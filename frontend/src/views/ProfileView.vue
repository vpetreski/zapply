<template>
  <div class="profile-container">
    <h1>Profile</h1>

    <!-- Loading State -->
    <div v-if="loading && !profile" class="loading">
      <p>Loading profile...</p>
    </div>

    <!-- No Profile State -->
    <div v-else-if="!profile && !editMode" class="no-profile">
      <h2>No Profile Found</h2>
      <p>Create your profile to start matching jobs with AI.</p>
      <button @click="startCreate" class="btn-primary">
        Create Profile
      </button>
    </div>

    <!-- View Mode -->
    <div v-else-if="!editMode && profile" class="profile-view">
      <!-- Header with actions -->
      <section class="profile-section">
        <div class="section-header">
          <h2>Profile</h2>
          <div class="action-buttons">
            <button @click="startEdit" class="btn-primary">
              Edit Profile
            </button>
            <button @click="confirmDelete" class="btn-danger-outline">
              Delete
            </button>
          </div>
        </div>

        <div class="info-grid">
          <div class="info-item">
            <span class="info-label">CV File:</span>
            <span class="info-value">{{ profile.cv_filename || 'Not uploaded' }}</span>
          </div>
        </div>
      </section>

      <!-- Custom Instructions -->
      <section class="profile-section">
        <h2>Custom Instructions</h2>
        <div class="instructions-text">{{ profile.custom_instructions || 'No custom instructions provided' }}</div>
      </section>

      <!-- AI-Generated Profile -->
      <section class="profile-section ai-section">
        <h2>AI-Generated Profile (Used for Job Matching)</h2>

        <div v-if="profile.ai_generated_summary" class="ai-summary">
          <strong>Summary:</strong> {{ profile.ai_generated_summary }}
        </div>

        <div class="ai-subsection">
          <h3>Skills ({{ profile.skills?.length || 0 }})</h3>
          <div class="skills-container">
            <span v-for="skill in profile.skills" :key="skill" class="skill-badge">
              {{ skill }}
            </span>
          </div>
        </div>

        <div class="ai-subsection">
          <h3>Preferences</h3>
          <pre class="json-display">{{ JSON.stringify(profile.preferences, null, 2) }}</pre>
        </div>

        <div class="ai-subsection">
          <h3>Profile Text</h3>
          <div class="cv-text">{{ profile.cv_text }}</div>
        </div>
      </section>

      <!-- Timestamps -->
      <section class="profile-section timestamps">
        <div class="timestamp-item">
          <span class="info-label">Created:</span>
          <span class="info-value">{{ formatDate(profile.created_at) }}</span>
        </div>
        <div class="timestamp-item">
          <span class="info-label">Updated:</span>
          <span class="info-value">{{ formatDate(profile.updated_at) }}</span>
        </div>
      </section>
    </div>

    <!-- Edit / Create Mode -->
    <div v-else class="profile-edit">
      <h2>{{ profile ? 'Edit Profile' : 'Create Profile' }}</h2>

      <!-- CV Selection -->
      <section class="profile-section">
        <h3>CV (PDF)</h3>
        <div class="upload-section">
          <button @click="$refs.fileInput.click()" class="btn-secondary">
            {{ uploadedFile ? 'Change PDF' : 'Select PDF File' }}
          </button>
          <input
            type="file"
            accept=".pdf"
            @change="handleFileUpload"
            ref="fileInput"
            style="display: none"
          />
          <span v-if="uploadedFile" class="file-info">
            <span class="file-name">{{ uploadedFile.name }}</span>
            <span class="file-size">({{ formatFileSize(uploadedFile.size) }})</span>
          </span>
          <span v-else-if="profile?.cv_filename" class="file-name file-not-selected">
            Current: {{ profile.cv_filename }} (select to update)
          </span>
        </div>
      </section>

      <!-- Custom Instructions -->
      <section class="profile-section">
        <h3>Custom Instructions for AI</h3>
        <textarea
          v-model="formData.customInstructions"
          rows="12"
          placeholder="Example:

- Name: John Doe
- Email: john@example.com
- Location: Colombia (Colombian and Serbian citizenship)
- Rate: $10,000-15,000/month
- NO US work authorization - can only work for companies that hire international contractors
- 100% remote work only - no hybrid or office-based positions
- Contractor arrangement only
- Looking for Principal/Staff Engineer roles in backend, architecture, or tech leadership
- Strong preference for companies in fintech, SaaS, or developer tools
- Focus on roles using Java, Kotlin, Spring Boot, or similar backend technologies"
          class="custom-instructions-textarea"
        ></textarea>
      </section>

      <!-- Save Actions -->
      <section class="profile-section save-section">
        <div class="action-buttons">
          <button
            @click="saveAllChanges"
            class="btn-primary btn-large"
            :disabled="saving || !canGenerate"
          >
            <span v-if="saving" class="saving-spinner"></span>
            {{ saving ? 'Generating...' : 'Save' }}
          </button>
          <button @click="cancelEdit" class="btn-secondary" :disabled="saving">
            Cancel
          </button>
        </div>
        <div v-if="!canGenerate && !saving" class="validation-message">
          Select CV and add custom instructions to continue
        </div>
      </section>

      <!-- Error Message -->
      <div v-if="error" class="error-message">
        {{ error }}
      </div>
    </div>
  </div>

  <!-- Delete Confirmation Dialog -->
  <ConfirmDialog
    v-model:isOpen="showDeleteDialog"
    title="Delete Profile"
    message="This will permanently delete your profile! All profile data including CV, skills, and preferences will be removed. This action cannot be undone."
    confirmText="Delete Profile"
    cancelText="Cancel"
    processingText="Deleting..."
    variant="danger"
    @confirm="handleDeleteConfirm"
  />
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'
import ConfirmDialog from '@/components/ConfirmDialog.vue'

interface Profile {
  id: number
  cv_filename: string | null
  cv_text: string | null
  custom_instructions: string | null
  skills: string[] | null
  preferences: Record<string, any> | null
  ai_generated_summary: string | null
  created_at: string
  updated_at: string
}

interface GeneratedProfile {
  cv_text: string
  skills: string[]
  preferences: Record<string, any>
  generated_summary: string
}

const route = useRoute()
const loading = ref(false)
const saving = ref(false)
const profile = ref<Profile | null>(null)
const editMode = ref(false)
const error = ref('')
const showDeleteDialog = ref(false)

const formData = ref({
  cvText: '',
  cvFilename: '',
  customInstructions: ''
})

const uploadedFile = ref<File | null>(null)

const canGenerate = computed(() => {
  return uploadedFile.value && formData.value.customInstructions.trim()
})

async function loadProfile() {
  loading.value = true
  error.value = ''
  try {
    const response = await axios.get('/api/profile')
    profile.value = response.data
  } catch (err: any) {
    if (err.response?.status !== 404) {
      error.value = 'Failed to load profile'
    }
  } finally {
    loading.value = false
  }
}

function startCreate() {
  editMode.value = true
  formData.value = {
    cvText: '',
    cvFilename: '',
    customInstructions: ''
  }
  uploadedFile.value = null
}

function startEdit() {
  if (!profile.value) return

  editMode.value = true
  formData.value = {
    cvText: profile.value.cv_text || '',
    cvFilename: profile.value.cv_filename || '',
    customInstructions: profile.value.custom_instructions || ''
  }
  uploadedFile.value = null
}

function cancelEdit() {
  editMode.value = false
  uploadedFile.value = null
  error.value = ''
}

function handleFileUpload(event: Event) {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]

  if (!file) return

  uploadedFile.value = file
  formData.value.cvFilename = file.name

  // Reset input value to allow re-selecting the same file
  target.value = ''
}

async function saveAllChanges() {
  if (!canGenerate.value || !uploadedFile.value) return

  saving.value = true
  error.value = ''

  try {
    // Step 1: Read CV file content as text (for now, we'll extract on frontend)
    const cvText = await readFileAsText(uploadedFile.value)

    // Step 2: Generate profile with Claude AI
    const generateResponse = await axios.post('/api/profile/generate', {
      cv_text: cvText,
      custom_instructions: formData.value.customInstructions
    })

    const generated = generateResponse.data

    // Step 3: Save everything to the database
    await axios.put('/api/profile', {
      cv_filename: formData.value.cvFilename,
      cv_text: generated.cv_text,
      custom_instructions: formData.value.customInstructions,
      skills: generated.skills,
      preferences: generated.preferences,
      ai_generated_summary: generated.generated_summary
    })

    // Reload profile and exit edit mode
    await loadProfile()
    editMode.value = false
    uploadedFile.value = null
  } catch (err: any) {
    error.value = `Failed to save profile: ${err.response?.data?.detail || err.message}`
  } finally {
    saving.value = false
  }
}

async function readFileAsText(file: File): Promise<string> {
  // For PDF files, we'll just send a placeholder - in production we'd use a PDF parser
  // The AI will work with whatever text is provided
  return `[CV from file: ${file.name}]\n\nNote: PDF text extraction should be implemented server-side for production use.`
}

function confirmDelete() {
  showDeleteDialog.value = true
}

async function handleDeleteConfirm() {
  loading.value = true
  error.value = ''

  try {
    await axios.delete('/api/profile')
    profile.value = null
    showDeleteDialog.value = false
  } catch (err: any) {
    error.value = `Failed to delete profile: ${err.response?.data?.detail || err.message}`
    showDeleteDialog.value = false
  } finally {
    loading.value = false
  }
}

function formatDate(dateString: string): string {
  const date = new Date(dateString + 'Z')
  return date.toLocaleString('en-US', {
    timeZone: 'America/Bogota',
    year: 'numeric',
    month: 'numeric',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    second: '2-digit',
    hour12: true
  })
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

onMounted(() => {
  loadProfile()

  if (route.query.create === 'true' && !profile.value) {
    startCreate()
  }
})
</script>

<style scoped>
.profile-container {
  max-width: 1200px;
  margin: 0 auto;
}

h1 {
  margin-bottom: 2rem;
  color: #e0e0e0;
}

.loading {
  text-align: center;
  padding: 3rem;
  background: #1e1e1e;
  border-radius: 8px;
  border: 1px solid #333;
}

.no-profile {
  text-align: center;
  padding: 3rem;
  background: linear-gradient(135deg, #4a2c1e 0%, #3a1f1a 100%);
  border-radius: 8px;
  border: 2px solid #7a4a3a;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.no-profile h2 {
  color: #ffaa88;
  margin-bottom: 1rem;
  font-size: 1.5rem;
}

.no-profile p {
  color: #cc8866;
  margin-bottom: 2rem;
  font-size: 1.1rem;
}

.profile-section {
  background: #1e1e1e;
  border-radius: 8px;
  padding: 2rem;
  margin-bottom: 2rem;
  border: 1px solid #333;
}

.profile-section h2, .profile-section h3 {
  margin-top: 0;
  margin-bottom: 1.5rem;
  color: #e0e0e0;
}

.profile-section h3 {
  font-size: 1.2rem;
  color: #4a9eff;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.section-header h2 {
  margin: 0;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.info-label {
  font-size: 0.85rem;
  color: #888;
  font-weight: 500;
}

.info-value {
  font-size: 1rem;
  color: #e0e0e0;
}

.instructions-text {
  background: #0a0a0a;
  color: #e0e0e0;
  padding: 1.5rem;
  border-radius: 4px;
  white-space: pre-wrap;
  line-height: 1.6;
  border: 1px solid #333;
  max-height: 400px;
  overflow-y: auto;
}

.ai-section {
  border: 2px solid #4a9eff;
  background: #1a2a3a;
}

.ai-summary {
  background: #0a1a2a;
  padding: 1rem;
  border-radius: 4px;
  margin-bottom: 1.5rem;
  color: #8bb4e0;
  border-left: 4px solid #4a9eff;
}

.ai-subsection {
  margin-bottom: 1.5rem;
}

.ai-subsection:last-child {
  margin-bottom: 0;
}

.ai-subsection h3 {
  font-size: 1rem;
  color: #4a9eff;
  margin-bottom: 0.75rem;
}

.skills-container {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.skill-badge {
  background: #2a4a6a;
  color: #8bb4e0;
  padding: 0.4rem 0.8rem;
  border-radius: 4px;
  font-size: 0.85rem;
  font-weight: 500;
}

.json-display {
  background: #0a0a0a;
  color: #4a9eff;
  padding: 1rem;
  border-radius: 4px;
  overflow-x: auto;
  font-size: 0.9rem;
  border: 1px solid #333;
}

.cv-text {
  background: #0a0a0a;
  color: #e0e0e0;
  padding: 1.5rem;
  border-radius: 4px;
  white-space: pre-wrap;
  line-height: 1.6;
  border: 1px solid #333;
  max-height: 600px;
  overflow-y: auto;
}

.timestamps {
  display: flex;
  gap: 2rem;
  background: #151515;
}

.timestamp-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.action-buttons {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.btn-primary, .btn-secondary, .btn-danger-outline {
  padding: 0.6rem 1.2rem;
  border-radius: 4px;
  border: none;
  font-size: 0.95rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}

.btn-primary {
  background: #4a9eff;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #6ab0ff;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: #404040;
  color: white;
}

.btn-secondary:hover:not(:disabled) {
  background: #555;
}

.btn-secondary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-danger-outline {
  background: transparent;
  color: #ff6666;
  border: 1px solid #ff4444;
}

.btn-danger-outline:hover {
  background: #3a1a1a;
  border-color: #ff6666;
}

.btn-large {
  padding: 1rem 2rem;
  font-size: 1.1rem;
}

.upload-section {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}

.file-info {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.file-name {
  color: #4a9eff;
  font-size: 0.9rem;
  font-weight: 500;
}

.file-size {
  color: #888;
  font-size: 0.85rem;
}

.file-not-selected {
  color: #888;
}

.custom-instructions-textarea {
  width: 100%;
  background: #0a0a0a;
  color: #e0e0e0;
  border: 1px solid #333;
  border-radius: 4px;
  padding: 1rem;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  font-size: 0.95rem;
  line-height: 1.6;
  resize: vertical;
  min-height: 300px;
}

.custom-instructions-textarea:focus {
  outline: none;
  border-color: #4a9eff;
}

.save-section {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.validation-message {
  color: #888;
  font-size: 0.9rem;
}

.saving-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.error-message {
  background: #3a1a1a;
  color: #ff6666;
  padding: 1rem;
  border-radius: 4px;
  border: 1px solid #ff4444;
  margin-top: 1rem;
}
</style>
