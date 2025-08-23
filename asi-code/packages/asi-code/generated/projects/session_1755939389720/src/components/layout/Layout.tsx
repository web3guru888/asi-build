import React from 'react';

import Header from './Header';
import Footer from './Footer';
import Navbar from './Navbar';
import Sidebar from './Sidebar';

interface LayoutProps {
  /**
   * The main content to be rendered within the layout
   */
  children: React.ReactNode;
  /**
   * Optional header title
   * @default 'My Application'
   */
  title?: string;
  /**
   * Optional header subtitle
   */
  subtitle?: string;
  /**
   * Optional copyright text passed to Footer
   * @default '© 2025 Your Company. All rights reserved.'
   */
  copyright?: string;
  /**
   * Logo element to pass to Navbar
   */
  logo?: React.ReactNode;
  /**
   * Navigation items for the Navbar
   */
  navItems?: {
    label: string;
    href: string;
    ariaLabel?: string;
  }[];
  /**
   * Sidebar navigation items
   */
  sidebarItems?: {
    label: string;
    href: string;
    icon?: React.ReactNode;
    ariaLabel?: string;
    children?: {
      label: string;
      href: string;
      icon?: React.ReactNode;
      ariaLabel?: string;
    }[];
  }[];
  /**
   * Control whether sidebar is visible
   * @default true
   */
  showSidebar?: boolean;
  /**
   * Control whether navbar is visible
   * @default true
   */
  showNavbar?: boolean;
  /**
   * Control whether header is visible
   * @default true
   */
  showHeader?: boolean;
  /**
   * Control whether footer is visible
   * @default true
   */
  showFooter?: boolean;
}

/**
 * Layout component provides a consistent structure for the application
 * Includes Header, Navbar, Sidebar, main content area, and Footer
 * Uses Tailwind CSS for responsive, modern styling
 */
const Layout: React.FC<LayoutProps> = ({
  children,
  title = 'My Application',
  subtitle,
  copyright = '© 2025 Your Company. All rights reserved.',
  logo,
  navItems = [],
  sidebarItems = [],
  showSidebar = true,
  showNavbar = true,
  showHeader = true,
  showFooter = true,
}) => {
  // State for mobile menu toggle in navbar
  const [isMobileMenuOpen, setIsMobileMenuOpen] = React.useState(false);

  // Close mobile menu when clicking a nav item
  const handleNavItemClick = () => {
    setIsMobileMenuOpen(false);
  };

  // Handle window resize to auto-close mobile menu on larger screens
  React.useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth >= 768 && isMobileMenuOpen) {
        setIsMobileMenuOpen(false);
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [isMobileMenuOpen]);

  return (
    <div className="flex flex-col min-h-screen bg-gray-50 text-gray-900">
      {/* Navbar */}
      {showNavbar && (
        <Navbar
          logo={logo}
          items={navItems}
          isMobileMenuOpen={isMobileMenuOpen}
          onMobileMenuToggle={() =>
            setIsMobileMenuOpen((prev) => !prev)
          }
          onNavItemClick={handleNavItemClick}
        />
      )}

      <div className="flex flex-1">
        {/* Sidebar */}
        {showSidebar && (
          <Sidebar items={sidebarItems} onLinkClick={handleNavItemClick} />
        )}

        {/* Main Content Area */}
        <main
          className={`flex-1 transition-all duration-300 ${
            showSidebar ? 'md:ml-64' : ''
          }`}
        >
          {/* Header */}
          {showHeader && (
            <Header title={title} subtitle={subtitle} />
          )}

          {/* Page Content */}
          <div className="p-6">
            {children}
          </div>
        </main>
      </div>

      {/* Footer */}
      {showFooter && <Footer copyright={copyright} />}
    </div>
  );
};

export default Layout;