# Superintelligence.io Website Scraping Report

## Summary
Successfully scraped the ASI Alliance website (superintelligence.io) for branding assets and content.

## Scraping Details

- **Date**: 2025-08-21
- **Website**: https://superintelligence.io
- **Total Files Downloaded**: 301
- **Total Size**: 25MB
- **Method**: wget with mirror, recursive download, and page requisites

## Content Structure

### Main Pages Scraped
- Homepage (index.html)
- About section
- Blog/News articles
- Products pages
- Community pages
- Developer Hub
- Infrastructure pages
- Research section
- Terms of Service
- Portfolio

### Blog/News Articles
- ASI 1 Mini Knowledge Graph Integration
- ASI Developer Forum
- ASI Token (FET)
- Artificial Superintelligence Alliance Token Migration
- Building Greener AI Infrastructure with CUDOS Intercloud
- ETHGlobal NYC Winners
- Fetch.ai ASI-1 Mini announcement
- Metta Kernel Decentralized AI
- Season 12 Ocean Zealy

### Asset Types Downloaded

#### WordPress Content (`/wp-content/`)
- **Themes**: Salient theme files including:
  - CSS stylesheets (grid system, responsive, skin-material)
  - JavaScript files (animations, smooth scroll, init scripts)
  - Font files (OpenSans, FavoritPro)
  
- **Plugins**:
  - Contact Form 7
  - Salient Nectar Slider
  - Salient Social
  - EventON
  - EWWW Image Optimizer
  - Salient Portfolio
  - Salient Core

- **Uploads** (2025):
  - Logo files (logo.svg, mobile-logo.svg)
  - Favicon images (32x32, 192x192, 180x180)
  - Font files (FavoritPro-Book, FavoritPro-Medium, FavoritPro-Regular)
  - Various content images

### Technical Assets
- **CSS Files**: 65+ stylesheets including:
  - Main theme styles
  - Plugin styles
  - Responsive layouts
  - Animation styles
  - Font Awesome icons

- **JavaScript Files**: 30+ scripts including:
  - jQuery and jQuery plugins
  - Anime.js for animations
  - Flickity carousel
  - Smooth scrolling
  - Form handling
  - Map integration

- **Images & Graphics**: 68+ files including:
  - PNG images
  - SVG logos and icons
  - Favicon variants
  - Content images

- **Fonts**: Multiple font formats:
  - OpenSans (Light, Regular, SemiBold, Bold)
  - FavoritPro (Book, Medium, Regular)
  - Web fonts (WOFF, TTF, OTF formats)

## Key Branding Elements Captured

1. **Logo Assets**:
   - Main logo: `/wp-content/uploads/2025/01/logo.svg`
   - Mobile logo: `/wp-content/uploads/2025/01/mobile-logo.svg`
   - Favicons in multiple sizes

2. **Typography**:
   - Primary font: FavoritPro family
   - Secondary font: OpenSans family
   - Complete font files in multiple formats

3. **Color Scheme & Styles**:
   - Material design skin CSS
   - Dynamic styles configuration
   - Theme color definitions

4. **UI Components**:
   - Navigation menus
   - Grid systems
   - Form styles
   - Animation libraries
   - Responsive breakpoints

## File Organization

```
superintelligence.io/
├── index.html (Homepage)
├── robots.txt
├── feed/ (RSS feeds)
├── about/ (About pages)
├── blog/ (Blog section)
├── products/ (Product pages)
├── community/ (Community section)
├── wp-content/
│   ├── themes/salient/ (Main theme)
│   ├── plugins/ (WordPress plugins)
│   └── uploads/2025/ (Media files)
├── wp-includes/ (WordPress core)
└── wp-json/ (REST API endpoints)
```

## Usage Notes

All scraped content is owned by the ASI Alliance and should be used in accordance with the organization's branding guidelines. This local copy provides:

1. **Offline access** to the website structure and content
2. **Branding reference** for consistent design implementation
3. **Asset library** for marketing and development purposes
4. **Technical reference** for website functionality

## Next Steps

1. Review and catalog all image assets for branding guidelines
2. Extract color palette from CSS files
3. Document typography specifications
4. Create brand asset library from scraped content
5. Analyze site structure for information architecture reference

---

*Scraping completed for ASI Alliance Build Team internal use*
*Date: 2025-08-21*