# PC_Workman Landing Page

Modern, SEO-optimized landing page for PC_Workman - an AI-powered system monitoring and optimization tool.
**Version:** 2.0.0
**Style:** Dark mode, minimalist design
**Framework:** Vanilla HTML/CSS/JavaScript
-
## Project Structure
```
docs/
├── index.html                      # Main landing page
├── index_en.html                   # Main landing page EN
├── /ASSETS
|   ├── /CSS
|       ├── styles.css              # Stylesheet (dark theme, responsive)
|       ├── story-button.css        # Style
|   ├── /JS
|       ├── script.js               # Interactive features (quiz, accordion, animations)
|   ├── /IMAGES...
|
|
|
├── story.html              # Build in public story page
├── story-button.css        # Story button styles
├── sitemap.xml            
└── README.md               # This file
```
-
## Features

### Design
- **Dark-first theme** with neon accents (#00FF99, #00D9FF, #FF0066)
- **X (Twitter) inspired** left sticky sidebar navigation
- **Responsive design** with mobile-first approach
- **Geometric icon system** - Custom CSS shapes with animations
- **Smooth scroll** with active section highlighting
- **Parallax effects** on hero background

### Interactive Elements
- **Typing animation** in hero section with blinking cursor
- **Interactive quiz** demonstrating hck_GPT AI capabilities
- **FAQ accordion** with expand/collapse functionality
- **Newsletter signup forms** (story section + footer)
- **Mobile menu toggle** for responsive navigation
- **Konami Code easter egg** for engaged users

### SEO Optimization
- **Schema.org markup** (SoftwareApplication, Organization, FAQPage)
- **Open Graph tags** for social media sharing
- **Twitter Cards** for enhanced X previews
- **Semantic HTML5** structure
- **Meta tags** with targeted keywords
- **Mobile-first indexing** ready
-

-

## Technical Details

### Responsive Breakpoints
- **Desktop:** 1200px+ (full sidebar)
- **Tablet:** 768px-1199px (compact sidebar)
- **Mobile:** <768px (hamburger menu)

### Color Scheme
Edit CSS variables in `styles.css`:

```css
:root {
    --neon-green: #00FF99;
    --neon-cyan: #00D9FF;
    --neon-red: #FF0066;
    --dark-bg: #0A192F;
}
```

### Adding Quiz Responses

Edit `quizResponses` object in `script.js`:

```javascript
'keyword': {
    answer: 'Your AI response here...',
    suggestions: [
        'Suggestion 1',
        'Suggestion 2'
    ]
}
```

### Adding New Sections

1. Add `<section id="new-section">` in `index.html`
2. Add navigation link in sidebar `<nav>`
3. Style in `styles.css`
4. Section auto-highlights on scroll

-

## Performance

### Optimizations
- Lazy loading for images
- DNS prefetch for external resources
- GPU-accelerated CSS animations
- Minified production assets recommended

### Analytics Recommendations
- Bounce rate target: <50%
- Time on page target: >2 minutes
- Track: CTA clicks, quiz submissions, newsletter signups
- Monitor scroll depth to optimize content placement

-

## Browser Support

- Chrome/Edge: Latest 2 versions
- Opera: Latest 5 versions
- Firefox: Latest 2 versions
- Safari: Latest 2 versions
- Mobile browsers: iOS Safari 12+, Chrome Mobile

-

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

-

## License

MIT License - See [LICENSE](LICENSE) file for details

-

## Links

- **GitHub Repository:** [PC_Workman](https://github.com/HuckleR2003)

-

## Support

For issues or questions:
- Open an issue on GitHub
- Contact: marcin.firmuga.s@gmail.com
