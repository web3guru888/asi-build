import React from 'react';

/**
 * FooterProps defines the props interface for the Footer component
 */
interface FooterProps {
  /**
   * Optional copyright text to display
   * @default '© 2025 Your Company. All rights reserved.'
   */
  copyright?: string;
  /**
   * Optional array of footer links
   */
  links?: Array<{
    label: string;
    url: string;
    ariaLabel?: string;
  }>;
  /**
   * Optional callback for when a link is clicked
   */
  onLinkClick?: (url: string, label: string) => void;
}

/**
 * Footer component displays the application footer with copyright information and optional navigation links
 * Uses Tailwind CSS for styling and follows accessible web practices
 */
const Footer: React.FC<FooterProps> = ({
  copyright = '© 2025 Your Company. All rights reserved.',
  links = [],
  onLinkClick,
}) => {
  const handleLinkClick = (url: string, label: string) => {
    try {
      if (onLinkClick) {
        onLinkClick(url, label);
      }
    } catch (error) {
      console.error('Error handling footer link click:', error);
    }
  };

  return (
    <footer
      className="bg-gray-50 dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800"
      role="contentinfo"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex flex-col md:flex-row justify-between items-center">
          {/* Copyright Text */}
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-4 md:mb-0">
            {copyright}
          </p>

          {/* Footer Links */}
          {links.length > 0 && (
            <nav
              aria-label="Footer navigation"
              className="flex flex-wrap justify-center gap-6"
            >
              {links.map((link, index) => (
                <a
                  key={index}
                  href={link.url}
                  aria-label={link.ariaLabel || `Visit ${link.label}`}
                  onClick={(e) => {
                    e.preventDefault();
                    handleLinkClick(link.url, link.label);
                  }}
                  className="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300 transition-colors duration-200 no-underline"
                >
                  {link.label}
                </a>
              ))}
            </nav>
          )}
        </div>

        {/* Optional: Back to top button for long pages */}
        <button
          type="button"
          aria-label="Back to top"
          onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
          className="mt-6 text-xs text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300 transition-colors duration-200 focus:outline-none focus:underline"
        >
          Back to top ↑
        </button>
      </div>
    </footer>
  );
};

export default Footer;