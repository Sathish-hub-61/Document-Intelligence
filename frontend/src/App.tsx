import React, { useState } from 'react';

export function App() {
  const [role, setRole] = useState<'student' | 'faculty' | 'staff' | 'admin'>('student');

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-800">
      <header className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between shadow-sm">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-blue-600 text-white rounded-lg flex items-center justify-center font-bold text-lg shadow-sm">
            UD
          </div>
          <div>
            <h1 className="font-semibold text-lg leading-tight text-slate-900">University Document Intelligence</h1>
            <p className="text-xs text-slate-500">Official Policy & Regulations Grounded Assistant</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-slate-500">Current Role:</span>
          <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-blue-50 text-blue-700 border border-blue-200 uppercase tracking-wide">
            {role}
          </span>
        </div>
      </header>

      <main className="flex-1 max-w-6xl w-full mx-auto p-6 flex flex-col gap-6">
        <div className="bg-white rounded-xl border border-slate-200 p-8 text-center shadow-sm max-w-2xl mx-auto my-auto">
          <h2 className="text-2xl font-bold text-slate-900 mb-2">Grounded University Document Assistant</h2>
          <p className="text-slate-600 mb-6 text-sm">
            Ask questions about academic regulations, exam rules, circulars, and university procedures.
            Answers are strictly cited to official document sections.
          </p>
          <div className="flex justify-center gap-3 text-sm">
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-emerald-50 text-emerald-700 text-xs font-medium border border-emerald-200">
              ✓ Dual-Layer Role Filter
            </span>
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-indigo-50 text-indigo-700 text-xs font-medium border border-indigo-200">
              ✓ Verifiable Citations
            </span>
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-amber-50 text-amber-700 text-xs font-medium border border-amber-200">
              ✓ Zero Hallucination Gate
            </span>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;

