import React from 'react';

interface HeaderProps {
  title: string;
  subtitle?: string;
}

/**
 * Header component displays the main heading and optional subtitle for the application
 * Uses Tailwind CSS for styling with a modern, clean design
 */
const Header: React.FC<HeaderProps> = ({ title, subtitle }) => {
  return (
    <header className="w-full bg-white shadow-sm border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-gray-900 sm:text-4xl">{title}</h1>
          {subtitle && (
            <p className="mt-2 text-lg text-gray-600">{subtitle}</p>
          )}
        </div>
      </div>
    </header>
  );
};

Header.displayName = 'Header';

export default Header;