// src/App.jsx
import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import TripForm from "./components/TripForm";
import ResultsPage from "./pages/ResultsPage";

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
        <Routes>
          <Route path="/" element={<TripForm />} />
          <Route path="/results/:id" element={<ResultsPage />} />
          <Route path="*" element={<TripForm />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
