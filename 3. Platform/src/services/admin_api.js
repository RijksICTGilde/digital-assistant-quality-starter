import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json'
  }
})

export const adminAPI = {
  // ==================== FEEDBACK ====================

  submitFeedback: (feedback) => api.post('/feedback', feedback),

  getFeedbackStats: () => api.get('/feedback/stats'),

  exportFeedback: () => api.get('/feedback/export'),

  getRecentFeedback: (limit = 50) => api.get(`/feedback/recent?limit=${limit}`),

  getFeedbackByRating: (rating) => api.get(`/feedback/by-rating/${rating}`),

  getFeedbackAnalytics: () => api.get('/feedback/analytics'),

  // ==================== CONFIG ====================

  getConfig: () => api.get('/admin/config'),

  getDefaults: () => api.get('/admin/config/defaults'),

  setThreshold: (dimension, value) =>
    api.put(`/admin/config/thresholds/${dimension}`, { value }),

  setAllThresholds: (thresholds) =>
    api.put('/admin/config/thresholds', thresholds),

  setSimilarityThreshold: (value) =>
    api.put('/admin/config/rag/similarity-threshold', { value }),

  setMaxResults: (value) =>
    api.put('/admin/config/rag/max-results', { value }),

  setMaxImprovementRounds: (value) =>
    api.put('/admin/config/max-improvement-rounds', { value }),

  resetThresholds: () => api.post('/admin/config/reset/thresholds'),

  resetThreshold: (dimension) =>
    api.post(`/admin/config/reset/thresholds/${dimension}`),

  resetRag: () => api.post('/admin/config/reset/rag'),

  resetAll: () => api.post('/admin/config/reset/all'),

  exportConfig: () => api.get('/admin/config/export'),

  importConfig: (config) => api.post('/admin/config/import', config),

  // ==================== KNOWLEDGE BASE ====================

  getKnowledgeStats: () => api.get('/knowledge/stats'),

  // ==================== HEALTH ====================

  getHealth: () => api.get('/health'),

  // ==================== REVIEW QUEUE ====================

  getPendingReviews: () => api.get('/admin/review/pending'),

  getAllReviews: () => api.get('/admin/review/all'),

  getReviewStats: () => api.get('/admin/review/stats'),

  getReviewItem: (id) => api.get(`/admin/review/${id}`),

  approveReview: (id, data = {}) => api.post(`/admin/review/${id}/approve`, data),

  rejectReview: (id, data = {}) => api.post(`/admin/review/${id}/reject`, data),

  correctReview: (id, data) => api.post(`/admin/review/${id}/correct`, data),

  deleteReview: (id) => api.delete(`/admin/review/${id}`),

  flagForReview: (data) => api.post('/admin/review/flag', data),

  // ==================== GOLDEN ANSWERS ====================

  getGoldenAnswers: () => api.get('/admin/golden'),

  getActiveGoldenAnswers: () => api.get('/admin/golden/active'),

  getGoldenAnswer: (id) => api.get(`/admin/golden/${id}`),

  addGoldenAnswer: (data) => api.post('/admin/golden', data),

  importFromReview: (reviewId) => api.post(`/admin/golden/import/${reviewId}`),

  deactivateGoldenAnswer: (id) => api.delete(`/admin/golden/${id}`),

  deleteGoldenAnswer: (id) => api.delete(`/admin/golden/${id}/permanent`),

  runRegressionTest: () => api.post('/admin/golden/test'),

  getGoldenAnswerStats: () => api.get('/admin/golden/stats'),

  // ==================== AUDIT LOG ====================

  getAuditLogs: () => api.get('/admin/audit'),

  getRecentAuditLogs: (limit = 50) => api.get(`/admin/audit/recent?limit=${limit}`),

  getAuditStats: () => api.get('/admin/audit/stats'),

  getAuditByType: (type) => api.get(`/admin/audit/by-type/${type}`),

  cleanupAuditLogs: (daysToKeep = 90) => api.delete(`/admin/audit/cleanup?daysToKeep=${daysToKeep}`),
}

export default adminAPI
