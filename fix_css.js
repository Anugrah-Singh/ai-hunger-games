const fs = require('fs');
let css = fs.readFileSync('frontend/src/styles.css', 'utf8');

// Fix 1: Workspace tablet layout. Change breakpoint for .workspace stacking to 900px
// We can just change all `max-width: 720px` and `max-width: 680px` to `max-width: 900px` for the workspace block.
// Let's replace the whole media query values
css = css.replace(/@media \(max-width: 680px\)/g, '@media (max-width: 900px)');
css = css.replace(/@media \(max-width: 720px\)/g, '@media (max-width: 900px)');

// Fix 2: Topbar actions flex-wrap and button text hiding.
// Let's modify `.topbar-actions { flex-wrap: wrap;`
css = css.replace(/\.topbar-actions \{\s*flex-wrap: wrap;/g, '.topbar-actions {\n    flex-wrap: nowrap;');

// Fix 3: Experiment list padding for horizontal scroll cut-off
// Find `.experiment-list { display: flex; overflow-x: auto;` or just append to the file
css += `
/* Responsive fixes */
@media (max-width: 500px) {
  .topbar-actions .primary-button {
    font-size: 0;
    padding: 0 10px;
  }
  .topbar-actions .primary-button svg {
    margin-right: 0;
  }
}

.experiment-list::after {
  content: "";
  flex: 0 0 12px;
}
`;

fs.writeFileSync('frontend/src/styles.css', css);
console.log("CSS updated!");
