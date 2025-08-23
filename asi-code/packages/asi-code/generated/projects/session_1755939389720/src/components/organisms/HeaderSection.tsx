import React from 'react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';

interface HeaderSectionProps {
  title: string;
  subtitle?: string;
  searchPlaceholder?: string;
  onSearch?: (value: string) => void;
  ctaText?: string;
  onCtaClick?: () => void;
  className?: string;
}

const HeaderSection: React.FC<HeaderSectionProps> = ({
  title,
  subtitle,
  searchPlaceholder = 'Search...',
  onSearch,
  ctaText,
  onCtaClick,
  className = '',
}) => {
  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    onSearch?.(value);
  };

  const handleCtaClick = () => {
    onCtaClick?.();
  };

  return (
    <header className={`px-6 py-8 md:py-12 bg-white dark:bg-gray-900 ${className}`}>
      <div className="max-w-7xl mx-auto">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
          <div className="flex-1">
            <h1 className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-white mb-2">
              {title}
            </h1>
            {subtitle && (
              <p className="text-lg text-gray-600 dark:text-gray-300">
                {subtitle}
              </p>
            )}
          </div>

          {(onSearch || onCtaClick) && (
            <div className="flex flex-col sm:flex-row gap-4 min-w-[280px]">
              {onSearch && (
                <Input
                  type="text"
                  placeholder={searchPlaceholder}
                  onChange={handleSearchChange}
                  className="flex-1 py-2 px-4 rounded-md border border-gray-300 dark:border-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:text-white"
                />
              )}
              {onCtaClick && ctaText && (
                <Button
                  onClick={handleCtaClick}
                  className="sm:min-w-fit px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-md transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-gray-900"
                >
                  {ctaText}
                </Button>
              )}
            </div>
          )}
        </div>
      </div>
    </header>
  );
};

export default HeaderSection;