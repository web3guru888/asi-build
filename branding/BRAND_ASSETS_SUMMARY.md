# ASI Alliance Brand Assets Summary

## Quick Reference

### 🎨 Brand Colors
- **Primary Green**: `#96ea8c` (ASI Green)
- **Secondary Cyan**: `#8be8da` (ASI Cyan)
- **Dark**: `#202124` (Text)
- **Light**: `#ffffff` (Background)

### 🖼️ Logo Files
- **Main Logo**: `/branding/images/logos/logo.svg` (21KB)
- **Mobile Logo**: `/branding/images/logos/mobile-logo.svg` (1.6KB)

### 🌐 Favicon Set
- 32×32px: `/branding/images/favicons/cropped-favicon-32x32.png`
- 180×180px: `/branding/images/favicons/cropped-favicon-180x180.png` (iOS)
- 192×192px: `/branding/images/favicons/cropped-favicon-192x192.png` (Android)

### 📱 Product Showcase Images

#### ASI Core Products
1. **ASI-1 Mini** (1.7MB) - The world's first Web3 LLM for agentic AI
   - Path: `/branding/images/products/asi1-mini.png`
   
2. **ASI API** (259KB) - Developer API visualization
   - Path: `/branding/images/products/asi-api-full.png`
   
3. **ASI Wallet** (506KB) - Token management interface
   - Path: `/branding/images/products/asi-wallet-full.png`

#### Platform Images
- **Agentverse** - Agent development platform (3 screenshots)
  - `/branding/images/products/agentverse-1.png`
  - `/branding/images/products/agentverse-2.png`
  - `/branding/images/products/agentverse-3.png`

### 🖼️ Hero & Backgrounds
- **Alliance Hero Banner** (679KB): `/branding/images/hero/alliance-hero.png`
- **Tech Background** (JPG): `/branding/images/hero/tech-background.jpg`
- **Foam Texture** (768KB): `/branding/images/misc/foam-background.png`

## File Organization

```
branding/
├── images/
│   ├── logos/          # 2 files (SVG logos)
│   ├── favicons/       # 3 files (PNG icons)
│   ├── products/       # 9 files (Product images)
│   ├── hero/           # 2 files (Banner images)
│   └── misc/           # 1 file (Background texture)
├── scrape/             # Full website mirror (301 files, 25MB)
├── ASI_BRAND_GUIDE.md  # Complete brand guidelines
├── SCRAPING_REPORT.md  # Website scraping details
└── BRAND_ASSETS_SUMMARY.md # This file

Total Brand Assets: 17 organized image files + complete website mirror
```

## Quick Implementation

### Add Logo to README
```markdown
![ASI Alliance](branding/images/logos/logo.svg)
```

### Use in HTML
```html
<link rel="icon" href="/branding/images/favicons/cropped-favicon-32x32.png">
<img src="/branding/images/logos/logo.svg" alt="ASI Alliance">
```

### Apply Brand Colors
```css
:root {
  --asi-green: #96ea8c;
  --asi-cyan: #8be8da;
  --asi-dark: #202124;
  --asi-light: #ffffff;
}
```

## Typography
- **Primary Font**: FavoritPro (Book, Medium, Regular)
- **Secondary Font**: Open Sans (Light, Regular, SemiBold, Bold)
- **Font Files**: Available in `/branding/scrape/superintelligence.io/wp-content/uploads/2025/01/`

## Next Steps
1. ✅ Logos organized and ready for use
2. ✅ Product images available for documentation
3. ✅ Hero images for presentations
4. ✅ Complete color palette extracted
5. ⏳ Consider creating a brand style guide PDF
6. ⏳ Generate icon font from SVG assets
7. ⏳ Create social media templates

---

*ASI:BUILD Branding Resources - Ready for Implementation*
*Last Updated: 2025-08-21*