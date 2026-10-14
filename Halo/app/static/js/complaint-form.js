'use strict';
(() => {
  const prior = document.getElementById('previous_report');
  const followLabel = document.getElementById('followup_label');
  const followDetails = document.getElementById('follow_up_details');
  if (!prior || !followLabel || !followDetails) return;
  const toggleFollowup = () => {
    const show = prior.value === 'yes';
    followLabel.hidden = !show;
    followDetails.required = show;
  };
  prior.addEventListener('change', toggleFollowup);
  toggleFollowup();
})();


// Client-side upload size guard; server-side validation remains authoritative.
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('input[type="file"][data-max-bytes]').forEach(input => {
    input.addEventListener('change', () => {
      const max = Number(input.dataset.maxBytes);
      const file = input.files && input.files[0];
      if (file && file.size > max) {
        alert(`File is too large. Maximum allowed size is ${Math.round(max / 1024 / 1024)} MB.`);
        input.value = '';
      }
    });
  });
});
