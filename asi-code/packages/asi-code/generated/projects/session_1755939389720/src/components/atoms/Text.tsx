import React from 'react';

interface TextProps {
  /**
   * The content to be rendered inside the text element
   */
  children: React.ReactNode;
  /**
   * The semantic HTML tag to use for the text
   * @default 'p'
   */
  as?: 'p' | 'span' | 'div' | 'small' | 'strong' | 'em';
  /**
   * The size of the text
   * @default 'base'
   */
  size?: 'xs' | 'sm' | 'base' | 'lg' | 'xl';
  /**
   * The color variant of the text
   * @default 'default'
   */
  color?: 'default' | 'muted' | 'danger' | 'success' | 'accent';
  /**
   * Whether the text should be bold
   * @default false
   */
  bold?: boolean;
  /**
   * Additional CSS classes to apply
   */
  className?: string;
  /**
   * Accessibility role if needed
   */
  role?: string;
  /**
   * Custom id for DOM element
   */
  id?: string;
  /**
   * Text alignment
   * @default 'left'
   */
  align?: 'left' | 'center' | 'right';
}

/**
 * A modern, accessible text component with Tailwind CSS styling
 * Supports multiple variants, sizes, and semantic HTML elements
 */
const Text: React.FC<TextProps> = ({
  children,
  as: Tag = 'p',
  size = 'base',
  color = 'default',
  bold = false,
  className = '',
  role,
  id,
  align = 'left',
}) => {
  const baseClasses = 'font-normal leading-relaxed';

  const sizeClasses = {
    xs: 'text-xs',
    sm: 'text-sm',
    base: 'text-base',
    lg: 'text-lg',
    xl: 'text-xl',
  };

  const colorClasses = {
    default: 'text-gray-900 dark:text-gray-100',
    muted: 'text-gray-600 dark:text-gray-400',
    danger: 'text-red-600 dark:text-red-400',
    success: 'text-green-600 dark:text-green-400',
    accent: 'text-blue-600 dark:text-blue-400',
  };

  const alignClasses = {
    left: 'text-left',
    center: 'text-center',
    right: 'text-right',
  };

  const fontWeight = bold ? 'font-semibold' : '';

  const classes = [
    baseClasses,
    sizeClasses[size],
    colorClasses[color],
    alignClasses[align],
    fontWeight,
    className,
  ].filter(Boolean).join(' ');

  return (
    <Tag id={id} className={classes} role={role}>
      {children}
    </Tag>
  );
};

export default Text;