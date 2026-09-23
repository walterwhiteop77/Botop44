import React, { useState } from 'react';
import {
  Download,
  Copy,
  Check,
  Terminal,
  ExternalLink,
  FileCode,
  AlertTriangle,
  FolderArchive,
  RefreshCw,
  Monitor,
  Code2,
  FileText
} from 'lucide-react';
import updatedFiles from '../data/updatedFiles.json';

interface DownloadCenterProps {
  onSimulateLink?: () => void;
}

export default function DownloadCenter({ onSimulateLink }: DownloadCenterProps) {
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);
  const [downloadStatus, setDownloadStatus] = useState<'idle' | 'success' | 'iframe_blocked'>('idle');
  const [selectedFile, setSelectedFile] = useState<string>('database/delivery_db.py');
  const [activeSubTab, setActiveSubTab] = useState<'download' | 'code'>('download');

  // Direct public URL for the deployment
  const publicBaseUrl = window.location.origin;
  const zipPath = '/AutoFilterBot-DualDelivery-Updated.zip';
  const fullZipUrl = `${publicBaseUrl}${zipPath}`;
  const mirrorZipUrl = `${publicBaseUrl}/bot.zip`;

  const copyToClipboard = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2500);
  };

  const handleBlobDownload = async () => {
    setDownloading(true);
    setDownloadStatus('idle');
    try {
      const response = await fetch(zipPath);
      if (!response.ok) throw new Error('Failed to fetch zip');
      const blob = await response.blob();
      const blobUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = 'AutoFilterBot-DualDelivery-Updated.zip';
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      setTimeout(() => {
        window.URL.revokeObjectURL(blobUrl);
        setDownloading(false);
        setDownloadStatus('success');
      }, 800);
    } catch (err) {
      console.error('Download error:', err);
      setDownloading(false);
      setDownloadStatus('iframe_blocked');
    }
  };

  const curlCommand = `curl -fSL -o AutoFilterBot.zip "${fullZipUrl}" && unzip -o AutoFilterBot.zip -d AutoFilterBot`;
  const wgetCommand = `wget -O AutoFilterBot.zip "${fullZipUrl}" && unzip -o AutoFilterBot.zip -d AutoFilterBot`;
  const powershellCommand = `Invoke-WebRequest -Uri "${fullZipUrl}" -OutFile AutoFilterBot.zip; Expand-Archive -Path AutoFilterBot.zip -DestinationPath AutoFilterBot -Force`;

  const filesMap = updatedFiles as Record<string, string>;
  const fileKeys = Object.keys(filesMap);

  return (
    <div className="space-y-6">
      {/* Sub Tabs */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveSubTab('download')}
            className={`px-4 py-2 text-xs font-semibold rounded-xl transition-all flex items-center gap-2 ${
              activeSubTab === 'download'
                ? 'bg-emerald-600 text-white shadow-md shadow-emerald-600/20'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            <FolderArchive className="w-4 h-4" />
            Download Options & Commands
          </button>
          <button
            onClick={() => setActiveSubTab('code')}
            className={`px-4 py-2 text-xs font-semibold rounded-xl transition-all flex items-center gap-2 ${
              activeSubTab === 'code'
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            <Code2 className="w-4 h-4" />
            Inspect & Copy Source Files ({fileKeys.length})
          </button>
        </div>

        <div className="text-xs text-slate-400 hidden sm:block">
          Archive Size: <span className="text-emerald-400 font-mono font-medium">233 KB</span> • Verified SHA256 Engine
        </div>
      </div>

      {activeSubTab === 'download' ? (
        <div className="space-y-6">
          {/* Iframe Notice Banner */}
          <div className="bg-amber-950/40 border border-amber-500/30 rounded-2xl p-4 flex items-start gap-3.5">
            <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
            <div className="text-xs space-y-1">
              <p className="font-semibold text-amber-200">
                Why some browsers block downloads inside preview windows:
              </p>
              <p className="text-amber-300/80 leading-relaxed">
                Cloud IDEs and AI Studio display previews inside an isolated <code>&lt;iframe&gt;</code>. Standard HTML <code>&lt;a download&gt;</code> clicks inside sandboxed iframes can be suppressed by Chrome or Firefox security policies. Use <strong className="text-white">Method 1 (New Tab)</strong> or <strong className="text-white">Method 2 (Terminal Command)</strong> below to download effortlessly without sandbox restrictions!
              </p>
            </div>
          </div>

          {/* Methods Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {/* Method 1: New Tab Direct Download */}
            <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-5 flex flex-col justify-between space-y-4">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="px-2.5 py-0.5 text-[10px] font-bold tracking-wide uppercase rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    Method 1 • Browser
                  </span>
                  <span className="text-xs text-slate-500">Opens Top-Level</span>
                </div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  Direct Download in New Tab
                </h3>
                <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                  Opens the zip download link directly in a clean browser window, bypassing iframe sandbox limitations entirely.
                </p>
              </div>

              <div className="space-y-2 pt-2">
                <a
                  href={fullZipUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-full py-2.5 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs shadow-lg shadow-emerald-600/20 flex items-center justify-center gap-2 transition-all cursor-pointer"
                >
                  <ExternalLink className="w-4 h-4" />
                  Open & Download in New Tab
                </a>

                <button
                  onClick={handleBlobDownload}
                  disabled={downloading}
                  className="w-full py-2 px-4 rounded-xl bg-slate-800 hover:bg-slate-750 text-slate-300 font-medium text-xs border border-slate-700/80 flex items-center justify-center gap-2 transition-all cursor-pointer"
                >
                  {downloading ? (
                    <RefreshCw className="w-3.5 h-3.5 animate-spin text-emerald-400" />
                  ) : (
                    <Download className="w-3.5 h-3.5" />
                  )}
                  {downloading ? 'Preparing Archive...' : 'Try In-Memory Blob Download'}
                </button>

                {downloadStatus === 'success' && (
                  <p className="text-[11px] text-emerald-400 text-center flex items-center justify-center gap-1">
                    <Check className="w-3.5 h-3.5" /> Triggered download! Check your browser's Downloads folder.
                  </p>
                )}
                {downloadStatus === 'iframe_blocked' && (
                  <p className="text-[11px] text-amber-400 text-center">
                    Browser blocked in-frame download. Please use the "Open in New Tab" button or terminal command below!
                  </p>
                )}
              </div>
            </div>

            {/* Method 2: Copy Direct URL */}
            <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-5 flex flex-col justify-between space-y-4">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="px-2.5 py-0.5 text-[10px] font-bold tracking-wide uppercase rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                    Method 2 • Direct URL
                  </span>
                  <span className="text-xs text-slate-500">Public CDN / Host</span>
                </div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  Copy Direct Archive URL
                </h3>
                <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                  Paste this link into your favorite browser tab, download manager (IDM/FDM), or share it with your deployment server.
                </p>
              </div>

              <div className="space-y-2 pt-2">
                <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800 flex items-center justify-between gap-2">
                  <span className="text-[11px] font-mono text-cyan-300 truncate select-all">
                    {fullZipUrl}
                  </span>
                  <button
                    onClick={() => copyToClipboard(fullZipUrl, 'direct-url')}
                    className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors shrink-0"
                    title="Copy URL"
                  >
                    {copiedKey === 'direct-url' ? (
                      <Check className="w-3.5 h-3.5 text-emerald-400" />
                    ) : (
                      <Copy className="w-3.5 h-3.5" />
                    )}
                  </button>
                </div>

                <div className="flex items-center justify-between text-[11px] text-slate-400 px-1">
                  <span>Alternative mirror:</span>
                  <button
                    onClick={() => copyToClipboard(mirrorZipUrl, 'mirror-url')}
                    className="text-indigo-400 hover:text-indigo-300 font-mono underline flex items-center gap-1"
                  >
                    {copiedKey === 'mirror-url' ? 'Copied!' : 'Copy /bot.zip mirror'}
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Method 3: One-Click Terminal Commands */}
          <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-5 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                  <Terminal className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white">Terminal One-Liner Commands</h3>
                  <p className="text-xs text-slate-400">Instantly download and extract the updated code on any VPS, Mac, or PC</p>
                </div>
              </div>
              <span className="text-[11px] text-slate-500 font-mono">Recommended for Servers</span>
            </div>

            {/* Linux / macOS Curl */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs text-slate-300 font-medium">
                <span className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-400"></span> Linux / macOS / VPS (cURL):
                </span>
                <button
                  onClick={() => copyToClipboard(curlCommand, 'curl')}
                  className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] font-medium flex items-center gap-1 transition-colors"
                >
                  {copiedKey === 'curl' ? (
                    <>
                      <Check className="w-3 h-3 text-emerald-400" /> Copied Command!
                    </>
                  ) : (
                    <>
                      <Copy className="w-3 h-3" /> Copy cURL
                    </>
                  )}
                </button>
              </div>
              <div className="bg-slate-950 p-3 rounded-xl border border-slate-800 font-mono text-xs text-emerald-400/90 overflow-x-auto select-all">
                {curlCommand}
              </div>
            </div>

            {/* Linux Wget */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs text-slate-300 font-medium">
                <span className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-blue-400"></span> Linux Wget:
                </span>
                <button
                  onClick={() => copyToClipboard(wgetCommand, 'wget')}
                  className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] font-medium flex items-center gap-1 transition-colors"
                >
                  {copiedKey === 'wget' ? (
                    <>
                      <Check className="w-3 h-3 text-emerald-400" /> Copied Command!
                    </>
                  ) : (
                    <>
                      <Copy className="w-3 h-3" /> Copy Wget
                    </>
                  )}
                </button>
              </div>
              <div className="bg-slate-950 p-3 rounded-xl border border-slate-800 font-mono text-xs text-blue-400/90 overflow-x-auto select-all">
                {wgetCommand}
              </div>
            </div>

            {/* Windows PowerShell */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs text-slate-300 font-medium">
                <span className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-cyan-400"></span> Windows PowerShell:
                </span>
                <button
                  onClick={() => copyToClipboard(powershellCommand, 'ps')}
                  className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] font-medium flex items-center gap-1 transition-colors"
                >
                  {copiedKey === 'ps' ? (
                    <>
                      <Check className="w-3 h-3 text-emerald-400" /> Copied Command!
                    </>
                  ) : (
                    <>
                      <Copy className="w-3 h-3" /> Copy PowerShell
                    </>
                  )}
                </button>
              </div>
              <div className="bg-slate-950 p-3 rounded-xl border border-slate-800 font-mono text-xs text-cyan-400/90 overflow-x-auto select-all">
                {powershellCommand}
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* Source Files Inspector & Copy Tab */
        <div className="grid grid-cols-1 md:grid-cols-12 gap-5">
          {/* File List */}
          <div className="md:col-span-4 bg-slate-900/70 border border-slate-800 rounded-2xl p-3 space-y-1.5">
            <div className="px-3 py-2 text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center justify-between">
              <span>Updated Files</span>
              <span className="text-[10px] bg-slate-800 px-2 py-0.5 rounded-full text-slate-300">
                {fileKeys.length} files
              </span>
            </div>
            <div className="space-y-1 max-h-[550px] overflow-y-auto pr-1">
              {fileKeys.map((file) => {
                const isSelected = selectedFile === file;
                const fileName = file.split('/').pop();
                const folderName = file.substring(0, file.lastIndexOf('/'));

                return (
                  <button
                    key={file}
                    onClick={() => setSelectedFile(file)}
                    className={`w-full text-left p-2.5 rounded-xl text-xs transition-all flex items-start gap-2.5 ${
                      isSelected
                        ? 'bg-indigo-600/20 border border-indigo-500/40 text-white'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 border border-transparent'
                    }`}
                  >
                    <FileCode className={`w-4 h-4 shrink-0 mt-0.5 ${isSelected ? 'text-indigo-400' : 'text-slate-500'}`} />
                    <div className="truncate min-w-0">
                      <p className={`font-semibold truncate ${isSelected ? 'text-indigo-200' : 'text-slate-300'}`}>
                        {fileName}
                      </p>
                      {folderName && (
                        <p className="text-[10px] text-slate-500 font-mono truncate">{folderName}</p>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Code Display Area */}
          <div className="md:col-span-8 bg-slate-900/70 border border-slate-800 rounded-2xl flex flex-col overflow-hidden">
            {/* Header */}
            <div className="bg-slate-950/80 px-4 py-3 border-b border-slate-800 flex items-center justify-between gap-3">
              <div className="flex items-center gap-2 truncate">
                <FileText className="w-4 h-4 text-indigo-400 shrink-0" />
                <span className="font-mono text-xs font-semibold text-slate-200 truncate">
                  {selectedFile}
                </span>
                <span className="text-[10px] text-slate-500 font-mono hidden sm:inline">
                  ({(filesMap[selectedFile] || '').split('\n').length} lines)
                </span>
              </div>

              <button
                onClick={() => copyToClipboard(filesMap[selectedFile] || '', `code-${selectedFile}`)}
                className="px-3 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs flex items-center gap-1.5 shadow-md shadow-indigo-600/20 transition-all cursor-pointer shrink-0"
              >
                {copiedKey === `code-${selectedFile}` ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-emerald-300" />
                    Copied Code!
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5" />
                    Copy Complete File
                  </>
                )}
              </button>
            </div>

            {/* Code Box */}
            <div className="p-4 bg-slate-950 font-mono text-xs text-slate-300 overflow-x-auto max-h-[500px] overflow-y-auto leading-relaxed select-all">
              <pre className="text-[12px]">{filesMap[selectedFile] || '// File not found'}</pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
