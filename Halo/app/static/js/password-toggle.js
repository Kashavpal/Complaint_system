(() => {
  const field = document.getElementById('login-password');
  const button = document.getElementById('toggle-login-password');
  if (!field || !button) return;
  button.addEventListener('click', () => {
    const reveal = field.type === 'password';
    field.type = reveal ? 'text' : 'password';
    button.setAttribute('aria-pressed', String(reveal));
    button.setAttribute('aria-label', reveal ? 'Hide password' : 'Show password');
    button.setAttribute('title', reveal ? 'Hide password' : 'Show password');
    field.focus();
  });
})();
