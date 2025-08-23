Welcome to the Fonts directory of the Dog-Themed Website project!

This folder is designated for custom font files used across the website. Currently, this project utilizes web-safe fonts and SVG icons for dog-themed visuals, so no custom font files are included by default.

However, if you wish to add custom typography (e.g., a playful "Paw Font" or "Doggy Script"), you may include font files in this directory in the following formats:

- `.woff` and `.woff2` — Preferred modern web font formats
- `.ttf` — TrueType Font (widely supported)
- `.eot` — Legacy format for older IE versions
- `.svg` — Optional, for icon fonts (not recommended for body text)

📌 Best Practices:
- Always include `woff2` for better compression and performance.
- Use `@font-face` in `styles/main.css` to load custom fonts.
- Name fonts clearly (e.g., `DoggySans-Regular.woff2`, `BarkScript-Bold.woff`).
- Ensure proper licensing for any third-party fonts.

Example usage in CSS:
```css
@font-face {
  font-family: 'DoggyScript';
  src: url('../assets/fonts/DoggyScript-Regular.woff2') format('woff2'),
       url('../assets/fonts/DoggyScript-Regular.woff') format('woff');
  font-weight: normal;
  font-style: normal;
  font-display: swap;
}
```

🚫 Note: Avoid embedding large font files unnecessarily. For small icon-like text, prefer SVGs or CSS-styled elements.

For dog-themed visual text (like “WOOF!”), consider using animated SVG texts or icon substitutions instead.

For more details, refer to:
- `styles/main.css` — Font definitions and usage
- `scripts/utils/svg-generator.ts` — Dynamic SVG generation
- `assets/images/` — Current SVG icons (logo, pawprint, bone, dog icon)

You can always enhance the typographic experience using CSS animations, text-shadows, and SVG filters to match the playful dog theme! 🐶🐾