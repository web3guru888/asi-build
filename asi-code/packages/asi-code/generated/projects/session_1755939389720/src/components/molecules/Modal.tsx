import React from 'react';

interface ModalProps extends React.HTMLAttributes<HTMLDivElement> {
  /**
   * The open state of the modal.
   */
  isOpen: boolean;
  /**
   * Function to be called when the modal is closed.
   */
  onClose: () => void;
  /**
   * The title of the modal.
   */
  title?: string;
  /**
   * The content of the modal.
   */
  children: React.ReactNode;
  /**
   * Optional footer content, such as action buttons.
   */
  footer?: React.ReactNode;
  /**
   * Optional additional class names.
   */
  className?: string;
  /**
   * If true, clicking outside the modal will close it.
   * @default true
   */
  closeOnOutsideClick?: boolean;
  /**
   * If true, the modal will include a close button in the header.
   * @default true
   */
  showCloseButton?: boolean;
}

/**
 * A modern, accessible modal component built with React and Tailwind CSS.
 */
const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  children,
  footer,
  className = '',
  closeOnOutsideClick = true,
  showCloseButton = true,
  ...props
}) => {
  if (!isOpen) return null;

  // Handle background click
  const handleBackgroundClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget && closeOnOutsideClick) {
      onClose();
    }
  };

  // Handle keyboard events
  React.useEffect(() => {
    const handleEscKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscKey);
    return () => {
      document.removeEventListener('keydown', handleEscKey);
    };
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center w-full h-full bg-black bg-opacity-50"
      onClick={handleBackgroundClick}
      role="dialog"
      aria-modal="true"
      aria-labelledby={title ? 'modal-title' : undefined}
    >
      <div
        className={`relative w-full max-w-lg p-6 mx-4 bg-white rounded-lg shadow-xl dark:bg-gray-800 sm:mx-0 ${className}`}
        {...props}
      >
        {/* Header */}
        {(title || showCloseButton) && (
          <div className="flex items-start justify-between mb-4">
            {title && (
              <h3
                id="modal-title"
                className="text-lg font-semibold text-gray-900 dark:text-white"
              >
                {title}
              </h3>
            )}
            {showCloseButton && (
              <button
                type="button"
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 dark:focus:ring-offset-gray-800 rounded-full"
                onClick={onClose}
                aria-label="Close modal"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="w-6 h-6"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            )}
          </div>
        )}

        {/* Body */}
        <div className="mb-4 text-sm text-gray-700 dark:text-gray-300">
          {children}
        </div>

        {/* Footer */}
        {footer && <div className="flex justify-end space-x-3">{footer}</div>}
      </div>
    </div>
  );
};

export default Modal;