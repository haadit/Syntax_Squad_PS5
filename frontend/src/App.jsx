import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Navigation from "./components/Navigation";
import HomePage from "./components/HomePage";
import ETAPredictor from "./components/ETAPredictor";

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
        <Navigation />
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/predict" element={<ETAPredictor />} />
            {/* Add more routes as needed */}
          </Routes>
        </main>
        <footer className="bg-white/80 backdrop-blur-sm mt-8 py-4">
          <div className="container-width mx-auto px-4">
            <p className="text-center text-gray-500 text-sm">
              © {new Date().getFullYear()} Commute Time Predictor. All rights
              reserved.
            </p>
          </div>
        </footer>
      </div>
    </Router>
  );
}

export default App;
