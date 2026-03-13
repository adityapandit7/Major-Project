import React, { useState } from 'react';

function ProcessingOptions({ onProcess, isProcessing }) {
  const [selectedOption, setSelectedOption] = useState('');

  const options = [
    { 
      id: 'refactor', 
      label: 'Refactor Only', 
      description: 'Clean up your code structure, improve readability, and fix formatting issues',
      icon: '🔄',
      badge: 'Popular',
      color: '#4299e1'
    },
    { 
      id: 'document', 
      label: 'Document Only', 
      description: 'Add comprehensive documentation, comments, and JSDoc annotations',
      icon: '📝',
      badge: 'Recommended',
      color: '#48bb78'
    },
    { 
      id: 'both', 
      label: 'Full Optimization', 
      description: 'Complete code transformation with both refactoring and documentation',
      icon: '⚡',
      badge: 'Best Value',
      color: '#9f7aea'
    }
  ];

  const handleSubmit = (e) => {
    e.preventDefault();
    if (selectedOption) {
      onProcess(selectedOption);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <div className="options-grid">
        {options.map((option) => (
          <label 
            key={option.id} 
            className={`option-card ${selectedOption === option.id ? 'selected' : ''}`}
          >
            <input
              type="radio"
              name="processingOption"
              value={option.id}
              checked={selectedOption === option.id}
              onChange={(e) => setSelectedOption(e.target.value)}
              disabled={isProcessing}
              style={{ display: 'none' }}
            />
            <span className="option-icon">{option.icon}</span>
            <h3>{option.label}</h3>
            <p>{option.description}</p>
            {option.badge && <span className="option-badge">{option.badge}</span>}
          </label>
        ))}
      </div>

      <div className="process-button-container">
        <button 
          type="submit" 
          disabled={!selectedOption || isProcessing}
          className="process-button"
        >
          {isProcessing ? (
            <>
              <span className="button-loader"></span>
              Processing...
            </>
          ) : (
            'Process File'
          )}
        </button>
      </div>
    </form>
  );
}

export default ProcessingOptions;
