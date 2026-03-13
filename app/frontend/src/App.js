import React, { useState } from 'react';
import FileUploader from './components/FileUploader';
import ProcessingOptions from './components/ProcessingOptions';
import ResultDisplay from './components/ResultDisplay';
import './App.css';

function App() {
  const [uploadedFile, setUploadedFile] = useState(null);
  const [processingResult, setProcessingResult] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState(null);

  const handleFileUpload = (file) => {
    setUploadedFile(file);
    setProcessingResult(null);
    setError(null);
  };

  const handleProcessFile = async (option) => {
    if (!uploadedFile) {
      setError('Please upload a file first');
      return;
    }

    setIsProcessing(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', uploadedFile);
    formData.append('option', option);

    try {
      const response = await fetch('http://localhost:3001/api/process-file', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Processing failed');
      }

      const result = await response.json();
      setProcessingResult(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsProcessing(false);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(1) + ' MB';
  };

  return (
    <div className="App">
      {/* Navigation Bar */}
      <nav className="navbar">
        <div className="nav-container">
          <div className="logo">
            <span className="logo-icon">⚡</span>
            <span>CodeProcessor</span>
          </div>
          <div className="nav-links">
            <a href="#home">Home</a>
            <a href="#features">Features</a>
            <a href="#pricing">Pricing</a>
            <a href="#about">About</a>
            <a href="#contact" className="nav-button">Get Started</a>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="main-container">
        {/* Hero Section */}
        <div className="hero-section fade-in">
          <h1 className="hero-title">Transform Your Code Instantly</h1>
          <p className="hero-subtitle">
            Upload your file and let our AI-powered processor refactor, document, or optimize your code in seconds
          </p>
        </div>

        {/* Upload Card */}
        <div className="upload-card fade-in">
          <FileUploader onFileUpload={handleFileUpload} />
          
          {uploadedFile && (
            <div className="file-info-card">
              <div className="file-info-content">
                <span className="file-icon">📄</span>
                <div className="file-details">
                  <h3>Uploaded File</h3>
                  <p>{uploadedFile.name}</p>
                </div>
              </div>
              <span className="file-size">{formatFileSize(uploadedFile.size)}</span>
            </div>
          )}
        </div>

        {/* Options Section */}
        {uploadedFile && (
          <div className="options-section fade-in">
            <div className="section-title">
              <h2>Choose Your Processing Method</h2>
              <p>Select how you want to transform your code</p>
            </div>
            
            <ProcessingOptions 
              onProcess={handleProcessFile} 
              isProcessing={isProcessing}
            />
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="error-message fade-in">
            <span>⚠️</span>
            <span>{error}</span>
          </div>
        )}

        {/* Result Section */}
        {processingResult && (
          <div className="result-card fade-in">
            <ResultDisplay result={processingResult} />
          </div>
        )}
      </div>

      {/* Footer */}
      <footer className="footer">
        <div className="footer-content">
          <p>© 2026 CodeProcessor. All rights reserved.</p>
          <div className="footer-links">
            <a href="#privacy">Privacy Policy</a>
            <a href="#terms">Terms of Service</a>
            <a href="#contact">Contact Us</a>
            <a href="#docs">Documentation</a>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;