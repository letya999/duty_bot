import React from 'react';

interface CardProps {
  className?: string;
  children: React.ReactNode;
}

export const Card: React.FC<CardProps> = ({ className = '', children }) => (
  <div className={`bg-white rounded-3xl shadow-xl border border-gray-100 overflow-hidden ${className}`}>
    {children}
  </div>
);

interface CardHeaderProps {
  className?: string;
  children: React.ReactNode;
}

export const CardHeader: React.FC<CardHeaderProps> = ({ className = '', children }) => (
  <div className={`px-8 py-6 border-b border-gray-50 flex items-center justify-between ${className}`}>
    {children}
  </div>
);

interface CardBodyProps {
  className?: string;
  children: React.ReactNode;
}

export const CardBody: React.FC<CardBodyProps> = ({ className = '', children }) => (
  <div className={`p-8 ${className}`}>
    {children}
  </div>
);

interface CardFooterProps {
  className?: string;
  children: React.ReactNode;
}

export const CardFooter: React.FC<CardFooterProps> = ({ className = '', children }) => (
  <div className={`px-8 py-6 border-t border-gray-50 bg-gray-50/50 ${className}`}>
    {children}
  </div>
);
