import React, { useState } from 'react';

function ResultDisplay({ result }) {
  const [copied, setCopied] = useState(false);

  const handleDownload = () => {
    const blob = new Blob([result.processedContent], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = result.fileName || 'processed-file.txt';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  };

  const handleOpenInVSCode = () => {
    const content = result.processedContent;
    const dataUrl = `data:text/plain;charset=utf-8,${encodeURIComponent(content)}`;
    window.open(dataUrl, '_blank');
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(result.processedContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <>
      <div className="result-header">
        <h2>Processing Complete! 🎉</h2>
        <span className="result-badge">Success</span>
      </div>

      {result.stats && (
        <div className="stats-grid">
          <div className="stat-item">
            <div className="stat-value">{result.stats.originalLines}</div>
            <div className="stat-label">Original Lines</div>
          </div>
          <div className="stat-item">
            <div className="stat-value">{result.stats.processedLines}</div>
            <div className="stat-label">Processed Lines</div>
          </div>
          <div className="stat-item">
            <div className="stat-value">+{result.stats.changes}</div>
            <div className="stat-label">Changes Made</div>
          </div>
          <div className="stat-item">
            <div className="stat-value">
              {((result.stats.processedLines - result.stats.originalLines) / result.stats.originalLines * 100).toFixed(1)}%
            </div>
            <div className="stat-label">Growth</div>
          </div>
        </div>
      )}

      <div className="result-summary">
        <p>{result.summary || 'Your file has been successfully processed and optimized!'}</p>
      </div>

      <div className="code-preview-container">
        <div className="preview-header">
          <div className="preview-title">
            <span>📄 Preview</span>
          </div>
          <div className="preview-actions">
            <button onClick={handleCopy} className="preview-action-btn">
              {copied ? '✅ Copied!' : '📋 Copy'}
            </button>
          </div>
        </div>
        <pre className="code-preview">
          {result.processedContent}
        </pre>
      </div>

      <div className="action-buttons">
        <button onClick={handleDownload} className="action-button download-button">
          <span>⬇️</span>
          Download File
        </button>
        <button onClick={handleOpenInVSCode} className="action-button vscode-button">
          <span>🔧</span>
          Open in VS Code
        </button>
      </div>

      <p style={{ textAlign: 'center', color: '#718096', marginTop: '1rem' }}>
        💡 The processed file will be downloaded. You can open it directly in VS Code or any text editor.
      </p>
    </>
  );
}

export default ResultDisplay;