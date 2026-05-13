import React, { useState } from 'react'
import { Layout, Search, FlaskConical, AlertTriangle, CheckCircle, Info, Loader2, Sparkles, ShieldAlert } from 'lucide-react'
import { analyzeFormulation, searchIngredients } from './services/api'
import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

function cn(...inputs) {
  return twMerge(clsx(inputs))
}

function formatError(err) {
  try {
    const status = err?.response?.status
    const data = err?.response?.data
    let raw = (data && (data.detail || data.error || data.message)) || err?.message || 'Unexpected error'
    if (typeof raw !== 'string') raw = JSON.stringify(raw)

    let text = raw
    // Normalize whitespace and escapes
    text = text.replace(/\\n/g, ' ').replace(/\s+/g, ' ').trim()

    // Friendly mappings for common Gemini errors
    if (/suspended/i.test(text)) {
      text = 'Gemini access denied: API key appears suspended. Please update GOOGLE_API_KEY.'
    } else if (/not\s*found[^]*api\s*version/i.test(text)) {
      text = 'Requested Gemini model is unavailable for this API key/version. Try models/gemini-flash-lite-latest.'
    } else if (/permission\s*denied/i.test(text)) {
      text = 'Permission denied by Gemini API. Check key status and project access.'
    }

    // Truncate overly long messages
    if (text.length > 220) text = text.slice(0, 220) + '...'

    return `${status ? `Error ${status}: ` : ''}${text}`
  } catch (_) {
    return 'An unexpected error occurred.'
  }
}

function App() {
  const [activeTab, setActiveTab] = useState('analyze')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [form, setForm] = useState({
    product_name: '',
    category: '',
    ingredients_text: '',
    marketing_claims: ''
  })
  const [analysisResult, setAnalysisResult] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [searching, setSearching] = useState(false)

  const normalizeAnalysisResult = (result) => {
    try {
      const out = { ...result }
      // Normalize observations: accept list of strings or list of objects with 'observation'/'note'
      const rawObs = out.formulation_observations
      if (Array.isArray(rawObs)) {
        const obs = rawObs.map((o) => {
          if (typeof o === 'string') return o
          if (o && typeof o === 'object') return o.observation || o.note || JSON.stringify(o)
          return String(o)
        }).filter(Boolean)
        out.formulation_observations = obs.length ? obs : ["No specific observations generated."]
      } else if (typeof rawObs === 'string') {
        out.formulation_observations = rawObs ? [rawObs] : ["No specific observations generated."]
      } else {
        out.formulation_observations = ["No specific observations generated."]
      }

      // Ensure ingredient statuses exist and accept object maps as well
      let items = []
      if (Array.isArray(out.extracted_ingredients)) {
        items = out.extracted_ingredients
      } else if (out.extracted_ingredients && typeof out.extracted_ingredients === 'object') {
        items = Object.values(out.extracted_ingredients)
      } else {
        items = []
      }
      out.extracted_ingredients = items.map(x => ({ ...x, status: x.status || 'ok' }))

      // Add any user-entered ingredients missing from extraction as OK items
      const rawLines = (form.ingredients_text || '').split('\n').map(l => l.trim()).filter(Boolean)
      const parsedInput = rawLines.map((l) => {
        const m = l.match(/^(.+?)\s+(\d+(?:\.\d+)?)\s*([a-zA-Zµμ%]+)?$/i)
        if (m) {
          const name = m[1].trim()
          const dosage = m[2]
          const unit = m[3] ? m[3].trim() : ''
          return { ingredient: name, dosage, unit, status: 'ok' }
        }
        return { ingredient: l, status: 'ok' }
      })
      const existsByName = (name) => out.extracted_ingredients.some(x => (x.ingredient || x.canonical_name || '').toLowerCase() === String(name).toLowerCase())
      parsedInput.forEach(pi => { if (pi.ingredient && !existsByName(pi.ingredient)) out.extracted_ingredients.push(pi) })

      // If backend defaulted to 100 but we have warnings/dangers, gently downgrade for display
      const anyWarn = out.extracted_ingredients.some(x => x.status === 'warning')
      const anyDanger = out.extracted_ingredients.some(x => x.status === 'danger')
      if ((out.safety_score == null) || (out.safety_score === 100 && (anyWarn || anyDanger))) {
        let score = 100
        if (anyDanger) score -= 40
        if (anyWarn) score -= 20
        out.safety_score = Math.max(0, score)
      }

      if (!out.review_summary) out.review_summary = 'Analysis complete.'
      return out
    } catch (e) {
      return result
    }
  }

  const handleAnalyze = async () => {
    if (!form.ingredients_text) return
    setLoading(true)
    setError(null)
    try {
      const claims = form.marketing_claims ? form.marketing_claims.split('\n').filter(c => c.trim()) : []
      const result = await analyzeFormulation({
        ...form,
        marketing_claims: claims
      })
      console.debug('[FRONTEND] Analysis result:', result)
      setAnalysisResult(normalizeAnalysisResult(result))
    } catch (err) {
      console.error(err)
      setError(formatError(err))
    } finally {
      setLoading(false)
    }
  }

  const getVerdict = (res) => {
    try {
      if (!res) return 'Analysis'
      const score = typeof res.safety_score === 'number' ? res.safety_score : 0
      const items = Array.isArray(res.extracted_ingredients) ? res.extracted_ingredients : []
      const hasDanger = items.some(i => i.status === 'danger')
      const hasWarn = items.some(i => i.status === 'warning')
      if (hasDanger || score < 50) return 'Unsafe'
      if (hasWarn || score <= 80) return 'Caution'
      return 'Safe'
    } catch (_) {
      return 'Analysis'
    }
  }

  const handleCopySummary = () => {
    try {
      if (!analysisResult) return
      const verdict = getVerdict(analysisResult)
      const obsArr = Array.isArray(analysisResult.formulation_observations)
        ? analysisResult.formulation_observations
        : [String(analysisResult.formulation_observations || '')]
      const issues = (analysisResult.extracted_ingredients || []).filter(i => i.status === 'danger' || i.status === 'warning')
      const lines = [
        `Verdict: ${verdict} (Score ${analysisResult.safety_score})`,
        `Summary: ${analysisResult.review_summary}`,
        `Observations:`,
        ...obsArr.map(o => `- ${o}`),
        issues.length ? `Issues:` : '',
        ...issues.map(i => `- ${i.ingredient}: ${i.risk_note || i.status}`)
      ].filter(Boolean)
      navigator.clipboard?.writeText(lines.join('\n'))
    } catch (_) {}
  }

  const handleSearch = async (e) => {
    // If e exists, it might be a keyboard event. If not, it's a button click.
    if (e && e.key && e.key !== 'Enter') return;
    
    if (searchQuery) {
      setSearching(true)
      setError(null)
      try {
        console.log("[FRONTEND] Initiating search for:", searchQuery)
        const data = await searchIngredients(searchQuery)
        setSearchResults(data.results)
      } catch (err) {
        console.error(err)
        setError(formatError(err))
      } finally {
        setSearching(false)
      }
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50 flex flex-col font-sans">
      {/* Header */}
      <header className="border-b border-white/5 bg-slate-900/50 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3 group cursor-pointer">
            <div className="p-2 bg-blue-500/10 rounded-xl group-hover:bg-blue-500/20 transition-all">
              <FlaskConical className="w-8 h-8 text-blue-500" />
            </div>
            <h1 className="text-2xl font-bold tracking-tight bg-gradient-to-r from-blue-400 via-emerald-400 to-blue-400 bg-size-200 animate-gradient bg-clip-text text-transparent">
              SuppCheck AI
            </h1>
          </div>
          <nav className="flex gap-2 p-1 bg-slate-800/50 rounded-xl border border-white/5">
            <button 
              onClick={() => setActiveTab('analyze')}
              className={cn(
                "px-6 py-2 rounded-lg text-sm font-medium transition-all",
                activeTab === 'analyze' ? "bg-blue-600 shadow-lg shadow-blue-900/20 text-white" : "text-slate-400 hover:text-slate-100 hover:bg-white/5"
              )}
            >
              Analyze
            </button>
            <button 
              onClick={() => setActiveTab('search')}
              className={cn(
                "px-6 py-2 rounded-lg text-sm font-medium transition-all",
                activeTab === 'search' ? "bg-blue-600 shadow-lg shadow-blue-900/20 text-white" : "text-slate-400 hover:text-slate-100 hover:bg-white/5"
              )}
            >
              Semantic Search
            </button>
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 w-full">
        {error && (
          <div className="mb-8 p-4 bg-red-500/10 border border-red-500/50 rounded-xl flex items-center gap-3 text-red-200 animate-in fade-in slide-in-from-top-4 duration-300">
            <div className="p-2 bg-red-500/20 rounded-lg">
              <ShieldAlert className="w-5 h-5 text-red-500" />
            </div>
            <div className="flex-1">
              <p className="font-medium">Analysis Error</p>
              <p className="text-sm opacity-80">{error}</p>
            </div>
            <button onClick={() => setError(null)} className="p-2 hover:bg-white/5 rounded-lg transition-colors">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        )}

        {activeTab === 'analyze' ? (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-12">
            {/* Input Section */}
            <div className="lg:col-span-5 space-y-8">
              <div className="space-y-4">
                <h2 className="text-3xl font-bold">New Formulation Review</h2>
                <p className="text-slate-400">Extract ingredients, detect risks, and evaluate marketing claims using state-of-the-art AI.</p>
              </div>

              <section className="bg-slate-900/50 border border-white/5 rounded-3xl p-8 shadow-2xl backdrop-blur-sm">
                <div className="space-y-6">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Product Name</label>
                      <input 
                        type="text" 
                        value={form.product_name}
                        onChange={(e) => setForm({...form, product_name: e.target.value})}
                        placeholder="e.g. FocusMax" 
                        className="w-full bg-slate-800/50 border border-white/10 rounded-2xl px-4 py-3 focus:ring-2 focus:ring-blue-500/50 outline-none transition-all" 
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Category</label>
                      <input 
                        type="text" 
                        value={form.category}
                        onChange={(e) => setForm({...form, category: e.target.value})}
                        placeholder="e.g. Nootropic" 
                        className="w-full bg-slate-800/50 border border-white/10 rounded-2xl px-4 py-3 focus:ring-2 focus:ring-blue-500/50 outline-none transition-all" 
                      />
                    </div>
                  </div>
                  
                  <div className="space-y-2">
                    <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Ingredient List & Dosage</label>
                    <textarea 
                      rows="5" 
                      value={form.ingredients_text}
                      onChange={(e) => setForm({...form, ingredients_text: e.target.value})}
                      placeholder="Melatonin 10mg&#10;Magnesium 200mg&#10;L-Theanine 100mg" 
                      className="w-full bg-slate-800/50 border border-white/10 rounded-2xl px-4 py-3 focus:ring-2 focus:ring-blue-500/50 outline-none transition-all resize-none"
                    ></textarea>
                    <p className="text-[10px] text-slate-600">Enter each ingredient followed by its dosage on a new line.</p>
                  </div>

                  <div className="space-y-2">
                    <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Marketing Claims (Optional)</label>
                    <textarea 
                      rows="3" 
                      value={form.marketing_claims}
                      onChange={(e) => setForm({...form, marketing_claims: e.target.value})}
                      placeholder="Instant focus hack&#10;Cures morning brain fog" 
                      className="w-full bg-slate-800/50 border border-white/10 rounded-2xl px-4 py-3 focus:ring-2 focus:ring-blue-500/50 outline-none transition-all resize-none"
                    ></textarea>
                  </div>

                  <button 
                    onClick={handleAnalyze}
                    disabled={loading || !form.ingredients_text}
                    className="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold py-4 rounded-2xl transition-all shadow-xl shadow-blue-500/10 flex items-center justify-center gap-2 group"
                  >
                    {loading ? (
                      <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                      <>
                        <Sparkles className="w-5 h-5 group-hover:scale-110 transition-transform" />
                        Run AI Analysis
                      </>
                    )}
                  </button>
                </div>
              </section>
            </div>

            {/* Results Section */}
            <div className="lg:col-span-7">
              {!analysisResult ? (
                <div className="h-full bg-slate-900/30 border-2 border-dashed border-white/5 rounded-[2.5rem] flex flex-col items-center justify-center text-slate-600 p-12 text-center">
                  <div className="w-20 h-20 bg-slate-800/50 rounded-3xl flex items-center justify-center mb-6">
                    <FlaskConical className="w-10 h-10 opacity-20" />
                  </div>
                  <h3 className="text-xl font-semibold text-slate-400 mb-2">Awaiting Formulation</h3>
                  <p className="max-w-xs">Fill in the product details on the left to generate an AI-powered review.</p>
                </div>
              ) : (
                <div className="space-y-8 animate-in fade-in slide-in-from-right-4 duration-500">
                  <section className="bg-slate-900 border border-white/5 rounded-[2.5rem] p-8 shadow-2xl relative overflow-hidden flex flex-col md:flex-row gap-8 items-center">
                    {/* Score Gauge */}
                    <div className="relative w-32 h-32 flex-shrink-0">
                      <svg className="w-full h-full transform -rotate-90">
                        <circle
                          cx="64"
                          cy="64"
                          r="58"
                          fill="transparent"
                          stroke="currentColor"
                          strokeWidth="8"
                          className="text-slate-800"
                        />
                        <circle
                          cx="64"
                          cy="64"
                          r="58"
                          fill="transparent"
                          stroke="currentColor"
                          strokeWidth="8"
                          strokeDasharray={364.4}
                          strokeDashoffset={364.4 - (364.4 * analysisResult.safety_score) / 100}
                          strokeLinecap="round"
                          className={cn(
                            "transition-all duration-1000 ease-out",
                            analysisResult.safety_score > 80 ? "text-emerald-500" : 
                            analysisResult.safety_score > 50 ? "text-yellow-500" : "text-red-500"
                          )}
                        />
                      </svg>
                      <div className="absolute inset-0 flex flex-col items-center justify-center">
                        <span className="text-3xl font-black">{analysisResult.safety_score}</span>
                        <span className="text-[10px] font-bold text-slate-500 uppercase">Score</span>
                      </div>
                    </div>

                    <div className="relative z-10 space-y-4 flex-1 text-center md:text-left">
                      <div className="flex items-center justify-center md:justify-start gap-2 text-blue-400 text-xs font-bold uppercase tracking-widest">
                        <Sparkles className="w-4 h-4" />
                        AI Analysis Verdict
                      </div>
                      <div className="flex items-center justify-center md:justify-start gap-2">
                        <span
                          className={cn(
                            "px-2.5 py-1 rounded-lg text-[10px] font-bold uppercase border",
                            getVerdict(analysisResult) === 'Unsafe'
                              ? "bg-red-500/10 text-red-400 border-red-500/20"
                              : getVerdict(analysisResult) === 'Caution'
                              ? "bg-yellow-500/10 text-yellow-400 border-yellow-500/20"
                              : "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                          )}
                        >
                          {getVerdict(analysisResult)}
                        </span>
                        <button onClick={handleCopySummary} className="text-[10px] font-bold text-slate-500 uppercase hover:text-slate-300">
                          Copy summary
                        </button>
                      </div>
                      <h3 className="text-2xl font-bold text-white leading-tight">
                        {analysisResult.review_summary}
                      </h3>
                      <div className="pt-4 border-t border-white/5 text-slate-400 leading-relaxed text-sm">
                        {Array.isArray(analysisResult.formulation_observations) ? (
                          <ul className="list-disc pl-5 space-y-1 text-left">
                            {analysisResult.formulation_observations.map((o, i) => (
                              <li key={i}>{o}</li>
                            ))}
                          </ul>
                        ) : (
                          <ul className="list-disc pl-5 space-y-1 text-left">
                            <li>{analysisResult.formulation_observations}</li>
                          </ul>
                        )}
                      </div>
                    </div>
                  </section>

                  {/* Highlights Grid */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Ingredients table */}
                    <div className="bg-slate-900 border border-white/5 rounded-3xl overflow-hidden shadow-xl">
                      <div className="p-6 border-b border-white/5 bg-white/5 flex items-center justify-between">
                        <h4 className="font-bold flex items-center gap-2">
                          <CheckCircle className="w-4 h-4 text-emerald-400" />
                          Ingredient Extraction
                        </h4>
                        <div className="flex items-center gap-2">
                          <span className="px-2 py-0.5 rounded-md text-[10px] font-bold uppercase bg-red-500/10 text-red-400 border border-red-500/20">
                            Danger: {analysisResult.extracted_ingredients.filter(i => i.status === 'danger').length}
                          </span>
                          <span className="px-2 py-0.5 rounded-md text-[10px] font-bold uppercase bg-yellow-500/10 text-yellow-400 border border-yellow-500/20">
                            Warning: {analysisResult.extracted_ingredients.filter(i => i.status === 'warning').length}
                          </span>
                          <span className="px-2 py-0.5 rounded-md text-[10px] font-bold uppercase bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                            OK: {analysisResult.extracted_ingredients.filter(i => i.status !== 'danger' && i.status !== 'warning').length}
                          </span>
                        </div>
                      </div>
                      <div className="divide-y divide-white/5">
                        {analysisResult.extracted_ingredients
                          .slice()
                          .sort((a, b) => {
                            const r = (s) => (s === 'danger' ? 0 : s === 'warning' ? 1 : 2)
                            const ra = r(a.status || 'ok')
                            const rb = r(b.status || 'ok')
                            if (ra !== rb) return ra - rb
                            return (a.ingredient || '').localeCompare(b.ingredient || '')
                          })
                          .map((ing, idx) => (
                          <div key={idx} className="p-4 flex items-start justify-between gap-3 hover:bg-white/5 transition-colors">
                            <div className="flex-1 min-w-0 pr-3 break-words">
                              <div className="font-medium flex items-center gap-2 flex-wrap break-words">
                                {ing.ingredient}
                                {ing.canonical_name && ing.canonical_name !== ing.ingredient && (
                                  <span className="text-[10px] px-1.5 py-0.5 bg-slate-800 text-slate-400 rounded border border-white/5">
                                    {ing.canonical_name}
                                  </span>
                                )}
                              </div>
                              <div className="text-xs text-slate-500">{[ing.dosage, ing.unit].filter(Boolean).join(' ')}</div>
                              {ing.risk_note && (
                                <div className="text-xs text-slate-400 mt-1">{ing.risk_note}</div>
                              )}
                            </div>
                            <div className={cn(
                              "px-2 py-1 rounded-lg text-[10px] font-bold uppercase whitespace-nowrap flex-shrink-0",
                              ing.status === 'danger' ? "bg-red-500/10 text-red-400" : 
                              ing.status === 'warning' ? "bg-yellow-500/10 text-yellow-400" : 
                              "bg-emerald-500/10 text-emerald-400"
                            )}>
                              {ing.status}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Claims analysis */}
                    <div className="bg-slate-900 border border-white/5 rounded-3xl overflow-hidden shadow-xl">
                      <div className="p-6 border-b border-white/5 bg-white/5">
                        <h4 className="font-bold flex items-center gap-2">
                          <ShieldAlert className="w-4 h-4 text-orange-400" />
                          Claim Compliance
                        </h4>
                      </div>
                      <div className="p-4 space-y-4">
                        {analysisResult.claim_analysis.length > 0 ? analysisResult.claim_analysis.map((claim, idx) => (
                          <div key={idx} className="space-y-1">
                            <div className={cn("text-xs font-medium", claim.is_problematic ? "text-red-400" : "text-emerald-400")}>
                              {claim.claim}
                            </div>
                            <p className="text-[10px] text-slate-500">{claim.reason}</p>
                          </div>
                        )) : (
                          <p className="text-slate-500 text-sm">No marketing claims provided for analysis.</p>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Detailed Risks */}
                  {analysisResult.extracted_ingredients.some(i => i.risk_note) && (
                    <section className="bg-red-500/5 border border-red-500/10 rounded-3xl p-6">
                      <h4 className="text-red-400 font-bold mb-4 flex items-center gap-2">
                        <AlertTriangle className="w-5 h-5" />
                        Safety Warnings
                      </h4>
                      <div className="space-y-3">
                        {analysisResult.extracted_ingredients.filter(i => i.risk_note).map((ing, idx) => (
                          <div key={idx} className="bg-slate-900/80 p-4 rounded-2xl border border-red-500/10">
                            <span className="font-bold text-slate-200 text-sm">{ing.ingredient}: </span>
                            <span className="text-slate-400 text-sm">{ing.risk_note}</span>
                          </div>
                        ))}
                      </div>
                    </section>
                  )}
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="max-w-4xl mx-auto space-y-12">
            <section className="text-center space-y-6">
              <h2 className="text-5xl font-black tracking-tight">Semantic Explorer</h2>
              <p className="text-slate-400 text-xl max-w-2xl mx-auto">Discover ingredients using meaningful queries.</p>
              
              <div className="relative mt-12 max-w-2xl mx-auto group">
                <div className="absolute -inset-1 bg-gradient-to-r from-blue-600 to-emerald-600 rounded-[2rem] blur opacity-25 group-focus-within:opacity-50 transition duration-1000"></div>
                <div className="relative flex items-center bg-slate-900 rounded-[2rem] border border-white/10 shadow-2xl p-2 focus-within:border-blue-500/50 transition-all">
                  <Search className="ml-4 text-slate-500 w-6 h-6" />
                  <input 
                    type="text" 
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                    placeholder="e.g. 'natural ingredients for energy and focus'" 
                    className="w-full bg-transparent px-4 py-4 text-lg outline-none placeholder:text-slate-600"
                  />
                  <button 
                    onClick={handleSearch}
                    disabled={searching || !searchQuery}
                    className="mr-1 px-8 py-3 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed rounded-full text-white font-bold transition-all flex items-center gap-2"
                  >
                    {searching ? <Loader2 className="w-5 h-5 animate-spin" /> : <Sparkles className="w-5 h-5" />}
                    Search
                  </button>
                </div>
              </div>
            </section>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {searchResults.map((res, idx) => (
                <div key={idx} className="bg-slate-900/50 border border-white/5 rounded-3xl p-6 hover:bg-slate-900 transition-all group hover:-translate-y-2 hover:shadow-2xl hover:shadow-blue-500/10">
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h4 className="text-xl font-bold text-white group-hover:text-blue-400 transition-colors">{res.name}</h4>
                      <div className="mt-1 flex items-center gap-2">
                        <span className="px-2 py-0.5 bg-blue-500/10 text-blue-400 rounded-md text-[10px] font-bold uppercase tracking-wider">{res.category}</span>
                        <span className="text-[10px] text-slate-500 font-medium">Similarity: {Math.round(res.score * 100)}%</span>
                      </div>
                    </div>
                    <div className="p-2 bg-slate-800 rounded-xl border border-white/5 group-hover:border-blue-500/30 transition-colors">
                      <FlaskConical className="w-5 h-5 text-slate-500 group-hover:text-blue-400" />
                    </div>
                  </div>
                  <p className="text-slate-400 text-sm leading-relaxed mb-4 line-clamp-3 group-hover:line-clamp-none transition-all">{res.description}</p>
                  
                  {res.explanation && (
                    <div className="mb-4 p-3 bg-blue-500/5 border border-blue-500/10 rounded-xl italic text-xs text-blue-200/70">
                      "{res.explanation}"
                    </div>
                  )}

                  <div className="flex items-center gap-3 pt-4 border-t border-white/5">
                    <div className="h-1.5 flex-1 bg-slate-800 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-blue-600 to-emerald-500 rounded-full transition-all duration-1000" 
                        style={{ width: `${res.score * 100}%` }}
                      ></div>
                    </div>
                    <span className="text-[10px] font-bold text-slate-500 uppercase whitespace-nowrap tracking-widest">Match Score</span>
                  </div>
                </div>
              ))}
              
              {!searching && searchResults.length === 0 && searchQuery && (
                <div className="col-span-full py-20 text-center text-slate-500">
                  No strongly relevant supplement ingredients found.
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-white/5 py-12 mt-20 bg-slate-900/30">
        <div className="max-w-7xl mx-auto px-4 flex flex-col md:flex-row items-center justify-between gap-8">
          <div className="flex items-center gap-2 opacity-50">
            <FlaskConical className="w-5 h-5" />
            <span className="font-bold tracking-tight">SuppCheck AI</span>
          </div>
          <div className="text-slate-500 text-sm">
            Powered by SuppCheck Engine
          </div>
          <div className="flex gap-6 text-slate-400 text-xs font-medium">
            <a href="#" className="hover:text-white transition-colors">Documentation</a>
            <a href="#" className="hover:text-white transition-colors">Privacy Policy</a>
            <a href="#" className="hover:text-white transition-colors">Connect API</a>
          </div>
        </div>
      </footer>

      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes gradient {
          0% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
          100% { background-position: 0% 50%; }
        }
        .animate-gradient {
          background-size: 200% auto;
          animation: gradient 3s linear infinite;
        }
      `}} />
    </div>
  )
}

export default App
