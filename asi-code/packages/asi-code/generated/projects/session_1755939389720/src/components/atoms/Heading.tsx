import React from 'react';

interface HeadingProps {
  /**
   * The content to be rendered inside the heading
   */
  children: React.ReactNode;
  /**
   * The heading level (1-6)
   * @default 1
   */
  level?: 1 | 2 | 3 | 4 | 5 | 6;
  /**
   * Additional CSS classes to apply
   */
  className?: string;
  /**
   * If true, applies a more prominent visual style
   */
  prominent?: boolean;
  /**
   * Custom id for the heading element
   */
  id?: string;
}

/**
 * A flexible heading component with customizable levels and styling
 * Built with Tailwind CSS for modern, responsive designs
 */
const Heading: React.FC<HeadingProps> = ({
  children,
  level = 1,
  className = '',
  prominent = false,
  id,
}) => {
  const baseStyles = 'font-semibold tracking-tight';
  
  const levelStyles = {
    1: 'text-4xl md:text-5xl lg:text-6xl',
    2: 'text-3xl md:text-4xl lg:text-5xl',
    3: 'text-2xl md:text-3xl lg:text-4xl',
    4: 'text-xl md:text-2xl lg:text-3xl',
    5: 'text-lg md:text-xl lg:text-2xl',
    6: 'text-base md:text-lg lg:text-xl',
  };

  const prominentStyles = prominent
    ? 'bg-gradient-to-r from-slate-900 to-slate-700 bg-clip-text text-transparent dark:from-slate-100 dark:to-slate-400'
    : '';

  const combinedClassName = `${baseStyles} ${levelStyles[level]} ${prominentStyles} ${className}`.trim();

  const HeadingTag = `h${level}` as keyof JSX.IntrinsicElements;

  return (
    <HeadingTag id={id} className={combinedClassName}>
      {children}
    </HeadingTag>
  );
};

export default Heading;