import { createRoot } from 'react-dom/client'

import App from './App'
import './styles.css'

// Phaser owns an imperative canvas lifecycle. React StrictMode intentionally
// mounts effects twice in development, which can let a destroyed Phaser loader
// finish after cleanup. Keep the React shell single-mounted so scene resources
// and global office events are registered exactly once.
createRoot(document.getElementById('root')!).render(<App />)

