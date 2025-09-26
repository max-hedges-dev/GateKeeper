import { useState } from 'react'

export default function App() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [snapshot, setSnapshot] = useState(null)
  const [findings, setFindings] = useState([])

  async function runScan() {
    setLoading(true); setError(null); setSnapshot(null); setFindings([])
    try {
      const res = await fetch('/api/scan', { method: 'POST' }) // if no proxy, use full URL
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      if (data.snapshot && data.findings) {
        setSnapshot(data.snapshot); setFindings(data.findings)
      } else {
        setSnapshot(data); setFindings([])
      }
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container">
      <div className="row" style={{justifyContent:'space-between'}}>
        <h1 className="h1">GateKeeper</h1>
        <button className="btn" onClick={runScan} disabled={loading}>
          {loading ? 'Scanning…' : 'Run Scan'}
        </button>
      </div>

      {error && <div className="card" style={{borderColor:'#5a2d2f',background:'#261416',color:'#ffb3b6'}}>{error}</div>}

      {!snapshot && !loading && !error && (
        <div className="card">
          Click <b>Run Scan</b> to probe your default gateway and see results here.
        </div>
      )}

      {snapshot && (
        <>
          <div className="card">
            <h2>Snapshot</h2>
            <div className="kv">
              <div>Target</div><div>{snapshot.target}</div>
              <div>Started</div><div>{snapshot.started_at}</div>
              <div>Duration</div><div>{snapshot.duration_ms} ms</div>
            </div>
          </div>

          <div className="card">
            <h2>Checks</h2>
            <div className="head" style={{padding:'4px 0 8px'}}>Overview</div>
            <table className="table">
              <thead>
                <tr>
                  <th className="th">Name</th>
                  <th className="th">Proto</th>
                  <th className="th">Port</th>
                  <th className="th">TCP</th>
                  <th className="th">HTTP</th>
                  <th className="th">Duration</th>
                </tr>
              </thead>
              <tbody>
                {(snapshot.checks || []).map((c, i) => (
                  <tr key={i} className="tr">
                    <td className="td">{c.name}</td>
                    <td className="td">{c.protocol}</td>
                    <td className="td">{c.port}</td>
                    <td className="td"><span className={`badge ${c.tcp_connect==='open'?'ok':''}`}>{c.tcp_connect ?? '—'}</span></td>
                    <td className="td"><span className={`badge ${c.http?.status===200?'ok':''}`}>{c.http?.status ?? '—'}</span></td>
                    <td className="td">{c.duration_ms} ms</td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div className="hr" />

            <details>
              <summary style={{cursor:'pointer',color:'var(--muted)'}}>Raw headers & body snippets</summary>
              {(snapshot.checks || []).map((c, i) => (
                <div key={i} style={{marginTop:12}}>
                  <div style={{fontWeight:700}}>{c.name}</div>
                  {c.http?.headers && (
                    <>
                      <div className="head" style={{marginTop:6}}>Headers</div>
                      <pre className="code">{c.http.headers}</pre>
                    </>
                  )}
                  {c.http?.body_snippet && (
                    <>
                      <div className="head" style={{marginTop:10}}>Body Snippet</div>
                      <pre className="code">{c.http.body_snippet}</pre>
                    </>
                  )}
                </div>
              ))}
            </details>
          </div>

          <div className="card">
            <h2>Findings</h2>
            {findings.length === 0 ? (
              <div className="badge na">No findings</div>
            ) : (
              <table className="table">
                <thead>
                  <tr>
                    <th className="th">Rule</th>
                    <th className="th">Check</th>
                    <th className="th">Severity</th>
                    <th className="th">Advice</th>
                    <th className="th">Evidence</th>
                  </tr>
                </thead>
                <tbody>
                  {findings.map((f, i) => (
                    <tr key={i} className="tr">
                      <td className="td">{f.rule_id}</td>
                      <td className="td">{f.check}</td>
                      <td className="td">
                        <span className={`badge ${f.severity==='issue'?'err':f.severity==='warning'?'warn':'ok'}`}>
                          {f.severity}
                        </span>
                      </td>
                      <td className="td">{f.advice}</td>
                      <td className="td"><pre className="code">{f.evidence || '—'}</pre></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
    </div>
  )
}