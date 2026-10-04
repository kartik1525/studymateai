import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
});

/**
 * Health check service to verify backend connectivity.
 */
export const checkHealth = async () => {
  const response = await apiClient.get('/health');
  return response.data;
};

/**
 * Upload a PDF document for processing.
 * @param {File} file 
 * @param {string} className 
 * @param {string} subject 
 */
export const uploadDocument = async (file, className, subject) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('class_name', className);
  formData.append('subject', subject);

  const response = await apiClient.post('/documents/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    timeout: 30000, // Upload might take slightly longer depending on file size
  });
  return response.data;
};

/**
 * Get a list of all documents.
 */
export const getDocuments = async () => {
  const response = await apiClient.get('/documents');
  return response.data;
};

/**
 * Get detailed information for a specific document, including processing status and chapters.
 * @param {string} documentId 
 */
export const getDocument = async (documentId) => {
  const response = await apiClient.get(`/documents/${documentId}`);
  return response.data;
};

/**
 * Ask a question grounded in the selected chapters of a document.
 * @param {string} documentId 
 * @param {Array<number>} chapters 
 * @param {string} question 
 */
export const askTutor = async (documentId, chapters, question) => {
  const response = await apiClient.post('/tutor/ask', {
    document_id: documentId,
    chapters: chapters,
    question: question
  }, {
    timeout: 60000 // 60 seconds dedicated timeout for RAG + Generation
  });
  return response.data;
};

export const generateQuiz = async (documentId, chapters, questionCount, difficulty, questionTypes) => {
  const response = await apiClient.post('/quiz/generate', {
    document_id: documentId,
    chapters: chapters,
    question_count: questionCount,
    difficulty: difficulty,
    question_types: questionTypes
  }, {
    timeout: 120000 // 120 seconds timeout for larger quiz generation
  });
  return response.data;
};

export default apiClient;
