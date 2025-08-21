# ASI Alliance Brand Assets Inventory

## Overview
This directory contains all brand-related images extracted from superintelligence.io, organized by category for easy access and use across the ASI:BUILD project.

## Directory Structure

```
images/
├── logos/           # Primary brand logos
├── favicons/        # Favicon variants for web use
├── products/        # Product and feature images
├── hero/            # Hero and banner images
└── misc/            # Miscellaneous brand assets
```

## Asset Inventory

### 1. Logos (`/logos/`)
Primary brand identity assets for the ASI Alliance.

| File | Description | Format | Size | Usage |
|------|-------------|--------|------|-------|
| `logo.svg` | Main ASI Alliance logo | SVG | 21KB | Primary brand mark, headers, documentation |
| `mobile-logo.svg` | Mobile-optimized logo | SVG | 1.6KB | Mobile apps, responsive designs |

### 2. Favicons (`/favicons/`)
Web browser icons in multiple resolutions.

| File | Description | Dimensions | Size | Usage |
|------|-------------|------------|------|-------|
| `cropped-favicon-32x32.png` | Standard favicon | 32×32px | 1.1KB | Browser tabs, bookmarks |
| `cropped-favicon-180x180.png` | Apple Touch Icon | 180×180px | 5.8KB | iOS home screen |
| `cropped-favicon-192x192.png` | Android Chrome icon | 192×192px | 6.2KB | Android devices, PWA |

### 3. Product Images (`/products/`)
Images related to ASI Alliance products and services.

| File | Description | Size | Purpose |
|------|-------------|------|---------|
| **ASI Core Products** |
| `asi1-full.png` | ASI-1 product image | 33KB | ASI-1 announcements, documentation |
| `asi1-mini.png` | ASI-1 Mini LLM illustration | 1.7MB | ASI-1 Mini features, Web3 LLM content |
| `asi-api-full.png` | ASI API visualization | 259KB | API documentation, developer resources |
| `asi-wallet-full.png` | ASI Wallet interface | 506KB | Wallet features, token management |
| `asi-seo-full.png` | ASI SEO/branding image | 120KB | Marketing, SEO, social media |
| **Partner Products** |
| `cudo-compute.png` | CUDO Compute partnership | 218KB | Infrastructure, compute resources |
| **Agentverse Platform** |
| `agentverse-1.png` | Agentverse screenshot 1 | 126KB | Agent development platform |
| `agentverse-2.png` | Agentverse screenshot 2 | 82KB | Agent marketplace features |
| `agentverse-3.png` | Agentverse screenshot 3 | 130KB | Agent deployment interface |

### 4. Hero Images (`/hero/`)
Large banner and hero section images.

| File | Description | Dimensions | Size | Usage |
|------|-------------|------------|------|-------|
| `alliance-hero.png` | ASI Alliance hero banner | 900×604px | 679KB | Homepage hero, major announcements |

### 5. Miscellaneous (`/misc/`)
Additional brand and design assets.

| File | Description | Size | Usage |
|------|-------------|------|-------|
| `foam-background.png` | Abstract foam texture | 768KB | Background patterns, design elements |

## Usage Guidelines

### Logo Usage
- **Primary Logo**: Use `logo.svg` for all standard applications
- **Mobile Logo**: Use `mobile-logo.svg` for screens < 768px width
- **Minimum Size**: Logos should not be displayed smaller than 100px width
- **Clear Space**: Maintain clear space equal to the height of the 'A' in ASI around all logos

### Color Extraction
Based on the brand images, key colors include:
- **ASI Green**: Prominent in logos and UI elements
- **ASI Cyan**: Accent color in product interfaces
- **Dark backgrounds**: Used in product screenshots
- **White/Light**: Primary background color

### Image Optimization
All images have been preserved in their original quality. For web use:
1. Consider creating WebP versions for modern browsers
2. Use responsive images with srcset for different screen sizes
3. Implement lazy loading for product images
4. Optimize PNG files with tools like pngquant if needed

### File Naming Convention
- Logos: `{name}-logo.{ext}`
- Products: `{product-name}-{variant}.{ext}`
- Favicons: `{type}-favicon-{size}.{ext}`
- Hero: `{name}-hero.{ext}`

## Integration Examples

### HTML Logo Implementation
```html
<!-- Primary Logo -->
<img src="/branding/images/logos/logo.svg" alt="ASI Alliance" class="logo">

<!-- Responsive Logo -->
<picture>
  <source media="(max-width: 768px)" srcset="/branding/images/logos/mobile-logo.svg">
  <img src="/branding/images/logos/logo.svg" alt="ASI Alliance">
</picture>
```

### Favicon Implementation
```html
<link rel="icon" type="image/png" sizes="32x32" href="/branding/images/favicons/cropped-favicon-32x32.png">
<link rel="icon" type="image/png" sizes="192x192" href="/branding/images/favicons/cropped-favicon-192x192.png">
<link rel="apple-touch-icon" sizes="180x180" href="/branding/images/favicons/cropped-favicon-180x180.png">
```

### Product Image Gallery
```html
<div class="product-gallery">
  <img src="/branding/images/products/asi1-mini.png" alt="ASI-1 Mini">
  <img src="/branding/images/products/asi-api-full.png" alt="ASI API">
  <img src="/branding/images/products/asi-wallet-full.png" alt="ASI Wallet">
</div>
```

## Maintenance Notes

- **Source**: All images scraped from https://superintelligence.io on 2025-08-21
- **Original Paths**: Preserved in scrape folder at `superintelligence.io/wp-content/uploads/`
- **Updates**: Check the live website periodically for new brand assets
- **Backup**: Keep original scrape folder as source reference

## License & Usage Rights

These assets are property of the ASI Alliance and should be used in accordance with the organization's brand guidelines and intellectual property policies. Internal use only for ASI:BUILD project development.

---

*Last Updated: 2025-08-21*
*Part of ASI:BUILD Branding Resources*