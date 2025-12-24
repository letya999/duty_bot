import React from 'react';

interface CardProps {
  className?: string;
  children: React.ReactNode;
}

export const Card: React.FC<CardProps> = ({ className = '', children }) => (
  <div className={`bg-white rounded-lg shadow-sm border border-gray-200 ${className}`}>
    {children}
  </div>
);

interface CardHeaderProps {
  className?: string;
  children: React.ReactNode;
}

export const CardHeader: React.FC<CardHeaderProps> = ({ className = '', children }) => (
  <div className={`px-6 py-4 border-b border-gray-200 ${className}`}>
    {children}
  </div>
);

interface CardBodyProps {
  className?: string;
  children: React.ReactNode;
}

export const CardBody: React.FC<CardBodyProps> = ({ className = '', children }) => (
  <div className={`px-6 py-4 ${className}`}>
    {children}
  </div>
);

interface CardFooterProps {
  className?: string;
  children: React.ReactNode;
}

export const CardFooter: React.FC<CardFooterProps> = ({ className = '', children }) => (
  <div className={`px-6 py-4 border-t border-gray-200 bg-gray-50 rounded-b-lg ${className}`}>
    {children}
  </div>
);
