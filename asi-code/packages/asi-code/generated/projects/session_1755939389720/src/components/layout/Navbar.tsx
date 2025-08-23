import React, { useState } from 'react';

interface NavItem {
  label: string;
  href: string;
  ariaLabel?: string;
}

interface NavbarProps {
  /**
   * Optional logo element to display on the left side
   */
  logo?: React.ReactNode;
  /**
   * List of navigation items to display in the navbar
   * @default []
   */
  navItems?: NavItem[];
  /**
   * Optional action button on the right side of the navbar
   */
  actionButton?: React.ReactNode;
  /**
   * Optional CSS class name for additional styling
   */
  className?: string;
  /**
   * Callback function when a nav item is clicked
   */
  onNavClick?: (href: string) => void;
}

/**
 * Navbar component provides a responsive navigation bar for the application
 * Features include mobile hamburger menu, accessible navigation, and customizable branding
 * Uses Tailwind CSS for styling with dark mode support
 *
 * @example
 * <Navbar
 *   logo={<Logo />}
 *   navItems={[
 *     { label: 'Home', href: '/' },
 *     { label: 'About', href: '/about' },
 *   ]}
 *   actionButton={<Button>Sign In</Button>}
 * />
 */
const Navbar: React.FC<NavbarProps> = ({
  logo,
  navItems = [],
  actionButton,
  className = '',
  onNavClick,
}) => {
  const [isMenuOpen, setIsMenuOpen] = useState<boolean>(false);

  const handleNavClick = (href: string) => {
    onNavClick?.(href);
    setIsMenuOpen(false);
  };

  const toggleMenu = () => {
    setIsMenuOpen((prev) => !prev);
  };

  return (
    <nav
      className={`bg-white dark:bg-gray-900 fixed w-full z-50 top-0 left-0 border-b border-gray-200 dark:border-gray-700 ${className}`}
      role="navigation"
      aria-label="Main navigation"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center">
            {logo ? (
              <div className="flex-shrink-0" data-testid="navbar-logo">
                {logo}
              </div>
            ) : null}
            <div className="hidden md:block">
              <div className="ml-10 flex items-center space-x-4">
                {navItems.map((item) => (
                  <a
                    key={item.href}
                    href={item.href}
                    className="text-gray-800 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 px-3 py-2 rounded-md text-sm font-medium transition-colors duration-200"
                    aria-label={item.ariaLabel || item.label}
                    onClick={(e) => {
                      e.preventDefault();
                      handleNavClick(item.href);
                    }}
                  >
                    {item.label}
                  </a>
                ))}
              </div>
            </div>
          </div>
          <div className="flex items-center">
            {actionButton && (
              <div className="hidden md:block" data-testid="navbar-action">
                {actionButton}
              </div>
            )}
            <div className="-mr-2 flex md:hidden">
              <button
                type="button"
                className="inline-flex items-center justify-center p-2 rounded-md text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500"
                aria-expanded={isMenuOpen}
                aria-label="Main menu"
                aria-controls="mobile-menu"
                onClick={toggleMenu}
              >
                <span className="sr-only">Open main menu</span>
                <svg
                  className={`${isMenuOpen ? 'hidden' : 'block'} h-6 w-6`}
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 6h16M4 12h16M4 18h16"
                  />
                </svg>
                <svg
                  className={`${isMenuOpen ? 'block' : 'hidden'} h-6 w-6`}
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Mobile menu, show/hide based on menu state */}
      <div
        className={`${isMenuOpen ? 'block' : 'hidden'} md:hidden`}
        id="mobile-menu"
      >
        <div className="px-4 pt-2 pb-3 space-y-1 bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700">
          {navItems.map((item) => (
            <a
              key={item.href}
              href={item.href}
              className="block px-3 py-2 rounded-md text-base font-medium text-gray-800 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors duration-200"
              aria-label={item.ariaLabel || item.label}
              onClick={(e) => {
                e.preventDefault();
                handleNavClick(item.href);
              }}
            >
              {item.label}
            </a>
          ))}
          {actionButton && (
            <div className="mt-2 md:hidden" data-testid="navbar-action-mobile">
              {actionButton}
            </div>
          )}
        </div>
      </div>
    </nav>
  );
};

export default Navbar;