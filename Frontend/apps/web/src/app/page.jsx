"use client";

import { Link } from "react-router-dom";

import { useEffect } from "react";
import {
  Sparkles,
  Upload,
  MessageSquare,
  Brain,
  ArrowRight,
} from "lucide-react";

export default function HomePage() {
  useEffect(() => {
    // Initialize theme on load
    document.documentElement.classList.add("dark");
  }, []);

  const navigateTo = (path) => {
    window.location.href = path;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-black to-purple-900">
      {/* Hero Section */}
      <div className="relative overflow-hidden">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
          {/* Header */}
          <nav className="flex justify-between items-center mb-20">
            <div className="flex items-center gap-2">
              <Sparkles className="text-purple-500" size={32} />
              <h1 className="text-3xl font-bold text-white">ExplainX</h1>
            </div>

            <div className="flex gap-4">
              <Link
                to="/login"
                className="px-6 py-2 text-white hover:text-purple-400 transition-colors"
              >
                Login
              </Link>

              <Link
                to="/signup"
                className="px-6 py-2 bg-gradient-to-r from-purple-600 to-pink-600 
                          hover:from-purple-700 hover:to-pink-700 
                          text-white rounded-lg transition-all font-medium"
              >
                Sign Up
              </Link>
            </div>
          </nav>



          {/* Hero Content */}
          <div className="text-center space-y-8 mb-20">
            <div className="inline-block">
              <div className="flex items-center gap-2 bg-purple-900/30 border border-purple-500/30 rounded-full px-4 py-2 mb-6">
                <Sparkles size={16} className="text-purple-400" />
                <span className="text-purple-300 text-sm font-medium">
                  Multimodal RAG System
                </span>
              </div>
            </div>

            <h2 className="text-5xl md:text-7xl font-bold text-white mb-6">
              Welcome To{" "}
              <span className="bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
                ExplainX
              </span>
            </h2>

            <p className="text-xl md:text-2xl text-gray-300 max-w-3xl mx-auto">
              Upload videos, PDFs, presentations, or documents and get
              intelligent answers using advanced AI. Powered by Whisper, YOLOv8,
              OCR, and Gemini 2.5 Flash.
            </p>

            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center pt-8">
              <button
                onClick={() => navigateTo("/chat")}
                className="group px-8 py-4 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white rounded-xl transition-all font-semibold text-lg flex items-center gap-2 shadow-lg"
              >
                Get Started
                <ArrowRight
                  size={20}
                  className="group-hover:translate-x-1 transition-transform"
                />
              </button>
              <button
                onClick={() => navigateTo("/chat")}
                className="px-8 py-4 border border-purple-500 hover:bg-purple-900/30 text-white rounded-xl transition-all font-semibold text-lg"
              >
                Try Demo
              </button>
            </div>
          </div>

          {/* Features Grid */}
          <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            <div className="bg-gray-800/50 backdrop-blur-lg border border-gray-700 rounded-2xl p-6 hover:border-purple-500/50 transition-all">
              <div className="w-12 h-12 bg-purple-600/20 rounded-lg flex items-center justify-center mb-4">
                <Upload className="text-purple-400" size={24} />
              </div>
              <h3 className="text-white text-xl font-bold mb-2">
                Upload Anything
              </h3>
              <p className="text-gray-400">
                Support for videos, PDFs, PowerPoint, Word documents, images,
                and more. Any file type accepted.
              </p>
            </div>

            <div className="bg-gray-800/50 backdrop-blur-lg border border-gray-700 rounded-2xl p-6 hover:border-purple-500/50 transition-all">
              <div className="w-12 h-12 bg-pink-600/20 rounded-lg flex items-center justify-center mb-4">
                <Brain className="text-pink-400" size={24} />
              </div>
              <h3 className="text-white text-xl font-bold mb-2">
                AI Processing
              </h3>
              <p className="text-gray-400">
                Advanced extraction using Whisper for audio, YOLOv8 for objects,
                OCR for text, and intelligent parsers.
              </p>
            </div>

            <div className="bg-gray-800/50 backdrop-blur-lg border border-gray-700 rounded-2xl p-6 hover:border-purple-500/50 transition-all">
              <div className="w-12 h-12 bg-blue-600/20 rounded-lg flex items-center justify-center mb-4">
                <MessageSquare className="text-blue-400" size={24} />
              </div>
              <h3 className="text-white text-xl font-bold mb-2">
                Smart Answers
              </h3>
              <p className="text-gray-400">
                Ask questions and get accurate, context-aware answers powered by
                Gemini 2.5 Flash and ChromaDB RAG.
              </p>
            </div>
          </div>
        </div>

        {/* Background decoration */}
        {/* Background decoration */}
        <div className="absolute top-0 right-0 w-96 h-96 bg-purple-500 rounded-full filter blur-3xl opacity-10 -z-10 pointer-events-none"></div>
        <div className="absolute bottom-0 left-0 w-96 h-96 bg-pink-500 rounded-full filter blur-3xl opacity-10 -z-10 pointer-events-none"></div>

      </div>
    </div>
  );
}
