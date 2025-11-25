<template>
  <div class="profile-container">
    <h1>👤 User Profile</h1>

    <!-- Loading State -->
    <div v-if="loading && !profile" class="loading">
      <p>🔄 Loading profile...</p>
    </div>

    <!-- No Profile State -->
    <div v-else-if="!profile && !editMode" class="no-profile">
      <h2>No Profile Found</h2>
      <p>Create your profile to start matching jobs with AI.</p>
      <button @click="startCreate" class="btn-primary">
        ➕ Create Profile
      </button>
    </div>

    <!-- View Mode -->
    <div v-else-if="!editMode && profile" class="profile-view">
      <!-- Basic Info -->
      <section class="profile-section">
        <div class="section-header">
          <h2>📋 Basic Information</h2>
          <div class="action-buttons">
            <button @click="startEdit" class="btn-primary">
              ✏️ Edit Profile
            </button>
            <button @click="confirmDelete" class="btn-danger-outline">
              🗑️ Delete
            </button>
          </div>
        </div>

        <div class="info-grid">
          <div class="info-item">
            <span class="info-label">Name:</span>
            <span class="info-value">{{ profile.name }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">Email:</span>
            <span class="info-value">{{ profile.email }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">Location:</span>
            <span class="info-value">{{ profile.location }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">Rate:</span>
            <span class="info-value">{{ profile.rate }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">Created:</span>
            <span class="info-value">{{ formatDate(profile.created_at) }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">Updated:</span>
            <span class="info-value">{{ formatDate(profile.updated_at) }}</span>
          </div>
        </div>
      </section>

      <!-- Skills -->
      <section class="profile-section">
        <h2>🎯 Skills ({{ profile.skills?.length || 0 }})</h2>
        <div class="skills-container">
          <span v-for="skill in profile.skills" :key="skill" class="skill-badge">
            {{ skill }}
          </span>
        </div>
      </section>

      <!-- Preferences -->
      <section class="profile-section">
        <h2>⚙️ Preferences</h2>
        <pre class="json-display">{{ JSON.stringify(profile.preferences, null, 2) }}</pre>
      </section>

      <!-- CV Text -->
      <section class="profile-section">
        <h2>📄 Profile / CV Text</h2>
        <div class="cv-text">{{ profile.cv_text }}</div>
      </section>
    </div>

    <!-- Edit / Create Mode -->
    <div v-else class="profile-edit">
      <h2>{{ profile ? '✏️ Edit Profile' : '➕ Create Profile' }}</h2>

      <!-- Step 1: Upload CV or Paste Text -->
      <section class="profile-section">
        <h3>Step 1: Provide Your CV</h3>

        <div class="upload-section">
          <label class="upload-label">
            📎 Upload PDF CV
            <input
              type="file"
              accept=".pdf"
              @change="handleFileUpload"
              ref="fileInput"
              style="display: none"
            />
          </label>
          <button @click="$refs.fileInput.click()" class="btn-secondary">
            Choose PDF File
          </button>
          <span v-if="uploadedFile" class="file-name">{{ uploadedFile.name }}</span>
        </div>

        <div class="divider">OR</div>

        <div class="textarea-section">
          <label>Paste CV Text:</label>
          <textarea
            v-model="formData.cvText"
            rows="15"
            placeholder="Paste your CV content here..."
            class="cv-textarea"
          ></textarea>
        </div>
      </section>

      <!-- Step 2: Custom Instructions -->
      <section class="profile-section">
        <h3>Step 2: Custom Instructions for Claude AI</h3>
        <p class="help-text">
          Tell Claude how to optimize your profile. Example: "Focus on backend and architecture roles at Principal level. Emphasize Kotlin and Spring Boot experience."
        </p>
        <textarea
          v-model="formData.customPrompt"
          rows="6"
          placeholder="Enter your instructions for Claude AI..."
          class="prompt-textarea"
        ></textarea>
      </section>

      <!-- Step 3: Basic Info -->
      <section class="profile-section">
        <h3>Step 3: Basic Information</h3>
        <div class="form-grid">
          <div class="form-field">
            <label>Name *</label>
            <input v-model="formData.name" type="text" required />
          </div>
          <div class="form-field">
            <label>Email *</label>
            <input v-model="formData.email" type="email" required />
          </div>
          <div class="form-field">
            <label>Location *</label>
            <input v-model="formData.location" type="text" required />
          </div>
          <div class="form-field">
            <label>Rate *</label>
            <input v-model="formData.rate" type="text" placeholder="e.g. $10,000/month" required />
          </div>
        </div>
      </section>

      <!-- Generate Profile Button -->
      <section class="profile-section">
        <h3>Step 4: Generate Profile with AI</h3>
        <p class="help-text">
          Claude will analyze your CV and instructions to create an optimized profile for job matching.
        </p>
        <button
          @click="generateProfile"
          class="btn-primary btn-large"
          :disabled="generating || !canGenerate"
        >
          {{ generating ? '🤖 Generating with Claude AI...' : '✨ Generate Profile' }}
        </button>
      </section>

      <!-- Generated Profile Preview -->
      <section v-if="generatedProfile" class="profile-section generated-preview">
        <h3>✨ Generated Profile Preview</h3>

        <div class="generation-summary">
          <strong>Summary:</strong> {{ generatedProfile.generated_summary }}
        </div>

        <div class="preview-section">
          <h4>Skills ({{ generatedProfile.skills.length }})</h4>
          <div class="skills-container">
            <span v-for="skill in generatedProfile.skills" :key="skill" class="skill-badge">
              {{ skill }}
            </span>
          </div>
        </div>

        <div class="preview-section">
          <h4>Preferences</h4>
          <pre class="json-display">{{ JSON.stringify(generatedProfile.preferences, null, 2) }}</pre>
        </div>

        <div class="preview-section">
          <h4>Profile Text</h4>
          <div class="cv-text">{{ generatedProfile.cv_text }}</div>
        </div>

        <div class="save-section">
          <button @click="saveProfile" class="btn-primary btn-large" :disabled="saving">
            {{ saving ? '💾 Saving...' : '💾 Save Profile' }}
          </button>
          <button @click="cancelEdit" class="btn-secondary">
            Cancel
          </button>
        </div>
      </section>

      <!-- Cancel if not generated yet -->
      <div v-else class="action-buttons">
        <button @click="cancelEdit" class="btn-secondary">
          Cancel
        </button>
      </div>

      <!-- Error Message -->
      <div v-if="error" class="error-message">
        ❌ {{ error }}
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
import axios from 'axios'
import ConfirmDialog from '@/components/ConfirmDialog.vue'

interface Profile {
  id: number
  name: string
  email: string
  location: string
  rate: string
  cv_path: string | null
  cv_text: string | null
  skills: string[] | null
  preferences: Record<string, any> | null
  created_at: string
  updated_at: string
}

interface GeneratedProfile {
  cv_text: string
  skills: string[]
  preferences: Record<string, any>
  generated_summary: string
}

const loading = ref(false)
const generating = ref(false)
const saving = ref(false)
const profile = ref<Profile | null>(null)
const editMode = ref(false)
const error = ref('')
const showDeleteDialog = ref(false)

const formData = ref({
  name: '',
  email: '',
  location: '',
  rate: '',
  cvText: '',
  customPrompt: ''
})

const uploadedFile = ref<File | null>(null)
const generatedProfile = ref<GeneratedProfile | null>(null)

const canGenerate = computed(() => {
  return formData.value.name &&
         formData.value.email &&
         formData.value.location &&
         formData.value.rate &&
         formData.value.cvText &&
         formData.value.customPrompt
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
    name: '',
    email: '',
    location: '',
    rate: '',
    cvText: '',
    customPrompt: ''
  }
  generatedProfile.value = null
}

function startEdit() {
  if (!profile.value) return

  editMode.value = true
  formData.value = {
    name: profile.value.name,
    email: profile.value.email,
    location: profile.value.location,
    rate: profile.value.rate,
    cvText: profile.value.cv_text || '',
    customPrompt: ''
  }
  generatedProfile.value = null
}

function cancelEdit() {
  editMode.value = false
  generatedProfile.value = null
  error.value = ''
}

async function handleFileUpload(event: Event) {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]

  if (!file) return

  uploadedFile.value = file

  try {
    const formDataUpload = new FormData()
    formDataUpload.append('file', file)

    const response = await axios.post('/api/profile/upload-cv', formDataUpload, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })

    formData.value.cvText = response.data.text
  } catch (err: any) {
    error.value = `Failed to upload CV: ${err.response?.data?.detail || err.message}`
  }
}

async function generateProfile() {
  if (!canGenerate.value) return

  generating.value = true
  error.value = ''

  try {
    const response = await axios.post('/api/profile/generate', {
      cv_text: formData.value.cvText,
      custom_prompt: formData.value.customPrompt,
      name: formData.value.name,
      email: formData.value.email,
      location: formData.value.location,
      rate: formData.value.rate
    })

    generatedProfile.value = response.data
  } catch (err: any) {
    error.value = `Failed to generate profile: ${err.response?.data?.detail || err.message}`
  } finally {
    generating.value = false
  }
}

async function saveProfile() {
  if (!generatedProfile.value) return

  saving.value = true
  error.value = ''

  try {
    await axios.put('/api/profile', {
      name: formData.value.name,
      email: formData.value.email,
      location: formData.value.location,
      rate: formData.value.rate,
      cv_text: generatedProfile.value.cv_text,
      skills: generatedProfile.value.skills,
      preferences: generatedProfile.value.preferences
    })

    // Reload profile and exit edit mode
    await loadProfile()
    editMode.value = false
    generatedProfile.value = null
  } catch (err: any) {
    error.value = `Failed to save profile: ${err.response?.data?.detail || err.message}`
  } finally {
    saving.value = false
  }
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
  return new Date(dateString).toLocaleString()
}

onMounted(() => {
  loadProfile()
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

.loading, .no-profile {
  text-align: center;
  padding: 3rem;
  background: #1e1e1e;
  border-radius: 8px;
  border: 1px solid #333;
}

.no-profile h2 {
  color: #888;
  margin-bottom: 1rem;
}

.no-profile p {
  color: #666;
  margin-bottom: 2rem;
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

.action-buttons {
  display: flex;
  gap: 1rem;
}

.btn-primary, .btn-secondary, .btn-danger-outline {
  padding: 0.6rem 1.2rem;
  border-radius: 4px;
  border: none;
  font-size: 0.95rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
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

.btn-secondary:hover {
  background: #555;
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

/* Edit Mode Styles */
.upload-section {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
}

.file-name {
  color: #4a9eff;
  font-size: 0.9rem;
}

.divider {
  text-align: center;
  color: #666;
  margin: 1.5rem 0;
  font-weight: bold;
}

.textarea-section {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.textarea-section label {
  color: #e0e0e0;
  font-weight: 500;
}

.cv-textarea, .prompt-textarea {
  background: #0a0a0a;
  color: #e0e0e0;
  border: 1px solid #333;
  border-radius: 4px;
  padding: 1rem;
  font-family: monospace;
  font-size: 0.9rem;
  resize: vertical;
}

.cv-textarea:focus, .prompt-textarea:focus {
  outline: none;
  border-color: #4a9eff;
}

.help-text {
  color: #888;
  font-size: 0.9rem;
  margin-bottom: 1rem;
  font-style: italic;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-field label {
  color: #e0e0e0;
  font-weight: 500;
  font-size: 0.9rem;
}

.form-field input {
  background: #0a0a0a;
  color: #e0e0e0;
  border: 1px solid #333;
  border-radius: 4px;
  padding: 0.7rem;
  font-size: 0.95rem;
}

.form-field input:focus {
  outline: none;
  border-color: #4a9eff;
}

.generated-preview {
  border: 2px solid #4a9eff;
  background: #1a2a3a;
}

.generation-summary {
  background: #0a1a2a;
  padding: 1rem;
  border-radius: 4px;
  margin-bottom: 1.5rem;
  color: #8bb4e0;
  border-left: 4px solid #4a9eff;
}

.preview-section {
  margin-bottom: 1.5rem;
}

.preview-section h4 {
  color: #4a9eff;
  margin-bottom: 0.75rem;
}

.save-section {
  display: flex;
  gap: 1rem;
  margin-top: 2rem;
  padding-top: 2rem;
  border-top: 1px solid #333;
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
