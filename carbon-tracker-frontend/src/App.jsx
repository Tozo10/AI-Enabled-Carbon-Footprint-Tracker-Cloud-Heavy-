import { useState, useEffect } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'

function App() {
  const [count, setCount] = useState(0)

  useEffect(() => {
    window.location.href = '/a.html'
  }, [])

  return null // or a loading spinner if you want
}

export default App
