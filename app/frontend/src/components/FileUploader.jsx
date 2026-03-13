import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';

function FileUploader({ onFileUpload }) {
  const onDrop = useCallback((acceptedFiles) => {
    if (acceptedFiles.length > 0) {
      onFileUpload(acceptedFiles[0]);
    }
  }, [onFileUpload]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: false,
    accept: {
      'text/*': ['.js', '.py', '.java', '.cpp', '.txt', '.html', '.css', '.json']
    }
  });

  return (
    <div 
      {...getRootProps()} 
      className={`upload-area ${isDragActive ? 'active' : ''}`}
    >
      <input {...getInputProps()} />
      <span className="upload-icon">{isDragActive ? '📂' : '📁'}</span>
      {isDragActive ? (
        <>
          <p className="upload-text">Drop your file here...</p>
          <p className="upload-hint">Release to upload</p>
        </>
      ) : (
        <>
          <p className="upload-text">Drag & drop your file here</p>
          <p className="upload-hint">or click to browse (JS, PY, JAVA, CPP, TXT, etc.)</p>
        </>
      )}
    </div>
  );
}

export default FileUploader;
