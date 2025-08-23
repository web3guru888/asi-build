import React, { useState } from 'react';

interface ImageProps {
  /**
   * The image source URL
   */
  src: string;
  /**
   * The alternative text for accessibility
   */
  alt: string;
  /**
   * The width of the image
   * @default 'auto'
   */
  width?: string | number;
  /**
   * The height of the image
   * @default 'auto'
   */
  height?: string | number;
  /**
   * Additional CSS classes for styling
   */
  className?: string;
  /**
   * Callback function triggered when the image loads successfully
   */
  onLoad?: () => void;
  /**
   * Callback function triggered when the image fails to load
   */
  onError?: () => void;
  /**
   * Determines if the image should be loaded lazily
   * @default false
   */
  loading?: 'lazy' | 'eager';
  /**
   * Defines how the image should be resized to fit its container
   * @default 'cover'
   */
  objectFit?: 'contain' | 'cover' | 'fill' | 'scale-down' | 'none';
  /**
   * Defines the horizontal alignment of the image
   * @default 'left'
   */
  align?: 'left' | 'center' | 'right';
}

/**
 * A customizable image component with error handling and loading states
 */
const Image: React.FC<ImageProps> = ({
  src,
  alt,
  width = 'auto',
  height = 'auto',
  className = '',
  onLoad,
  onError,
  loading = 'eager',
  objectFit = 'cover',
  align = 'left',
}) => {
  const [isLoaded, setIsLoaded] = useState(false);
  const [hasError, setHasError] = useState(false);

  const handleLoad = () => {
    setIsLoaded(true);
    onLoad?.();
  };

  const handleError = () => {
    setHasError(true);
    onError?.();
  };

  const getImageAlignmentClass = () => {
    switch (align) {
      case 'center':
        return 'mx-auto';
      case 'right':
        return 'ml-auto';
      case 'left':
      default:
        return 'mr-auto';
    }
  };

  return (
    <img
      src={src}
      alt={alt}
      width={typeof width === 'number' ? width : undefined}
      height={typeof height === 'number' ? height : undefined}
      style={{
        width: typeof width === 'string' ? width : undefined,
        height: typeof height === 'string' ? height : undefined,
        objectFit,
      }}
      className={`
        ${className}
        ${getImageAlignmentClass()}
        ${isLoaded ? 'opacity-100' : 'opacity-0'}
        ${hasError ? 'hidden' : ''}
        transition-opacity duration-300 ease-in-out
      `.trim()}
      loading={loading}
      onLoad={handleLoad}
      onError={handleError}
      aria-hidden={hasError}
    />
  );
};

export default Image;