import React, { useState, useEffect } from 'react';

interface SidebarItem {
  label: string;
  href: string;
  icon?: React.ReactNode;
  ariaLabel?: string;
  children?: SidebarItem[];
}

interface SidebarProps {
  /**
   * Optional logo element to display at the top of the sidebar
   */
  logo?: React.ReactNode;
  /**
   * Array of navigation items to display in the sidebar
   */
  items: SidebarItem[];
  /**
   * Optional callback when a sidebar item is clicked
   */
  onItemClick?: (item: SidebarItem) => void;
  /**
   * Optional class name to customize styling
   */
  className?: string;
  /**
   * Whether the sidebar should be collapsible
   * @default false
   */
  collapsible?: boolean;
  /**
   * Initial state for collapsed view
   * @default false
   */
  defaultCollapsed?: boolean;
  /**
   * Optional header/title for the sidebar
   */
  title?: string;
}

/**
 * Sidebar component provides a vertical navigation menu for the application layout
 * Supports nested navigation items and optional collapsible behavior
 * Uses Tailwind CSS for responsive, modern styling with dark mode support
 */
const Sidebar: React.FC<SidebarProps> = ({
  logo,
  items,
  onItemClick,
  className = '',
  collapsible = false,
  defaultCollapsed = false,
  title,
}) => {
  const [collapsed, setCollapsed] = useState(defaultCollapsed);
  const [openSubmenus, setOpenSubmenus] = useState<Set<string>>(new Set());

  useEffect(() => {
    setCollapsed(defaultCollapsed);
  }, [defaultCollapsed]);

  const toggleSidebar = () => {
    if (collapsible) {
      setCollapsed((prev) => !prev);
    }
  };

  const toggleSubmenu = (label: string) => {
    const newOpenSubmenus = new Set(openSubmenus);
    if (newOpenSubmenus.has(label)) {
      newOpenSubmenus.delete(label);
    } else {
      newOpenSubmenus.add(label);
    }
    setOpenSubmenus(newOpenSubmenus);
  };

  const handleItemClick = (item: SidebarItem) => {
    if (item.children && item.children.length > 0) {
      toggleSubmenu(item.label);
      return;
    }

    onItemClick?.(item);
  };

  const renderMenuItems = (menuItems: SidebarItem[], level = 0) => {
    return (
      <ul className={level === 0 ? 'space-y-1' : 'space-y-0.5 mt-1'}>
        {menuItems.map((item) => {
          const hasChildren = item.children && item.children.length > 0;
          const isOpen = openSubmenus.has(item.label);

          return (
            <li key={item.href}>
              <div className="flex items-center">
                <button
                  type="button"
                  onClick={() => handleItemClick(item)}
                  aria-expanded={hasChildren ? isOpen : undefined}
                  aria-haspopup={hasChildren}
                  aria-label={item.ariaLabel || item.label}
                  className={`
                    flex items-center w-full px-3 py-2 text-sm font-medium rounded-lg
                    transition-all duration-200
                    ${
                      level === 0
                        ? 'text-gray-700 hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-gray-700'
                        : 'text-gray-600 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-800'
                    }
                    ${level > 0 ? 'pl-6' : ''}
                    ${hasChildren ? 'justify-between' : ''}
                  `}
                >
                  <div className="flex items-center truncate">
                    {item.icon && (
                      <span
                        className={`${
                          level === 0 ? 'mr-3' : 'mr-2'
                        } flex-shrink-0 text-gray-500 dark:text-gray-400`}
                      >
                        {item.icon}
                      </span>
                    )}
                    {!collapsed && <span className="truncate">{item.label}</span>}
                  </div>
                  {hasChildren && !collapsed && (
                    <svg
                      className={`ml-1 h-4 w-4 text-gray-500 transition-transform duration-200 dark:text-gray-400 ${
                        isOpen ? 'rotate-180' : ''
                      }`}
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                      xmlns="http://www.w3.org/2000/svg"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M19 9l-7 7-7-7"
                      />
                    </svg>
                  )}
                </button>
              </div>
              {hasChildren && isOpen && !collapsed && (
                <div className="mt-1 border-l-2 border-gray-200 dark:border-gray-700">
                  {renderMenuItems(item.children, level + 1)}
                </div>
              )}
            </li>
          );
        })}
      </ul>
    );
  };

  return (
    <aside
      className={`
        bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700
        transition-all duration-300 ease-in-out flex flex-col
        ${collapsible ? (collapsed ? 'w-16' : 'w-64') : 'w-64'}
        ${className}
      `}
      aria-label="Sidebar"
    >
      <div className="flex items-center justify-between h-16 px-4 border-b border-gray-200 dark:border-gray-700">
        {logo && (
          <div
            className={`${
              collapsed ? 'mx-auto' : 'flex items-center'
            } transition-opacity duration-200`}
          >
            {React.isValidElement(logo) ? logo : null}
          </div>
        )}
        {title && !collapsed && (
          <h2 className="text-lg font-semibold text-gray-800 dark:text-white truncate">
            {title}
          </h2>
        )}
        {collapsible && (
          <button
            type="button"
            onClick={toggleSidebar}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            className="p-2 text-gray-500 rounded-lg hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
          >
            <svg
              className={`h-5 w-5 transition-transform duration-200 ${
                collapsed ? 'rotate-180' : ''
              }`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M11 19l-7-7 7-7m8 14l-7-7 7-7"
              />
            </svg>
          </button>
        )}
      </div>
      <div className="flex-1 overflow-y-auto overflow-x-hidden p-3">
        {!collapsed ? (
          <nav aria-label="Sidebar navigation">{renderMenuItems(items)}</nav>
        ) : (
          <div className="flex flex-col items-center space-y-3 mt-4">
            {items.map((item) => (
              <button
                key={item.href}
                title={item.label}
                onClick={() => handleItemClick(item)}
                aria-label={item.ariaLabel || item.label}
                className="flex items-center justify-center w-10 h-10 rounded-lg text-gray-700 hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-gray-800 transition-colors duration-200"
              >
                {item.icon}
              </button>
            ))}
          </div>
        )}
      </div>
    </aside>
  );
};

export default Sidebar;