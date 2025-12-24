import React from 'react';
import { AlertCircle, CheckCircle, Info, X } from 'lucide-react';

interface AlertProps {
  type: 'success' | 'error' | 'warning' | 'info';
  message: string;
  onClose?: () => void;
}

export const Alert: React.FC<AlertProps> = ({ type, message, onClose }) => {
  const typeClasses = {
    success: {
      bg: 'bg-green-50',
      border: 'border-green-200',
      icon: <CheckCircle className="text-green-600" size={20} />,
      text: 'text-green-800',
    },
    error: {
      bg: 'bg-red-50',
      border: 'border-red-200',
      icon: <AlertCircle className="text-red-600" size={20} />,
      text: 'text-red-800',
    },
    warning: {
      bg: 'bg-yellow-50',
      border: 'border-yellow-200',
      icon: <AlertCircle className="text-yellow-600" size={20} />,
      text: 'text-yellow-800',
    },
    info: {
      bg: 'bg-blue-50',
      border: 'border-blue-200',
      icon: <Info className="text-blue-600" size={20} />,
      text: 'text-blue-800',
    },
  };

  const classes = typeClasses[type];

  return (
    <div className={`${classes.bg} border ${classes.border} rounded-lg p-4 flex items-start gap-3`}>
      {classes.icon}
      <p className={`flex-1 ${classes.text}`}>{message}</p>
      {onClose && (
        <button
          onClick={onClose}
          className={`${classes.text} hover:opacity-70`}
        >
          <X size={20} />
        </button>
      )}
    </div>
  );
};
