"use client";

import { Link } from "react-router-dom";
import {
  Upload,
  MessageSquare,
  FileText,
  ArrowRight,
} from "lucide-react";

export default function HomePage() {
  const navigateTo = (path) => {
    window.location.href = path;
  };

  return (
    <div className="min-h-screen bg-white text-black antialiased">
      {/* Header */}
      <header className="border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex justify-between items-center">
          <div className="flex items-center gap-2">
            <span className="font-bold text-xl tracking-tight">ExplainX</span>
          </div>

          <div className="flex items-center gap-4">
            <Link
              to="/login"
              className="text-sm font-medium text-gray-700 hover:text-black transition-colors"
            >
              Login
            </Link>

            <Link
              to="/signup"
              className="px-4 py-2 bg-black text-white hover:bg-gray-800 rounded-md text-sm font-medium transition-colors"
            >
              Sign Up
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
        <div className="text-center space-y-6">
          <div className="inline-flex items-center gap-2 border border-gray-300 rounded-full px-3 py-1 text-xs font-semibold text-gray-700 uppercase tracking-wider">
            Multimodal Document & Video Intelligence
          </div>

          <h1 className="text-5xl sm:text-6xl font-extrabold tracking-tight text-black max-w-3xl mx-auto">
            Grounded Answers from Mixed-Format Documents
          </h1>

          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Extract, index, and query PDF documents, presentations, and video feeds with strict source attribution, spatial bounding boxes, and anti-hallucination guardrails.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center pt-6">
            <button
              onClick={() => navigateTo("/chat")}
              className="px-6 py-3 bg-black hover:bg-gray-800 text-white rounded-md text-sm font-medium flex items-center gap-2 transition-colors shadow-sm"
            >
              Open Workspace
              <ArrowRight size={16} />
            </button>
            <button
              onClick={() => navigateTo("/chat")}
              className="px-6 py-3 border border-gray-300 hover:bg-gray-50 text-black rounded-md text-sm font-medium transition-colors"
            >
              Try Demo
            </button>
          </div>
        </div>

        {/* Features Grid */}
        <div className="grid md:grid-cols-3 gap-6 mt-24">
          <div className="border border-gray-200 rounded-lg p-6 hover:border-gray-400 transition-colors">
            <div className="w-10 h-10 border border-gray-200 rounded-md flex items-center justify-center mb-4">
              <Upload size={20} className="text-black" />
            </div>
            <h2 className="text-base font-semibold text-black mb-1">
              Multi-Format Ingestion
            </h2>
            <p className="text-sm text-gray-600 leading-relaxed">
              Support for PDFs, PowerPoint presentations, and video lectures. Preserves spatial layout coordinates and table cell structures.
            </p>
          </div>

          <div className="border border-gray-200 rounded-lg p-6 hover:border-gray-400 transition-colors">
            <div className="w-10 h-10 border border-gray-200 rounded-md flex items-center justify-center mb-4">
              <FileText size={20} className="text-black" />
            </div>
            <h2 className="text-base font-semibold text-black mb-1">
              Spatial Attribution
            </h2>
            <p className="text-sm text-gray-600 leading-relaxed">
              Every factual statement links directly to its source with page number, element type, and bounding-box coordinates.
            </p>
          </div>

          <div className="border border-gray-200 rounded-lg p-6 hover:border-gray-400 transition-colors">
            <div className="w-10 h-10 border border-gray-200 rounded-md flex items-center justify-center mb-4">
              <MessageSquare size={20} className="text-black" />
            </div>
            <h2 className="text-base font-semibold text-black mb-1">
              Anti-Hallucination Guardrails
            </h2>
            <p className="text-sm text-gray-600 leading-relaxed">
              Strict verification gates trigger refusal when content cannot be directly proven from the ingested documents.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
