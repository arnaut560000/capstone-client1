document.querySelectorAll('[data-print]').forEach(button => button.addEventListener('click', () => window.print()));
document.querySelectorAll('form[data-confirm]').forEach(form => form.addEventListener('submit', event => {
  if (!window.confirm(form.dataset.confirm)) event.preventDefault();
}));
const birthdate = document.getElementById('birthdate');
birthdate?.addEventListener('input', () => {
  const date = new Date(birthdate.value + 'T00:00:00');
  const today = new Date();
  let age = today.getFullYear() - date.getFullYear();
  if (today.getMonth() < date.getMonth() || (today.getMonth() === date.getMonth() && today.getDate() < date.getDate())) age--;
  document.getElementById('calculated-age').value = Number.isFinite(age) && age >= 0 ? age + ' years old' : '';
});
let previewUrl;
document.getElementById('photo-input')?.addEventListener('change', event => {
  const file = event.target.files[0];
  if (!file) return;
  if (file.size > 2 * 1024 * 1024 || !['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
    alert('Choose a JPG, PNG or WebP image smaller than 2 MB.'); event.target.value = ''; return;
  }
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  previewUrl = URL.createObjectURL(file);
  const image = document.createElement('img'); image.src = previewUrl; image.alt = 'Profile photo preview'; image.className = 'avatar large-avatar';
  document.getElementById('photo-preview').replaceChildren(image);
});
