'use strict';
// CSP blocks inline handlers, so confirmation prompts are wired here.
document.addEventListener('submit', (event) => {
  const message = event.target.dataset && event.target.dataset.confirm;
  if (message && !window.confirm(message)) event.preventDefault();
});
