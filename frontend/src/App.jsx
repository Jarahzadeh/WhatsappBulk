import React, { useEffect, useState } from 'react'
import axios from 'axios'

const api = axios.create({ baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api' })

const labels = {
  en: { title: 'Compliance First WhatsApp CRM', health: 'Health', contacts: 'Contacts', campaigns: 'Campaigns' },
  fa: { title: 'سامانه واتساپ با رعایت قوانین', health: 'سلامت', contacts: 'مخاطبین', campaigns: 'کمپین‌ها' }
}

export default function App() {
  const [health, setHealth] = useState(null)
  const [contacts, setContacts] = useState([])
  const [lang, setLang] = useState('en')

  useEffect(() => {
    api.get('/health').then(r => setHealth(r.data))
    api.get('/contacts').then(r => setContacts(r.data))
  }, [])

  return (
    <div style={{ fontFamily: 'sans-serif', margin: 20 }}>
      <h1>{labels[lang].title}</h1>
      <button onClick={() => setLang(lang === 'en' ? 'fa' : 'en')}>EN/FA</button>
      <h2>{labels[lang].health}</h2>
      <pre>{JSON.stringify(health, null, 2)}</pre>
      <h2>{labels[lang].contacts}</h2>
      <table border="1" cellPadding="6">
        <thead><tr><th>Name</th><th>Phone</th><th>Opt-in</th><th>Language</th><th>Tags</th></tr></thead>
        <tbody>
          {contacts.map(c => <tr key={c.id}><td>{c.name}</td><td>{c.phone_e164}</td><td>{String(c.opt_in_status)}</td><td>{c.language}</td><td>{(c.tags||[]).join(', ')}</td></tr>)}
        </tbody>
      </table>
      <p><b>Compliance rule:</b> only contacts with opt-in or recent inbound should be targeted.</p>
    </div>
  )
}
