import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
// import App from './App.jsx'
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import AuthForm from './LoginPage.jsx'
import Dashboard from './dashBoard.jsx'
import Activity from './activity.jsx'

createRoot(document.getElementById('root')).render(
  <Router>
      <Routes>
        {/* Home page → AuthForm */}
        <Route path="/" element={<AuthForm />} />

        {/* Dashboard after login */}
        <Route path="/dashboard" element={<Dashboard />} />

        {/* Activity page */}
        <Route path="/activity" element={<Activity />} />
      </Routes>
    </Router>

)
