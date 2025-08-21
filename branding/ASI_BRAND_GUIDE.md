# ASI Alliance Brand Guidelines
*Extracted from superintelligence.io*

## Brand Identity

### Logo Assets
- **Primary Logo**: `logo.svg` - Main brand mark
- **Mobile Logo**: `mobile-logo.svg` - Optimized for small screens
- **Favicon**: Available in 32x32, 180x180, and 192x192 PNG formats

### Color Palette

#### Primary Colors
- **ASI Green**: `#96ea8c` - Primary brand color (appears 132 times)
- **ASI Cyan**: `#8be8da` - Secondary accent color (32 occurrences)

#### Neutral Colors
- **White**: `#ffffff` / `#fff` - Primary background
- **Dark Gray**: `#202124` - Primary text color (106 occurrences)
- **Charcoal**: `#1f1f1f` - Dark backgrounds (72 occurrences)
- **Light Gray**: `#e5e5e5` - Borders and dividers (58 occurrences)
- **Medium Gray**: `#656565` - Secondary text (34 occurrences)
- **Subtle Gray**: `#888` - Tertiary elements (39 occurrences)

#### System Colors
- **Pure Black**: `#000000` / `#000` - High contrast elements
- **Dark**: `#333` - Alternative dark text
- **Light Border**: `#ddd` - UI borders (40 occurrences)

## Typography

### Primary Font Family
**FavoritPro** - Main brand typeface
- FavoritPro-Book (232KB OTF)
- FavoritPro-Medium (233KB OTF)
- FavoritPro-Regular (211KB TTF)

### Secondary Font Family
**Open Sans** - Supporting typeface
- OpenSans-Light
- OpenSans-Regular
- OpenSans-SemiBold
- OpenSans-Bold

### Font Usage
- Headlines: FavoritPro Medium
- Body Text: FavoritPro Book/Regular
- UI Elements: Open Sans (various weights)
- System Fallback: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto

## Visual Style

### Design System
- **Framework**: Material Design influences (skin-material.css)
- **Grid System**: Custom responsive grid (grid-system.css)
- **Animation Library**: Anime.js for smooth transitions
- **Carousel**: Flickity for content sliders

### UI Components
1. **Navigation**
   - Header with secondary nav support
   - Superfish menu system for dropdowns
   - Mobile-responsive hamburger menu

2. **Content Elements**
   - Post grids for blog/news
   - Fancy unordered lists for features
   - Milestone counters for statistics
   - Recent posts widgets

3. **Interactive Elements**
   - Contact Form 7 integration
   - Nectar Slider for hero sections
   - Social sharing buttons (Salient Social)
   - Event management (EventON)

### Responsive Breakpoints
Based on responsive.css analysis:
- Mobile: < 768px
- Tablet: 768px - 1024px
- Desktop: > 1024px
- Wide: > 1440px

## Brand Voice & Messaging

### Key Themes (from scraped content)
1. **Artificial Superintelligence** - Core mission
2. **Decentralization** - Architectural principle
3. **Open Source AGI** - Development philosophy
4. **Web3 Integration** - Technology stack
5. **Green Infrastructure** - Sustainability focus
6. **Developer-First** - Community approach

### Content Categories
- Technical announcements (ASI-1 Mini, Metta Kernel)
- Partnership news (CUDOS, SingularityNET)
- Community initiatives (Developer Forum, Grants)
- Infrastructure updates (Compute, Token)
- Research publications

## Digital Assets Structure

### WordPress Theme
- **Theme Name**: Salient (v17.0.7)
- **Style Approach**: Modular CSS with separate critical/non-critical styles
- **Performance**: Lazy loading images (EWWW Image Optimizer)
- **SEO**: Structured data support via wp-json

### JavaScript Libraries
- jQuery 3.7.1 with Migration support
- Waypoints for scroll triggers
- Transit for CSS3 transitions
- Hoverintent for improved hover UX
- TouchSwipe for mobile gestures

## Implementation Guidelines

### CSS Architecture
```
/css/
├── build/          # Compiled styles
├── fonts/          # Web fonts
├── grid-system/    # Layout foundation
├── responsive/     # Media queries
├── skin-material/  # Theme variations
└── third-party/    # Plugin styles
```

### Performance Optimizations
1. Critical CSS inline loading
2. Non-critical CSS deferred
3. Image lazy loading enabled
4. Font preloading for FavoritPro
5. Minified JavaScript bundles

## File Naming Conventions
- CSS: `{component}-{variant}.css?ver={version}`
- JS: `{library}.min.js?ver={version}`
- Images: Descriptive names with size variants
- Fonts: `{family}-{weight}.{format}`

## Brand Application Examples

### Website Header
- Logo placement: Left aligned
- Navigation: Right aligned with dropdown support
- Mobile: Collapsible menu with mobile logo

### Content Layout
- Max width containers for readability
- Card-based design for features
- Image-heavy layouts with lazy loading
- Prominent CTAs with brand colors

### Footer Structure
- Multi-column layout
- Social media integration
- Newsletter signup (Contact Form 7)
- Legal links (Terms of Service)

## Version Control
- Theme Version: 17.0.7
- WordPress Core: 6.8.2
- Last Update: 2025-08-21

---

*This brand guide is derived from the live superintelligence.io website and represents the current ASI Alliance visual identity.*