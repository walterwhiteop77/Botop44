import React, { useState } from 'react';
import {
  Bot,
  ShieldCheck,
  Key,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Terminal,
  Settings,
  Send,
  Clock,
  Lock,
  Database,
  Users,
  FileText,
  Zap,
  ChevronRight,
  Sliders,
  ExternalLink,
  Layers,
  ArrowRight,
  Download,
  Package,
  FolderArchive
} from 'lucide-react';
import DownloadCenter from './components/DownloadCenter';

export default function App() {
  const [activeTab, setActiveTab] = useState<'architecture' | 'admin_panel' | 'flow_simulator' | 'security' | 'downloads'>('downloads');
  const [testUserId, setTestUserId] = useState('548192031');
  const [testFileName, setTestFileName] = useState('Inception.2010.1080p.BluRay.x264.mkv');
  const [simStep, setSimStep] = useState<number>(1);
  const [generatedToken, setGeneratedToken] = useState<string>('tok_8f92a10b4c731e84df');

  const handleSimulate = (step: number) => {
    setSimStep(step);
    if (step === 3) {
      const rand = Math.random().toString(36).substring(2, 12) + Math.random().toString(36).substring(2, 10);
      setGeneratedToken(`tok_${rand}`);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-indigo-500 selection:text-white">
      {/* Top Navigation Bar */}
      <header className="border-b border-slate-800/80 bg-slate-900/60 backdrop-blur-md sticky top-0 z-50 px-6 py-4">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="font-bold text-lg tracking-tight text-white">Auto Filter Bot</h1>
                <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                  Dual-Bot Delivery Active
                </span>
              </div>
              <p className="text-xs text-slate-400">Main Bot (Bot 1) + File Delivery Worker (Bot 2)</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1 bg-slate-900/80 p-1 rounded-xl border border-slate-800">
              <button
                onClick={() => setActiveTab('downloads')}
                className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all flex items-center gap-1.5 ${
                  activeTab === 'downloads'
                    ? 'bg-emerald-600 text-white shadow-sm'
                    : 'text-emerald-400 hover:text-emerald-300'
                }`}
              >
                <FolderArchive className="w-3.5 h-3.5" />
                Download & Files
              </button>
              <button
                onClick={() => setActiveTab('architecture')}
                className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-all flex items-center gap-1.5 ${
                  activeTab === 'architecture' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Layers className="w-3.5 h-3.5" />
                Architecture
              </button>
              <button
                onClick={() => setActiveTab('admin_panel')}
                className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-all flex items-center gap-1.5 ${
                  activeTab === 'admin_panel' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Sliders className="w-3.5 h-3.5" />
                Bot 2 Admin Panel (/filebot)
              </button>
              <button
                onClick={() => setActiveTab('flow_simulator')}
                className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-all flex items-center gap-1.5 ${
                  activeTab === 'flow_simulator' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Zap className="w-3.5 h-3.5" />
                Direct Link Simulator
              </button>
              <button
                onClick={() => setActiveTab('security')}
                className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-all flex items-center gap-1.5 ${
                  activeTab === 'security' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <ShieldCheck className="w-3.5 h-3.5" />
                Security
              </button>
            </div>

            <button
              onClick={() => setActiveTab('downloads')}
              className="px-3.5 py-2 text-xs font-semibold rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white shadow-lg shadow-emerald-600/25 transition-all flex items-center gap-1.5 border border-emerald-400/30 cursor-pointer"
            >
              <Download className="w-4 h-4" />
              Download ZIP / Files
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl mx-auto w-full p-6 space-y-6">
        {/* Prominent ZIP Download Banner */}
        <div className="bg-gradient-to-r from-emerald-950/60 via-slate-900/90 to-indigo-950/60 border border-emerald-500/30 rounded-3xl p-5 md:p-6 shadow-xl relative overflow-hidden">
          <div className="absolute top-0 right-0 -mt-8 -mr-8 w-48 h-48 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none"></div>
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="px-2.5 py-0.5 text-xs font-bold rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 flex items-center gap-1">
                  <Package className="w-3 h-3" /> Ready for Deployment
                </span>
                <span className="text-xs text-slate-400">• Updated codebase with Bot 2 File Delivery integration</span>
              </div>
              <h2 className="text-lg font-bold text-white tracking-tight">AutoFilterBot-DualDelivery-Updated.zip</h2>
              <p className="text-xs text-slate-300 max-w-2xl leading-relaxed">
                Complete production package ready for download or one-line terminal setup. Includes Bot 1 &amp; Bot 2 native Pyrogram runners, encrypted token vault, MongoDB atomic queries, and admin control suite.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <button
                onClick={() => setActiveTab('downloads')}
                className="px-5 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs shadow-lg shadow-emerald-500/30 transition-all flex items-center gap-2 cursor-pointer"
              >
                <Download className="w-4 h-4" />
                Download Options &amp; Terminal (cURL)
              </button>
              <a
                href="/AutoFilterBot-DualDelivery-Updated.zip"
                target="_blank"
                rel="noopener noreferrer"
                className="px-4 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 font-semibold text-xs border border-slate-700/80 transition-all flex items-center gap-1.5 cursor-pointer"
              >
                <ExternalLink className="w-3.5 h-3.5 text-emerald-400" />
                Open in New Tab
              </a>
            </div>
          </div>
        </div>
        {/* System Vital Stats Banner */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-slate-400 font-medium">BOT 1 (Main Bot)</p>
              <p className="text-sm font-semibold text-white mt-1">Search, F-Sub & Checks</p>
              <p className="text-[11px] text-emerald-400 mt-1 flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" /> Fully Operational
              </p>
            </div>
            <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
              <Bot className="w-5 h-5" />
            </div>
          </div>

          <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-slate-400 font-medium">BOT 2 (Delivery Node)</p>
              <p className="text-sm font-semibold text-white mt-1">Direct Native Delivery</p>
              <p className="text-[11px] text-cyan-400 mt-1 flex items-center gap-1">
                <Zap className="w-3 h-3" /> Ready for Hot-Swap
              </p>
            </div>
            <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
              <Send className="w-5 h-5" />
            </div>
          </div>

          <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-slate-400 font-medium">SECURITY BROKER</p>
              <p className="text-sm font-semibold text-white mt-1">Atomic Single-Use Tokens</p>
              <p className="text-[11px] text-emerald-400 mt-1 flex items-center gap-1">
                <Lock className="w-3 h-3" /> Replay-Proof (SHA-256)
              </p>
            </div>
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
              <ShieldCheck className="w-5 h-5" />
            </div>
          </div>

          <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-slate-400 font-medium">AUTO-DELETE ENGINE</p>
              <p className="text-sm font-semibold text-white mt-1">Configurable Timer</p>
              <p className="text-[11px] text-amber-400 mt-1 flex items-center gap-1">
                <Clock className="w-3 h-3" /> Synced with Bot 1 Setting
              </p>
            </div>
            <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
              <Clock className="w-5 h-5" />
            </div>
          </div>
        </div>

        {/* Tab 1: Architecture Overview */}
        {activeTab === 'architecture' && (
          <div className="space-y-6">
            <div className="bg-slate-900/40 border border-slate-800 rounded-3xl p-6 md:p-8">
              <div className="max-w-2xl mb-8">
                <h2 className="text-xl font-bold text-white tracking-tight">Direct Dual-Bot Delivery Workflow</h2>
                <p className="text-sm text-slate-400 mt-2">
                  Bot 1 maintains all search, indexing, premium, and access verification controls. When access is granted,
                  Bot 1 generates a one-time cryptographic token and directly serves the <b>📥 Get File</b> button linking to Bot 2.
                </p>
              </div>

              {/* Architecture Diagram */}
              <div className="grid grid-cols-1 md:grid-cols-5 gap-4 items-center">
                {/* Step 1 */}
                <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 relative group hover:border-indigo-500/50 transition-all">
                  <div className="w-8 h-8 rounded-lg bg-indigo-500/20 text-indigo-400 font-bold text-xs flex items-center justify-center mb-3">
                    01
                  </div>
                  <h3 className="font-semibold text-sm text-white">Search on Bot 1</h3>
                  <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                    User searches for movies, series, or files via inline or PM queries.
                  </p>
                  <div className="mt-3 text-[11px] bg-slate-950 p-2 rounded-lg border border-slate-800/80 font-mono text-indigo-300">
                    /start search
                  </div>
                </div>

                <div className="hidden md:flex justify-center text-slate-600">
                  <ArrowRight className="w-5 h-5" />
                </div>

                {/* Step 2 */}
                <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 relative group hover:border-violet-500/50 transition-all">
                  <div className="w-8 h-8 rounded-lg bg-violet-500/20 text-violet-400 font-bold text-xs flex items-center justify-center mb-3">
                    02
                  </div>
                  <h3 className="font-semibold text-sm text-white">Bot 1 Access Verification</h3>
                  <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                    Existing force-sub, shortener verification, and premium checks run untouched.
                  </p>
                  <div className="mt-3 text-[11px] bg-slate-950 p-2 rounded-lg border border-slate-800/80 font-mono text-violet-300">
                    Passes All Checks ✓
                  </div>
                </div>

                <div className="hidden md:flex justify-center text-slate-600">
                  <ArrowRight className="w-5 h-5" />
                </div>

                {/* Step 3 */}
                <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 relative group hover:border-cyan-500/50 transition-all">
                  <div className="w-8 h-8 rounded-lg bg-cyan-500/20 text-cyan-400 font-bold text-xs flex items-center justify-center mb-3">
                    03
                  </div>
                  <h3 className="font-semibold text-sm text-white">Direct Deep Link</h3>
                  <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                    Bot 1 displays <b>📥 Get File</b> button pointing straight to Bot 2 deep link.
                  </p>
                  <div className="mt-3 text-[11px] bg-slate-950 p-2 rounded-lg border border-slate-800/80 font-mono text-cyan-300">
                    t.me/Bot2?start=TOK
                  </div>
                </div>
              </div>

              {/* Second row of diagram */}
              <div className="grid grid-cols-1 md:grid-cols-5 gap-4 items-center mt-6">
                {/* Step 4 */}
                <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 relative group hover:border-emerald-500/50 transition-all">
                  <div className="w-8 h-8 rounded-lg bg-emerald-500/20 text-emerald-400 font-bold text-xs flex items-center justify-center mb-3">
                    04
                  </div>
                  <h3 className="font-semibold text-sm text-white">Atomic Claim & Verification</h3>
                  <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                    Bot 2 validates user ID, expiry time, maintenance status, and claims token atomically.
                  </p>
                  <div className="mt-3 text-[11px] bg-slate-950 p-2 rounded-lg border border-slate-800/80 font-mono text-emerald-300">
                    find_one_and_update
                  </div>
                </div>

                <div className="hidden md:flex justify-center text-slate-600">
                  <ArrowRight className="w-5 h-5" />
                </div>

                {/* Step 5 */}
                <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 relative group hover:border-amber-500/50 transition-all">
                  <div className="w-8 h-8 rounded-lg bg-amber-500/20 text-amber-400 font-bold text-xs flex items-center justify-center mb-3">
                    05
                  </div>
                  <h3 className="font-semibold text-sm text-white">Native Media Delivery</h3>
                  <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                    Pyrogram send_cached_media sends exact file with custom cover & stream buttons.
                  </p>
                  <div className="mt-3 text-[11px] bg-slate-950 p-2 rounded-lg border border-slate-800/80 font-mono text-amber-300">
                    send_cached_media()
                  </div>
                </div>

                <div className="hidden md:flex justify-center text-slate-600">
                  <ArrowRight className="w-5 h-5" />
                </div>

                {/* Step 6 */}
                <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 relative group hover:border-rose-500/50 transition-all">
                  <div className="w-8 h-8 rounded-lg bg-rose-500/20 text-rose-400 font-bold text-xs flex items-center justify-center mb-3">
                    06
                  </div>
                  <h3 className="font-semibold text-sm text-white">Automated Cleanup</h3>
                  <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                    File message and warning deleted automatically after configured timer expires.
                  </p>
                  <div className="mt-3 text-[11px] bg-slate-950 p-2 rounded-lg border border-slate-800/80 font-mono text-rose-300">
                    schedule_delete(300s)
                  </div>
                </div>
              </div>
            </div>

            {/* Core Architectural Pillars */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 space-y-3">
                <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                  <ShieldCheck className="w-5 h-5" />
                </div>
                <h3 className="font-semibold text-base text-white">Zero Crash Guarantee</h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Bot 2 runs as an isolated worker with guarded error handlers. If Bot 2 is stopped, misconfigured, or
                  disabled, Bot 1 continues executing search, indexing, and administration with zero downtime.
                </p>
              </div>

              <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 space-y-3">
                <div className="w-10 h-10 rounded-xl bg-violet-500/10 border border-violet-500/20 flex items-center justify-center text-violet-400">
                  <RefreshCw className="w-5 h-5" />
                </div>
                <h3 className="font-semibold text-base text-white">Hot-Swapping Without Downtime</h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  When changing Bot 2 in the Bot 1 admin panel, the new bot token is pre-validated with Telegram first.
                  If the token is invalid, the existing Bot 2 is preserved running without disruption.
                </p>
              </div>

              <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 space-y-3">
                <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
                  <Lock className="w-5 h-5" />
                </div>
                <h3 className="font-semibold text-base text-white">Persistent Credential Security</h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Bot 2 tokens are never stored in plaintext and never logged. Configuration is stored in MongoDB using
                  authenticated HMAC-SHA256 PRF cipher encryption that persists across restarts.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Bot 2 Admin Panel (/filebot) */}
        {activeTab === 'admin_panel' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Telegram UI Mockup */}
            <div className="lg:col-span-2 bg-slate-900/60 border border-slate-800 rounded-3xl p-6">
              <div className="flex items-center justify-between pb-4 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-red-500/80"></div>
                  <div className="w-3 h-3 rounded-full bg-amber-500/80"></div>
                  <div className="w-3 h-3 rounded-full bg-emerald-500/80"></div>
                  <span className="text-xs text-slate-400 font-mono ml-2">Telegram PM — Admin Console (/filebot)</span>
                </div>
                <span className="text-[11px] font-mono text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">
                  ADMIN ONLY
                </span>
              </div>

              {/* Bot Message Preview */}
              <div className="mt-6 max-w-lg mx-auto bg-slate-950 border border-slate-800 rounded-2xl p-5 shadow-2xl">
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-7 h-7 rounded-full bg-indigo-600 flex items-center justify-center text-[10px] font-bold text-white">
                    DX
                  </div>
                  <div>
                    <span className="text-xs font-semibold text-white">DreamXBotz [Main Bot]</span>
                    <span className="text-[10px] text-slate-500 ml-1.5">bot</span>
                  </div>
                </div>

                <div className="text-xs space-y-2 text-slate-300 font-sans border-l-2 border-indigo-500 pl-3 py-1">
                  <p className="font-bold text-white text-sm">🤖 File Delivery Bot (Bot 2) Control Panel</p>
                  <p className="text-[11px] text-slate-400">━━━━━━━━━━━━━━━━━━━━━━━━━</p>
                  <p>• <b>Status:</b> <span className="text-emerald-400 font-semibold">🟢 Running</span></p>
                  <p>• <b>Bot:</b> @DeliveryBot_X (<code>7192839210</code>)</p>
                  <p>• <b>Uptime:</b> <code>14h 32m</code></p>
                  <p>• <b>Maintenance:</b> 🟢 OFF</p>
                  <p>• <b>Auto Delete:</b> <code>5 minutes</code> (300s)</p>
                  <p>• <b>Token Expiry:</b> <code>600s</code> (10m)</p>
                  <p>• <b>Force Sub:</b> 🟢 Enabled (2 channels)</p>
                  <p className="text-[11px] text-slate-400">─────────────────────────</p>
                  <p>📊 <b>Deliveries:</b> Total: <code>1,482</code> | Today: <code>219</code></p>
                  <p>👥 <b>Users:</b> <code>8,940</code> | Banned: <code>12</code></p>
                  <p className="text-[11px] text-slate-400">━━━━━━━━━━━━━━━━━━━━━━━━━</p>
                  <p className="text-slate-400">Select an option below to manage Bot 2:</p>
                </div>

                {/* Inline Buttons Grid matching plugins/delivery_bot_admin.py */}
                <div className="mt-4 space-y-1.5 text-xs font-medium">
                  <div className="grid grid-cols-2 gap-1.5">
                    <button className="bg-slate-900 hover:bg-slate-800 text-slate-200 py-2 px-3 rounded-lg border border-slate-700/60 text-center transition-colors">
                      🔄 Change Bot
                    </button>
                    <button className="bg-slate-900 hover:bg-slate-800 text-rose-400 py-2 px-3 rounded-lg border border-slate-700/60 text-center transition-colors">
                      🗑 Remove Bot
                    </button>
                  </div>
                  <div className="grid grid-cols-2 gap-1.5">
                    <button className="bg-slate-900 hover:bg-slate-800 text-amber-400 py-2 px-3 rounded-lg border border-slate-700/60 text-center transition-colors">
                      🔴 Disable Bot
                    </button>
                    <button className="bg-slate-900 hover:bg-slate-800 text-slate-200 py-2 px-3 rounded-lg border border-slate-700/60 text-center transition-colors">
                      ❤️ Status
                    </button>
                  </div>
                  <div className="grid grid-cols-2 gap-1.5">
                    <button className="bg-slate-900 hover:bg-slate-800 text-slate-200 py-2 px-3 rounded-lg border border-slate-700/60 text-center transition-colors">
                      📊 Statistics
                    </button>
                    <button className="bg-slate-900 hover:bg-slate-800 text-slate-200 py-2 px-3 rounded-lg border border-slate-700/60 text-center transition-colors">
                      👤 Users
                    </button>
                  </div>
                  <div className="grid grid-cols-2 gap-1.5">
                    <button className="bg-slate-900 hover:bg-slate-800 text-indigo-300 py-2 px-3 rounded-lg border border-slate-700/60 text-center transition-colors">
                      📢 Broadcast
                    </button>
                    <button className="bg-slate-900 hover:bg-slate-800 text-slate-200 py-2 px-3 rounded-lg border border-slate-700/60 text-center transition-colors">
                      📢 Force Sub
                    </button>
                  </div>
                  <div className="grid grid-cols-2 gap-1.5">
                    <button className="bg-slate-900 hover:bg-slate-800 text-slate-200 py-2 px-3 rounded-lg border border-slate-700/60 text-center transition-colors">
                      ⏱ Auto Delete
                    </button>
                    <button className="bg-slate-900 hover:bg-slate-800 text-slate-200 py-2 px-3 rounded-lg border border-slate-700/60 text-center transition-colors">
                      🛠 Maintenance
                    </button>
                  </div>
                  <div className="grid grid-cols-2 gap-1.5">
                    <button className="bg-slate-900 hover:bg-slate-800 text-slate-200 py-2 px-3 rounded-lg border border-slate-700/60 text-center transition-colors">
                      📜 Delivery Logs
                    </button>
                    <button className="bg-slate-900 hover:bg-slate-800 text-slate-200 py-2 px-3 rounded-lg border border-slate-700/60 text-center transition-colors">
                      ⚙️ Settings
                    </button>
                  </div>
                  <div>
                    <button className="w-full bg-slate-900/60 hover:bg-slate-800 text-slate-400 py-1.5 px-3 rounded-lg border border-slate-800 text-center transition-colors">
                      ❌ Close
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* Feature Breakdown */}
            <div className="space-y-4">
              <div className="bg-slate-900/60 border border-slate-800 rounded-3xl p-5 space-y-3">
                <div className="flex items-center gap-2 text-indigo-400">
                  <Terminal className="w-4 h-4" />
                  <h3 className="font-semibold text-sm text-white">Admin Commands</h3>
                </div>
                <div className="space-y-2 text-xs">
                  <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800/80">
                    <span className="font-mono text-indigo-400 font-bold">/filebot</span>
                    <p className="text-slate-400 mt-0.5">Open the full interactive File Delivery Bot management control panel.</p>
                  </div>
                  <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800/80">
                    <span className="font-mono text-indigo-400 font-bold">/deliverybot</span>
                    <p className="text-slate-400 mt-0.5">Alias command to access the Bot 2 administration interface.</p>
                  </div>
                  <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800/80">
                    <span className="font-mono text-indigo-400 font-bold">/broadcast</span>
                    <p className="text-slate-400 mt-0.5">Choose to broadcast to Main Bot, File Bot, or Both bots concurrently.</p>
                  </div>
                </div>
              </div>

              <div className="bg-slate-900/60 border border-slate-800 rounded-3xl p-5 space-y-3">
                <div className="flex items-center gap-2 text-emerald-400">
                  <Users className="w-4 h-4" />
                  <h3 className="font-semibold text-sm text-white">Isolated User Tracking</h3>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Bot 2 maintains its own dedicated <code className="text-emerald-400 font-mono">file_bot_users</code> table in MongoDB,
                  tracking each recipient's first seen date, total files delivered, and individual ban status independently of Bot 1.
                </p>
              </div>

              <div className="bg-slate-900/60 border border-slate-800 rounded-3xl p-5 space-y-3">
                <div className="flex items-center gap-2 text-cyan-400">
                  <Send className="w-4 h-4" />
                  <h3 className="font-semibold text-sm text-white">Multi-Target Broadcast</h3>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Broadcasts to File Bot are delivered using Bot 2's own Telegram bot client—never routing File Bot broadcasts
                  through Bot 1.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Tab 3: Direct Link & Flow Simulator */}
        {activeTab === 'flow_simulator' && (
          <div className="space-y-6">
            <div className="bg-slate-900/60 border border-slate-800 rounded-3xl p-6">
              <div className="max-w-2xl mb-6">
                <h2 className="text-xl font-bold text-white tracking-tight">Interactive Direct Link Flow Simulator</h2>
                <p className="text-sm text-slate-400 mt-1">
                  Test and inspect the transition from Bot 1 search completion directly into Bot 2 native file delivery.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Simulation Controls */}
                <div className="space-y-4 bg-slate-950 p-5 rounded-2xl border border-slate-800">
                  <h3 className="text-sm font-semibold text-slate-200">Simulation Parameters</h3>
                  
                  <div>
                    <label className="text-xs text-slate-400 block mb-1">Telegram User ID (Requester)</label>
                    <input
                      type="text"
                      value={testUserId}
                      onChange={(e) => setTestUserId(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-indigo-500"
                    />
                  </div>

                  <div>
                    <label className="text-xs text-slate-400 block mb-1">Selected Movie / File</label>
                    <input
                      type="text"
                      value={testFileName}
                      onChange={(e) => setTestFileName(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-indigo-500"
                    />
                  </div>

                  <div className="pt-2">
                    <p className="text-xs text-slate-400 mb-2 font-medium">Workflow Stage:</p>
                    <div className="grid grid-cols-4 gap-2">
                      <button
                        onClick={() => handleSimulate(1)}
                        className={`py-2 px-2 text-xs font-semibold rounded-lg border transition-all ${
                          simStep === 1
                            ? 'bg-indigo-600 border-indigo-500 text-white'
                            : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
                        }`}
                      >
                        1. Search
                      </button>
                      <button
                        onClick={() => handleSimulate(2)}
                        className={`py-2 px-2 text-xs font-semibold rounded-lg border transition-all ${
                          simStep === 2
                            ? 'bg-indigo-600 border-indigo-500 text-white'
                            : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
                        }`}
                      >
                        2. Verify
                      </button>
                      <button
                        onClick={() => handleSimulate(3)}
                        className={`py-2 px-2 text-xs font-semibold rounded-lg border transition-all ${
                          simStep === 3
                            ? 'bg-indigo-600 border-indigo-500 text-white'
                            : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
                        }`}
                      >
                        3. Deep Link
                      </button>
                      <button
                        onClick={() => handleSimulate(4)}
                        className={`py-2 px-2 text-xs font-semibold rounded-lg border transition-all ${
                          simStep === 4
                            ? 'bg-emerald-600 border-emerald-500 text-white'
                            : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
                        }`}
                      >
                        4. Delivery
                      </button>
                    </div>
                  </div>
                </div>

                {/* Simulation Output Card */}
                <div className="bg-slate-950 p-5 rounded-2xl border border-slate-800 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                      <span className="text-xs font-mono text-slate-400">Stage Outcome</span>
                      <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-900 text-indigo-400 border border-slate-800">
                        Step {simStep} of 4
                      </span>
                    </div>

                    <div className="mt-4">
                      {simStep === 1 && (
                        <div className="space-y-2">
                          <p className="text-xs font-semibold text-slate-300">Bot 1 Search Display</p>
                          <div className="bg-slate-900 p-3 rounded-xl border border-slate-800 text-xs font-mono text-slate-300">
                            🔍 <b>Search results for:</b> Inception<br />
                            1. [{testFileName}]<br />
                            👉 User taps on file
                          </div>
                        </div>
                      )}

                      {simStep === 2 && (
                        <div className="space-y-2">
                          <p className="text-xs font-semibold text-slate-300">Bot 1 Verification Checks</p>
                          <div className="bg-slate-900 p-3 rounded-xl border border-slate-800 text-xs font-mono text-emerald-400">
                            ✓ Force Subscription: Joined<br />
                            ✓ Shortener Token: Validated<br />
                            ✓ User Binding: {testUserId}<br />
                            → Ready for delivery token creation
                          </div>
                        </div>
                      )}

                      {simStep === 3 && (
                        <div className="space-y-3">
                          <p className="text-xs font-semibold text-slate-300">Bot 1 Direct Handoff Button</p>
                          <div className="bg-slate-900 p-3 rounded-xl border border-slate-800 text-xs">
                            <p className="text-white font-semibold">📁 File Ready For Delivery!</p>
                            <p className="text-slate-400 text-[11px] mt-1">🎬 File: {testFileName}</p>
                            <div className="mt-3">
                              <a
                                href="#simulation"
                                onClick={(e) => { e.preventDefault(); handleSimulate(4); }}
                                className="inline-flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-xl font-bold text-xs shadow-lg shadow-indigo-600/30 transition-all cursor-pointer"
                              >
                                📥 Get File <ExternalLink className="w-3.5 h-3.5" />
                              </a>
                            </div>
                          </div>
                          <div className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-800 text-[11px] font-mono text-slate-400 break-all">
                            Target: <span className="text-indigo-400">https://t.me/DeliveryBot?start={generatedToken}</span>
                          </div>
                        </div>
                      )}

                      {simStep === 4 && (
                        <div className="space-y-3">
                          <p className="text-xs font-semibold text-emerald-400 flex items-center gap-1.5">
                            <CheckCircle2 className="w-4 h-4" /> Bot 2 Atomic Delivery & Cleanup
                          </p>
                          <div className="bg-slate-900 p-3 rounded-xl border border-slate-800 text-xs space-y-1.5">
                            <p className="text-emerald-400 font-semibold">✓ Token Claimed: Single-use guarantee validated</p>
                            <p className="text-slate-300">📦 Media: send_cached_media() dispatched</p>
                            <p className="text-amber-400 text-[11px]">⏱ Auto-Delete timer scheduled: 300 seconds</p>
                            <p className="text-slate-400 text-[11px]">📊 Log recorded: file_delivery_requests.status = 'delivered'</p>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-500 font-mono">
                    <span>Target Bot: @DeliveryBot</span>
                    <span>Replay Token: {generatedToken.substring(0, 10)}...</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab 4: Security & Replay Protection */}
        {activeTab === 'security' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-slate-900/60 border border-slate-800 rounded-3xl p-6 space-y-4">
              <div className="flex items-center gap-2 text-indigo-400">
                <Lock className="w-5 h-5" />
                <h3 className="font-semibold text-base text-white">Replay-Proof Delivery Protocol</h3>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                Delivery links are protected against replay attacks, tampering, link sharing, and race conditions
                via four concentric defense layers:
              </p>

              <div className="space-y-2.5 text-xs">
                <div className="bg-slate-950 p-3 rounded-xl border border-slate-800/80">
                  <span className="font-semibold text-white">1. Cryptographic Opaque Tokens</span>
                  <p className="text-slate-400 text-[11px] mt-0.5">
                    Tokens are 32-byte URL-safe random secrets generated with Python's <code className="text-indigo-400 font-mono">secrets</code> module.
                    Only the SHA-256 hash is indexed in the database.
                  </p>
                </div>
                <div className="bg-slate-950 p-3 rounded-xl border border-slate-800/80">
                  <span className="font-semibold text-white">2. Atomic Single-Use Transition</span>
                  <p className="text-slate-400 text-[11px] mt-0.5">
                    Bot 2 calls <code className="text-emerald-400 font-mono">find_one_and_update({'{'} status: 'pending' {'}'})</code> in MongoDB.
                    Even if a user rapidly double-taps the link, only one delivery process can claim the token.
                  </p>
                </div>
                <div className="bg-slate-950 p-3 rounded-xl border border-slate-800/80">
                  <span className="font-semibold text-white">3. Strict User Binding</span>
                  <p className="text-slate-400 text-[11px] mt-0.5">
                    The Telegram user ID of the person opening Bot 2 is validated against the <code className="text-indigo-400 font-mono">user_id</code> stored
                    when Bot 1 generated the request. Forwarded or leaked links are automatically rejected.
                  </p>
                </div>
                <div className="bg-slate-950 p-3 rounded-xl border border-slate-800/80">
                  <span className="font-semibold text-white">4. Short-Lived TTL Expiration</span>
                  <p className="text-slate-400 text-[11px] mt-0.5">
                    Delivery tokens expire automatically after the configured time (default 10 minutes). Expired tokens
                    cannot be claimed and are marked as expired in logs.
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-slate-900/60 border border-slate-800 rounded-3xl p-6 space-y-4">
              <div className="flex items-center gap-2 text-cyan-400">
                <Database className="w-5 h-5" />
                <h3 className="font-semibold text-base text-white">Database Collections Schema</h3>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                Dedicated collections provisioned within the bot's existing MongoDB database:
              </p>

              <div className="space-y-2.5 text-xs font-mono">
                <div className="bg-slate-950 p-3 rounded-xl border border-slate-800/80">
                  <div className="flex items-center justify-between text-indigo-400 font-semibold mb-1">
                    <span>file_delivery_requests</span>
                    <span className="text-[10px] text-slate-500 font-normal">Indexed</span>
                  </div>
                  <p className="text-slate-400 text-[11px] font-sans">
                    Holds active delivery requests: request_id, token_hash, user_id, file_id, file_type, grp_id, status (pending/processing/delivered/failed), expires_at.
                  </p>
                </div>

                <div className="bg-slate-950 p-3 rounded-xl border border-slate-800/80">
                  <div className="flex items-center justify-between text-cyan-400 font-semibold mb-1">
                    <span>file_delivery_bot_config</span>
                    <span className="text-[10px] text-slate-500 font-normal">Singleton</span>
                  </div>
                  <p className="text-slate-400 text-[11px] font-sans">
                    Stores Bot 2 credentials (encrypted), enabled flag, auto_delete period, token_expiry, force_sub channels, maintenance_mode.
                  </p>
                </div>

                <div className="bg-slate-950 p-3 rounded-xl border border-slate-800/80">
                  <div className="flex items-center justify-between text-emerald-400 font-semibold mb-1">
                    <span>file_bot_users</span>
                    <span className="text-[10px] text-slate-500 font-normal">Unique user_id</span>
                  </div>
                  <p className="text-slate-400 text-[11px] font-sans">
                    Tracks users who have received files from Bot 2, delivery counts, last_seen, and ban records for Bot 2.
                  </p>
                </div>

                <div className="bg-slate-950 p-3 rounded-xl border border-slate-800/80">
                  <div className="flex items-center justify-between text-amber-400 font-semibold mb-1">
                    <span>delivery_logs</span>
                    <span className="text-[10px] text-slate-500 font-normal">Timestamp sorted</span>
                  </div>
                  <p className="text-slate-400 text-[11px] font-sans">
                    Audit trail for every file dispatch: request_id, user_id, file_name, delivery_bot, status, created_at, delivered_at.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab 5: Download & Code Center */}
        {activeTab === 'downloads' && (
          <DownloadCenter onSimulateLink={() => setActiveTab('flow_simulator')} />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 bg-slate-950 px-6 py-4 mt-auto">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-4 text-xs text-slate-500">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
            <span>Auto Filter Bot Dual-Delivery Engine • v2.0 Production Ready</span>
          </div>
          <div className="flex items-center gap-4">
            <span>Admin Command: <code className="text-indigo-400 font-mono">/filebot</code></span>
            <span>•</span>
            <span>Broadcast: <code className="text-indigo-400 font-mono">/broadcast</code></span>
          </div>
        </div>
      </footer>
    </div>
  );
}
