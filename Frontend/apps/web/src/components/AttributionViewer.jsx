import { useState, useEffect, useRef, useMemo } from "react";
import useChatStore from "@/store/chatStore";
import { API_BASE } from "@/config";
import { 
  FileText, 
  Film, 
  ChevronLeft, 
  ChevronRight, 
  ZoomIn, 
  ZoomOut, 
  Layers, 
  Table as TableIcon,
} from "lucide-react";

const isVideo = (f) => {
  if (!f) return false;
  if (f.type === "video") return true;
  const name = (f.name || "").toLowerCase();
  const ext = (f.ext || "").toLowerCase();
  return ext === ".mp4" || ext === ".mov" || ext === ".webm" || ext === ".avi" || ext === ".mkv" ||
         name.endsWith(".mp4") || name.endsWith(".mov") || name.endsWith(".webm") ||
         name.includes("youtube.com") || name.includes("youtu.be");
};

const getYouTubeId = (url) => {
  if (!url) return null;
  const match = url.match(/(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))([\w-]{11})/);
  return match ? match[1] : null;
};

export default function AttributionViewer() {
  const {
    uploadedFiles,
    activeFile,
    setActiveFile,
    viewerTab,
    setViewerTab,
    activeHighlight,
    activeVideoSeek,
    pdfPage,
    setPdfPage,
    pdfTotalPages,
    setPdfTotalPages,
    zoom,
    setZoom
  } = useChatStore();

  const [metadata, setMetadata] = useState(null);
  const [loadingMeta, setLoadingMeta] = useState(false);
  const [docMode, setDocMode] = useState("preview"); // "preview" | "canvas"
  const [playerMode, setPlayerMode] = useState("youtube"); // "youtube" | "native"
  const videoRef = useRef(null);
  const containerRef = useRef(null);
  const prevSeekRef = useRef(null);
  const prevHighlightRef = useRef(null);

  const docFiles = useMemo(() => (uploadedFiles || []).filter(f => !isVideo(f)), [uploadedFiles]);
  const videoFiles = useMemo(() => (uploadedFiles || []).filter(f => isVideo(f)), [uploadedFiles]);

  // Default activeFile when tab changes or files load if none selected
  useEffect(() => {
    if (!activeFile) {
      if (viewerTab === "video" && videoFiles.length > 0) {
        setActiveFile(videoFiles[0]);
      } else if (viewerTab === "document" && docFiles.length > 0) {
        setActiveFile(docFiles[0]);
      } else if (uploadedFiles && uploadedFiles.length > 0) {
        setActiveFile(uploadedFiles[0]);
      }
    }
  }, [viewerTab, videoFiles, docFiles, activeFile, uploadedFiles, setActiveFile]);

  // Load document metadata when activeFile changes
  useEffect(() => {
    if (activeFile && !isVideo(activeFile)) {
      const docUuid = activeFile.uuid || activeFile.name;
      setLoadingMeta(true);
      fetch(`${API_BASE}/api/documents/${encodeURIComponent(docUuid)}/metadata`)
        .then(res => res.ok ? res.json() : null)
        .then(data => {
          if (data) {
            setMetadata(data);
            const total = Object.keys(data).filter(k => k.startsWith("page_")).length;
            if (total > 0) setPdfTotalPages(total);
          }
          setLoadingMeta(false);
        })
        .catch(() => setLoadingMeta(false));
    }
  }, [activeFile, setPdfTotalPages]);

  // When a document citation is clicked in chat, jump to page and highlight bounding box
  useEffect(() => {
    if (activeHighlight && activeHighlight !== prevHighlightRef.current) {
      prevHighlightRef.current = activeHighlight;
      setDocMode("canvas");
      if (viewerTab !== "document") {
        setViewerTab("document");
      }
      if (activeHighlight.page && pdfPage !== activeHighlight.page) {
        setPdfPage(activeHighlight.page);
      }
      if (activeHighlight.doc_name && docFiles.length > 0) {
        const match = docFiles.find(f => 
          f.name === activeHighlight.doc_name || 
          f.real_name === activeHighlight.doc_name ||
          (f.uuid && activeHighlight.doc_name.includes(f.uuid))
        );
        if (match && (!activeFile || (activeFile.name !== match.name && activeFile.uuid !== match.uuid))) {
          setActiveFile(match);
        }
      }
    }
  }, [activeHighlight, docFiles, activeFile, viewerTab, pdfPage, setPdfPage, setActiveFile, setViewerTab]);

  // When a video citation is clicked in chat, jump to exact timestamp
  useEffect(() => {
    if (activeVideoSeek && activeVideoSeek !== prevSeekRef.current) {
      prevSeekRef.current = activeVideoSeek;
      if (viewerTab !== "video") {
        setViewerTab("video");
      }
      if (videoFiles.length > 0) {
        const match = videoFiles.find(f => 
          f.name === activeVideoSeek.video_name || 
          f.real_name === activeVideoSeek.video_name ||
          f.uuid === activeVideoSeek.video_name ||
          (f.source_url && f.source_url === activeVideoSeek.video_name)
        ) || videoFiles[0];
        if (match && (!activeFile || (activeFile.uuid !== match.uuid && activeFile.name !== match.name))) {
          setActiveFile(match);
        }
      }
      if (videoRef.current) {
        videoRef.current.currentTime = activeVideoSeek.seconds;
        videoRef.current.play().catch(() => {});
      }
    }
  }, [activeVideoSeek, videoFiles, activeFile, viewerTab, setActiveFile, setViewerTab]);

  // Current page data from metadata
  const currentPageKey = `page_${pdfPage}`;
  const currentPageData = metadata ? metadata[currentPageKey] : null;
  const pageTables = currentPageData?.tables || [];
  const pageBlocks = currentPageData?.text_blocks || [];
  const rawPage = currentPageData?.raw_page_data;
  const pageWidth = rawPage?.width || 595.0;
  const pageHeight = rawPage?.height || 842.0;

  // Zoom handlers
  const handleZoomIn = () => setZoom(Math.min(zoom + 0.15, 2.5));
  const handleZoomOut = () => setZoom(Math.max(zoom - 0.15, 0.6));
  const handlePrevPage = () => { if (pdfPage > 1) setPdfPage(pdfPage - 1); };
  const handleNextPage = () => { if (pdfPage < pdfTotalPages) setPdfPage(pdfPage + 1); };

  const currentDocIdentifier = activeFile ? (activeFile.uuid || activeFile.name) : null;
  const pdfFileUrl = currentDocIdentifier 
    ? `${API_BASE}/api/documents/${encodeURIComponent(currentDocIdentifier)}/file#page=${pdfPage}&zoom=${Math.round(zoom * 100)}` 
    : "";

  return (
    <div className="h-full flex flex-col bg-white border-r border-gray-200 select-none">
      {/* Viewer Header */}
      <div className="flex items-center justify-between px-3 py-2 bg-white border-b border-gray-200">
        {/* Tab Switcher */}
        <div className="flex items-center gap-1 bg-gray-100 p-0.5 rounded border border-gray-200">
          <button
            onClick={() => setViewerTab("document")}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium transition-all ${
              viewerTab === "document"
                ? "bg-black text-white shadow-xs"
                : "text-gray-600 hover:text-black"
            }`}
          >
            <FileText size={13} />
            <span>Document</span>
            {docFiles.length > 0 && (
              <span className="px-1 py-0.2 bg-gray-200 text-gray-800 rounded text-[9px] font-mono">
                {docFiles.length}
              </span>
            )}
          </button>

          <button
            onClick={() => setViewerTab("video")}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium transition-all ${
              viewerTab === "video"
                ? "bg-black text-white shadow-xs"
                : "text-gray-600 hover:text-black"
            }`}
          >
            <Film size={13} />
            <span>Video</span>
            {videoFiles.length > 0 && (
              <span className="px-1 py-0.2 bg-gray-200 text-gray-800 rounded text-[9px] font-mono">
                {videoFiles.length}
              </span>
            )}
          </button>
        </div>

        {/* Center / Right controls */}
        <div className="flex items-center gap-2">
          {/* Document View Mode Switcher (PDF vs BBox Canvas) */}
          {viewerTab === "document" && activeFile && (
            <div className="flex items-center gap-1 bg-gray-100 p-0.5 rounded border border-gray-200">
              <button
                onClick={() => setDocMode("preview")}
                className={`px-2 py-0.5 rounded text-[11px] font-medium transition-all ${
                  docMode === "preview"
                    ? "bg-black text-white shadow-xs"
                    : "text-gray-600 hover:text-black"
                }`}
              >
                Document View
              </button>
              <button
                onClick={() => setDocMode("canvas")}
                className={`px-2 py-0.5 rounded text-[11px] font-medium transition-all flex items-center gap-1 ${
                  docMode === "canvas"
                    ? "bg-black text-white shadow-xs"
                    : "text-gray-600 hover:text-black"
                }`}
              >
                <Layers size={11} />
                <span>Layout & BBoxes</span>
              </button>
            </div>
          )}

          {/* File Selector Dropdown */}
          {viewerTab === "document" && docFiles.length > 1 && (
            <select
              value={activeFile?.name || ""}
              onChange={(e) => {
                const found = docFiles.find(f => f.name === e.target.value);
                if (found) setActiveFile(found);
              }}
              className="bg-white border border-gray-300 text-black text-xs rounded px-2 py-1 outline-none max-w-[130px] truncate"
            >
              {docFiles.map((f, i) => (
                <option key={i} value={f.name}>{f.name}</option>
              ))}
            </select>
          )}

          {viewerTab === "video" && videoFiles.length > 1 && (
            <select
              value={activeFile?.name || ""}
              onChange={(e) => {
                const found = videoFiles.find(f => f.name === e.target.value);
                if (found) setActiveFile(found);
              }}
              className="bg-white border border-gray-300 text-black text-xs rounded px-2 py-1 outline-none max-w-[130px] truncate"
            >
              {videoFiles.map((f, i) => (
                <option key={i} value={f.name}>{f.name}</option>
              ))}
            </select>
          )}

          {viewerTab === "document" && (
            <div className="flex items-center gap-1 bg-gray-100 rounded border border-gray-200 px-1 py-0.5">
              <button
                onClick={handlePrevPage}
                disabled={pdfPage <= 1}
                className="p-1 text-gray-500 hover:text-black disabled:opacity-30 rounded"
                title="Previous Page"
              >
                <ChevronLeft size={14} />
              </button>
              <span className="text-xs text-black font-mono px-1">
                {pdfPage}/{pdfTotalPages}
              </span>
              <button
                onClick={handleNextPage}
                disabled={pdfPage >= pdfTotalPages}
                className="p-1 text-gray-500 hover:text-black disabled:opacity-30 rounded"
                title="Next Page"
              >
                <ChevronRight size={14} />
              </button>

              <div className="w-[1px] h-3 bg-gray-300 mx-1" />

              <button
                onClick={handleZoomOut}
                className="p-1 text-gray-500 hover:text-black rounded"
                title="Zoom Out"
              >
                <ZoomOut size={13} />
              </button>
              <span className="text-[10px] text-gray-500 font-mono">
                {Math.round(zoom * 100)}%
              </span>
              <button
                onClick={handleZoomIn}
                className="p-1 text-gray-500 hover:text-black rounded"
                title="Zoom In"
              >
                <ZoomIn size={13} />
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Main Viewer Body */}
      <div 
        ref={containerRef}
        className="flex-1 overflow-auto bg-gray-50 p-2 flex items-center justify-center relative"
      >
        {/* DOCUMENT MODE */}
        {viewerTab === "document" && (
          <div className="w-full h-full flex flex-col items-center justify-center">
            {!activeFile ? (
              <div className="flex flex-col items-center justify-center h-full text-center p-6 space-y-1.5">
                <FileText size={24} className="text-gray-300 stroke-1 mx-auto" />
                <p className="text-gray-400 text-xs font-mono">No document selected</p>
              </div>
            ) : docMode === "preview" ? (
              /* REAL PDF PREVIEW (Full Fidelity Native PDF Rendering) */
              <div className="w-full h-full flex flex-col items-center justify-center p-1 bg-gray-50">
                <iframe
                  src={pdfFileUrl}
                  className="w-full h-full border border-gray-300 rounded shadow-xs bg-white"
                  title={activeFile.name}
                />
              </div>
            ) : (
              /* EXTRACTED LAYOUT & SPATIAL BBOX OVERLAY */
              <div 
                className="relative bg-white shadow-sm border border-gray-300 rounded-sm transition-transform duration-150 origin-top overflow-hidden my-auto"
                style={{
                  width: `${pageWidth * zoom}px`,
                  height: `${pageHeight * zoom}px`,
                  transformOrigin: "top center"
                }}
              >
                {loadingMeta ? (
                  <div className="p-8 text-center text-xs text-gray-400 font-mono">
                    Loading layout coordinates...
                  </div>
                ) : (
                  <>
                    {/* High-Resolution Rendered Document Page Image */}
                    <img
                      key={`page-img-${currentDocIdentifier}-${pdfPage}`}
                      src={`${API_BASE}/api/documents/${encodeURIComponent(currentDocIdentifier)}/page/${pdfPage}/image`}
                      alt={`Page ${pdfPage}`}
                      className="absolute inset-0 w-full h-full object-contain pointer-events-none select-none z-10"
                      onError={(e) => {
                        e.target.style.display = 'none';
                        const fb = document.getElementById(`fallback-doc-text-${pdfPage}`);
                        if (fb) fb.style.display = 'flex';
                      }}
                    />

                    {/* Fallback Structured View if Page Image Fails */}
                    <div 
                      id={`fallback-doc-text-${pdfPage}`}
                      className="hidden w-full h-full p-8 text-gray-900 font-sans relative flex-col justify-between overflow-auto"
                      style={{ minHeight: `${pageHeight * zoom}px` }}
                    >
                      {/* Page header */}
                      <div className="border-b border-gray-200 pb-1.5 mb-3 flex justify-between items-center text-[10px] font-mono text-gray-400">
                        <span>{activeFile.name}</span>
                        <span>Page {pdfPage} of {pdfTotalPages}</span>
                      </div>

                      {/* Render Extracted Text Blocks and Tables */}
                      <div className="space-y-3 flex-1">
                        {pageTables.map((tb, i) => (
                          <div 
                            key={i} 
                            className="my-2 p-2 bg-white border border-gray-300 rounded overflow-x-auto"
                          >
                            <div className="flex items-center gap-1 text-[11px] font-mono text-black font-semibold mb-1.5">
                              <TableIcon size={12} />
                              <span>{tb.table_id || `Table ${i+1}`}</span>
                            </div>
                            <table className="min-w-full text-xs border-collapse">
                              {tb.headers && tb.headers.length > 0 && (
                                <thead>
                                  <tr className="bg-gray-100">
                                    {tb.headers.map((h, hi) => (
                                      <th key={hi} className="p-1 border border-gray-300 text-left font-semibold text-black text-[10px]">
                                        {h}
                                      </th>
                                    ))}
                                  </tr>
                                </thead>
                              )}
                              <tbody>
                                {(tb.rows || []).slice(0, 10).map((r, ri) => (
                                  <tr key={ri} className={ri % 2 === 0 ? "bg-white" : "bg-gray-50"}>
                                    {r.map((cell, ci) => (
                                      <td key={ci} className="p-1 border border-gray-300 text-gray-800 font-mono text-[10px]">
                                        {cell}
                                      </td>
                                    ))}
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        ))}

                        {pageBlocks.map((blk, i) => (
                          <p key={i} className="text-xs text-gray-900 leading-relaxed font-sans">
                            {blk.text}
                          </p>
                        ))}

                        {!pageTables.length && !pageBlocks.length && currentPageData?.text && (
                          <pre className="text-xs text-gray-900 whitespace-pre-wrap font-sans">
                            {currentPageData.text}
                          </pre>
                        )}
                      </div>

                      {/* Page Footer */}
                      <div className="border-t border-gray-200 pt-1.5 mt-3 text-center">
                        <span className="text-[10px] text-gray-400 font-mono">{pdfPage}</span>
                      </div>
                    </div>
                  </>
                )}

                {/* SVG BOUNDING BOX OVERLAY LAYER */}
                <svg
                  className="absolute inset-0 pointer-events-none w-full h-full z-20"
                  viewBox={`0 0 ${pageWidth} ${pageHeight}`}
                  preserveAspectRatio="none"
                >
                  {/* Subtle border for detected tables */}
                  {pageTables.map((tb, idx) => {
                    const [x0, y0, x1, y1] = tb.bbox || [0, 0, 0, 0];
                    const w = Math.max(x1 - x0, 10);
                    const h = Math.max(y1 - y0, 10);
                    return (
                      <rect
                        key={`tab-${idx}`}
                        x={x0}
                        y={y0}
                        width={w}
                        height={h}
                        fill="rgba(0, 0, 0, 0.02)"
                        stroke="#9ca3af"
                        strokeWidth="1"
                        strokeDasharray="3 3"
                      />
                    );
                  })}

                  {/* ACTIVE CITATION BOUNDING BOX */}
                  {activeHighlight && activeHighlight.page === pdfPage && (
                    <g>
                      {(() => {
                        const [x0, y0, x1, y1] = activeHighlight.bbox || [50, 150, 450, 240];
                        const w = Math.max(x1 - x0, 20);
                        const h = Math.max(y1 - y0, 15);
                        const labelText = activeHighlight.label || "Source";
                        const badgeWidth = Math.max(80, Math.min(w, labelText.length * 6.8 + 14));

                        return (
                          <>
                            {/* High-contrast solid bounding box */}
                            <rect
                              x={x0}
                              y={y0}
                              width={w}
                              height={h}
                              fill="rgba(0, 0, 0, 0.08)"
                              stroke="#000000"
                              strokeWidth="2.5"
                              rx="2"
                            />
                            {/* Citation label badge */}
                            <rect
                              x={x0}
                              y={Math.max(y0 - 18, 2)}
                              width={badgeWidth}
                              height={16}
                              fill="#000000"
                              rx="2"
                            />
                            <text
                              x={x0 + 5}
                              y={Math.max(y0 - 6, 14)}
                              fill="#ffffff"
                              fontSize="9"
                              fontWeight="600"
                              fontFamily="monospace"
                            >
                              {labelText}
                            </text>
                          </>
                        );
                      })()}
                    </g>
                  )}
                </svg>
              </div>
            )}
          </div>
        )}

        {/* VIDEO MODE */}
        {viewerTab === "video" && (
          <div className="w-full h-full flex flex-col items-center justify-center p-3 overflow-auto">
            {(!activeFile || !isVideo(activeFile)) && videoFiles.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center p-6 space-y-1.5">
                <Film size={24} className="text-gray-300 stroke-1 mx-auto" />
                <p className="text-gray-400 text-xs font-mono">No video uploaded or registered in this session</p>
              </div>
            ) : (() => {
              const currentVideo = (activeFile && isVideo(activeFile)) ? activeFile : videoFiles[0];
              const ytId = getYouTubeId(currentVideo?.source_url || currentVideo?.name);
              const seekSec = activeVideoSeek?.seconds || 0;
              const videoFileUrl = `${API_BASE}/api/videos/${encodeURIComponent(currentVideo?.uuid || currentVideo?.name)}/file`;

              return (
                <div className="w-full max-w-3xl bg-white rounded-lg border border-gray-300 shadow-sm flex flex-col overflow-hidden my-auto">
                  {/* Video Player Header */}
                  <div className="bg-gray-50 px-3 py-2 border-b border-gray-200 flex justify-between items-center gap-2">
                    <div className="flex items-center gap-2 min-w-0 flex-1">
                      <Film size={14} className="text-gray-600 flex-shrink-0" />
                      <span className="text-xs font-medium text-black truncate" title={currentVideo?.name}>
                        {currentVideo?.name}
                      </span>
                    </div>

                    <div className="flex items-center gap-2 flex-shrink-0">
                      {ytId && (
                        <div className="flex items-center gap-1 bg-gray-200 p-0.5 rounded text-[11px]">
                          <button
                            onClick={() => setPlayerMode("youtube")}
                            className={`px-2 py-0.5 rounded font-mono transition-all ${
                              playerMode === "youtube"
                                ? "bg-red-600 text-white shadow-xs font-semibold"
                                : "text-gray-700 hover:text-black"
                            }`}
                          >
                            YouTube
                          </button>
                          <button
                            onClick={() => setPlayerMode("native")}
                            className={`px-2 py-0.5 rounded font-mono transition-all ${
                              playerMode === "native"
                                ? "bg-black text-white shadow-xs font-semibold"
                                : "text-gray-700 hover:text-black"
                            }`}
                          >
                            Local MP4
                          </button>
                        </div>
                      )}

                      {activeVideoSeek && (
                        <button
                          onClick={() => {
                            if (videoRef.current) {
                              videoRef.current.currentTime = seekSec;
                              videoRef.current.play().catch(() => {});
                            }
                          }}
                          className="flex items-center gap-1 text-[11px] bg-emerald-600 hover:bg-emerald-700 text-white px-2 py-0.5 rounded font-mono transition-colors"
                          title="Seek to cited timestamp"
                        >
                          <span>🎯 {activeVideoSeek.timestamp}</span>
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Player Frame */}
                  <div className="w-full bg-black flex items-center justify-center relative aspect-video">
                    {ytId && playerMode === "youtube" ? (
                      <iframe
                        key={`yt-${ytId}-${seekSec}`}
                        src={`https://www.youtube-nocookie.com/embed/${ytId}?start=${seekSec}&autoplay=1`}
                        title={currentVideo?.name}
                        className="w-full h-full border-0"
                        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                        allowFullScreen
                      />
                    ) : (
                      <video
                        ref={videoRef}
                        controls
                        autoPlay
                        playsInline
                        className="w-full h-full object-contain"
                        src={videoFileUrl}
                      >
                        Your browser does not support HTML5 video streaming.
                      </video>
                    )}
                  </div>

                  {/* Video Attribution Info Bar */}
                  <div className="bg-gray-50 px-3 py-2 border-t border-gray-200 flex items-center justify-between text-xs text-gray-600 font-mono">
                    <div className="flex items-center gap-2">
                      <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                      <span>{activeVideoSeek ? `Cited at ${activeVideoSeek.timestamp}` : "Ready"}</span>
                    </div>
                    {ytId && (
                      <a
                        href={`https://youtu.be/${ytId}?t=${seekSec}`}
                        target="_blank"
                        rel="noreferrer"
                        className="text-blue-600 hover:underline flex items-center gap-1"
                      >
                        Open on YouTube ↗
                      </a>
                    )}
                  </div>
                </div>
              );
            })()}
          </div>
        )}
      </div>

      {/* Footer Status Bar */}
      <div className="px-3 py-1.5 bg-white border-t border-gray-200 flex items-center justify-between text-[11px] font-mono text-gray-500">
        <span>{activeFile ? activeFile.name : "Ready"}</span>
        {activeHighlight && (
          <span className="text-black font-medium">
            {activeHighlight.label} (Page {activeHighlight.page})
          </span>
        )}
      </div>
    </div>
  );
}
