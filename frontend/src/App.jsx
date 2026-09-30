import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import AppLayout from './components/layout/AppLayout';
import Dashboard from './pages/Dashboard';
import Materials from './pages/Materials';
import MaterialUpload from './pages/MaterialUpload';
import Tutor from './pages/Tutor';
import Quizzes from './pages/Quizzes';
import QuizRunner from './pages/QuizRunner';
import QuizResults from './pages/QuizResults';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AppLayout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="materials" element={<Materials />} />
          <Route path="materials/upload" element={<MaterialUpload />} />
          <Route path="tutor" element={<Tutor />} />
          <Route path="quizzes" element={<Quizzes />} />
          <Route path="quiz/:id" element={<QuizRunner />} />
          <Route path="quiz/:id/results" element={<QuizResults />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
